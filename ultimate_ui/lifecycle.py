"""Design-lifecycle FSM (pure domain) — deterministic UX for a layout's progress.

A layout moves through three stages, tracked per (layout_id, paradigm) so the same
layout can be locked for `web` while still a draft for `flutter-cupertino`:

    draft ──mark_ready──▶ ready ──lock──▶ locked
      ▲                     │               │
      └──────unlock─────────┴───────────────┘   (unlock reopens for editing)
                     branch  ─▶ new layout_id @ draft   (keep original frozen)
                     amend   ─▶ same layout_id, version+1 @ draft (snapshot preserved)

Guards make the machine honest: you can only reach `ready` when `health.validate_spec`
passes ("finished enough"), and you can only `lock` a layout that is `ready`. A locked
layout refuses silent edits; the caller is offered explicit change-paths instead.

This module is PURE: it never touches disk or MCP. The surface (`promcp_surface.py`)
owns the persistent store and injects it here, mirroring how `health.diagnostics` takes
the idempotency ledger as a parameter. No import of anything above the domain layer.

Author: Alejandro Andrade (@alexlqi) — github.com/alexlqi
"""
from ultimate_ui import health as _health

__all__ = ["STATES", "MODES", "DEFAULT_MODE", "mode_flags", "key", "default_entry",
           "state_of", "finished_enough", "is_locked", "available_actions",
           "change_paths", "transition", "overview"]

STATES = ("draft", "ready", "locked")
_EDITABLE = ("draft", "ready")

# Global restriction modes dial the whole lifecycle machinery up or down.
MODES = ("none", "low", "mid", "high")
DEFAULT_MODE = "mid"


def mode_flags(mode: str) -> dict:
    """Decompose a restriction mode into the three switches the surface enforces.

        none → nothing (behaves like the pre-FSM server)
        low  → logging only
        mid  → logging + FSM, but a lock is advisory (nonblocking)   [default]
        high → logging + FSM, and a lock hard-blocks writes
    An unknown mode is treated as DEFAULT_MODE (defensive)."""
    if mode not in MODES:
        mode = DEFAULT_MODE
    return {"logs": mode in ("low", "mid", "high"),
            "fsm": mode in ("mid", "high"),
            "blocking": mode == "high"}


def key(layout_id: str, paradigm: str) -> str:
    return f"{layout_id}::{paradigm}"


def default_entry(layout_id: str, paradigm: str) -> dict:
    return {"layout_id": layout_id, "paradigm": paradigm, "stage": "draft",
            "version": 1, "spec": None, "validation": None, "locked_snapshot": None}


def state_of(store: dict, layout_id: str, paradigm: str) -> dict:
    """Current entry for a (layout, paradigm) — a copy, or a fresh draft default."""
    return dict(store.get(key(layout_id, paradigm)) or default_entry(layout_id, paradigm))


def finished_enough(entry: dict) -> bool:
    """True once a layout is validated (ready) or frozen (locked) — safe to move on."""
    return entry["stage"] in ("ready", "locked")


def is_locked(store: dict, layout_id: str, paradigm: str) -> bool:
    return state_of(store, layout_id, paradigm)["stage"] == "locked"


def available_actions(entry: dict) -> list:
    """Which transitions are valid from the current stage."""
    stage = entry["stage"]
    if stage == "draft":
        return ["mark_ready", "branch"]
    if stage == "ready":
        return ["lock", "mark_ready", "branch"]
    if stage == "locked":
        return ["unlock", "branch", "amend"]
    return []


def change_paths(entry: dict) -> list:
    """The explicit ways to modify a LOCKED layout — the paths the MCP offers instead
    of silently editing. Each carries the concrete do_lifecycle_transition call."""
    lid, para = entry["layout_id"], entry["paradigm"]
    return [
        {"action": "unlock",
         "label": "Unlock in place — reopen this layout for editing (reversible)",
         "call": (f"do_lifecycle_transition(layout_id={lid!r}, paradigm={para!r}, "
                  "action='unlock', idempotency_key=<key>)")},
        {"action": "branch",
         "label": "Branch to a new layout — clone the frozen spec into a new id, keep this one as baseline",
         "call": (f"do_lifecycle_transition(layout_id={lid!r}, paradigm={para!r}, "
                  "action='branch', new_layout_id='<new-id>', idempotency_key=<key>)")},
        {"action": "amend",
         "label": "Amend as a new version — bump version on this id, preserving the locked snapshot for diff",
         "call": (f"do_lifecycle_transition(layout_id={lid!r}, paradigm={para!r}, "
                  "action='amend', idempotency_key=<key>)")},
    ]


def _result(ok, store, previous, new_state, reason="", validation=None) -> dict:
    return {"ok": ok, "store": store, "previous": previous, "new_state": new_state,
            "reason": reason, "validation": validation,
            "allowed_actions": available_actions(new_state if ok else previous),
            "change_paths": change_paths(previous) if previous["stage"] == "locked" else []}


def transition(store: dict, layout_id: str, paradigm: str, action: str, *,
               spec: dict = None, new_layout_id: str = None) -> dict:
    """Pure FSM step. Returns {ok, store, previous, new_state, reason, validation,
    allowed_actions, change_paths}. `store` in the result is a NEW dict (input untouched);
    the caller persists it only when ok is True. Invalid transitions never raise — they
    return ok=False with a reason and the allowed actions / change-paths."""
    store = {k: dict(v) for k, v in store.items()}
    k = key(layout_id, paradigm)
    entry = store.get(k) or default_entry(layout_id, paradigm)
    prev = dict(entry)

    if action == "mark_ready":
        use_spec = spec if spec is not None else entry.get("spec")
        if use_spec is None:
            return _result(False, store, prev, prev, "mark_ready needs a spec to validate")
        rep = _health.validate_spec(use_spec, paradigm)
        if not rep["valid"]:
            reason = "spec not finished enough: " + "; ".join(rep["errors"])
            return _result(False, store, prev, prev, reason, validation=rep)
        entry.update(stage="ready", spec=use_spec, validation=rep["summary"])
        store[k] = entry
        return _result(True, store, prev, entry, "validated → ready", validation=rep)

    if action == "lock":
        if entry["stage"] != "ready":
            return _result(False, store, prev, prev,
                           "can only lock a 'ready' layout — run mark_ready first")
        entry.update(stage="locked", locked_snapshot=dict(entry.get("spec") or {}))
        store[k] = entry
        return _result(True, store, prev, entry, "locked (frozen)")

    if action == "unlock":
        if entry["stage"] != "locked":
            return _result(False, store, prev, prev, "nothing to unlock — layout is not locked")
        entry.update(stage="draft")
        store[k] = entry
        return _result(True, store, prev, entry, "unlocked → draft (editable)")

    if action == "branch":
        if not new_layout_id:
            return _result(False, store, prev, prev, "branch needs a new_layout_id")
        nk = key(new_layout_id, paradigm)
        if nk in store:
            return _result(False, store, prev, prev,
                           f"layout '{new_layout_id}' ({paradigm}) already exists")
        seed = dict(entry.get("locked_snapshot") or entry.get("spec") or spec or {})
        new_entry = default_entry(new_layout_id, paradigm)
        new_entry["spec"] = seed
        store[nk] = new_entry
        return _result(True, store, prev, new_entry,
                       f"branched → '{new_layout_id}' @ draft (original left frozen)")

    if action == "amend":
        if entry["stage"] != "locked":
            return _result(False, store, prev, prev, "amend applies to a locked layout")
        entry["locked_snapshot"] = dict(entry.get("locked_snapshot") or entry.get("spec") or {})
        entry.update(stage="draft", version=entry["version"] + 1)
        store[k] = entry
        return _result(True, store, prev, entry,
                       f"amended → version {entry['version']} @ draft (snapshot preserved)")

    return _result(False, store, prev, prev, f"unknown action '{action}'")


def overview(store: dict) -> dict:
    """Roll-up across all tracked layouts — answers 'what's done, what's still open?'."""
    layouts, finished, in_progress = {}, [], []
    for k, e in store.items():
        done = finished_enough(e)
        layouts[k] = {"layout_id": e["layout_id"], "paradigm": e["paradigm"],
                      "stage": e["stage"], "version": e["version"], "finished_enough": done}
        (finished if done else in_progress).append(k)
    return {"layouts": layouts, "finished": sorted(finished), "in_progress": sorted(in_progress)}
