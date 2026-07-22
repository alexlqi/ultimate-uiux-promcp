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
  return { colors, bgs, fonts, sizes, radii, shadows, spaces };
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

    return {
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
        "token_spec_seed": {"name": re.sub(r"^https?://(www\.)?", "", url).split("/")[0], "light": light, "dark": light},
        "note": "Extraction is heuristic. Confirm the summary before adopting; extend into a full TokenSpec.",
    }
