"""Deterministic contrast math: WCAG 2.1 ratio and APCA Lc.

Pure functions, no I/O. These are the kind of verifiable checks that belong in a tool
rather than in model context — you compute the number, you don't guess it.
"""
from __future__ import annotations

import math
import re

__all__ = [
    "parse_color",
    "relative_luminance",
    "wcag_ratio",
    "apca_lc",
    "contrast_report",
]

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_RGB = re.compile(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", re.I)


def parse_color(value: str) -> tuple[int, int, int]:
    """Parse '#rrggbb', '#rgb', 'rgb(r,g,b)', or 'r,g,b' into an (r,g,b) 0-255 tuple.

    OKLCH/named colors are intentionally not resolved here — pass sRGB. The token
    generator emits sRGB fallbacks alongside OKLCH for exactly this reason.
    """
    value = value.strip()
    m = _HEX.match(value)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = _RGB.search(value)
    if m:
        return tuple(min(255, max(0, round(float(g)))) for g in m.groups())  # type: ignore
    parts = [p for p in re.split(r"[,\s]+", value) if p]
    if len(parts) == 3 and all(p.replace(".", "").isdigit() for p in parts):
        return tuple(min(255, max(0, round(float(p)))) for p in parts)  # type: ignore
    raise ValueError(f"Unrecognized color: {value!r}. Use hex or rgb() in sRGB.")


def _srgb_to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_linear(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(fg: str, bg: str) -> float:
    """WCAG 2.1 contrast ratio (1..21). Order-independent."""
    lf = relative_luminance(parse_color(fg))
    lb = relative_luminance(parse_color(bg))
    hi, lo = max(lf, lb), min(lf, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- APCA (SAPC/APCA 0.0.98G-4g constants) ---------------------------------
_APCA = dict(
    Ntx=0.57, Nbg=0.56, Rtx=0.62, Rbg=0.65,
    Bthresh=0.022, Bclip=1.414, Wscale=1.14, Woffset=0.027, Wclamp=0.1,
)


def _apca_y(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126729 * (r / 255) ** 2.4 + 0.7151522 * (g / 255) ** 2.4 + 0.0721750 * (b / 255) ** 2.4


def _apca_clamp(y: float) -> float:
    return y + (_APCA["Bthresh"] - y) ** _APCA["Bclip"] if y < _APCA["Bthresh"] else y


def apca_lc(text: str, bg: str) -> float:
    """APCA lightness contrast (Lc), signed. |Lc|>=60 ~ body text; >=45 large; >=30 UI.

    Text-on-background is directional, so pass (text_color, bg_color) in that order.
    """
    ytx = _apca_clamp(_apca_y(parse_color(text)))
    ybg = _apca_clamp(_apca_y(parse_color(bg)))
    if abs(ybg - ytx) < 0.0005:
        return 0.0
    if ybg > ytx:  # normal polarity: dark text on light bg
        sapc = (ybg ** _APCA["Nbg"] - ytx ** _APCA["Ntx"]) * _APCA["Wscale"]
        out = 0.0 if sapc < _APCA["Wclamp"] else sapc - _APCA["Woffset"]
    else:  # reverse polarity: light text on dark bg
        sapc = (ybg ** _APCA["Rbg"] - ytx ** _APCA["Rtx"]) * _APCA["Wscale"]
        out = 0.0 if sapc > -_APCA["Wclamp"] else sapc + _APCA["Woffset"]
    return round(out * 100, 1)


def contrast_report(fg: str, bg: str, *, large: bool = False) -> dict:
    """Combined WCAG + APCA verdict for a foreground/background pair."""
    ratio = round(wcag_ratio(fg, bg), 2)
    lc = apca_lc(fg, bg)
    wcag_aa = ratio >= (3.0 if large else 4.5)
    wcag_aaa = ratio >= (4.5 if large else 7.0)
    # APCA use-case thresholds (Bronze-simple): body >=75 pref/60 min, large >=45, UI >=30
    apca_min = 45 if large else 60
    return {
        "fg": fg, "bg": bg, "large_text": large,
        "wcag_ratio": ratio, "wcag_AA": wcag_aa, "wcag_AAA": wcag_aaa,
        "apca_Lc": lc, "apca_min_needed": apca_min, "apca_pass": abs(lc) >= apca_min,
        "verdict": "pass" if (wcag_aa and abs(lc) >= apca_min) else "fail",
    }
