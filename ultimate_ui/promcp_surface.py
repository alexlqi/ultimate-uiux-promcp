"""ProMCP triadic surface for the ultimate-ui-design pipeline.

This layer wraps the pure core (contrast/tokens/audit/extract) in ProMCP contract
decorators, following the read/do distinction precisely:

  can_do   — singleton feasibility gate (does a capability's precondition hold?)
  read_*   — side-effect-free OBSERVATIONS: compute contrast, materialize token text,
             extract a site's tokens, audit code, read knowledge. Nothing is persisted.
  do_*     — MUTATIONS with an idempotency_key and compensation. Here the only true
             mutation is persisting token files to disk (compensable: delete them).

Generation is a read (pure); persistence is a do (side effect). That separation is the
whole point of the triadic convention — it makes the surface honest about what touches
the world. All tools register into a dedicated Registry for linting and transport export.

Author: Alejandro Andrade (@alexlqi) — github.com/alexlqi
"""
import json
import os
import time
from pathlib import Path

from promcp import can_do_tool, do_tool, read_tool
from promcp.registry import Registry

from ultimate_ui import audit as _audit
from ultimate_ui import contrast as _contrast
from ultimate_ui import extract as _extract
from ultimate_ui import health as _health
from ultimate_ui import lifecycle as _lifecycle
from ultimate_ui import tokens as _tokens

# Dedicated registry (not the global default) so this surface is independently lintable.
registry = Registry(name="ultimate-ui-design")

KNOWLEDGE = Path(__file__).parent / "knowledge"
_STAGES = {
    "intelligence": "design-intelligence.md", "tokens": "tokens.md", "brand": "brand.md",
    "extract": "extract.md", "image-to-code": "image-to-code.md", "motion": "motion.md",
    "audit": "web-guidelines.md", "web-stack": "web-stack.md", "flutter": "flutter.md",
    "flutter-material": "flutter-material.md", "flutter-cupertino": "flutter-cupertino.md",
    "email": "email.md", "lifecycle": "lifecycle.md",
}

# Capabilities the can_do gate reasons about, with their precondition checks.
_CAPABILITIES = {
    "extract_design_system": lambda ctx: _extract.playwright_available(),
    "write_token_files":     lambda ctx: _writable(ctx.get("output_dir", ".")),
    "generate_tokens":       lambda ctx: bool(ctx.get("has_required_roles", True)),
    "audit_ui":              lambda ctx: True,
    "check_contrast":        lambda ctx: True,
    # horizontal stability gates: a mobile/web build is feasible when its toolchain is ready
    "build_paradigm":        lambda ctx: _health.preflight(ctx.get("paradigm", "web"))["ready"],
    "validate_spec":         lambda ctx: True,
    "diagnostics":           lambda ctx: True,
    # lifecycle gates (mode-aware): a lock only blocks edits in 'high'; locking needs the
    # FSM enabled (mid/high) and a 'ready' layout.
    "modify_layout":         lambda ctx: not (
                                 _lifecycle.mode_flags(_current_mode())["blocking"]
                                 and _lifecycle.is_locked(_load_lifecycle(),
                                     ctx.get("layout_id", "default"), ctx.get("paradigm", "web"))),
    "lock_layout":           lambda ctx: (
                                 _lifecycle.mode_flags(_current_mode())["fsm"]
                                 and _lifecycle.state_of(_load_lifecycle(),
                                     ctx.get("layout_id", "default"),
                                     ctx.get("paradigm", "web"))["stage"] == "ready"),
}


def _writable(path: str) -> bool:
    try:
        p = Path(path)
        return p.exists() and p.is_dir() or not p.exists()
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# can_do — singleton feasibility gate
# ─────────────────────────────────────────────────────────────────────────────
@can_do_tool(
    description=(
        "Check feasibility of an intended UI-pipeline capability before acting. "
        "intent = {'semantic_tags': [<capability>...], optional 'context': {...}}. "
        "Capabilities: extract_design_system, write_token_files, generate_tokens, audit_ui, "
        "check_contrast, build_paradigm, validate_spec, diagnostics, modify_layout, lock_layout. "
        "For modify_layout/lock_layout pass context {'layout_id','paradigm'}; a locked layout is "
        "reported blocked with the change-paths to unlock/branch/amend. Call before "
        "do_write_token_files or do_lifecycle_transition when a precondition is uncertain."
    ),
    registry=registry,
)
def can_do(intent: dict, scope: list = None) -> dict:
    tags = intent.get("semantic_tags") or ([intent["capability"]] if "capability" in intent else [])
    ctx = intent.get("context", {})
    candidates, blocked = [], []
    for tag in tags:
        check = _CAPABILITIES.get(tag)
        if check is None:
            blocked.append({"capability": tag, "source": "ultimate-ui-design",
                            "permission": "denied", "reason": f"unknown capability '{tag}'"})
            continue
        ok = check(ctx)
        if ok:
            candidates.append({"capability": tag, "source": "ultimate-ui-design",
                               "confidence": 1.0, "permission": "allowed",
                               "valid_until": _iso_in(300)})
        else:
            extra = {}
            if tag == "extract_design_system":
                reason = "Playwright not installed (pip install playwright && playwright install chromium)"
            elif tag == "build_paradigm":
                pf = _health.preflight(ctx.get("paradigm", "web"))
                reason = "toolchain not ready: " + ("; ".join(pf["blockers"]) or "unknown paradigm")
            elif tag == "modify_layout":
                entry = _lifecycle.state_of(_load_lifecycle(), ctx.get("layout_id", "default"),
                                            ctx.get("paradigm", "web"))
                reason = (f"layout '{entry['layout_id']}' ({entry['paradigm']}) is locked — "
                          "edits are frozen; choose a change-path")
                extra["change_paths"] = _lifecycle.change_paths(entry)
            elif tag == "lock_layout":
                if not _lifecycle.mode_flags(_current_mode())["fsm"]:
                    reason = (f"FSM disabled in restriction mode '{_current_mode()}' — "
                              "raise to 'mid' or 'high' (do_set_restriction_mode) to lock layouts")
                else:
                    entry = _lifecycle.state_of(_load_lifecycle(), ctx.get("layout_id", "default"),
                                                ctx.get("paradigm", "web"))
                    reason = (f"layout '{entry['layout_id']}' ({entry['paradigm']}) is '{entry['stage']}', "
                              "not 'ready' — run do_lifecycle_transition(action='mark_ready') first")
            else:
                reason = "precondition not met"
            blocked.append({"capability": tag, "source": "ultimate-ui-design",
                            "permission": "denied", "reason": reason, **extra})
    return {"candidates": candidates, "blocked": blocked}


def _iso_in(seconds: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + seconds))


# ─────────────────────────────────────────────────────────────────────────────
# read_* — observations (no side effects)
# ─────────────────────────────────────────────────────────────────────────────
@read_tool(
    description=("Read the design-knowledge reference for a pipeline stage. Stages: "
                 "intelligence, tokens, brand, extract, image-to-code, motion, audit, "
                 "web-stack, flutter (adaptive), flutter-material (Android/MD3), "
                 "flutter-cupertino (iOS/HIG), email (bulletproof HTML email). Read the "
                 "stage before building it. Not for live web data."),
    registry=registry,
)
def read_design_reference(stage: str) -> dict:
    fname = _STAGES.get(stage)
    if not fname:
        return {"value": f"Unknown stage '{stage}'. Options: {', '.join(_STAGES)}", "quality": "error"}
    return {"value": (KNOWLEDGE / fname).read_text(encoding="utf-8")}


@read_tool(
    description=("Fetch the CURRENT Vercel Web Interface Guidelines (live network read). "
                 "Use before a serious audit. Quality=degraded if the network fetch fails."),
    registry=registry,
)
def read_web_guidelines() -> dict:
    try:
        return {"value": _audit.fetch_guidelines()}
    except Exception:
        fallback = (KNOWLEDGE / "web-guidelines.md").read_text(encoding="utf-8")
        return {"value": fallback, "quality": "degraded"}


@read_tool(
    description=("Observe WCAG 2.1 ratio AND APCA Lc for a foreground/background color pair, "
                 "with a pass/fail verdict. Colors in sRGB hex or rgb(). Measured, not estimated."),
    unit="wcag_ratio+apca_Lc",
    registry=registry,
)
def read_contrast(foreground: str, background: str, large_text: bool = False) -> dict:
    return {"value": _contrast.contrast_report(foreground, background, large=large_text)}


@read_tool(
    description=("Audit UI source with deterministic anti-slop / a11y heuristics. Input is "
                 "{path: source}. Returns file:line findings grouped by severity. Pair with "
                 "read_web_guidelines for judgment-level review."),
    registry=registry,
)
def read_ui_audit(files: dict) -> dict:
    return {"value": _audit.audit_source(files)}


@read_tool(
    description=("Materialize a token spec into file TEXT in-memory (returned as a value, never "
                 "touching disk): DTCG tokens.json, tokens.css, Tailwind v4 @theme, shadcn "
                 ":root/.dark, and three Flutter verticals — 'flutter' (adaptive), "
                 "'flutter-material' (Material 3 / Android: seeded ColorScheme, 8-dp grid, "
                 "ThemeExtension) and 'flutter-cupertino' (HIG / iOS: CupertinoThemeData, "
                 "44-pt targets, AppTokensScope), and 'email' (bulletproof responsive HTML email: "
                 "XHTML doctype, table layout, MSO ghost tables + VML button, prefers-color-scheme + "
                 "[data-ogsc] dark mode, CAN-SPAM/GDPR footer). targets from {dtcg,css,tailwind,shadcn,"
                 "flutter,flutter-material,flutter-cupertino,email}; default = web + adaptive bundle. "
                 "Includes a full light+dark contrast self-check. To persist, hand the result to the do_* action."),
    registry=registry,
)
def read_generated_tokens(spec: dict, targets: list = None) -> dict:
    return {"value": _materialize(spec, targets)}


@read_tool(
    description=("Extract design primitives from a PUBLIC site's live DOM into a token-spec "
                 "seed (colors, fonts, radii, shadows). Requires Playwright; check via can_do "
                 "first. Heuristic — confirm the summary before adopting. Quality=degraded on partial."),
    registry=registry,
)
def read_extracted_design_system(url: str) -> dict:
    try:
        return {"value": _extract.extract_tokens(url)}
    except Exception as exc:
        return {"value": {"error": str(exc)}, "quality": "error"}


@read_tool(
    description=("Preflight/doctor for a build paradigm: is its toolchain present? paradigm ∈ "
                "{web, flutter-material, flutter-cupertino, email}. Returns {ready, checks, blockers, "
                "warnings} — blockers stop a real build, warnings degrade (e.g. iOS build tools "
                "absent off macOS; email needs no toolchain but warns to verify in Litmus/Email on "
                "Acid). Run before scaffolding a stack."),
    registry=registry,
)
def read_preflight(paradigm: str = "web") -> dict:
    pf = _health.preflight(paradigm)
    quality = "good" if pf["ready"] else ("degraded" if paradigm in _health.PARADIGMS else "error")
    return {"value": pf, "quality": quality}


@read_tool(
    description=("Validate a token spec BEFORE persisting it (fault-tolerance gate). Checks required "
                "roles exist and parse, colors are valid sRGB, dark mode present, soft-role fallbacks, "
                "and AA/APCA contrast — per paradigm {web, flutter-material, flutter-cupertino, email}. Returns "
                "{valid, errors, warnings, summary}. On errors ⇒ do NOT persist yet (skip the do_ action)."),
    registry=registry,
)
def read_spec_validation(spec: dict, paradigm: str = "web") -> dict:
    rep = _health.validate_spec(spec, paradigm)
    return {"value": rep, "quality": "good" if rep["valid"] else "degraded"}


@read_tool(
    description=("Diagnostics/debug channel: one call surfaces the environment, per-paradigm "
                "readiness roll-up, the persist-action idempotency ledger (which files were applied, "
                "with compensation hints), and a live self-test running every emitter. Use to debug "
                "'what did the pipeline do?' and 'is any emitter broken?' without reading internals."),
    registry=registry,
)
def read_diagnostics() -> dict:
    rep = _health.diagnostics(_APPLIED)
    mode = _current_mode()
    rep["restriction"] = {"mode": mode, "flags": _lifecycle.mode_flags(mode),
                          "recent_events": _recent_events()}
    return {"value": rep, "quality": "good" if rep["emitters_ok"] else "degraded"}


@read_tool(
    description=("Observe a layout's design-lifecycle stage (draft → ready → locked), tracked per "
                 "(layout_id, paradigm). With no args: a roll-up of every tracked layout — which are "
                 "finished_enough (ready/locked) to move on from, which remain in progress. With "
                 "layout_id (+ optional paradigm): that layout's stage, whether it is finished_enough, "
                 "the valid next actions, and — when locked — the available_paths to change it "
                 "(unlock / branch / amend). Purely observational; changes go through "
                 "do_lifecycle_transition."),
    registry=registry,
)
def read_lifecycle_state(layout_id: str = None, paradigm: str = None) -> dict:
    store = _load_lifecycle()
    mode = _current_mode()
    flags = _lifecycle.mode_flags(mode)
    if layout_id is None:
        rep = _lifecycle.overview(store)
        rep["restriction_mode"] = mode
        rep["flags"] = flags
        quality = "good"
    else:
        entry = _lifecycle.state_of(store, layout_id, paradigm or "web")
        rep = {"layout_id": entry["layout_id"], "paradigm": entry["paradigm"],
               "stage": entry["stage"], "version": entry["version"],
               "finished_enough": _lifecycle.finished_enough(entry),
               "next_actions": _lifecycle.available_actions(entry),
               "available_paths": _lifecycle.change_paths(entry) if entry["stage"] == "locked" else [],
               "restriction_mode": mode, "flags": flags}
        quality = "good" if entry["stage"] != "locked" else "degraded"
    return {"value": rep, "quality": quality}


# ─────────────────────────────────────────────────────────────────────────────
# do_* — mutations (idempotency + compensation)
# ─────────────────────────────────────────────────────────────────────────────
_APPLIED: dict[str, dict] = {}       # token-write idempotency ledger: key -> result
_TRANSITIONS: dict[str, dict] = {}   # lifecycle-transition idempotency ledger: key -> result
_MODE_APPLIED: dict[str, dict] = {}  # set-restriction-mode idempotency ledger: key -> result

# The design-lifecycle FSM state, the restriction-mode config, and the event log are all
# persisted to disk so locks/stages/mode survive restarts. The surface owns this I/O;
# ultimate_ui.lifecycle stays pure (state is injected into it).
_LIFECYCLE_PATH = Path(os.environ.get("UIDESIGN_STATE", ".uidesign/lifecycle.json"))
_CONFIG_PATH = Path(os.environ.get("UIDESIGN_CONFIG", ".uidesign/config.json"))
_LOG_PATH = Path(os.environ.get("UIDESIGN_LOG", ".uidesign/events.log"))  # JSONL, append-only


def _load_lifecycle() -> dict:
    try:
        return json.loads(_LIFECYCLE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _save_lifecycle(store: dict) -> None:
    _LIFECYCLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LIFECYCLE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _current_mode() -> str:
    """The active restriction mode: persisted config → UIDESIGN_MODE env → default 'mid'."""
    try:
        mode = json.loads(_CONFIG_PATH.read_text(encoding="utf-8")).get("mode")
        if mode in _lifecycle.MODES:
            return mode
    except (FileNotFoundError, ValueError):
        pass
    env = os.environ.get("UIDESIGN_MODE")
    return env if env in _lifecycle.MODES else _lifecycle.DEFAULT_MODE


def _save_mode(mode: str) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps({"mode": mode}, indent=2), encoding="utf-8")


def _log(event: str, detail: dict) -> None:
    """Append one JSONL event — a no-op unless the active mode enables logging."""
    if not _lifecycle.mode_flags(_current_mode())["logs"]:
        return
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": _iso_in(0), "event": event, "detail": detail}) + "\n")


def _recent_events(n: int = 20) -> list:
    try:
        lines = _LOG_PATH.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


@do_tool(
    description=("Persist generated token files to a directory. This is the pipeline's only "
                 "true mutation (it writes to disk). Idempotent by key; compensable by deleting "
                 "the written files. targets subset of {dtcg,css,tailwind,shadcn,flutter,"
                 "flutter-material,flutter-cupertino,email}. Honors "
                 "the restriction mode (see do_set_restriction_mode): in 'high' a LOCKED layout "
                 "(layout_id defaults to spec.name, paradigm 'web') blocks the write (status='failed', "
                 "change-paths in compensation_hint); in 'mid' the write proceeds with status='partial' "
                 "and a locked advisory; 'low'/'none' never block."),
    compensable=True,
    side_effects=["token_files_written"],
    compensation_hint_template="rm -f {written_files}",
    registry=registry,
)
def do_write_token_files(
    spec: dict,
    output_dir: str,
    idempotency_key: str,
    targets: list = None,
    layout_id: str = None,
    paradigm: str = "web",
) -> dict:
    if idempotency_key in _APPLIED:
        return _APPLIED[idempotency_key]  # idempotent replay

    lid = layout_id or spec.get("name", "default")
    mode = _current_mode()
    flags = _lifecycle.mode_flags(mode)
    locked = flags["fsm"] and _lifecycle.is_locked(_load_lifecycle(), lid, paradigm)

    if locked and flags["blocking"]:  # high: hard-block, write nothing
        entry = _lifecycle.state_of(_load_lifecycle(), lid, paradigm)
        paths = "; ".join(p["action"] for p in _lifecycle.change_paths(entry))
        _log("write_blocked", {"layout": lid, "paradigm": paradigm, "mode": mode})
        result = {
            "status": "failed",
            "applied_value": [],
            "previous_value": sorted(_lifecycle.change_paths(entry), key=lambda p: p["action"]),
            "compensation_hint": (f"layout '{lid}' ({paradigm}) is locked - no files written. "
                                  f"To change it use do_lifecycle_transition action in {{{paths}}}."),
        }
        _APPLIED[idempotency_key] = result
        return result

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    materialized = _materialize(spec, targets)
    filename_map = {
        "tokens.json": "tokens.json",
        "tokens.css": "tokens.css",
        "app.css (tailwind v4 @theme)": "app.tailwind.css",
        "shadcn.css (:root/.dark)": "shadcn.css",
        "app_theme.dart": "app_theme.dart",
        "app_theme.dart (material 3 / android)": "app_theme_material.dart",
        "app_theme.dart (cupertino / ios)": "app_theme_cupertino.dart",
        "email.html": "email.html",
    }
    previously = sorted(str(p) for p in out.iterdir()) if out.exists() else []
    written = []
    for label, content in materialized.items():
        if label.startswith("_"):
            continue
        fname = filename_map.get(label, label.replace(" ", "_"))
        (out / fname).write_text(content, encoding="utf-8")
        written.append(str(out / fname))

    hint = "rm -f " + " ".join(written)
    if locked:  # mid: nonblocking override — wrote anyway, but flag it
        status = "partial"
        hint += (f" | ADVISORY: layout '{lid}' ({paradigm}) is locked (mode '{mode}') - "
                 "wrote anyway; set mode 'high' to enforce the lock")
        _log("write_over_lock", {"layout": lid, "paradigm": paradigm, "mode": mode, "files": written})
    else:
        status = "success"
    if flags["logs"]:
        _log("write", {"layout": lid, "paradigm": paradigm, "mode": mode, "files": written})

    result = {
        "status": status,
        "applied_value": written,
        "previous_value": previously,
        "compensation_hint": hint,
    }
    _APPLIED[idempotency_key] = result
    return result


_REVERSE_HINT = {
    "mark_ready": "re-edit the spec and mark_ready again (validation is not a state you undo)",
    "lock":       "do_lifecycle_transition(action='unlock') to reopen for editing",
    "unlock":     "do_lifecycle_transition(action='lock') to re-freeze (layout must be 'ready')",
    "branch":     "remove the new layout entry from lifecycle state (delete its key)",
    "amend":      "the previous locked snapshot is preserved on the entry for diff/rollback",
}


@do_tool(
    description=("Advance a layout's design-lifecycle FSM, tracked per (layout_id, paradigm). "
                 "action ∈ {mark_ready, lock, unlock, branch, amend}: mark_ready validates the spec "
                 "and marks the layout finished-enough; lock freezes a ready layout; unlock reopens a "
                 "locked one; branch clones the frozen spec into new_layout_id; amend bumps the version "
                 "and reopens, preserving the locked snapshot. Idempotent by key; compensable (each "
                 "transition has a reverse). Invalid transitions return status='failed' with the "
                 "allowed actions and change-paths in applied_value — no state changes. State persists to disk."),
    compensable=True,
    side_effects=["lifecycle_state_written"],
    compensation_hint_template="{reverse_transition}",
    registry=registry,
)
def do_lifecycle_transition(
    layout_id: str,
    paradigm: str,
    action: str,
    idempotency_key: str,
    spec: dict = None,
    new_layout_id: str = None,
) -> dict:
    if idempotency_key in _TRANSITIONS:
        return _TRANSITIONS[idempotency_key]  # idempotent replay

    mode = _current_mode()
    flags = _lifecycle.mode_flags(mode)
    if not flags["fsm"]:  # none/low: FSM disabled — logged no-op, not tracked, not cached
        _log("transition_attempt", {"layout": layout_id, "paradigm": paradigm,
                                     "action": action, "mode": mode})
        return {
            "status": "success",
            "applied_value": {"fsm_enabled": False, "mode": mode,
                              "note": "FSM disabled in this mode; transition not tracked"},
            "previous_value": {},
            "compensation_hint": "raise restriction mode to 'mid' or 'high' to track lifecycle",
        }

    store = _load_lifecycle()
    res = _lifecycle.transition(store, layout_id, paradigm, action,
                                spec=spec, new_layout_id=new_layout_id)
    if not res["ok"]:
        hint = res["reason"] + " | allowed actions: " + ", ".join(res["allowed_actions"])
        if res["change_paths"]:
            hint += " | change-paths: " + ", ".join(p["action"] for p in res["change_paths"])
        return {
            "status": "failed",
            "applied_value": {"reason": res["reason"], "allowed_actions": res["allowed_actions"],
                              "change_paths": res["change_paths"]},
            "previous_value": res["previous"],
            "compensation_hint": hint,
        }

    _save_lifecycle(res["store"])  # the one side effect: persist the advanced FSM
    _log("transition", {"layout": layout_id, "paradigm": paradigm, "action": action,
                        "stage": res["new_state"]["stage"], "mode": mode})
    result = {
        "status": "success",
        "applied_value": res["new_state"],
        "previous_value": res["previous"],
        "compensation_hint": _REVERSE_HINT.get(action, "no compensation"),
    }
    _TRANSITIONS[idempotency_key] = result
    return result


@do_tool(
    description=("Set the global design restriction mode (default 'mid'). mode ∈ "
                 "{none, low, mid, high}: none = no logging or FSM (pre-lifecycle behavior); "
                 "low = event logging only; mid = logging + FSM with an ADVISORY (nonblocking) "
                 "lock; high = logging + FSM with a hard-blocking lock. Governs do_write_token_files "
                 "and do_lifecycle_transition. Persisted to disk; observe it via read_diagnostics. "
                 "Idempotent by key; compensable by setting the previous mode."),
    compensable=True,
    side_effects=["restriction_mode_set"],
    compensation_hint_template="do_set_restriction_mode(mode='{previous_mode}')",
    registry=registry,
)
def do_set_restriction_mode(mode: str, idempotency_key: str) -> dict:
    if idempotency_key in _MODE_APPLIED:
        return _MODE_APPLIED[idempotency_key]  # idempotent replay

    if mode not in _lifecycle.MODES:
        return {
            "status": "failed",
            "applied_value": {"invalid_mode": mode, "allowed_modes": list(_lifecycle.MODES)},
            "previous_value": {"mode": _current_mode()},
            "compensation_hint": f"choose mode in {{{', '.join(_lifecycle.MODES)}}}",
        }

    previous = _current_mode()
    _save_mode(mode)
    _log("mode_change", {"from": previous, "to": mode})  # silent when new mode is 'none'
    result = {
        "status": "success",
        "applied_value": {"mode": mode, "flags": _lifecycle.mode_flags(mode)},
        "previous_value": {"mode": previous},
        "compensation_hint": f"do_set_restriction_mode(mode='{previous}')",
    }
    _MODE_APPLIED[idempotency_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# shared helpers (pure) — used by read_* and do_*
# ─────────────────────────────────────────────────────────────────────────────
def _token_contrast(spec: dict) -> dict:
    out = {"light": {}, "dark": {}, "failures": []}
    for mode in ("light", "dark"):
        colors = spec.get(mode) or spec.get("light", {})
        bg = colors.get("bg", "#ffffff")
        for role in ("fg", "muted-fg", "brand", "on-brand"):
            if role in colors:
                pair_bg = colors.get("brand", bg) if role == "on-brand" else bg
                rep = _contrast.contrast_report(colors[role], pair_bg)
                out[mode][f"{role}-on-{'brand' if role == 'on-brand' else 'bg'}"] = rep
                if rep["verdict"] == "fail":
                    out["failures"].append(f"{mode}:{role} (ratio {rep['wcag_ratio']}, Lc {rep['apca_Lc']})")
    out["passed"] = not out["failures"]
    return out


def _materialize(spec: dict, targets) -> dict:
    ts = _tokens.TokenSpec.from_dict(spec)
    targets = targets or ["dtcg", "css", "tailwind", "shadcn", "flutter"]
    out: dict = {}
    if "dtcg" in targets:
        out["tokens.json"] = json.dumps(_tokens.build_dtcg(ts), indent=2)
    if "css" in targets:
        out["tokens.css"] = _tokens.emit_css(ts)
    if "tailwind" in targets:
        out["app.css (tailwind v4 @theme)"] = _tokens.emit_tailwind_v4(ts)
    if "shadcn" in targets:
        out["shadcn.css (:root/.dark)"] = _tokens.emit_shadcn(ts)
    if "flutter" in targets:
        out["app_theme.dart"] = _tokens.emit_flutter(ts)
    if "flutter-material" in targets:
        out["app_theme.dart (material 3 / android)"] = _tokens.emit_flutter_material(ts)
    if "flutter-cupertino" in targets:
        out["app_theme.dart (cupertino / ios)"] = _tokens.emit_flutter_cupertino(ts)
    if "email" in targets:
        out["email.html"] = _tokens.emit_email(ts)
    out["_contrast_check"] = _token_contrast(spec)
    return out
