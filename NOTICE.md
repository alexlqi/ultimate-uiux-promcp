# Third-party notices

This project bundles or derives from the following MIT-licensed works.

- **taste-skill** — Copyright (c) 2026 Leonxlnx — https://github.com/Leonxlnx/taste-skill
  Bundled: `ultimate_ui/data/directions.json`, `palettes.json`, `motions.json`, `type.json`,
  `heroes.json`, `sections.json`.
  Distilled into: `ultimate_ui/knowledge/taste.md`; the `tell-*` rules in `ultimate_ui/audit.py`.
- **agent-skills** — Copyright (c) Vercel, Inc. — https://github.com/vercel-labs/agent-skills
  Distilled into: `knowledge/react-practices.md`, `knowledge/react-native.md`; the `react-*`,
  `perf-*`, `rn-*` rules in `audit.py`. Every rule file is bundled under `ultimate_ui/data/agent_skills/` (served offline by
  `read_agent_skill_rule`; live fetch only for rules newer than the snapshot).
- **awesome-design-md** — Copyright (c) 2026 VoltAgent — https://github.com/VoltAgent/awesome-design-md
  Bundled: brand slug list (`data/design_md_brands.json`). Brand DESIGN.md files are fetched live
  by `read_design_md`; they are third-party analyses of brand design languages and remain subject
  to their owners' trademarks.
- **Playwright** — Copyright (c) Microsoft Corporation (Apache-2.0) — https://github.com/microsoft/playwright
  Optional runtime dependency (`pip install "ultimate-ui-design-promcp[extract]"`); not bundled.
