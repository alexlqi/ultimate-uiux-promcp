"""Brand DESIGN.md import (awesome-design-md, MIT, github.com/VoltAgent/awesome-design-md).

A DESIGN.md is a brand's design language written for an LLM: colors, type ramp, radii,
spacing, components, do's and don'ts. This module fetches one (live read, bundled brand
list as the offline vocabulary) and normalizes it into the SAME TokenSpec seed shape the
generator and the Playwright extractor use — so a documented brand flows straight into
read_spec_validation → read_generated_tokens.

Two upstream formats exist and both are handled, tolerantly (a malformed file degrades to
fewer extracted roles, never a traceback):
  A. YAML-ish front matter (``colors:`` / ``typography:`` / ``rounded:`` / ``spacing:``)
  B. Markdown only, with a "Color Palette & Roles" section of ``**Name** (`#hex`): role``
"""
from __future__ import annotations

import json
import re
import urllib.request
from functools import lru_cache
from pathlib import Path

from ultimate_ui import contrast as _contrast

__all__ = ["bundled_brands", "list_brands", "fetch_design_md", "parse_design_md", "to_spec_seed"]

_RAW = "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{slug}/DESIGN.md"
_TREE = "https://api.github.com/repos/VoltAgent/awesome-design-md/contents/design-md"
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def _get(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ultimate-ui-design-mcp"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https hosts)
        return r.read().decode("utf-8", "replace")


@lru_cache(maxsize=1)
def bundled_brands() -> list[str]:
    return json.loads((Path(__file__).parent / "data" / "design_md_brands.json").read_text(encoding="utf-8"))


def list_brands(timeout: float = 8.0) -> dict:
    """Live brand list; falls back to the bundled snapshot (quality=degraded to the caller)."""
    try:
        items = json.loads(_get(_TREE, timeout))
        return {"brands": sorted(i["name"] for i in items if i.get("type") == "dir"), "source": "live"}
    except Exception:
        return {"brands": list(bundled_brands()), "source": "bundled"}


def fetch_design_md(slug: str, timeout: float = 10.0) -> str:
    slug = (slug or "").strip().lower()
    if not _SLUG.match(slug):
        raise ValueError(f"invalid brand slug {slug!r} (expected e.g. 'stripe', 'linear.app')")
    return _get(_RAW.format(slug=slug), timeout)


# ── parsing ──────────────────────────────────────────────────────────────────
def _front_matter(text: str) -> str:
    m = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
    return m.group(1) if m else ""


def _unq(v: str) -> str:
    return v.strip().strip("\"'")


def _sections(fm: str) -> dict[str, dict]:
    """Tolerant two-level reader: `section:` → {key: scalar | {subkey: scalar}} (indent-based).
    Lines it cannot read are skipped — one bad line must not lose the whole document."""
    out: dict[str, dict] = {}
    section, key = None, None
    for raw in fm.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        m = re.match(r"\s*([^:\s][^:]*?):\s*(.*)$", raw)
        if not m:
            continue
        k, v = m.group(1).strip().strip("\"'"), m.group(2)
        if indent == 0:
            section, key = k, None
            out.setdefault(section, {})
            if v.strip():
                out[section] = _unq(v)  # scalar top-level (name/description/version)
        elif section and isinstance(out.get(section), dict):
            if indent <= 2 or key is None:
                if v.strip():
                    out[section][k] = _unq(v)
                    key = None
                else:
                    out[section][k] = {}
                    key = k
            elif isinstance(out[section].get(key), dict) and v.strip():
                out[section][key][k] = _unq(v)
    return out


def _palette_from_markdown(text: str) -> list[tuple[str, str, str]]:
    """(name, hex, description) from the Color Palette section of a markdown-only DESIGN.md."""
    m = re.search(r"^##\s*\d*\.?\s*Colou?r[^\n]*\n(.*?)(?=^##\s)", text, re.S | re.M)
    body = m.group(1) if m else text
    rows = []
    for line in body.splitlines():
        mm = re.search(r"\*\*([^*]+)\*\*[^`\n]*`(#[0-9a-fA-F]{6})`\)?\s*[:\-–—]?\s*(.*)", line)
        if mm:
            rows.append((mm.group(1).strip(), mm.group(2).lower(), mm.group(3).strip()))
    return rows


def parse_design_md(text: str) -> dict:
    fm = _sections(_front_matter(text))
    colors = {k: v.lower() for k, v in (fm.get("colors") or {}).items()
              if isinstance(v, str) and _HEX.fullmatch(v.strip())}
    palette = [(k, v, "") for k, v in colors.items()] if colors else _palette_from_markdown(text)
    return {
        "format": "front-matter" if colors else ("markdown" if palette else "unparsed"),
        "name": fm.get("name") if isinstance(fm.get("name"), str) else None,
        "palette": palette,
        "typography": fm.get("typography") if isinstance(fm.get("typography"), dict) else {},
        "rounded": fm.get("rounded") if isinstance(fm.get("rounded"), dict) else {},
        "spacing": fm.get("spacing") if isinstance(fm.get("spacing"), dict) else {},
    }


# ── normalization into a TokenSpec seed ─────────────────────────────────────
def _lum(h: str) -> float:
    return _contrast.relative_luminance(_contrast.parse_color(h))


def _pick(palette, name_pats, desc_pats=(), exclude=()):
    for nm, hx, ds in palette:
        low = nm.lower()
        if any(re.search(p, low) for p in exclude):
            continue
        if any(re.fullmatch(p, low) for p in name_pats) or any(re.search(p, ds.lower()) for p in desc_pats):
            return hx
    return None


def _px(v) -> float | None:
    m = re.match(r"\s*([\d.]+)px", str(v))
    return float(m.group(1)) if m else None


def to_spec_seed(parsed: dict, fallback_name: str = "brand") -> dict:
    pal = parsed["palette"]
    if not pal:
        return {"error": "no colors could be extracted from this DESIGN.md",
                "hint": "read the raw document and author the spec by hand"}
    bg = _pick(pal, [r"canvas", r"background", r"page", r"canvas-light", r"surface-base"],
               [r"\bbackground\b", r"\bpage\b"]) or max((h for _, h, _ in pal), key=_lum)
    fg = _pick(pal, [r"ink", r"text", r"body", r"foreground"], [r"primary text", r"body text", r"main text"],
               exclude=[r"mute", r"soft", r"on-"]) or (
        "#ffffff" if _lum(bg) < 0.2 else "#111111")
    brand = _pick(pal, [r"primary", r"brand", r"accent"], [r"brand", r"\bcta\b", r"accent"],
                  exclude=[r"on-", r"deep", r"hover", r"press", r"active", r"disabled", r"bg", r"soft"])
    if not brand:  # most saturated colour wins
        brand = max((h for _, h, _ in pal),
                    key=lambda h: max(_contrast.parse_color(h)) - min(_contrast.parse_color(h)))
    # sanity: a ground that equals the brand, or can't carry the text, is a mis-mapped role
    if bg == brand or _contrast.wcag_ratio(fg, bg) < 3:
        ordered = sorted((h for _, h, _ in pal), key=_lum)
        bg = ordered[-1] if _lum(fg) < 0.4 else ordered[0]
    on_brand = _pick(pal, [r"on-primary", r"on-brand"]) or ("#ffffff" if _lum(brand) < 0.4 else "#111111")
    muted_fg = _pick(pal, [r"ink-mute", r"mute", r"muted", r"ink-secondary", r"body-muted"],
                     [r"secondary text", r"muted"], exclude=[r"on-"])
    border = _pick(pal, [r"hairline", r"border", r"divider"])
    surface = _pick(pal, [r"surface-soft", r"surface-card", r"surface", r"canvas-soft"])

    if muted_fg and _contrast.wcag_ratio(muted_fg, bg) < 3:
        muted_fg = None  # a "muted" text role that can't be read is not a role
    role = {"bg": bg, "fg": fg, "brand": brand, "on-brand": on_brand}
    for k, v in (("muted-fg", muted_fg), ("border", border), ("muted", surface), ("canvas", surface)):
        if v:
            role[k] = v
    native = "dark" if _lum(bg) < 0.2 else "light"

    radius = {}
    r = {k: _px(v) for k, v in parsed["rounded"].items() if _px(v) is not None}
    for tgt, cands in (("sm", ("sm", "xs")), ("md", ("md",)), ("lg", ("lg", "xl"))):
        for c in cands:
            if c in r:
                radius[tgt] = f"{r[c]:g}px"
                break
    if any(k in parsed["rounded"] for k in ("full", "pill")):
        radius["full"] = "9999px"

    font = {}
    for ramp in parsed["typography"].values():
        if isinstance(ramp, dict) and ramp.get("fontFamily"):
            fam = ramp["fontFamily"].split(",")[0].strip(" \"'")
            font.setdefault("sans", f"{fam}, system-ui, sans-serif")
            if ramp is not None and "display" in str(list(parsed["typography"])[:1]).lower():
                font.setdefault("display", f"{fam}, system-ui, sans-serif")
    checks = {
        "fg_on_bg": _contrast.contrast_report(fg, bg),
        "on_brand_on_brand": _contrast.contrast_report(on_brand, brand),
    }
    seed = {"name": re.sub(r"[^a-z0-9]+", "-", (parsed.get("name") or fallback_name).lower()).strip("-") or fallback_name,
            "light": dict(role), "dark": dict(role)}
    if radius:
        seed["radius"] = radius
    if font:
        seed["font"] = font
    return {
        "spec_seed": seed, "native_mode": native, "contrast": checks,
        "warnings": ([f"brand is natively {native}; the other mode is a copy of it — author the "
                      f"{'light' if native == 'dark' else 'dark'} side before shipping"]
                     + ([] if checks["fg_on_bg"]["wcag_AA"] else ["fg/bg fails WCAG AA — pick another text role"])),
        "note": "Heuristic role mapping. Validate with read_spec_validation before persisting.",
    }
