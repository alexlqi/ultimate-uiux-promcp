# ultimate-ui-design — ProMCP server

The token-first UI design pipeline, rebuilt as a **ProMCP-native** server on top of
`promcp>=0.3.0` (which sits over `fastmcp>=3.4,<4`). Where the plain-MCP version used
FastMCP directly, this one speaks ProMCP's **triadic contract convention** end to end:

- `can_do` — a **singleton** feasibility gate (`intent → candidates/blocked`, `feasible` auto-calculated).
- `read_*` — side-effect-free **observations**, auto-wrapped in the `{value, timestamp, quality, unit}` contract.
- `do_*` — **mutations** requiring `idempotency_key`, auto-wrapped in the `{status, compensable, applied_value, previous_value, compensation_hint}` contract.

Author: Alejandro Andrade ([@alexlqi](https://github.com/alexlqi))

## What changed vs. the plain-MCP version — and why it's more correct

The plain version modeled everything as flat FastMCP tools. ProMCP forces an honest
**read/do distinction**, which reshaped the surface:

| Operation | Plain MCP | ProMCP | Rationale |
|---|---|---|---|
| Compute contrast | `do_check_contrast` | `read_contrast` | pure computation = observation |
| Materialize token files | `do_generate_tokens` | `read_generated_tokens` | returns text, touches nothing = observation |
| Extract a site | `do_extract_design_system` | `read_extracted_design_system` | network read, no mutation |
| Audit code | `do_audit_ui` | `read_ui_audit` | inspection only |
| **Persist files to disk** | (n/a) | `do_write_token_files` | the **only** real mutation — writes files |
| Feasibility | two `can_do_*` tools | one `can_do` singleton | ProMCP: exactly one feasibility gate |

Generation is a `read`; **persistence is the one `do`** — and it's idempotent by key and
compensable (`compensation_hint: rm -f <written files>`). That separation is the point of
the triadic convention: the surface is now honest about what touches the world. This is the
Harness Engineering thesis in the type system — the LLM brings taste, the contract layer
makes side effects explicit, reversible, and auditable.

## Architecture (contract-first, one coupling boundary)

```
domain (pure core: contrast / tokens / audit / extract)   ← unchanged, no MCP knowledge
   └── ProMCP triadic surface  (@can_do_tool / @read_tool / @do_tool)   ← ultimate_ui/promcp_surface.py
         └── promcp.transport adapter  (can_do/read_/do_ names)  ← server.py wires it
               └── FastMCP  (MCP plumbing)                              ← reached only via .raw
```

Nothing outside `promcp.transport` imports `fastmcp`. Resources and prompts (not part of the
triadic *tool* surface) are attached through the adapter's deliberate `.raw` escape hatch —
grep `.raw` to audit transport coupling, exactly as ProMCP intends.

## Surface

**Tools** (exposed with canonical prefixes)
- `can_do(intent, scope?)` — gate for: extract_design_system, write_token_files,
  generate_tokens, audit_ui, render_qa, style_lookup, import_design_md, check_contrast (+ the
  stability and lifecycle gates).
- `read_design_reference(stage)` · `read_web_guidelines()` · `read_contrast(fg, bg, large?)`
  · `read_ui_audit(files)` · `read_generated_tokens(spec, targets?)` · `read_extracted_design_system(url)`
- `do_write_token_files(spec, output_dir, idempotency_key, targets?)`

**Ecosystem integrations** (all `read_*`, all pure observations — none of them writes anything):

| Source | Module | Tools | Notes |
| --- | --- | --- | --- |
| taste-skill (MIT) | `styles.py` + `brief.py` + `data/*.json` (bundled) | `read_design_brief` (composite),  `read_style_directions`, `read_palette_suggestions`, `read_type_systems`, `read_blueprints` | palettes get measured contrast + a `spec_seed`; `audit.py` carries the mechanical `tell-*` rules; judgment half is the `taste` stage |
| vercel-labs/agent-skills (MIT) | `skillrules.py`, `audit.py` | `read_agent_skill_rule` (bundled, offline; `rule=''` → full skill index; also react-view-transitions references) | allowlisted skills + strict slug → fixed raw URL; `react-*`/`rn-*` audit rules; `react`, `react-native` stages |
| awesome-design-md (MIT) | `designmd.py` | `read_design_md_catalog`, `read_design_md` | tolerant parser for both upstream formats (front matter / markdown); output is the same TokenSpec seed shape as extraction; bundled brand list is the offline fallback |
| Playwright (Apache-2.0) | `extract.py` (seed tokens in), `render.py` (QA out) | `read_extracted_design_system` (+ type scale, spacing grid, DESIGN.md export), `read_rendered_audit`, `do_capture_screenshots` (the only Playwright mutation: idempotent, compensable) | optional dependency; absence is structured data (`can_do render_qa`) |

Network reads are fixed-host (`raw.githubusercontent.com`, `api.github.com`) with validated slugs;
the render audit only opens http(s) URLs or an existing local file and never writes or clicks.

The five paradigm verticals (`web`, `flutter-material`, `flutter-cupertino`, `react-native`, `email`) are the
unit of vertical determinism; `health.PARADIGMS` maps each to its emitter targets and role
expectations, and `read_generated_tokens`/`do_write_token_files` select emitters by `targets`
(email → `email.html`, a bulletproof cross-client HTML newsletter).

**Resources** — `uidesign://reference/{stage}` knowledge docs (incl. `email`).
**Prompts** — `design_pipeline(brief, stack)`, `audit_only(target)`.

## ProMCP-clean

The server ships a linter pass over its own registry:
```bash
PYTHONPATH=. python -c "from server import lint; lint()"
# ProMCP lint: 25 tools, 0 errors, 0 warnings
# (one tolerated global S004 advisory — the stability + lifecycle layers intentionally exceed 8 tools)
```
Contracts are validated at **decoration time** (fail-fast): a `do_*` without `idempotency_key`,
or a mis-prefixed name, raises before the server can start.

## Install & run

End users install nothing but [uv](https://docs.astral.sh/uv/); `uvx` fetches the published
package and its deps into an isolated env:

```bash
uvx ultimate-ui-design-promcp          # stdio transport
```

From source (development):

```bash
pip install "promcp>=0.3.0,<0.4" "fastmcp>=3.4,<4"
# optional, only for read_extracted_design_system:
pip install playwright && playwright install chromium

python server.py            # stdio transport
```
Tests: `PYTHONPATH=. python tests/test_core.py` (30 pass, incl. the clean-lint assertion).

## Client configuration

```json
{
  "mcpServers": {
    "ultimate-ui-design": {
      "command": "uvx",
      "args": ["ultimate-ui-design-promcp"]
    }
  }
}
```
Or: `claude mcp add uidesign -- uvx ultimate-ui-design-promcp`
(from source: `claude mcp add uidesign -- python /absolute/path/to/server.py`)

## Token spec shape

```jsonc
{ "name": "fintech",
  "light": { "bg":"#ffffff","fg":"#0a0a0a","brand":"#2f6bff","on-brand":"#ffffff",
             "muted-fg":"#6b7280","border":"#e5e7eb","danger":"#d92d20" },
  "dark":  { "bg":"#0b0c0e","fg":"#fafafa","brand":"#5b8bff","on-brand":"#08101f",
             "muted-fg":"#9ca3af","border":"#26282c","danger":"#f97066" } }
```
Required roles: `bg`, `fg`, `brand`. Provide sRGB hex so contrast is checkable.

## Lineage

Same six design skills as the skill version, plus the Flutter dual-platform lineage
(nylo-core mobile-design; Material 3 audit arm). Transport convention: ProMCP by @alexlqi.
Personal/team synthesis; install the original skills for their maintained implementations.
