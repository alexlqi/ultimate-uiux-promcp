"""vercel-labs/agent-skills (MIT) rule files: bundled snapshot first, live fetch as fallback.

Every rule of react-best-practices, composition-patterns, react-native-skills and the
react-view-transitions references ships under ``ultimate_ui/data/agent_skills`` so the full
rule text (why it matters, incorrect vs correct code) works offline and deterministically.
A rule id missing from the snapshot (a newer upstream rule) falls back to the live raw file.

`rule=""` returns the skill's SKILL.md index (every rule with its one-line summary + impact).
Allowlisted skills + strict slugs keep both the file path and the URL under our control.
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

__all__ = ["SKILLS", "fetch_rule", "list_rules"]

_BASE = "https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/{skill}/{path}"
_BUNDLE = Path(__file__).parent / "data" / "agent_skills"
# skill -> upstream subdirectory holding its detail files
SKILLS = {
    "react-best-practices": "rules",
    "composition-patterns": "rules",
    "react-native-skills": "rules",
    "react-view-transitions": "references",
}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")


def list_rules(skill: str) -> list[str]:
    if skill not in SKILLS:
        raise ValueError(f"unknown skill {skill!r}; choose from {', '.join(SKILLS)}")
    return sorted(p.stem for p in (_BUNDLE / skill).glob("*.md")
                  if p.stem != "SKILL" and not p.stem.startswith("_"))


def fetch_rule(skill: str, rule: str = "", timeout: float = 10.0) -> str:
    skill, rule = (skill or "").strip(), (rule or "").strip().removesuffix(".md")
    if skill not in SKILLS:
        raise ValueError(f"unknown skill {skill!r}; choose from {', '.join(SKILLS)}")
    if not rule or rule.upper() == "SKILL":
        name, path = "SKILL", "SKILL.md"
    elif _SLUG.match(rule):
        name, path = rule, f"{SKILLS[skill]}/{rule}.md"
    else:
        raise ValueError(f"invalid rule id {rule!r} (e.g. 'async-parallel', 'list-performance-virtualize')")
    local = _BUNDLE / skill / f"{name}.md"
    if local.is_file():
        return local.read_text(encoding="utf-8")
    req = urllib.request.Request(_BASE.format(skill=skill, path=path),
                                 headers={"User-Agent": "ultimate-ui-design-mcp"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https host)
        return r.read().decode("utf-8", "replace")
