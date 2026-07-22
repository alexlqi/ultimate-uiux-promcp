"""Tests for the ProMCP surface. Run: PYTHONPATH=. python tests/test_core.py"""
import asyncio
import tempfile

from pathlib import Path

from ultimate_ui import contrast, tokens, audit, health, lifecycle
from ultimate_ui import promcp_surface as ps
from ultimate_ui.tokens import TokenSpec
from ultimate_ui.promcp_surface import (
    registry, can_do, read_contrast, read_generated_tokens, do_write_token_files,
    read_preflight, read_spec_validation, read_diagnostics,
    read_lifecycle_state, do_lifecycle_transition, do_set_restriction_mode,
)


def _iso_lifecycle():
    """Isolate lifecycle state, config, and log in fresh temp files; clear all ledgers.
    Each test starts at the default mode ('mid') with an empty log."""
    d = Path(tempfile.mkdtemp())
    ps._LIFECYCLE_PATH = d / "lifecycle.json"
    ps._CONFIG_PATH = d / "config.json"
    ps._LOG_PATH = d / "events.log"
    ps._TRANSITIONS.clear()
    ps._APPLIED.clear()
    ps._MODE_APPLIED.clear()

_SPEC = {"name": "t",
         "light": {"bg": "#fff", "fg": "#0a0a0a", "brand": "#2f6bff", "on-brand": "#fff"},
         "dark": {"bg": "#0b0c0e", "fg": "#fafafa", "brand": "#5b8bff", "on-brand": "#08101f"}}


def test_wcag_and_apca():
    assert round(contrast.wcag_ratio("#000", "#fff"), 1) == 21.0
    assert 100 < contrast.apca_lc("#000000", "#ffffff") < 112


def test_emitters():
    s = TokenSpec(name="t", light=_SPEC["light"], dark=_SPEC["dark"])
    assert "@theme inline" in tokens.emit_shadcn(s)
    assert "ThemeExtension" in tokens.emit_flutter(s)


def test_flutter_material_vertical():
    s = TokenSpec(name="t", light=_SPEC["light"], dark=_SPEC["dark"])
    dart = tokens.emit_flutter_material(s)
    # MD3 markers: seeded scheme, useMaterial3, ThemeExtension, 48-dp touch floor, 8-pt grid
    for marker in ("ColorScheme.fromSeed", "useMaterial3: true", "ThemeExtension<AppTokens>",
                   "AppMinTarget", "touch = 48.0", "AppSpacing"):
        assert marker in dart, f"missing {marker!r}"


def test_flutter_cupertino_vertical():
    s = TokenSpec(name="t", light=_SPEC["light"], dark=_SPEC["dark"])
    dart = tokens.emit_flutter_cupertino(s)
    # HIG markers: CupertinoThemeData, InheritedWidget token scope, 44-pt touch floor
    for marker in ("CupertinoThemeData", "AppTokensScope", "cupertino.dart", "touch = 44.0"):
        assert marker in dart, f"missing {marker!r}"


def test_mobile_targets_materialize_and_write():
    v = read_generated_tokens(_SPEC, targets=["flutter-material", "flutter-cupertino"])["value"]
    assert "app_theme.dart (material 3 / android)" in v
    assert "app_theme.dart (cupertino / ios)" in v
    d = tempfile.mkdtemp()
    r = do_write_token_files(_SPEC, d, idempotency_key="mob1",
                             targets=["flutter-material", "flutter-cupertino"])
    names = {p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for p in r["applied_value"]}
    assert {"app_theme_material.dart", "app_theme_cupertino.dart"} <= names


def test_email_vertical():
    s = TokenSpec(name="Acme", light=_SPEC["light"], dark=_SPEC["dark"])
    html = tokens.emit_email(s)
    # bulletproof/compat markers: XHTML doctype + VML ns, MSO DPI fix, ghost-table width,
    # presentation tables, VML button, dark mode (both mechanisms), Apple reformat guard,
    # exact line-height, and a CAN-SPAM unsubscribe.
    for marker in ('XHTML 1.0 Transitional', 'xmlns:v="urn:schemas-microsoft-com:vml"',
                   "PixelsPerInch", 'width="600"', 'role="presentation"', "v:roundrect",
                   "prefers-color-scheme", "[data-ogsc]", "x-apple-disable-message-reformatting",
                   "mso-line-height-rule", "Unsubscribe"):
        assert marker in html, f"missing {marker!r}"
    # tokens actually flow in: brand color reaches the button, spec name is the wordmark
    assert _SPEC["light"]["brand"] in html and "Acme" in html


def test_email_materialize_and_write():
    v = read_generated_tokens(_SPEC, targets=["email"])["value"]
    assert "email.html" in v
    d = tempfile.mkdtemp()
    r = do_write_token_files(_SPEC, d, idempotency_key="em1", targets=["email"])
    names = {p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for p in r["applied_value"]}
    assert "email.html" in names


def test_email_preflight_ready_without_toolchain():
    pf = read_preflight("email")["value"]
    # host-agnostic HTML: always ready, but warns to test cross-client (not a blocker)
    assert pf["ready"] is True and pf["warnings"]


def test_audit_flags_bad_button():
    r = audit.audit_source({"B.tsx": '<button className="transition-all"><svg/></button>'})
    ids = {f["id"] for f in r["findings"]}
    assert {"a11y-icon-button", "motion-transition-all"} <= ids


def test_can_do_feasibility_singleton():
    assert registry.get("can_do").category == "can_do"
    r = can_do({"semantic_tags": ["check_contrast", "unknown_cap"]})
    caps = {c["capability"] for c in r["candidates"]}
    blk = {b["capability"] for b in r["blocked"]}
    assert "check_contrast" in caps and "unknown_cap" in blk
    assert r["feasible"] is True


def test_read_contract_shape():
    r = read_contrast("#6b7280", "#ffffff")
    assert set(r.keys()) == {"value", "timestamp", "quality", "unit"}
    assert r["quality"] == "good"


def test_generated_tokens_includes_contrast_selfcheck():
    v = read_generated_tokens(_SPEC, targets=["shadcn"])["value"]
    assert "shadcn.css (:root/.dark)" in v and "_contrast_check" in v


def test_do_is_idempotent_and_compensable():
    d = tempfile.mkdtemp()
    r1 = do_write_token_files(_SPEC, d, idempotency_key="kX", targets=["css"])
    r2 = do_write_token_files(_SPEC, d, idempotency_key="kX", targets=["css"])
    assert r1["status"] == "success" and r1["compensable"] is True
    assert r1["compensation_hint"].startswith("rm -f")
    assert r1["applied_value"] == r2["applied_value"]


def test_preflight_reports_readiness():
    web = read_preflight("web")["value"]
    assert web["ready"] is True and "checks" in web
    bad = read_preflight("nope")["value"]
    assert bad["ready"] is False and bad["blockers"]


def test_spec_validation_gates_bad_specs():
    bad = read_spec_validation({"light": {"bg": "#fff", "fg": "notacolor"}}, "web")["value"]
    assert bad["valid"] is False and any("brand" in e for e in bad["errors"])
    good = read_spec_validation(_SPEC, "flutter-material")["value"]
    assert good["valid"] is True


def test_diagnostics_self_test_runs_all_emitters():
    diag = read_diagnostics()["value"]
    assert diag["emitters_ok"] is True
    assert {"flutter-material", "flutter-cupertino"} <= set(diag["emitter_selftest"])
    assert set(diag["paradigms"]) == set(health.PARADIGMS)


def test_promcp_lint_is_clean():
    from promcp.linter import lint_registry
    results, global_findings = lint_registry(registry)
    errors = [f for r in results for f in r.findings if f.severity.name == "ERROR"]
    errors += [f for f in global_findings if f.severity.name == "ERROR"]
    assert not errors, f"ProMCP lint errors: {[(f.code, f.message) for f in errors]}"
    # Tool-level warnings must stay at zero; the ONLY tolerated warning is the global S004
    # surface-size advisory (the horizontal stability layer intentionally exceeds 8 tools).
    tool_warnings = [f for r in results for f in r.findings if f.severity.name == "WARNING"]
    assert not tool_warnings, f"unexpected tool warnings: {[(f.code, f.tool, f.message) for f in tool_warnings]}"
    other_globals = [f for f in global_findings if f.severity.name == "WARNING" and f.code != "S004"]
    assert not other_globals, f"unexpected global warnings: {[(f.code, f.message) for f in other_globals]}"


def test_lifecycle_transition_idempotent():
    _iso_lifecycle()
    r1 = do_lifecycle_transition("home", "web", "mark_ready", "L1", spec=_SPEC)
    r2 = do_lifecycle_transition("home", "web", "mark_ready", "L1", spec=_SPEC)
    assert r1["status"] == "success" and r1["compensable"] is True
    assert r1["applied_value"]["stage"] == "ready"
    assert r1["applied_value"] == r2["applied_value"]


def test_mark_ready_rejects_invalid_spec():
    _iso_lifecycle()
    r = do_lifecycle_transition("bad", "web", "mark_ready", "R1",
                                spec={"light": {"bg": "#fff", "fg": "notacolor"}})
    assert r["status"] == "failed" and "mark_ready" in r["applied_value"]["allowed_actions"]


def test_high_blocks_write():
    _iso_lifecycle()
    do_set_restriction_mode("high", "m1")
    do_lifecycle_transition("chk", "web", "mark_ready", "a1", spec=_SPEC)
    lk = do_lifecycle_transition("chk", "web", "lock", "a2")
    assert lk["applied_value"]["stage"] == "locked"
    d = tempfile.mkdtemp()
    w = do_write_token_files(_SPEC, d, idempotency_key="w1", targets=["css"],
                             layout_id="chk", paradigm="web")
    assert w["status"] == "failed" and w["applied_value"] == []
    assert not list(Path(d).iterdir())  # nothing written
    r = can_do({"semantic_tags": ["modify_layout"],
                "context": {"layout_id": "chk", "paradigm": "web"}})
    blk = {b["capability"]: b for b in r["blocked"]}
    assert "modify_layout" in blk and blk["modify_layout"]["change_paths"]
    assert r["feasible"] is False


def test_default_mode_is_mid():
    _iso_lifecycle()
    assert ps._current_mode() == "mid"


def test_set_mode_valid_and_invalid():
    _iso_lifecycle()
    r = do_set_restriction_mode("high", "sm1")
    assert r["status"] == "success" and r["applied_value"]["mode"] == "high"
    assert r["previous_value"]["mode"] == "mid" and ps._current_mode() == "high"
    bad = do_set_restriction_mode("bogus", "sm2")
    assert bad["status"] == "failed" and "high" in bad["applied_value"]["allowed_modes"]


def test_mid_is_nonblocking():
    _iso_lifecycle()  # default mid
    do_lifecycle_transition("m", "web", "mark_ready", "b1", spec=_SPEC)
    do_lifecycle_transition("m", "web", "lock", "b2")
    d = tempfile.mkdtemp()
    w = do_write_token_files(_SPEC, d, idempotency_key="w1", targets=["css"],
                             layout_id="m", paradigm="web")
    assert w["status"] == "partial" and w["applied_value"]  # wrote anyway
    assert "ADVISORY" in w["compensation_hint"] and list(Path(d).iterdir())
    assert read_lifecycle_state("m", "web")["value"]["stage"] == "locked"  # still tracked


def test_none_bypasses_lock():
    _iso_lifecycle()
    do_set_restriction_mode("high", "n0")
    do_lifecycle_transition("n", "web", "mark_ready", "n1", spec=_SPEC)
    do_lifecycle_transition("n", "web", "lock", "n2")
    do_set_restriction_mode("none", "n3")
    d = tempfile.mkdtemp()
    w = do_write_token_files(_SPEC, d, idempotency_key="w1", targets=["css"],
                             layout_id="n", paradigm="web")
    assert w["status"] == "success" and list(Path(d).iterdir())  # lock ignored


def test_low_logs_only():
    _iso_lifecycle()
    do_set_restriction_mode("low", "l0")
    t = do_lifecycle_transition("lo", "web", "mark_ready", "l1", spec=_SPEC)
    assert t["status"] == "success" and t["applied_value"]["fsm_enabled"] is False
    assert ps._recent_events()  # something was logged
    d = tempfile.mkdtemp()
    w = do_write_token_files(_SPEC, d, idempotency_key="w1", targets=["css"], layout_id="lo")
    assert w["status"] == "success"  # never blocks in low


def test_diagnostics_reports_mode():
    _iso_lifecycle()
    do_set_restriction_mode("high", "d0")
    diag = read_diagnostics()["value"]
    assert diag["restriction"]["mode"] == "high"
    assert diag["restriction"]["flags"]["blocking"] is True


def test_unlock_branch_amend_paths():
    _iso_lifecycle()
    do_lifecycle_transition("v", "web", "mark_ready", "b1", spec=_SPEC)
    do_lifecycle_transition("v", "web", "lock", "b2")
    u = do_lifecycle_transition("v", "web", "unlock", "b3")
    assert u["applied_value"]["stage"] == "draft"
    do_lifecycle_transition("v", "web", "mark_ready", "b4", spec=_SPEC)
    do_lifecycle_transition("v", "web", "lock", "b5")
    br = do_lifecycle_transition("v", "web", "branch", "b6", new_layout_id="v2")
    assert br["status"] == "success" and br["applied_value"]["layout_id"] == "v2"
    assert br["applied_value"]["stage"] == "draft"
    am = do_lifecycle_transition("v", "web", "amend", "b7")
    assert am["applied_value"]["stage"] == "draft" and am["applied_value"]["version"] == 2


def test_read_lifecycle_state_reports_stage():
    _iso_lifecycle()
    do_lifecycle_transition("r", "web", "mark_ready", "s1", spec=_SPEC)
    v = read_lifecycle_state("r", "web")["value"]
    assert v["stage"] == "ready" and v["finished_enough"] is True
    ov = read_lifecycle_state()["value"]
    assert "r::web" in ov["finished"]


def test_lifecycle_state_survives_reload():
    _iso_lifecycle()
    do_lifecycle_transition("persist", "web", "mark_ready", "p1", spec=_SPEC)
    do_lifecycle_transition("persist", "web", "lock", "p2")
    store = ps._load_lifecycle()  # fresh read from disk
    assert store[lifecycle.key("persist", "web")]["stage"] == "locked"


def test_transport_exposes_prefixed_surface():
    # promcp 0.3.0 (stable) transport names: singleton `can_do`, and single-underscore
    # `read_<cap>` / `do_<cap>` — this is what end users get via `uvx`.
    from server import build_server
    names = {t.name for t in asyncio.run(build_server().raw.list_tools())}
    assert {"can_do", "read_contrast", "do_write_token_files",
            "read_lifecycle_state", "do_lifecycle_transition",
            "do_set_restriction_mode"} <= names


if __name__ == "__main__":
    import traceback
    p = f = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); p += 1; print(f"PASS {name}")
            except Exception:
                f += 1; print(f"FAIL {name}"); traceback.print_exc()
    print(f"\n{p} passed, {f} failed")
    raise SystemExit(1 if f else 0)
