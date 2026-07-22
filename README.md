# ultimate-ui-design

An MCP server that turns **design tokens into real, consistent UI** — for the web, Android,
and iOS — straight from your AI assistant (Claude Code, Claude Desktop, or any MCP client).

You describe what you want ("a calm fintech dashboard, dark-mode first"); the server walks the
model through a disciplined, token-first pipeline and can write the actual theme files to your
project. Colors, spacing, and type all flow from one source of truth — so nothing is hardcoded,
contrast is checked for you, and the output is the same every time you run it.

> Looking for how it's built internally? See **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## What you get

- **Three build targets ("paradigms"), one workflow**
  - `web` — React + Tailwind v4 + shadcn/ui
  - `flutter-material` — Flutter / Material 3 (Android)
  - `flutter-cupertino` — Flutter / Cupertino · HIG (iOS)
- **Tokens as the single source of truth** — one design decision generates deterministic,
  diff-able theme files. Same input → same output, every time.
- **Accessibility built in** — every color pair is checked (WCAG 2.1 + APCA) automatically.
- **Extract from any live site** — point it at a public URL and it reads the *computed* styles
  into a token spec you can reuse.
- **Design audit** — run your components against the live Web Interface Guidelines and get
  `file:line` findings.
- **Safe by design** — the model can generate and preview everything, but only **one** action
  ever writes to disk, and it's reversible.

---

## Install

Requires Python 3.10+.

```bash
pip install --pre "promcp==0.3.0.dev0" "fastmcp>=3.4,<4"

# Optional — only needed if you want to extract tokens from a live website:
pip install playwright && playwright install chromium
```

Then grab this repo and note the full path to `server.py`.

---

## Connect it to your client

### Claude Code
```bash
claude mcp add ultimate-ui-design -- python /absolute/path/to/ultimate-ui-design-promcp/server.py
```

### Claude Desktop (or any client using an `mcpServers` config)
```json
{
  "mcpServers": {
    "ultimate-ui-design": {
      "command": "python",
      "args": ["/absolute/path/to/ultimate-ui-design-promcp/server.py"]
    }
  }
}
```

Restart your client and the tools appear automatically.

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
7. **Audit** — reviews the result against current UI guidelines.

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

All three Flutter/web outputs can coexist in the same project.

---

## FAQ

**Will it overwrite my files?**
Writing is the only action that changes disk, it's opt-in, and it's reversible — the write
reports exactly which files it created so they can be removed if you change your mind.

**Do I need Playwright?**
Only for the "extract tokens from a live website" feature. Everything else works without it.

**Can I use it without the prompts?**
Yes. The prompts are just a guided path; you can ask for any single step (generate tokens,
check contrast, audit a file) directly.

---

Author: Alejandro Andrade ([@alexlqi](https://github.com/alexlqi)).
