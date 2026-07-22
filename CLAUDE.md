# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A token-first UI design pipeline exposed as a **ProMCP-native** MCP server. It runs over
`promcp>=0.3.0`, which sits over `fastmcp>=3.4,<4`. The server helps an LLM design and
build UIs across four deterministic **paradigm verticals** — `web` (React + Tailwind v4 +
shadcn/ui), `flutter-material` (Flutter/Material 3, Android), `flutter-cupertino`
(Flutter/Cupertino·HIG, iOS), and `email` (bulletproof responsive HTML email for
Outlook/Gmail/Apple Mail) — where design tokens are the single source of truth. A horizontal
stability layer (preflight, spec validation, diagnostics) makes builds fast and fault-tolerant.

## Docs

- `README.md` — user-facing guide (install, connect, use the prompts). Written for people who
  *use* the server, not extend it.
- `ARCHITECTURE.md` — the internal/technical reference: the triadic contract convention, the
  plain-MCP → ProMCP rationale, the transport coupling boundary, and the ProMCP-clean linter.
  This file (`CLAUDE.md`) is the condensed working guide; `ARCHITECTURE.md` is its prose companion —
  keep the two consistent when the surface or layering changes.

## Commands

```bash
# Install from source (end users use `uvx ultimate-ui-design-promcp` instead)
pip install "promcp>=0.3.0,<0.4" "fastmcp>=3.4,<4"
pip install playwright && playwright install chromium   # only for read_extracted_design_system

python server.py                                    # run the server (stdio transport)

PYTHONPATH=. python tests/test_core.py              # run tests (self-contained runner, no pytest)
pytest                                              # tests also run under pytest (pythonpath="." configured)
pytest tests/test_core.py::test_emitters            # run a single test

PYTHONPATH=. python -c "from server import lint; lint()"   # ProMCP linter over the registry
```

`PYTHONPATH=.` matters: modules import `from ultimate_ui import ...` and `from server import ...`
with the repo root on the path. `pyproject.toml` sets `pythonpath = ["."]` so pytest works without it.

## Architecture

The whole design is a **contract-first layering with exactly one transport coupling boundary**.
Understanding these four layers (top imports down, never up) is the key to being productive:

```
domain (pure core: contrast / tokens / audit / extract)   ← no MCP knowledge at all
   └── ProMCP triadic surface  (@can_do_tool / @read_tool / @do_tool)   ← ultimate_ui/promcp_surface.py
         └── promcp.transport adapter  (adds can_do__/read__/do__ prefixes)  ← server.py wires it
               └── FastMCP  (MCP plumbing)                                    ← reached only via .raw
```

**Nothing outside `promcp.transport` imports `fastmcp`.** Resources and prompts are attached
through the adapter's one deliberate escape hatch, `server.raw`. To audit transport coupling,
grep for `.raw`.

### The triadic contract convention (this is the core mental model)

ProMCP forces an honest read/do distinction. Every tool is exactly one of three categories,
and the category is enforced at **decoration time** (fail-fast — a misprefixed name or a `do_*`
missing `idempotency_key` raises before the server can start):

- **`can_do`** — a *singleton* feasibility gate. There is exactly ONE (`can_do` in
  `promcp_surface.py`, exposed as `can_do__feasibility`). It takes an intent with
  `semantic_tags` and returns `{candidates, blocked}`; `feasible` is auto-calculated.
  Capabilities and their precondition checks live in the `_CAPABILITIES` dict.
- **`read_*`** — side-effect-free **observations**, auto-wrapped in the
  `{value, timestamp, quality, unit}` contract. Includes pure computation (`read_contrast`),
  in-memory text materialization (`read_generated_tokens`), network reads
  (`read_web_guidelines`, `read_extracted_design_system`), code inspection (`read_ui_audit`),
  and the **horizontal stability layer** — `read_preflight` (per-paradigm toolchain doctor),
  `read_spec_validation` (gate a spec before persisting), `read_diagnostics` (one debug channel:
  ledger + per-paradigm readiness + live emitter self-test).
- **`do_*`** — **mutations** requiring an `idempotency_key`, auto-wrapped in the
  `{status, compensable, applied_value, previous_value, compensation_hint}` contract.

The load-bearing insight: **generation is a `read`, persistence is the one `do`.**
`read_generated_tokens` produces file *text* in memory (touches nothing);
`do_write_token_files` is the ONLY tool that writes to disk. It is idempotent by key (see the
`_APPLIED` ledger) and compensable (`compensation_hint: rm -f <written files>`). When adding a
tool, decide honestly which category it is — if it touches the world it's a `do_` and needs a key.

### Domain core (`ultimate_ui/`, no MCP knowledge)

- `contrast.py` — pure WCAG 2.1 ratio + APCA Lc math. Verifiable numbers, not estimates.
- `tokens.py` — `TokenSpec` dataclass + emitters. One design decision → deterministic files.
  **Four paradigm verticals**, each its own emitter: web (`emit_css`, `emit_tailwind_v4`,
  `emit_shadcn`) + DTCG (`build_dtcg`); Android (`emit_flutter_material` → MD3: seeded
  `ColorScheme.fromSeed` with spec roles pinned, 8-dp grid, 48-dp touch floor, `ThemeExtension`);
  iOS (`emit_flutter_cupertino` → HIG: `CupertinoThemeData`, 44-pt floor, `AppTokensScope`
  InheritedWidget); email (`emit_email` → one `email.html`: XHTML 1.0 + `xmlns:v`/`xmlns:o`, MSO
  DPI/ghost tables, inline styles, a VML+anchor bulletproof button, `prefers-color-scheme` +
  `[data-ogsc]`/`[data-ogsb]` dark mode, fluid-hybrid columns that survive Gmail head-stripping,
  and a CAN-SPAM/GDPR footer). `emit_flutter` (adaptive/combined) is kept for backward
  compatibility. Same input always yields the same output (reviewable/diffable).
- `health.py` — the horizontal stability layer (pure observations): `preflight(paradigm)` doctors
  a paradigm's toolchain; `validate_spec(spec, paradigm)` catches malformed specs before the `do_`;
  `diagnostics(ledger)` is the debug channel. `PARADIGMS` maps each vertical → its emitter targets
  + required/soft roles. Failures are structured data with severity + fix hints, never tracebacks.
- `audit.py` — fetches the live Vercel Web Interface Guidelines + runs deterministic anti-slop/
  a11y heuristics over source, returning `file:line` findings. Judgment-level review is left to
  the model reading the guidelines resource.
- `extract.py` — Playwright headless Chromium reads *computed* styles from a public site's DOM,
  normalizing into the same `TokenSpec` shape the generator consumes. Playwright is optional;
  its absence is reported by `can_do`, not a cryptic failure.

### Registration flow (`server.py`)

Tools are registered into a **dedicated `Registry`** (in `promcp_surface.py`, not the global
default) so the surface is independently lintable. `build_server()` iterates `registry.all()`
and dispatches each entry through `_CATEGORY_REGISTRARS` (maps category → the transport's
`register_can_do/register_read/register_do`, which apply the `can_do__`/`read__`/`do__` prefixes).
Resources (`uidesign://reference/{stage}`) and prompts (`design_pipeline`, `audit_only`) are
attached via `server.raw` because they're not part of the triadic *tool* surface.

## Conventions when extending

- The `_STAGES` dict maps stage names → knowledge markdown files in `ultimate_ui/knowledge/`.
  It is referenced by both `read_design_reference` and the `uidesign://reference/{stage}` resource —
  keep them in sync.
- Token specs must supply sRGB hex for color roles (`bg`, `fg`, `brand` required) so contrast is
  checkable. `_materialize` always appends a `_contrast_check` (full light+dark self-check).
- A **paradigm** is the unit of vertical determinism: `web`, `flutter-material`, `flutter-cupertino`,
  `email`. `health.PARADIGMS` is the single source for each vertical's emitter targets + role expectations;
  `read_generated_tokens`/`do_write_token_files` select emitters by `targets`, and the emitted
  Flutter filenames are distinct (`app_theme_material.dart` / `app_theme_cupertino.dart`) so all
  three Flutter variants can coexist. Each paradigm also has a knowledge stage in `_STAGES`.
- Keep `PYTHONPATH=. python -c "from server import lint; lint()"` at **0 errors and 0 tool-level
  warnings**. The one tolerated finding is the **global S004** surface-size advisory: the stability
  layer intentionally pushes the surface past 8 tools. `test_core.py::test_promcp_lint_is_clean`
  asserts 0 errors + no warnings *other than S004*; contract violations still fail fast at import.
