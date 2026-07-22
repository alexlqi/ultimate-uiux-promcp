"""ultimate-ui-design — ProMCP server (transport over FastMCP).

Wires the contract-decorated triadic surface (ultimate_ui.promcp_surface) onto the
ProMCP transport adapter, which sits over FastMCP. Nothing here imports fastmcp
directly — the only coupling boundary is promcp.transport, per ProMCP's architecture.

  domain (invariants, use cases)
    └── ProMCP triadic surface  (can_do / read_* / do_*)   ← promcp_surface.py
          └── promcp.transport adapter                       ← THIS file wires it
                └── FastMCP (MCP plumbing)                   ← behind .raw

Run: `python server.py`  (stdio)   |   requires promcp>=0.3.0, fastmcp>=3.4,<4.
Author: Alejandro Andrade (@alexlqi) — github.com/alexlqi
"""
from __future__ import annotations

from promcp.linter import lint_registry
from promcp.transport import ProMCPServer

from ultimate_ui.promcp_surface import registry

INSTRUCTIONS = (
    "Token-first UI design pipeline (ProMCP triadic surface). Tokens are the single source "
    "of truth: primitive → semantic → component, nothing hardcoded. read_* observes "
    "(contrast, generated token text, site extraction, audits, knowledge, preflight, spec "
    "validation, diagnostics); do_write_token_files is the only mutation (persists files, "
    "compensable); can_do gates preconditions. Four paradigm verticals: "
    "web = React + Tailwind v4 + shadcn/ui; flutter-material = Flutter/Material 3 (Android); "
    "flutter-cupertino = Flutter/Cupertino·HIG (iOS); email = bulletproof cross-client HTML "
    "email (Outlook/Gmail/Apple Mail, dark mode, CAN-SPAM). For fast + fault-tolerant builds: "
    "read_preflight('<paradigm>') → read_spec_validation(spec,'<paradigm>') → "
    "read_generated_tokens → do_write_token_files, and read_diagnostics to debug. "
    "Read read_design_reference('<stage>') before building each stage."
)

# Map ToolEntry.category -> the transport register method + how to derive the capability slug.
_CATEGORY_REGISTRARS = {
    "can_do": lambda srv, entry: srv.register_can_do(),
    "read":   lambda srv, entry: srv.register_read(entry.name[len("read_"):]),
    "do":     lambda srv, entry: srv.register_do(entry.name[len("do_"):]),
}


def build_server() -> ProMCPServer:
    """Construct the ProMCP server and export the domain registry over the transport."""
    server = ProMCPServer("ultimate-ui-design", instructions=INSTRUCTIONS)

    for entry in registry.all():
        registrar = _CATEGORY_REGISTRARS[entry.category]
        # entry.fn is the contract-enforcing wrapper produced by the ProMCP decorator.
        registrar(server, entry)(entry.fn)

    _attach_knowledge_and_prompts(server)
    return server


def _attach_knowledge_and_prompts(server: ProMCPServer) -> None:
    """Resources + prompts aren't part of the triadic tool surface, so we reach through
    the adapter's deliberate escape hatch (.raw). Grep for `.raw` to audit transport coupling.
    """
    from ultimate_ui.promcp_surface import KNOWLEDGE, _STAGES

    mcp = server.raw  # explicit, auditable coupling to FastMCP

    @mcp.resource("uidesign://reference/{stage}")
    def reference(stage: str) -> str:
        """Design knowledge for a pipeline stage (mirror of read_design_reference)."""
        fname = _STAGES.get(stage)
        return (KNOWLEDGE / fname).read_text(encoding="utf-8") if fname else f"Unknown stage '{stage}'."

    @mcp.prompt
    def design_pipeline(brief: str, paradigm: str = "web") -> str:
        """Orchestrate the full token-first pipeline for a paradigm vertical.
        paradigm ∈ {web, flutter-material (Android), flutter-cupertino (iOS), email (HTML email)}."""
        stack_ref = {
            "web": "web-stack",
            "flutter-material": "flutter-material",
            "flutter-cupertino": "flutter-cupertino",
            "email": "email",
        }.get(paradigm, "web-stack")
        target = {"web": "shadcn (+css/tailwind/dtcg)",
                  "flutter-material": "flutter-material",
                  "flutter-cupertino": "flutter-cupertino",
                  "email": "email"}.get(paradigm, "shadcn")
        return (
            f"Design and build: {brief}\nParadigm: {paradigm} → read_design_reference('{stack_ref}').\n\n"
            "Run the token-first pipeline using this server's ProMCP tools:\n"
            f"0. Preflight — read_preflight('{paradigm}'); resolve blockers before building (warnings are OK).\n"
            "1. Intelligence — read_design_reference('intelligence'); produce a design-system "
            "decision (pattern, palette, type ramp, spacing, effects, anti-pattern list).\n"
            f"2. Validate — read_spec_validation(spec, '{paradigm}'); fix every error before persisting.\n"
            f"3. Tokens — read_generated_tokens(spec, targets=['{target}']); verify its _contrast_check. "
            "can_do({'semantic_tags':['write_token_files'],'context':{'output_dir':...}}) "
            "then do_write_token_files to persist.\n"
            f"4. Components — read_design_reference('{stack_ref}'); consume ONLY tokens, all states.\n"
            "5. Motion — read_design_reference('motion'); add sparingly by interaction frequency.\n"
            "6. Audit — read_web_guidelines + read_ui_audit(files); fix before done.\n"
            "7. Debug — if anything is off, read_diagnostics to inspect the ledger + emitter health.\n\n"
            "Never hardcode a value that should be a token. Pass the anti-slop gate."
        )

    @mcp.prompt
    def audit_only(target: str = "the provided component files") -> str:
        """Prompt for an audit-only pass."""
        return (
            f"Audit {target}.\n1. read_web_guidelines for current rules.\n"
            "2. read_ui_audit(files) for deterministic findings.\n"
            "3. Add judgment-level findings the heuristics miss (hierarchy, motion, states).\n"
            "Report file:line grouped by severity with counts. Don't rewrite unprompted."
        )


def lint() -> None:
    """Run the ProMCP linter over the domain registry and print results."""
    results, global_findings = lint_registry(registry)
    n_err = sum(1 for r in results for f in r.findings if f.severity.name == "ERROR")
    n_warn = sum(1 for r in results for f in r.findings if f.severity.name == "WARNING")
    print(f"ProMCP lint: {len(results)} tools, {n_err} errors, {n_warn} warnings")
    for r in results:
        for f in r.findings:
            print(f"  [{f.severity.name}] {f.code} {f.tool}: {f.message}")
    for f in global_findings:
        print(f"  [GLOBAL {f.severity.name}] {f.code}: {f.message}")


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
