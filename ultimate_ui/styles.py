"""Curated style library: art directions, palettes and motion moves (pure observations).

Data comes from the MIT-licensed taste-skill library (github.com/Leonxlnx/taste-skill,
Copyright (c) 2026 Leonxlnx), bundled under ``ultimate_ui/data``. Palettes are turned into
token-spec seeds with their contrast MEASURED here (WCAG + APCA), so a suggestion is never
just a vibe: it ships with numbers.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ultimate_ui import contrast as _contrast

__all__ = ["style_directions", "palette_suggestions", "motion_moves", "catalog_summary",
           "type_systems", "blueprints"]

_DATA = Path(__file__).parent / "data"


@lru_cache(maxsize=None)
def _load(name: str) -> list[dict]:
    return json.loads((_DATA / f"{name}.json").read_text(encoding="utf-8"))


def _norm(v) -> str:
    return str(v or "").strip().lower()


def catalog_summary() -> dict:
    """Valid filter values, so a caller can discover the vocabulary instead of guessing."""
    dirs, pals = _load("directions"), _load("palettes")
    return {
        "directions": [d["id"] for d in dirs],
        "sectors": sorted({s for d in dirs for s in d["sectors"]}),
        "tones": sorted({t for d in dirs for t in d["tones"]}),
        "palette_tags": sorted({t for p in pals for t in p["tags"]}),
        "palettes": len(pals),
    }


def style_directions(sector: str = "", tone: str = "", limit: int = 5) -> dict:
    """Rank art directions by fit to a sector and tone (exact tag matches, deterministic)."""
    sector, tone = _norm(sector), _norm(tone)
    scored = []
    for i, d in enumerate(_load("directions")):
        score = (2 if sector and sector in d["sectors"] else 0) + (2 if tone and tone in d["tones"] else 0)
        if (sector or tone) and score == 0:
            continue
        scored.append((-score, i, d))
    scored.sort(key=lambda t: (t[0], t[1]))
    keep = (
        "id", "name", "idea", "composition", "typography", "typeClasses", "colour",
        "paletteTags", "imagery", "sectionTags", "motion", "richness", "pitfalls",
    )
    picks = [{k: d.get(k) for k in keep} | {"fit": -s} for s, _, d in scored[: max(1, limit)]]
    return {"query": {"sector": sector, "tone": tone}, "directions": picks,
            "vocabulary": {k: v for k, v in catalog_summary().items() if k in ("sectors", "tones")}}


def _measure(p: dict) -> dict:
    body = _contrast.contrast_report(p["ink"], p["bg"])
    muted = _contrast.contrast_report(p["muted"], p["bg"])
    cta = _contrast.contrast_report(p["accentInk"], p["accent"])
    return {"ink_on_bg": body, "muted_on_bg": muted, "accentInk_on_accent": cta}


def _passes(m: dict) -> bool:
    # body text and the CTA label are the load-bearing pairs; `muted` is reported, not gating
    return m["ink_on_bg"]["wcag_AA"] and m["accentInk_on_accent"]["wcag_AA"]


def _mix(a: str, b: str, t: float) -> str:
    """Linear sRGB mix: t=0 -> a, t=1 -> b."""
    ra, rb = _contrast.parse_color(a), _contrast.parse_color(b)
    return "#{:02x}{:02x}{:02x}".format(*(round(x + (y - x) * t) for x, y in zip(ra, rb)))


def _legible(fg: str, bg: str, fallback: str, need: float = 4.5) -> str:
    return fg if _contrast.wcag_ratio(fg, bg) >= need else fallback


def _dark_side(p: dict) -> dict:
    """A real dark mode, not a copy of light. Ground/ink come from the first of the palette's own
    inverted fields that reads at >=7:1, else are derived from its ink; muted surface, secondary text,
    brand and on-brand are then re-derived AGAINST that ground so every pair is measured."""
    bg = fg = None
    for f in p.get("fields") or []:
        if _contrast.wcag_ratio(f["ink"], f["bg"]) >= 7:
            bg, fg = f["bg"], f["ink"]
            break
    if bg is None:
        bg = _mix(p["ink"], "#000000", 0.7)
        fg = p["bg"] if _contrast.wcag_ratio(p["bg"], bg) >= 7 else "#f5f5f5"
    surface = _mix(bg, fg, 0.08)
    muted_fg = _legible(_mix(fg, bg, 0.35), surface, fg)
    brand = p["accent"]
    for t in (0.0, 0.15, 0.3, 0.45, 0.6, 0.8):  # lift a dim accent toward the ink until it reads (3:1)
        brand = _mix(p["accent"], fg, t)
        if _contrast.wcag_ratio(brand, bg) >= 3.0:
            break
    on_brand = "#000000" if _contrast.wcag_ratio("#000000", brand) >= _contrast.wcag_ratio("#ffffff", brand)         else "#ffffff"
    return {"bg": bg, "fg": fg, "brand": brand, "on-brand": on_brand,
            "muted": surface, "muted-fg": muted_fg, "canvas": surface}


def _seed(p: dict) -> dict:
    """Palette -> token-spec seed with distinct light and dark roles."""
    light = {"bg": p["bg"], "fg": p["ink"], "brand": p["accent"], "on-brand": p["accentInk"],
             "muted": p["surface"], "muted-fg": p["muted"], "canvas": p["surface"]}
    return {"name": p["id"], "light": light, "dark": _dark_side(p)}


def palette_suggestions(tags: list | None = None, limit: int = 5, accessible_only: bool = True) -> dict:
    """Palettes whose tags intersect `tags`, each with measured contrast and a spec seed."""
    want = {_norm(t) for t in (tags or []) if _norm(t)}
    out = []
    for p in _load("palettes"):
        if want and not want & set(p["tags"]):
            continue
        m = _measure(p)
        ok = _passes(m)
        if accessible_only and not ok:
            continue
        out.append({
            "id": p["id"], "name": p["name"], "tags": p["tags"], "note": p["note"],
            "colors": {k: p[k] for k in ("bg", "surface", "ink", "muted", "accent", "accentInk")},
            "contrast": m, "aa_clean": ok, "spec_seed": _seed(p),
        })
    return {"query": {"tags": sorted(want), "accessible_only": accessible_only},
            "palettes": out[: max(1, limit)], "matched": len(out),
            "note": "spec_seed.dark is derived against the palette's inverted field (muted/canvas/"
                    "muted-fg re-computed, not copied from light) - run read_spec_validation before persisting."}


def motion_moves() -> list[dict]:
    return _load("motions")


# ── type systems, hero and section blueprints (taste-skill library) ─────────
def type_systems(type_classes: list | None = None, limit: int = 5) -> dict:
    """Dealt type systems (display/text faces, weights, fluid scale) filtered by class."""
    want = {_norm(c) for c in (type_classes or []) if _norm(c)}
    allt = _load("type")
    picks = [t for t in allt if not want or _norm(t["class"]) in want]
    keep = ("id", "name", "class", "display", "text", "standsInFor", "note", "links", "scale")
    return {"query": {"classes": sorted(want)}, "matched": len(picks),
            "systems": [{k: t.get(k) for k in keep} for t in picks[: max(1, limit)]],
            "classes": sorted({t["class"] for t in allt}),
            "note": "Faces are free/CDN sources (see links); scale is a clamp() ramp of <=5 steps."}


def blueprints(kind: str = "section", direction: str = "", role: str = "", limit: int = 5) -> dict:
    """Hero (kind='hero') or section (kind='section') composition blueprints for a direction/role."""
    kind, direction, role = _norm(kind), _norm(direction), _norm(role)
    if kind not in ("hero", "section"):
        raise ValueError("kind must be 'hero' or 'section'")
    rows = _load("heroes" if kind == "hero" else "sections")
    out = []
    for r in rows:
        if direction and direction not in r.get("directions", []):
            continue
        if kind == "section" and role and _norm(r.get("role")) != role:
            continue
        out.append(r)
    keep = ("id", "name", "role", "shape", "archetype", "tags", "directions", "blueprint",
            "mobile", "headline", "motion")
    return {"kind": kind, "query": {"direction": direction, "role": role}, "matched": len(out),
            "blueprints": [{k: r[k] for k in keep if k in r} for r in out[: max(1, limit)]],
            "roles": sorted({r["role"] for r in rows if "role" in r}) if kind == "section" else None}
