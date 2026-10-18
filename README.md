# ultimate-ui-design

An MCP server that turns **design tokens into real, consistent UI** — for the web, Android,
iOS, and email — straight from your AI assistant (Claude Code, Claude Desktop, or any MCP client).

You describe what you want ("a calm fintech dashboard, dark-mode first"); the server walks the
model through a disciplined, token-first pipeline and can write the actual theme files to your
project. Colors, spacing, and type all flow from one source of truth — so nothing is hardcoded,
contrast is checked for you, and the output is the same every time you run it.

> Looking for how it's built internally? See **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## What you get

- **Five build targets ("paradigms"), one workflow**
  - `web` — React + Tailwind v4 + shadcn/ui
  - `flutter-material` — Flutter / Material 3 (Android)
  - `flutter-cupertino` — Flutter / Cupertino · HIG (iOS)
  - `react-native` — React Native / Expo (typed `theme.ts` + `useTokens()` hook, 44pt/48dp touch floor)
  - `email` — bulletproof responsive HTML email (Outlook/Gmail/Apple Mail · dark mode · CAN-SPAM)
- **Tokens as the single source of truth** — one design decision generates deterministic,
  diff-able theme files. Same input → same output, every time.
- **Accessibility built in** — every color pair is checked (WCAG 2.1 + APCA) automatically.
- **Extract from any live site** — point it at a public URL and it reads the *computed* styles
  into a token spec you can reuse.
- **Design audit** — run your components against the live Web Interface Guidelines and get
  `file:line` findings, including *taste tells* (gradient text, violet gradients, glass, eyebrows,
  emoji icons…) and Vercel React/React-Native rules (fetch-in-effect, barrel imports, index keys,
  clickable divs, `ScrollView.map`…).
- **Taste, with numbers** — curated art directions and palettes (from
  [taste-skill](https://github.com/Leonxlnx/taste-skill)): pick a direction for your sector and
  tone, get palettes with measured WCAG/APCA contrast and a ready-to-validate token seed.
- **Learn from documented brands** — pull a brand's `DESIGN.md` from
  [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) (Stripe, Linear, Apple,
  Vercel, Supabase… ~84 brands) and get a token-spec seed to adapt.
- **One call to a validated starting point** — `read_design_brief(sector, tone, paradigm)` chains
  direction → palette → type → blueprints into a spec already checked for web, Android, iOS or email.
- **App code audited too** — Dart rules for the Flutter verticals (hardcoded `Color(0x…)`, `Colors.red`,
  non-lazy `ListView`, undersized tap targets, images without semantics) next to the web/React Native rules.
- **Deeper than a palette** — dealt type systems (faces, free CDN links, fluid scale), hero and
  per-role section blueprints keyed to your art direction, so sections don't all share one layout.
- **See what the browser sees** — [Playwright](https://github.com/microsoft/playwright) renders
  your build (URL, local file, even the generated `email.html`) at phone/tablet/desktop and
  reports overflow, console errors, contrast and touch-target problems; it can also save
  PNG screenshots per viewport (the one extra step that writes to disk, and it's reversible).
  Site extraction now includes the type scale, spacing grid and a ready-to-commit `DESIGN.md`.
- **Safe by design** — the model can generate and preview everything, but only **one** action
  ever writes to disk, and it's reversible.

---

## Install

There's nothing to clone and no Python packages to manage. The one prerequisite is
[**uv**](https://docs.astral.sh/uv/) — a single self-contained binary that pulls Python,
`promcp`, and `fastmcp` into an isolated, cached environment for you:

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

That's the only thing you install. Everything else is handled by `uvx` at launch.

---

## Connect it to your client

### Claude Code (recommended)

One command — `uvx` fetches the package and all its dependencies automatically:

```bash
claude mcp add uidesign -- uvx ultimate-ui-design-promcp
```

Or just **ask Claude Code to do it for you**:

> Add the ultimate-ui-design MCP server with `uvx ultimate-ui-design-promcp`.

### Claude Desktop (or any client using an `mcpServers` config)

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

Restart your client and the tools appear automatically. On first launch `uvx` downloads and
caches the package; subsequent starts are instant.

### Optional — live-site extraction and rendered QA

`read_extracted_design_system` (reading tokens from a public website) and `read_rendered_audit`
(rendering your build at three viewports) need Playwright.
Pull it in via the `extract` extra and do the one-time browser download:

```bash
uvx --from "ultimate-ui-design-promcp[extract]" ultimate-ui-design-promcp
# then, once, to fetch the headless browser binary:
uvx --from "ultimate-ui-design-promcp[extract]" playwright install chromium
```

Everything else works without it.

<details>
<summary>Run from source instead (for development)</summary>

```bash
pip install "promcp>=0.3.0,<0.4" "fastmcp>=3.4,<4"
python server.py   # stdio
# register: claude mcp add uidesign -- python /absolute/path/to/server.py
```
</details>

---

## Using it

The easiest way to start is the built-in **`design_pipeline`** prompt. Just tell it your brief
and which paradigm you're targeting:

> **design_pipeline** — brief: *"A calm, trustworthy fintech dashboard, dark-mode first"*,
> paradigm: *web*

The assistant then runs the full token-first flow for you:

1. **Preflight** — checks your toolchain is ready for the chosen paradigm.
2. **Design decision** — picks a pattern, palette, type scale, spacing, and effects.
3. **Validate** — sanity-checks the token spec before anything is written.
4. **Tokens** — generates the theme files (and verifies contrast) — still in memory.
5. **Write** — persists the files to your project (the one step that touches disk).
6. **Components + motion** — builds UI that consumes *only* tokens, in every state.
7. **Preview** — serves the output over a lightweight **local HTTP server** and opens it in your
   browser. (Browsers block raw `file://` for ES modules, `fetch`, and relative assets, so a
   `file://` preview renders broken — this serves `http://127.0.0.1:<port>/` instead. The server
   is pinned per output directory, so re-previewing keeps the same URL; stop it with `stop=True`.)
8. **Audit** — reviews the result against current UI guidelines.

Prefer a review pass on existing UI? Use the **`audit_only`** prompt and point it at your
component files.

You can also just talk to it naturally — "generate a light+dark theme for this brand color and
write it into `./theme`" — and it will pick the right tools.

---

## Your design in one spec

Everything comes from a small JSON token spec. Colors are sRGB hex so contrast can be verified:

```jsonc
{
  "name": "fintech",
  "light": {
    "bg": "#ffffff", "fg": "#0a0a0a",
    "brand": "#2f6bff", "on-brand": "#ffffff",
    "muted-fg": "#6b7280", "border": "#e5e7eb", "danger": "#d92d20"
  },
  "dark": {
    "bg": "#0b0c0e", "fg": "#fafafa",
    "brand": "#5b8bff", "on-brand": "#08101f",
    "muted-fg": "#9ca3af", "border": "#26282c", "danger": "#f97066"
  }
}
```

Only `bg`, `fg`, and `brand` are required — fill in the rest as your design grows.

---

## What it generates

| Paradigm | Output |
|---|---|
| `web` | CSS variables, Tailwind v4 theme, shadcn/ui theme, DTCG tokens |
| `flutter-material` | `app_theme_material.dart` — seeded Material 3 `ColorScheme`, 8-dp grid, `ThemeExtension` |
| `flutter-cupertino` | `app_theme_cupertino.dart` — `CupertinoThemeData`, 44-pt touch targets, token scope |
| `email` | `email.html` — bulletproof responsive newsletter: XHTML + VML for Outlook, MSO ghost tables, VML button, `prefers-color-scheme` + `[data-ogsc]` dark mode, CAN-SPAM/GDPR footer, <102 KB (no Gmail clip) |

All web/Flutter/email outputs can coexist in the same project.

---

## FAQ

**Will it overwrite my files?**
Writing is the only action that changes disk, it's opt-in, and it's reversible — the write
reports exactly which files it created so they can be removed if you change your mind.

**Do I need Playwright?**
Only for "extract tokens from a live website" and the rendered viewport audit. Everything else
works without it (and `can_do(['render_qa'])` tells you if it's available).

**Does it copy brands?**
No. `read_design_md` is a *reference*: it shows how a documented system handles accent, type and
depth, and seeds tokens you then adapt. Don't ship someone else's trademarks or licensed fonts.

**Can I use it without the prompts?**
Yes. The prompts are just a guided path; you can ask for any single step (generate tokens,
check contrast, audit a file) directly.

---

Author: Alejandro Andrade ([@alexlqi](https://github.com/alexlqi)).
