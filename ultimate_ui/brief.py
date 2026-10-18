"""One-call design brief: sector + tone + paradigm -> a committed, validated starting point.

Chains the taste-skill library (direction -> palette -> type system -> blueprints) into a
token-spec seed for the chosen paradigm vertical and runs it through the same validation gate
(`health.validate_spec`) the persist step uses. Pure observation, deterministic: the same
inputs always select the same direction, palette and type system.
"""
from __future__ import annotations

from ultimate_ui import health as _health
from ultimate_ui import styles as _styles

__all__ = ["design_brief"]

_APP_NOTES = {
    "flutter-material": ("Android / Material 3: seed ColorScheme from `brand`; 8-dp grid, 48-dp targets. "
                         "Use the blueprint's `mobile` re-flow as the screen structure (not the desktop "
                         "composition); fonts via google_fonts or bundled assets."),
    "flutter-cupertino": ("iOS / HIG: CupertinoThemeData from `brand`; 44-pt targets, large-title navigation. "
                          "Use the blueprint's `mobile` re-flow; prefer SF (system) text with the display face "
                          "only for large titles."),
    "react-native": ("React Native / Expo: import colours, spacing, radius and minTarget from the generated "
                     "theme.ts via useTokens(); FlashList for lists, Pressable with minTarget, expo-image, "
                     "native stack/tabs. Use the blueprint's `mobile` re-flow as the screen structure."),
    "email": ("HTML email: single column <=600px, web-safe fallback stack after the dealt face, no "
              "webfont reliance in Outlook; one CTA (bulletproof button) carries the accent."),
    "web": "Web: use hero + section blueprints desktop-first with their `mobile` notes for <768px.",
}


def _family(face: dict | None) -> str | None:
    return (face or {}).get("family")


def design_brief(sector: str = "", tone: str = "", paradigm: str = "web", name: str = "app",
                 direction: str = "") -> dict:
    if paradigm not in _health.PARADIGMS:
        raise ValueError(f"paradigm must be one of {', '.join(_health.PARADIGMS)}")
    dirs = _styles.style_directions(sector, tone, 20)["directions"]
    if direction:
        dirs = [d for d in dirs if d["id"] == direction] or [
            d for d in _styles.style_directions("", "", 50)["directions"] if d["id"] == direction]
        if not dirs:
            raise ValueError(f"unknown direction {direction!r}")
    if not dirs:
        raise ValueError("no direction matches; call read_style_directions() for the vocabulary")
    chosen = dirs[0]

    pal = _styles.palette_suggestions(chosen.get("paletteTags") or [], 1)["palettes"]
    if not pal:  # direction's tags have no accessible palette: fall back to any accessible one
        pal = _styles.palette_suggestions([], 1)["palettes"]
    palette = pal[0]
    seed = dict(palette["spec_seed"])
    seed["name"] = name

    types = _styles.type_systems(chosen.get("typeClasses") or [], 1)["systems"] or \
        _styles.type_systems([], 1)["systems"]
    ts = types[0]
    display, text = _family(ts.get("display")), _family(ts.get("text"))
    if display or text:
        seed["font"] = {"display": f"{display or text}, sans-serif", "sans": f"{text or display}, sans-serif",
                        "mono": "ui-monospace, monospace"}

    hero = _styles.blueprints("hero", chosen["id"], limit=1)["blueprints"]
    sections = {}
    for role in ("features", "proof", "cta"):
        got = _styles.blueprints("section", chosen["id"], role, 1)["blueprints"]
        if got:
            sections[role] = got[0]

    validation = _health.validate_spec(seed, paradigm)
    return {
        "paradigm": paradigm,
        "direction": {k: chosen.get(k) for k in ("id", "name", "idea", "composition", "motion", "pitfalls")},
        "palette": {k: palette[k] for k in ("id", "name", "note", "colors", "contrast")},
        "type_system": {k: ts.get(k) for k in ("id", "name", "class", "display", "text", "links", "scale")},
        "hero": hero[0] if hero else None,
        "sections": sections,
        "spec_seed": seed,
        "validation": {"valid": validation["valid"], "errors": validation.get("errors", []),
                       "warnings": validation.get("warnings", [])},
        "paradigm_notes": _APP_NOTES[paradigm],
        "next_steps": [
            f"read_spec_validation(spec_seed, '{paradigm}') - author the dark/other mode if flagged",
            f"read_generated_tokens(spec_seed, paradigm='{paradigm}')",
            "do_write_token_files(...) to persist, then build with the blueprints",
            "read_ui_audit / read_rendered_audit before done",
        ],
    }
