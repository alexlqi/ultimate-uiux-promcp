# Extract — Extract Design System

*Source lineage: arvindrk/extract-design-system — "Extract Design System"*

Purpose: reverse-engineer a **public** website's design primitives into project-local starter
token files, so you can match an existing visual language instead of starting from generic
defaults.

## Before you start — set expectations
- Confirm the target URL is public and reachable.
- This extracts **tokens and starter assets, not a full component library**. It's for
  initialization, not pixel-perfect reproduction.
- Do **not** overwrite an existing design system or app styling without explicit confirmation.
- Respect the source: this is for *inspiration and matching your own product*, not cloning a
  competitor wholesale. Extracted tokens are a foundation you build on.

## Workflow
1. Confirm the URL is public and reachable.
2. Capture computed styles from the live DOM. The reference implementation runs Playwright
   (headless Chromium) to read real rendered CSS, not the source stylesheet — this catches
   what's actually applied.
   ```bash
   npx playwright install chromium
   npx extract-design-system <url>
   ```
3. Extract these categories:
   - **Colors** — brand palette, background layers, text colors, borders. De-duplicate
     near-identical colors (merge in OKLab) so you get the real palette, not 40 noise shades.
   - **Typography** — font families, sizes, weights, line heights.
   - **Spacing** — the padding/margin scale in use.
   - **Border radius** — button, card, pill radii.
   - **Shadows** — box-shadow values across elevation levels.
4. Normalize and emit:
   - `.extract-design-system/raw.json` — raw extraction.
   - `normalized.json` — cleaned, de-duplicated tokens.
   - `tokens.json` (W3C DTCG) + `tokens.css` (custom properties) — ready to drop in.
5. **Summarize before adopting.** State the likely primary/secondary/accent colors, detected
   fonts, and the spacing/radius/shadow scales. Let the user confirm the extraction looks
   usable before generating starter files — extraction is heuristic, not authoritative.

## Hand-off
Feed the normalized tokens into `references/tokens.md` as the primitive layer, then bind
semantic roles. From there the pipeline continues normally (Components → Motion → Audit). The
extracted site gave you the *look*; the token contract makes it *yours* and maintainable.

## Limitations to state honestly
- Extraction reads what the DOM computes, so heavily JS-driven or canvas-rendered visuals
  won't extract well.
- It captures tokens, not layout logic, component composition, or motion — those you rebuild.
- Treat the output as a strong starting scaffold that saves hours of manual token setup, not
  as a finished system.
