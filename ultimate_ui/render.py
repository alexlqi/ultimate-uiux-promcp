"""Rendered-page QA with Playwright (github.com/microsoft/playwright, Apache-2.0).

`extract.py` reads a site's computed styles to SEED tokens; this module closes the loop on the
way out: it renders a build (a public URL, a local file such as the generated ``email.html``,
or a dev server) at several viewports and reports what the browser actually did — console
errors, failed requests, horizontal overflow, undersized touch targets, unlabeled controls and
images, heading structure, and computed-style text contrast (with the real effective background,
measured by the same WCAG/APCA math as ``read_contrast``).

Pure observation: nothing is written, nothing is clicked. Playwright is optional; its absence is
reported as structured data, never a traceback.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from ultimate_ui import contrast as _contrast
from ultimate_ui.extract import playwright_available

__all__ = ["VIEWPORTS", "normalize_target", "render_audit", "capture_screenshots"]

VIEWPORTS = {"mobile": (375, 812), "tablet": (768, 1024), "desktop": (1280, 800)}
# WCAG 2.2 AA minimum is 24px; Apple HIG 44pt / Material 48dp are the comfortable floors.
_MIN_TARGET_AA, _MIN_TARGET_COMFORT = 24, 44

_PROBE = r"""
(args) => {
  const { minTarget, maxItems } = args;
  const out = { overflow: null, smallTargets: [], unlabeled: [], imgNoAlt: [], headings: [],
                lowContrast: [], meta: {} };
  const de = document.documentElement;
  out.overflow = { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth,
                   horizontal: de.scrollWidth > de.clientWidth + 1 };
  out.meta = { title: document.title || '', lang: de.getAttribute('lang') || '',
               viewportMeta: !!document.querySelector('meta[name=viewport]'),
               h1: document.querySelectorAll('h1').length };
  const sel = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) return s + '#' + el.id;
    const c = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return c ? s + '.' + c : s;
  };
  const visible = (el) => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const name = (el) => (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') ||
    el.getAttribute('title') || el.textContent || el.getAttribute('alt') || '').trim();

  for (const el of document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,[role=button]')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (Math.min(r.width, r.height) < minTarget && out.smallTargets.length < maxItems)
      out.smallTargets.push({ el: sel(el), w: Math.round(r.width), h: Math.round(r.height) });
    const hasLabel = name(el) || (el.id && document.querySelector('label[for="' + el.id + '"]')) || el.closest('label');
    if (!hasLabel && out.unlabeled.length < maxItems) out.unlabeled.push({ el: sel(el) });
  }
  for (const img of document.querySelectorAll('img')) {
    if (!img.hasAttribute('alt') && out.imgNoAlt.length < maxItems) out.imgNoAlt.push({ el: sel(img) });
  }
  out.headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => +h.tagName[1]);

  // effective background = first non-transparent ancestor background
  const effBg = (el) => { for (let n = el; n; n = n.parentElement) {
    const b = getComputedStyle(n).backgroundColor;
    const m = b.match(/rgba?\(([^)]+)\)/);
    if (m) { const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
             if ((p.length < 4 ? 1 : p[3]) > 0.95) return b; } }
    return 'rgb(255,255,255)'; };
  const seen = new Set();
  const walker = document.createTreeWalker(document.body || de, NodeFilter.SHOW_TEXT);
  for (let n; (n = walker.nextNode()); ) {
    if (!n.nodeValue.trim()) continue;
    const el = n.parentElement; if (!el || seen.has(el) || !visible(el)) continue;
    seen.add(el);
    const s = getComputedStyle(el);
    if (+s.opacity < 1 || seen.size > 1500) continue;
    out.lowContrast.push({ el: sel(el), fg: s.color, bg: effBg(el), size: parseFloat(s.fontSize),
                           weight: parseInt(s.fontWeight, 10) || 400, text: n.nodeValue.trim().slice(0, 40) });
  }
  return out;
}
"""


def normalize_target(target: str) -> tuple[str, str]:
    """(url, kind). Accepts http(s) URLs or a local file path (→ file:// URI)."""
    t = (target or "").strip()
    if re.match(r"^https?://", t):
        return t, "url"
    p = Path(t).expanduser()
    if p.is_file():
        return p.resolve().as_uri(), "file"
    raise ValueError(f"target must be an http(s) URL or an existing file path, got {target!r}")


def _is_large(size: float, weight: int) -> bool:
    return size >= 24 or (size >= 18.66 and weight >= 700)


def _contrast_findings(rows: list[dict], cap: int) -> list[dict]:
    worst: dict[tuple, dict] = {}
    for r in rows:
        try:
            ratio = _contrast.wcag_ratio(r["fg"], r["bg"])
        except Exception:
            continue
        need = 3.0 if _is_large(r["size"], r["weight"]) else 4.5
        if ratio < need:
            key = (r["fg"], r["bg"], need)
            hit = worst.setdefault(key, {"fg": r["fg"], "bg": r["bg"], "ratio": int(ratio * 100) / 100,  # truncate: 4.499 must not read as a pass
                                         "required": need, "count": 0, "example": r["el"],
                                         "text": r["text"]})
            hit["count"] += 1
    return sorted(worst.values(), key=lambda h: h["ratio"])[:cap]


def render_audit(target: str, viewports: list[str] | None = None, timeout_ms: int = 20000,
                 max_items: int = 8) -> dict:
    """Render `target` at each viewport and return structured, severity-tagged findings."""
    if not playwright_available():
        return {"error": "playwright_missing",
                "hint": "pip install playwright && playwright install chromium"}
    url, kind = normalize_target(target)
    names = [v for v in (viewports or list(VIEWPORTS)) if v in VIEWPORTS]
    if not names:
        raise ValueError(f"viewports must be a subset of {list(VIEWPORTS)}")

    from playwright.sync_api import sync_playwright  # optional dependency

    report: dict = {"target": url, "kind": kind, "viewports": {}, "findings": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name in names:
                w, h = VIEWPORTS[name]
                ctx = browser.new_context(viewport={"width": w, "height": h},
                                          has_touch=name != "desktop", is_mobile=name == "mobile")
                page = ctx.new_page()
                console, failed = [], []
                page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
                page.on("requestfailed", lambda r: failed.append(f"{r.url[:120]} ({r.failure})"))
                page.on("response", lambda r: failed.append(f"{r.url[:120]} (HTTP {r.status})")
                        if r.status >= 400 else None)
                page.goto(url, wait_until="load", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass  # long-poll/analytics pages never idle; load is enough
                probe = page.evaluate(_PROBE, {"minTarget": _MIN_TARGET_AA, "maxItems": max_items})
                ctx.close()
                low = _contrast_findings(probe["lowContrast"], max_items)
                report["viewports"][name] = {
                    "size": f"{w}x{h}", "console_errors": console[:max_items],
                    "failed_requests": failed[:max_items], "overflow": probe["overflow"],
                    "small_targets": probe["smallTargets"], "unlabeled_controls": probe["unlabeled"],
                    "img_without_alt": probe["imgNoAlt"], "low_contrast": low,
                    "comfortable_target_floor": _MIN_TARGET_COMFORT,
                }
                if name == names[0]:
                    report["meta"] = probe["meta"]
                    report["heading_outline"] = probe["headings"][:40]
        finally:
            browser.close()
    report["findings"] = _summarize(report)
    report["counts"] = {s: sum(1 for f in report["findings"] if f["severity"] == s)
                        for s in ("Critical", "Major", "Minor")}
    return report


def _summarize(rep: dict) -> list[dict]:
    out: list[dict] = []

    def add(sev, vp, rule, msg):
        out.append({"severity": sev, "viewport": vp, "rule": rule, "message": msg})

    meta = rep.get("meta", {})
    if rep["kind"] == "url" or meta.get("title") is not None:
        if not meta.get("title"):
            add("Minor", "all", "meta-title", "document has no <title>")
        if not meta.get("lang"):
            add("Major", "all", "meta-lang", "<html> has no lang attribute (screen readers, hyphenation)")
        if not meta.get("viewportMeta"):
            add("Major", "all", "meta-viewport", "no <meta name=viewport>: mobile renders at desktop width")
        if meta.get("h1", 0) != 1:
            add("Minor", "all", "heading-h1", f"expected exactly one <h1>, found {meta.get('h1', 0)}")
    hs = rep.get("heading_outline", [])
    for prev, cur in zip(hs, hs[1:]):
        if cur > prev + 1:
            add("Minor", "all", "heading-skip", f"heading level jumps h{prev} → h{cur}")
            break
    for vp, d in rep["viewports"].items():
        if d["overflow"]["horizontal"]:
            add("Critical", vp, "overflow-x",
                f"horizontal scroll: content {d['overflow']['scrollWidth']}px > viewport "
                f"{d['overflow']['clientWidth']}px")
        for e in d["console_errors"]:
            add("Major", vp, "console-error", e[:160])
        for e in d["failed_requests"]:
            add("Major", vp, "failed-request", e)
        for t in d["small_targets"]:
            add("Major" if vp == "mobile" else "Minor", vp, "target-size",
                f"{t['el']} is {t['w']}x{t['h']}px (< {_MIN_TARGET_AA}px WCAG 2.2 minimum)")
        for u in d["unlabeled_controls"]:
            add("Critical", vp, "control-label", f"{u['el']} has no accessible name")
        for i in d["img_without_alt"]:
            add("Major", vp, "img-alt", f"{i['el']} has no alt attribute")
        for c in d["low_contrast"]:
            add("Major", vp, "text-contrast",
                f"{c['fg']} on {c['bg']} = {c['ratio']}:1 (needs {c['required']}:1) "
                f"× {c['count']} e.g. {c['example']} “{c['text']}”")
    # one finding per (rule, message): keep the worst severity, mark cross-viewport repeats
    rank = {"Critical": 0, "Major": 1, "Minor": 2}
    merged: dict[tuple, dict] = {}
    for f in out:
        key = (f["rule"], f["message"])
        cur = merged.get(key)
        if cur is None:
            merged[key] = dict(f)
            continue
        if f["viewport"] != cur["viewport"]:
            cur["viewport"] = "multiple"
        if rank[f["severity"]] < rank[cur["severity"]]:
            cur["severity"] = f["severity"]
    uniq = list(merged.values())
    order = {"Critical": 0, "Major": 1, "Minor": 2}
    return sorted(uniq, key=lambda f: order[f["severity"]])


def capture_screenshots(target: str, output_dir: str, viewports: list[str] | None = None,
                        full_page: bool = True, timeout_ms: int = 20000) -> list[str]:
    """Write one PNG per viewport into `output_dir` and return the paths (a disk mutation —
    the surface exposes this only as an idempotent, compensable do_ action)."""
    if not playwright_available():
        raise RuntimeError("playwright_missing: pip install playwright && playwright install chromium")
    url, _ = normalize_target(target)
    names = [v for v in (viewports or list(VIEWPORTS)) if v in VIEWPORTS]
    if not names:
        raise ValueError(f"viewports must be a subset of {list(VIEWPORTS)}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    label = Path(unquote(urlparse(url).path)).stem if url.startswith("file:") else re.sub(r"^\w+://", "", url)
    stem = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "page"
    from playwright.sync_api import sync_playwright  # optional dependency

    written: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name in names:
                w, h = VIEWPORTS[name]
                ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=name == "mobile")
                page = ctx.new_page()
                page.goto(url, wait_until="load", timeout=timeout_ms)
                path = out / f"{stem}-{name}-{w}x{h}.png"
                page.screenshot(path=str(path), full_page=full_page)
                ctx.close()
                written.append(str(path))
        finally:
            browser.close()
    return written
