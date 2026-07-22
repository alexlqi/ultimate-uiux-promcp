# Design lifecycle — deterministic UX for a layout

Every layout has an explicit stage so you (and the user driving you) always know *where a
design is* and *whether it is finished enough to move on*. State is tracked per
**`(layout_id, paradigm)`** — the same layout can be `locked` for `web` while still `draft`
for `flutter-cupertino`.

## The three stages

| Stage | Meaning | `finished_enough`? |
|-------|---------|--------------------|
| `draft` | being worked on; spec may be incomplete or invalid | no |
| `ready` | passed `validate_spec` — a real, buildable design you can move on from | yes |
| `locked` | frozen; refuses silent edits until you pick a change-path | yes |

## Transitions (`do_lifecycle_transition`, `action=…`)

```
draft ──mark_ready──▶ ready ──lock──▶ locked
  ▲                     │               │
  └───────unlock────────┴───────────────┘
                 branch ─▶ new layout_id @ draft   (original stays frozen)
                 amend  ─▶ same id, version+1 @ draft (locked snapshot preserved)
```

- **`mark_ready`** — runs `health.validate_spec(spec, paradigm)`. Only a valid spec becomes
  `ready`. Invalid → `status: "failed"` (reason + allowed actions in `applied_value`); nothing changes.
- **`lock`** — only a `ready` layout can be locked. Freezes the spec as a baseline.
- **`unlock` / `branch` / `amend`** — the three ways to change a *locked* layout (below).

## When a layout is locked

The MCP will not silently edit a locked layout. Instead every channel reports it and offers
the same three **change-paths**:

- **`read_lifecycle_state(layout_id, paradigm)`** → `stage: "locked"` + `available_paths`.
- **`can_do__feasibility`** with `semantic_tags: ["modify_layout"]`, context `{layout_id, paradigm}`
  → a `blocked` entry carrying `change_paths`.
- **`do_write_token_files`** targeting a locked layout → `status: "failed"`, writes nothing (the
  change-paths are in `compensation_hint`).

The change-paths:

1. **Unlock in place** — `action="unlock"`: reopen for editing (reversible; re-`lock` when done).
2. **Branch to a new layout** — `action="branch", new_layout_id="…"`: clone the frozen spec into a
   new id that starts at `draft`; the locked original is kept as a baseline.
3. **Amend as a new version** — `action="amend"`: bump the version on the same id and reopen for
   editing, preserving the locked snapshot for diff/rollback.

## Typical flow

```
mark_ready → read_lifecycle_state (finished_enough: true) → lock
  → later: read_lifecycle_state (locked + available_paths)
  → do_write_token_files (blocked) → unlock | branch | amend → edit → mark_ready → …
```

State persists to disk (`UIDESIGN_STATE`, default `.uidesign/lifecycle.json`), so locks and
stages survive server restarts.

## Restriction modes

A single global mode dials the whole lifecycle machinery up or down. Set it with
`do_set_restriction_mode(mode, idempotency_key)`; observe the active mode, its flags, and the
recent event log in `read_diagnostics` (`value.restriction`). The mode persists to disk
(`UIDESIGN_CONFIG`, default `.uidesign/config.json`); the event log is JSONL at `UIDESIGN_LOG`
(default `.uidesign/events.log`).

| mode | logging | FSM tracked | lock blocks writes | meaning |
|------|---------|-------------|--------------------|---------|
| `none` | off | off | no | machinery fully bypassed — pre-lifecycle behavior |
| `low` | on | off | no | events logged; no stage tracking or enforcement |
| `mid` **(default)** | on | on | no (advisory) | full FSM + logs, but a lock only *warns* on write |
| `high` | on | on | yes | full restrictive — a lock hard-blocks writes |

How each mode changes the two `do_` tools:

- **`do_write_token_files`** — in `high`, writing a locked layout is refused (`status: "failed"`,
  nothing written). In `mid`, it writes anyway but returns `status: "partial"` with a locked
  advisory in `compensation_hint`. In `low`/`none`, the lock is never consulted.
- **`do_lifecycle_transition`** — in `none`/`low` the FSM is off, so a call is a logged no-op
  (`status: "success"`, `applied_value.fsm_enabled: false`) and nothing is tracked; raise the mode
  to `mid`/`high` to actually advance the machine.

Default is `mid`, so a lock is **advisory by default** — set mode `high` to make locks enforce.
