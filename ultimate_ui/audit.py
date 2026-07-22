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
                    "severity": sev, "id": cid, "file": path, "line": line_no,
                    "message": msg, "snippet": snippet,
                })

    findings.sort(key=lambda f: (order[f["severity"]], f["file"], f["line"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in order}
    report_lines = [f"{f['file']}:{f['line']} — [{f['severity']}] {f['message']}" for f in findings]
    return {
        "findings": findings,
        "counts": counts,
        "total": len(findings),
        "report": "\n".join(report_lines),
        "project_uses_shadcn": project_uses_shadcn,
    }
