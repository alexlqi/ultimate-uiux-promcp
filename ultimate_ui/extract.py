"""Extract design primitives from a public website's live DOM.

Uses Playwright (headless Chromium) to read *computed* styles — what's actually rendered,
not the source stylesheet. Near-identical colors are merged so you get the real palette,
not hundreds of noise shades. Output normalizes into the same TokenSpec shape the generator
consumes, so extraction flows straight into the pipeline.

Playwright is an optional dependency. If it's not installed, `can_extract` reports that
and `extract_tokens` raises a clear error instead of failing cryptically.
"""
from __future__ import annotations

import collections
import re

__all__ = ["playwright_available", "can_extract", "extract_tokens"]

_JS = r"""
() => {
  const els = Array.from(document.querySelectorAll('*')).slice(0, 4000);
  const colors = {}, bgs = {}, fonts = {}, sizes = {}, radii = {}, shadows = {}, spaces = {};
  const bump = (o, k) => { if (k) o[k] = (o[k] || 0) + 1; };
  for (const el of els) {
    const s = getComputedStyle(el);
    bump(colors, s.color);
    bump(bgs, s.backgroundColor);
    bump(fonts, s.fontFamily);
    bump(sizes, s.fontSize);
    bump(radii, s.borderRadius);
    if (s.boxShadow && s.boxShadow !== 'none') bump(shadows, s.boxShadow);
    for (const p of [s.paddingTop, s.paddingLeft, s.marginTop, s.gap]) bump(spaces, p);
  }
  const typo = {};
  for (const el of document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,a,button,label,small,code')) {
    const r = el.getBoundingClientRect(); if (!r.width || !el.textContent.trim()) continue;
    const s = getComputedStyle(el), k = el.tagName.toLowerCase();
    const row = typo[k] || (typo[k] = { n: 0, size: s.fontSize, weight: s.fontWeight,
      lh: s.lineHeight, ls: s.letterSpacing, family: s.fontFamily });
    row.n++;
  }
  return { colors, bgs, fonts, sizes, radii, shadows, spaces, typo };
}
"""


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def can_extract(url: str) -> dict:
    """Feasibility check (ProMCP can_do_*): is the URL well-formed and is Playwright present?"""
    ok_url = bool(re.match(r"^https?://[^\s]+\.[^\s]+", url))
    pw = playwright_available()
    reasons = []
    if not ok_url:
        reasons.append("URL must be an absolute http(s) URL to a public page")
    if not pw:
        reasons.append("Playwright not installed: run `pip install playwright && playwright install chromium`")
    return {"feasible": ok_url and pw, "url_ok": ok_url, "playwright": pw, "reasons": reasons}


def _rgb_key(css: str):
    m = re.search(r"rgba?\(([^)]+)\)", css)
    if not m:
        return None
    parts = [float(x) for x in re.split(r"[,\s/]+", m.group(1).strip()) if x]
    if len(parts) < 3:
        return None
    a = parts[3] if len(parts) > 3 else 1.0
    if a < 0.05:
        return None  # skip fully transparent
    return tuple(round(p) for p in parts[:3])


def _to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _merge_near(counter: collections.Counter, dist: int = 10):
    """Merge near-identical colors (Chebyshev distance in sRGB) keeping the most frequent."""
    items = counter.most_common()
    kept: list[tuple[tuple[int, int, int], int]] = []
    for rgb, n in items:
        for i, (krgb, kn) in enumerate(kept):
            if max(abs(a - b) for a, b in zip(rgb, krgb)) <= dist:
                kept[i] = (krgb, kn + n)
                break
        else:
            kept.append((rgb, n))
    kept.sort(key=lambda t: -t[1])
    return kept


def _px(v) -> float | None:
    m = re.match(r"\s*(-?[\d.]+)px", str(v))
    return float(m.group(1)) if m else None


def _type_scale(typo: dict) -> list[dict]:
    """Per-element typography as the browser computed it, largest first."""
    rows = []
    for tag, r in typo.items():
        size, lh, ls = _px(r["size"]), _px(r["lh"]), _px(r["ls"])
        rows.append({
            "tag": tag, "size_px": size, "weight": r["weight"], "count": r["n"],
            "line_height": round(lh / size, 2) if lh and size else None,
            "tracking_em": round(ls / size, 3) if ls is not None and size else None,
            "family": r["family"].split(",")[0].strip(" \"'"),
        })
    return sorted(rows, key=lambda x: -(x["size_px"] or 0))


def _spacing_scale(spaces: dict) -> dict:
    """Distinct px spacing values (>0) and the dominant base unit (4 or 8) that explains them."""
    vals = sorted({round(_px(k)) for k in spaces if _px(k) and 0 < _px(k) <= 256})
    base = max((4, 8), key=lambda b: (sum(1 for v in vals if v % b == 0), b)) if vals else None  # ties → 8
    on_grid = round(sum(1 for v in vals if base and v % base == 0) / len(vals), 2) if vals else None
    return {"values_px": vals[:24], "base_unit": base, "on_grid_ratio": on_grid}


def to_design_md(result: dict) -> str:
    """Render an extraction as a DESIGN.md (awesome-design-md shape) so it round-trips through
    designmd.parse_design_md and can be committed next to the tokens."""
    summ, seed = result["summary"], result["token_spec_seed"]
    light = seed["light"]
    colors = {"canvas": light.get("bg"), "ink": light.get("fg"), "primary": light.get("brand")}
    for i, hx in enumerate(summ.get("palette", [])):
        colors.setdefault(f"extra-{i + 1}", hx)
    lines = ["---", "version: alpha", f"name: {seed['name']}-extracted",
             f"description: Computed-style extraction of {result['url']}", "", "colors:"]
    lines += [f'  {k}: "{v}"' for k, v in colors.items() if v]
    lines += ["", "typography:"]
    for r in result.get("type_scale", [])[:8]:
        lines += [f"  {r['tag']}:", f"    fontFamily: {r['family']}", f"    fontSize: {r['size_px']:g}px",
                  f"    fontWeight: {r['weight']}"]
        if r["line_height"]:
            lines.append(f"    lineHeight: {r['line_height']}")
        if r["tracking_em"] is not None:
            lines.append(f"    letterSpacing: {r['tracking_em']}em")
    if summ.get("radii"):
        lines += ["", "rounded:"]
        lines += [f"  {n}: {rad.split()[0]}" for n, rad in zip(["sm", "md", "lg", "xl"], summ["radii"])]
    lines += ["", "spacing:"]
    lines += [f"  s{v}: {v}px" for v in result.get("spacing_scale", {}).get("values_px", [])[:12]]
    lines += ["---", "", f"# {seed['name']} (extracted)", "",
              "Heuristic extraction from the live DOM; review roles before adopting.", ""]
    return "\n".join(lines)


def extract_tokens(url: str, timeout_ms: int = 20000) -> dict:
    """Scrape computed styles and return normalized tokens + a summary for confirmation."""
    feas = can_extract(url)
    if not feas["feasible"]:
        raise RuntimeError("Cannot extract: " + "; ".join(feas["reasons"]))

    from playwright.sync_api import sync_playwright  # local import; optional dep

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        raw = page.evaluate(_JS)
        browser.close()

    fg = collections.Counter()
    for css, n in raw["colors"].items():
        k = _rgb_key(css)
        if k:
            fg[k] += n
    bg = collections.Counter()
    for css, n in raw["bgs"].items():
        k = _rgb_key(css)
        if k:
            bg[k] += n

    fg_merged = _merge_near(fg)
    bg_merged = _merge_near(bg)
    fonts = [f.split(",")[0].strip(' "\'') for f, _ in collections.Counter(raw["fonts"]).most_common(4)]
    sizes = sorted({s for s in raw["sizes"]}, key=lambda x: float(re.sub(r"[^\d.]", "", x) or 0))
    radii = [r for r, _ in collections.Counter(raw["radii"]).most_common(6) if r not in ("0px", "")]
    shadows = [s for s, _ in collections.Counter(raw["shadows"]).most_common(5)]

    light = {}
    if bg_merged:
        light["bg"] = _to_hex(bg_merged[0][0])
    if fg_merged:
        light["fg"] = _to_hex(fg_merged[0][0])
    # heuristic brand = most frequent saturated non-neutral foreground/bg
    def saturated(rgb):
        return (max(rgb) - min(rgb)) > 40
    brand = next((rgb for rgb, _ in fg_merged + bg_merged if saturated(rgb)), None)
    if brand:
        light["brand"] = _to_hex(brand)

    result = {
        "url": url,
        "summary": {
            "primary_bg": light.get("bg"),
            "primary_fg": light.get("fg"),
            "likely_brand": light.get("brand"),
            "fonts": fonts,
            "font_sizes": sizes[:8],
            "radii": radii,
            "shadow_samples": shadows,
            "palette": [_to_hex(rgb) for rgb, _ in (fg_merged + bg_merged)[:8]],
        },
        "type_scale": _type_scale(raw.get("typo", {})),
        "spacing_scale": _spacing_scale(raw["spaces"]),
        "token_spec_seed": {"name": re.sub(r"^https?://(www\.)?", "", url).split("/")[0], "light": light, "dark": light},
        "note": "Extraction is heuristic. Confirm the summary before adopting; extend into a full TokenSpec.",
    }
    result["design_md"] = to_design_md(result)
    return result
