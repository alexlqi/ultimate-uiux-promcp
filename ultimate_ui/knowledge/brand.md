# Brand — Build The Brand

*Source lineage: plugin87/ux-ui-agent-skills — "brandkit" (Build The Brand)*

Purpose: turn a one-line concept ("a wellness brand for daily balance", "a minimalist café")
into a **complete visual identity** that then feeds the token system.

## Inputs
- The concept / positioning (one sentence is enough to start).
- Optional: audience, tone words, competitors to differentiate from, any locked constraints
  (existing logo, mandated color, etc.).

## Outputs (in order)
1. **Rough-idea capture** — restate the concept and the one-line positioning so the brand has
   a north star ("Wellness brand for daily balance").
2. **Logo direction** — not a final logo render, but a described mark: symbol concept,
   construction logic, wordmark treatment, and the reasoning. If image generation is
   available, produce reference mockups; otherwise describe precisely enough to hand to a
   designer or an image model.
3. **Color palette** — a primary, secondary, and accent plus neutrals, given as exact values
   (OKLCH + hex). These become **primitive tokens** directly.
4. **Typography** — a display + body pairing (and mono if the product is technical), with the
   rationale for why the pairing carries the brand's tone.
5. **Mockups** — the identity applied to a representative surface (product shot, card, hero)
   so the brand is seen in context, not in the abstract.
6. **Visual direction** — the mood: photography/illustration style, texture, spacing feel,
   the adjectives the visuals must hit.

## The primitive→semantic→component discipline
Brandkit output is the **primitive** layer. Don't stop at "here are five hex codes." Bind
them to roles immediately so the brand is usable:
- brand palette → `--color-brand`, `--color-accent`
- neutrals → background layers + text hierarchy
- derive semantic success/warn/error/info that harmonize with the brand hue (tint them
  toward the brand where possible instead of stock red/green/yellow)

Then produce a `theme.css` (light + dark) so the brand is immediately themeable. This is the
hand-off to `references/tokens.md`.

## Quality bar
- Every brand color pair used for text must pass contrast in both light and dark — verify.
- The palette should have a clear hierarchy (one dominant brand color, not five competing
  ones). Generic brand kits fail by giving equal weight to too many colors.
- Typography pairing should have real contrast between display and body (weight, or a
  serif/sans split) — not two similar sans fonts.
