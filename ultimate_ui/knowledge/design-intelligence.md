# Design Intelligence

*Source lineage: nextlevelbuilder/ui-ux-pro-max-skill — "UI/UX Pro Max"*

Purpose: turn a vague brief into a **concrete, defensible design system decision** before
any pixel is drawn. This is the stage that pulls the output away from the generic center.

## Workflow

### 1. Analyze the request
Extract four things explicitly. If any are missing and can't be inferred, pick a sensible
default and state it:
- **Product type** — SaaS, e-commerce, portfolio, dashboard, landing page, docs, marketing,
  admin console, mobile app, etc.
- **Style keywords** — minimal, playful, professional, elegant, brutalist, editorial, dark,
  retro, technical, warm, etc.
- **Industry** — fintech, health, dev-tools, consumer, B2B, gaming, etc. Industry constrains
  conventions (fintech = trust/density; consumer = delight/space).
- **Stack** — the framework the code must target (React/Tailwind, Vue, Next.js, iOS, etc.).

### 2. Produce a design-system decision (required output)
Synthesize a complete recommendation. Don't hand back one axis; give the whole system:

- **Layout pattern** — the structural archetype (e.g. sidebar + content, centered hero +
  sections, split-screen, bento grid, dense data table shell).
- **Style direction** — the aesthetic, named and justified against the brief.
- **Color strategy** — a role-based palette (brand, background layers, text hierarchy,
  borders, semantic success/warn/error/info, one accent). Reason about it in a perceptual
  space (OKLCH) so lightness steps are even.
- **Typography ramp** — font pairing (display / body / mono) + a modular scale (e.g. 1.2 or
  1.25 ratio) with named steps.
- **Spacing scale** — a base unit (4px is the safe default) and the multiples you'll use.
- **Effects** — shadow elevation system (layered), border treatment, radius scale.
- **Anti-patterns to avoid** — the single most valuable output. List what would make *this
  specific* design look generic, and forbid it. Example for a fintech dashboard: "no purple
  gradient, no oversized rounded cards, no emoji icons, use tabular-nums for all figures."

### 3. Hand off to tokenization
The decision is not the deliverable — it's the spec. Feed it into the Tokens stage
(`references/tokens.md`) which turns each named choice into a real token. Nothing proceeds
to components until the decision exists, because components without a system drift.

## Thinking prompts (use these to search your own knowledge)

When you need to make a specific call, reason along these domains separately, then combine:
- **product** — what layout & density does this product type demand?
- **style** — what visual language matches these keywords without cliché?
- **color** — what palette conveys the industry's expected trust/energy level?
- **landing/structure** — what section order maximizes the page's job?
- **typography** — what pairing carries the style at both display and body sizes?

## Why this matters
The generic look isn't a rendering failure — it's a *decision* failure. When no system is
chosen, the model defaults to the average of everything it's seen. Choosing a pattern,
palette, ramp, and an explicit anti-pattern list is what makes the result look authored.
