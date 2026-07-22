"""Horizontal stability layer: preflight, spec validation, and diagnostics.

These are the fault-tolerance and debuggability channels that sit ACROSS the three
paradigm verticals (web, flutter-material, flutter-cupertino). Everything here is a pure
OBSERVATION — it reads the environment or inspects a spec, but writes nothing. The ProMCP
surface wraps each of these as a `read_*` tool.

Three pillars:
  * preflight(paradigm)      — is the toolchain for this paradigm actually present? (doctor)
  * validate_spec(spec, ...) — is this spec safe to materialize/persist? (catch before do_)
  * diagnostics(ledger)      — what has the pipeline done, and does every emitter still run?

The point is that failure is reported as structured data with a severity and a fix hint,
never as a cryptic traceback. Callers can branch on `ready` / `valid` deterministically.
"""
from __future__ import annotations

import shutil
import sys

from ultimate_ui import contrast as _contrast
from ultimate_ui import tokens as _tokens

__all__ = ["PARADIGMS", "targets_for", "preflight", "validate_spec", "diagnostics"]

# The three first-class verticals → the emitter targets each one owns. `flutter` (the
# adaptive/combined emitter) is kept in the mobile paradigms for backward compatibility.
PARADIGMS: dict[str, dict] = {
    "web": {
        "targets": ["dtcg", "css", "tailwind", "shadcn"],
        "required_roles": ["bg", "fg", "brand"],
        "soft_roles": ["on-brand", "muted", "muted-fg", "accent", "border", "danger"],
        "label": "React + Tailwind v4 + shadcn/ui",
    },
    "flutter-material": {
        "targets": ["dtcg", "flutter-material", "flutter"],
        "required_roles": ["bg", "fg", "brand"],
        "soft_roles": ["on-brand", "danger", "accent"],
        "label": "Flutter / Material 3 (Android)",
    },
    "flutter-cupertino": {
        "targets": ["dtcg", "flutter-cupertino", "flutter"],
        "required_roles": ["bg", "fg", "brand"],
        "soft_roles": ["on-brand", "danger"],
        "label": "Flutter / Cupertino · HIG (iOS)",
    },
}


def targets_for(paradigm: str) -> list[str]:
    """Emitter targets a paradigm owns; [] for an unknown paradigm (caller decides)."""
    return list(PARADIGMS.get(paradigm, {}).get("targets", []))


# ── preflight / doctor ───────────────────────────────────────────────────────
def _check(name: str, ok: bool, detail: str, *, severity: str = "blocker") -> dict:
    # severity is only meaningful when ok is False; a passing check carries "ok".
    return {"name": name, "ok": ok, "severity": "ok" if ok else severity, "detail": detail}


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


def preflight(paradigm: str) -> dict:
    """Observe whether the toolchain for `paradigm` is present. Never raises.

    Returns {paradigm, ready, checks[], blockers[], warnings[]}. `ready` is True iff no
    check failed at "blocker" severity — "warning" checks (e.g. iOS build tools absent on a
    non-mac host) degrade the report without blocking token generation, which is host-agnostic.
    """
    if paradigm not in PARADIGMS:
        return {
            "paradigm": paradigm, "ready": False, "checks": [],
            "blockers": [f"unknown paradigm '{paradigm}'; choose from {', '.join(PARADIGMS)}"],
            "warnings": [],
        }

    checks: list[dict] = [_check("python", True, f"Python {sys.version.split()[0]}")]

    if paradigm == "web":
        node = _has("node")
        checks.append(_check("node", node, "node on PATH" if node else "install Node.js 18+ (nodejs.org)"))
        pm = next((p for p in ("pnpm", "npm", "yarn", "bun") if _has(p)), None)
        checks.append(_check("package-manager", pm is not None,
                             f"{pm} available" if pm else "no npm/pnpm/yarn/bun on PATH"))
        checks.append(_check("tailwind", True,
                             "Tailwind v4 is a project-local dep (npm i tailwindcss@next); not a global check",
                             severity="warning"))
    else:  # flutter-material / flutter-cupertino
        flutter = _has("flutter")
        checks.append(_check("flutter", flutter,
                             "flutter on PATH" if flutter else "install Flutter SDK (docs.flutter.dev/get-started)"))
        if paradigm == "flutter-material":
            adb = _has("adb")
            checks.append(_check("android-tooling", adb,
                                 "adb on PATH" if adb else "Android SDK/adb not found; needed to run on Android",
                                 severity="warning"))
        else:  # flutter-cupertino
            on_mac = sys.platform == "darwin"
            checks.append(_check("ios-build-host", on_mac,
                                 "macOS host (can build/run iOS)" if on_mac
                                 else "iOS build/run requires macOS + Xcode; token generation still works here",
                                 severity="warning"))

    blockers = [f"{c['name']}: {c['detail']}" for c in checks if not c["ok"] and c["severity"] == "blocker"]
    warnings = [f"{c['name']}: {c['detail']}" for c in checks if not c["ok"] and c["severity"] == "warning"]
    return {
        "paradigm": paradigm, "label": PARADIGMS[paradigm]["label"],
        "ready": not blockers, "checks": checks, "blockers": blockers, "warnings": warnings,
    }


# ── spec validation ──────────────────────────────────────────────────────────
def _valid_hex(v) -> bool:
    if not isinstance(v, str):
        return False
    try:
        _contrast.parse_color(v)
        return True
    except Exception:
        return False


def validate_spec(spec: dict, paradigm: str = "web") -> dict:
    """Deterministically check a token spec BEFORE it reaches do_write_token_files.

    Errors block persistence (missing/malformed required roles, unparseable colors);
    warnings surface risk without blocking (missing soft roles → emitter fallbacks used;
    contrast failures → readable but flagged). Returns {valid, errors[], warnings[], summary}.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spec, dict) or "light" not in spec or not isinstance(spec.get("light"), dict):
        return {"valid": False, "errors": ["spec must be a dict with a 'light' role→hex map"],
                "warnings": [], "summary": {}}

    meta = PARADIGMS.get(paradigm)
    if meta is None:
        warnings.append(f"unknown paradigm '{paradigm}'; validated against web defaults")
        meta = PARADIGMS["web"]

    light = spec.get("light", {})
    dark = spec.get("dark")
    if not dark:
        warnings.append("no 'dark' map: dark mode will mirror light (add a dark palette for real dark mode)")
    dark = dark or light

    # required roles must exist and parse in both modes
    for role in meta["required_roles"]:
        for mode, colors in (("light", light), ("dark", dark)):
            if role not in colors:
                errors.append(f"{mode}: required role '{role}' missing")
            elif not _valid_hex(colors[role]):
                errors.append(f"{mode}: role '{role}' = {colors[role]!r} is not a valid sRGB hex/rgb() color")

    # any other provided color that fails to parse is also an error (would crash an emitter)
    for mode, colors in (("light", light), ("dark", dark)):
        for role, val in colors.items():
            if role not in meta["required_roles"] and not _valid_hex(val):
                errors.append(f"{mode}: role '{role}' = {val!r} is not a valid color")

    # soft roles: fallbacks kick in, but tell the caller
    missing_soft = [r for r in meta["soft_roles"] if r not in light]
    if missing_soft:
        warnings.append(f"soft roles absent (emitter fallbacks used): {', '.join(missing_soft)}")

    # contrast self-check (only meaningful once required roles parse)
    contrast_failures: list[str] = []
    if not errors:
        for mode, colors in (("light", light), ("dark", dark)):
            bg = colors.get("bg", "#ffffff")
            for role in ("fg", "muted-fg", "brand"):
                if role in colors and _valid_hex(colors[role]) and _valid_hex(bg):
                    rep = _contrast.contrast_report(colors[role], bg)
                    if rep["verdict"] == "fail":
                        contrast_failures.append(f"{mode}:{role}-on-bg (ratio {rep['wcag_ratio']}, Lc {rep['apca_Lc']})")
            on_brand, brand = colors.get("on-brand"), colors.get("brand")
            if on_brand and brand and _valid_hex(on_brand) and _valid_hex(brand):
                rep = _contrast.contrast_report(on_brand, brand)
                if rep["verdict"] == "fail":
                    contrast_failures.append(f"{mode}:on-brand-on-brand (ratio {rep['wcag_ratio']}, Lc {rep['apca_Lc']})")
    if contrast_failures:
        warnings.append("contrast below AA/APCA: " + "; ".join(contrast_failures))

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "paradigm": paradigm,
            "targets": meta["targets"],
            "roles_present": sorted(light.keys()),
            "contrast_failures": contrast_failures,
        },
    }


# ── diagnostics / debug channel ──────────────────────────────────────────────
_SELFTEST_SPEC = {
    "name": "_selftest",
    "light": {"bg": "#ffffff", "fg": "#0a0a0a", "brand": "#2f6bff", "on-brand": "#ffffff", "danger": "#d92d20"},
    "dark": {"bg": "#0b0c0e", "fg": "#fafafa", "brand": "#5b8bff", "on-brand": "#08101f", "danger": "#f97066"},
}

_EMITTERS = {
    "dtcg": lambda ts: _tokens.build_dtcg(ts),
    "css": _tokens.emit_css,
    "tailwind": _tokens.emit_tailwind_v4,
    "shadcn": _tokens.emit_shadcn,
    "flutter": _tokens.emit_flutter,
    "flutter-material": _tokens.emit_flutter_material,
    "flutter-cupertino": _tokens.emit_flutter_cupertino,
}


def _emitter_selftest() -> dict:
    """Run every emitter on a canonical spec; report ok/error per target. Never raises."""
    ts = _tokens.TokenSpec.from_dict(_SELFTEST_SPEC)
    out: dict[str, dict] = {}
    for name, fn in _EMITTERS.items():
        try:
            result = fn(ts)
            size = len(result) if isinstance(result, str) else len(str(result))
            out[name] = {"ok": True, "bytes": size}
        except Exception as exc:  # a broken emitter must be visible, not fatal
            out[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return out


def diagnostics(applied_ledger: dict | None = None) -> dict:
    """A single debug channel: what the pipeline has persisted + a live emitter self-test.

    `applied_ledger` is the surface's idempotency ledger (key → do_ result); passed in so
    this stays pure (no global reads). Returns environment info, a per-paradigm preflight
    roll-up, the ledger summary, and per-emitter health.
    """
    ledger = applied_ledger or {}
    writes = []
    for key, res in ledger.items():
        writes.append({
            "idempotency_key": key,
            "status": res.get("status"),
            "files": res.get("applied_value", []),
            "compensation_hint": res.get("compensation_hint"),
        })

    selftest = _emitter_selftest()
    return {
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "playwright": _has_playwright(),
        },
        "paradigms": {p: preflight(p)["ready"] for p in PARADIGMS},
        "ledger": {"total_writes": len(writes), "entries": writes},
        "emitter_selftest": selftest,
        "emitters_ok": all(v["ok"] for v in selftest.values()),
    }


def _has_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False
