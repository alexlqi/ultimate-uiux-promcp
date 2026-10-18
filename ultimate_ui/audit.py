"""UI audit: fetch the live Web Interface Guidelines and run deterministic heuristic
checks over source code. The heuristics catch the mechanical, unambiguous violations
(transition:all, icon buttons without labels, raw palette colors in shadcn projects,
missing focus-visible, hardcoded hex where tokens exist). Judgment-level review still
belongs to the model reading the guidelines resource — this tool does the grunt work
and hands back file:line findings.
"""
from __future__ import annotations

import re
import urllib.request

GUIDELINES_URL = "https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md"

__all__ = ["fetch_guidelines", "audit_source"]


def fetch_guidelines(timeout: float = 10.0) -> str:
    """Pull the current Vercel Web Interface Guidelines command prompt."""
    req = urllib.request.Request(GUIDELINES_URL, headers={"User-Agent": "ultimate-ui-design-mcp"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed trusted URL)
        return r.read().decode("utf-8", "replace")


# (severity, id, message, compiled regex, optional guard that must ALSO be present in file)
_CHECKS = [
    ("Critical", "a11y-icon-button",
     "icon-only button without an accessible name (add aria-label)",
     re.compile(r"<button(?![^>]*aria-label)[^>]*>\s*<(?:svg|[A-Z][A-Za-z]*Icon|Icon)\b"), None),
    ("Major", "motion-transition-all",
     "transition: all / transition-all animates layout; list transform/opacity instead",
     re.compile(r"transition:\s*all\b|\btransition-all\b"), None),
    ("Major", "motion-layout-anim",
     "animating layout property (width/height/top/left); prefer transform/opacity",
     re.compile(r"@keyframes[^}]*\b(?:width|height|top|left)\s*:", re.S), None),
    ("Major", "a11y-focus-removed",
     "focus outline removed without a visible replacement (:focus-visible / ring)",
     re.compile(r"outline:\s*none|outline-none"), re.compile(r"focus-visible|:focus-visible|ring-")),
    ("Minor", "shadcn-raw-palette",
     "raw Tailwind palette color in app code; use semantic tokens (bg-background, text-foreground…)",
     re.compile(r"\b(?:bg|text|border|ring)-(?:zinc|slate|gray|neutral|stone|red|blue|green|indigo|purple|violet)-\d{2,3}\b"), None),
    ("Minor", "hardcoded-hex",
     "hardcoded hex color in a component; promote to a token",
     re.compile(r"(?<![\w#])#[0-9a-fA-F]{6}\b"), None),
    ("Minor", "no-tabular-nums",
     "possible numeric table/figure without tabular-nums (verify alignment)",
     re.compile(r"toLocaleString\(|\.toFixed\("), None),
    ("Enhancement", "flat-shadow",
     "single-layer box-shadow; layered (ambient + direct) reads more natural",
     re.compile(r"box-shadow:\s*[^;,{]+;"), None),
]

# Taste "tells" (github.com/Leonxlnx/taste-skill, MIT): devices that make a page read as
# generated. Mechanical subset only — the judgment half lives in the `taste` knowledge stage.
_CHECKS += [
    ("Major", "tell-gradient-text",
     "gradient-filled headline text is a generated-page tell; use solid ink",
     re.compile(r"bg-clip-text|(?:-webkit-)?background-clip:\s*text"), None),
    ("Major", "tell-violet-gradient",
     "violet/indigo gradient is the default-AI palette; draw a palette from the subject instead",
     re.compile(r"\b(?:from|via|to)-(?:violet|indigo|purple|fuchsia)-\d{2,3}\b|"
                r"linear-gradient\([^)]*#(?:6366f1|8b5cf6|7c3aed|a855f7|4f46e5)", re.I), None),
    ("Minor", "tell-glass",
     "backdrop blur / glass panel; prefer an opaque surface one tone step from the ground",
     re.compile(r"\bbackdrop-blur(?:-\w+)?\b|backdrop-filter:\s*blur"), None),
    ("Minor", "tell-glow",
     "decorative glow shadow; flat tone steps read as more deliberate",
     re.compile(r"shadow-\[0_0_\d+px|box-shadow:\s*0\s+0\s+\d+px", re.I), None),
    ("Minor", "tell-eyebrow",
     "tiny tracked uppercase eyebrow label; fold it into the heading or delete it",
     re.compile(r"\buppercase\b[^\"'`]*\btracking-(?:wide|wider|widest)\b|"
                r"\btracking-(?:wide|wider|widest)\b[^\"'`]*\buppercase\b"), None),
    ("Minor", "tell-emoji-icon",
     "emoji used as an icon/bullet; use a real icon or words",
     re.compile("[🌀-🫿✅✨⚡⭐]"), None),
    ("Minor", "tell-bounce",
     "animate-bounce/ping is decorative motion; remove or tie it to a state change",
     re.compile(r"\banimate-(?:bounce|ping)\b"), None),
    ("Enhancement", "tell-default-font",
     "Inter as the only face is the generated-page default; choose a face for the subject",
     re.compile(r"font-family:\s*['\"]?Inter\b|fontFamily:\s*['\"]Inter\b"), None),
]

# Vercel react-best-practices / composition / react-native subset (github.com/vercel-labs/agent-skills,
# MIT): only rules a regex can decide. Priorities follow upstream (waterfalls, bundle size first).
_CHECKS += [
    ("Major", "react-effect-fetch",
     "fetch inside useEffect creates a client waterfall; fetch on the server or use SWR/React Query "
     "(client-swr-dedup, async-suspense-boundaries)",
     re.compile(r"useEffect\(\s*\(\)\s*=>\s*\{[^}]{0,300}\bfetch\(", re.S), None),
    ("Major", "react-barrel-import",
     "barrel import pulls the whole package into the bundle; import the specific path "
     "(bundle-barrel-imports)",
     re.compile(r"from\s+['\"](?:lodash|@mui/icons-material|@mui/material|react-icons)['\"]"), None),
    ("Minor", "react-sequential-await",
     "await inside a loop runs serially; use Promise.all for independent work (async-parallel)",
     re.compile(r"for\s*\([^)]*\)\s*\{[^}]{0,200}\bawait\b", re.S), None),
    ("Minor", "react-index-key",
     "array index as key breaks reconciliation when the list reorders (rerender-*)",
     re.compile(r"key=\{(?:i|idx|index)\}"), None),
    ("Critical", "a11y-div-click",
     "clickable <div> without a role/keyboard handler; use <button> or add role+tabIndex+onKeyDown",
     re.compile(r"<div(?![^>]*\brole=)[^>]*\bonClick="), None),
    ("Major", "a11y-img-alt",
     "<img> without alt text",
     re.compile(r"<img(?![^>]*\balt=)[^>]*>"), None),
    ("Minor", "perf-img-size",
     "<img> without width/height causes layout shift (or use next/image)",
     re.compile(r"<img(?![^>]*\bwidth=)(?![^>]*\bheight=)[^>]*\balt="), None),
    ("Minor", "react-dangerous-html",
     "dangerouslySetInnerHTML: ensure the input is sanitized",
     re.compile(r"dangerouslySetInnerHTML"), None),
    ("Major", "rn-scrollview-map",
     "ScrollView rendering a mapped list does not virtualize; use FlashList/FlatList "
     "(list-performance-virtualize)",
     re.compile(r"<ScrollView[^>]*>[^<]{0,80}\{[^}]{0,80}\.map\(", re.S), None),
    ("Enhancement", "rn-flatlist",
     "FlatList → FlashList for large lists (list-performance-virtualize)",
     re.compile(r"<FlatList\b"), None),
    ("Enhancement", "rn-touchable",
     "TouchableOpacity → Pressable (ui-pressable)",
     re.compile(r"<TouchableOpacity\b"), None),
]

# More Vercel agent-skills rules decidable by pattern (react-best-practices / react-native-skills).
_CHECKS += [
    ("Major", "react-falsy-and",
     "`{count && <X/>}` renders 0 for an empty list; use a ternary or a boolean (rendering-conditional-render)",
     re.compile(r"\{\s*[\w.]+\.length\s*&&\s*<"), None),
    ("Minor", "react-inline-component",
     "component defined inside another component remounts every render (rerender-no-inline-components)",
     re.compile(r"\n\s{2,}(?:const|function)\s+[A-Z]\w*\s*(?:=\s*\([^)]*\)\s*=>|\([^)]*\)\s*\{)[^\n]*\n[^\n]*return\s*\(?\s*<"),
     None),
    ("Minor", "react-scroll-passive",
     "scroll/touch/wheel listener without { passive: true } blocks scrolling (client-passive-event-listeners)",
     re.compile(r"addEventListener\(\s*['\"](?:scroll|touchstart|touchmove|wheel)['\"]\s*,[^)]*\)\s*;?(?<!passive: true\))"),
     None),
    ("Minor", "react-script-blocking",
     "<script src> without defer/async blocks parsing (rendering-script-defer-async)",
     re.compile(r"<script(?![^>]*\b(?:defer|async|type=['\"]module['\"]))[^>]*\bsrc="), None),
    ("Minor", "react-regexp-in-loop",
     "RegExp created inside a loop; hoist it (js-hoist-regexp)",
     re.compile(r"(?:for|while)\s*\([^)]*\)\s*\{[^}]{0,200}new RegExp\(", re.S), None),
    ("Minor", "react-sort-mutates",
     ".sort() mutates the array (props/state); use toSorted() (js-tosorted-immutable)",
     re.compile(r"\b(?:props|state)\.\w+\.sort\("), None),
    ("Major", "rn-text-outside-text",
     "string literal directly inside <View> crashes React Native; wrap it in <Text> (rendering-text-in-text-component)",
     re.compile(r"<View[^>/]*>\s*[A-Za-z][^<{\n]{2,}\s*</View>"), None),
    ("Minor", "rn-inline-style",
     "inline style object is re-created every render; use StyleSheet.create (ui-styling)",
     re.compile(r"<(?:View|Text|Pressable)\b[^>]*\bstyle=\{\{"), None),
]

# Flutter / Dart checks for the app verticals (Material 3 + Cupertino). Applied only to *.dart.
_DART_CHECKS = [
    ("Major", "dart-hardcoded-color",
     "hardcoded Color(0xFF...) in a widget; read it from Theme/ColorScheme or the AppTokens extension",
     re.compile(r"\bColor\(\s*0x[0-9a-fA-F]{6,8}\s*\)")),
    ("Minor", "dart-material-palette",
     "direct Colors.<name> bypasses the theme (and dark mode); use Theme.of(context).colorScheme",
     re.compile(r"\bColors\.(?!transparent\b|white\b|black\b)[a-z]+(?:\[\d+\]|\.shade\d+)?")),
    ("Major", "dart-small-target",
     "interactive widget sized below the 44pt (iOS) / 48dp (Android) touch floor",
     re.compile(r"(?:IconButton|GestureDetector|InkWell)[^;]{0,200}?(?:width|height|size):\s*(?:[1-3]\d|4[0-3])(?:\.\d+)?\b",
                re.S)),
    ("Major", "dart-nonlazy-list",
     "ListView(children: [...map(...)]) builds every row up front; use ListView.builder",
     re.compile(r"ListView\(\s*children:\s*[\w.]+\.map\(")),
    ("Minor", "dart-no-semantics",
     "Image without semanticLabel/excludeFromSemantics is invisible to screen readers",
     re.compile(r"\bImage\.(?:network|asset)\((?![^)]*(?:semanticLabel|excludeFromSemantics))[^)]*\)")),
    ("Minor", "dart-hardcoded-size",
     "magic font size in TextStyle; use the theme text styles / token scale",
     re.compile(r"TextStyle\([^)]*\bfontSize:\s*\d")),
    ("Enhancement", "dart-cupertino-in-material",
     "Platform idiom mix: Cupertino widgets in a MaterialApp tree (or vice versa) - use adaptive constructors",
     re.compile(r"\bCupertino(?:Button|Switch|AlertDialog)\b")),
]

# guard so shadcn-raw-palette only fires in projects that actually use shadcn tokens
_SHADCN_SIGNAL = re.compile(r"bg-background|text-foreground|--primary|shadcn|cn\(")


def audit_source(files: dict[str, str]) -> dict:
    """Run heuristics over {path: source} and return grouped findings.

    Returns findings sorted Critical->Enhancement with a per-severity count, matching the
    Vercel skill's terse file:line output convention.
    """
    order = {"Critical": 0, "Major": 1, "Minor": 2, "Enhancement": 3}
    findings: list[dict] = []
    project_uses_shadcn = any(_SHADCN_SIGNAL.search(src) for src in files.values())

    for path, src in files.items():
        lines = src.splitlines()
        if path.endswith(".dart"):
            # generated/handwritten theme + token files DEFINE colours; the literal rules target widgets
            is_theme = re.search(r"(?:theme|token|palette|colors?)", path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1], re.I)
            for sev, cid, msg, pat in _DART_CHECKS:
                if is_theme and cid in ("dart-hardcoded-color", "dart-material-palette"):
                    continue
                for m in pat.finditer(src):
                    line_no = src.count("\n", 0, m.start()) + 1
                    findings.append({
                        "severity": sev, "id": cid, "category": "dart", "file": path, "line": line_no,
                        "message": msg,
                        "snippet": lines[line_no - 1].strip()[:120] if line_no <= len(lines) else "",
                    })
            continue  # web heuristics (JSX/CSS/Tailwind) do not apply to Dart sources
        for sev, cid, msg, pat, guard in _CHECKS:
            if cid == "shadcn-raw-palette" and not project_uses_shadcn:
                continue
            for m in pat.finditer(src):
                # focus check: only flag if the guard is NOT present anywhere in the file
                if guard is not None and guard.search(src):
                    continue
                line_no = src.count("\n", 0, m.start()) + 1
                snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ""
                findings.append({
                    "severity": sev, "id": cid, "category": cid.split("-", 1)[0],
                    "file": path, "line": line_no,
                    "message": msg, "snippet": snippet,
                })

    findings.sort(key=lambda f: (order[f["severity"]], f["file"], f["line"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in order}
    by_category: dict[str, int] = {}
    for f in findings:
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1
    report_lines = [f"{f['file']}:{f['line']} — [{f['severity']}] {f['message']}" for f in findings]
    return {
        "findings": findings,
        "counts": counts,
        "by_category": by_category,
        "total": len(findings),
        "report": "\n".join(report_lines),
        "project_uses_shadcn": project_uses_shadcn,
    }
