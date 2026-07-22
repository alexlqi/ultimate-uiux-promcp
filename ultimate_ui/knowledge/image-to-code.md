# Image → Code

*Source lineage: plugin87/ux-ui-agent-skills — "image-to-code" (Image To Code)*

Purpose: turn a **visual reference** — a screenshot, a Figma frame, or a photo of a UI — into
working, token-driven code without losing design details.

## The key move: infer the system *first*
Naive image-to-code hardcodes every pixel value it sees and produces unmaintainable output.
The disciplined move is to **infer the design system from the image before writing code**,
then generate token-driven code against that inferred system. You reconstruct the *rules*,
not just the appearance.

## Workflow
1. **Read the reference.** Identify the layout structure, the visual hierarchy, and the
   repeated patterns. What's the grid? What repeats? What's primary?
2. **Infer the design system** — extract the implicit tokens from the image:
   - **Layout** — columns, spacing rhythm, alignment grid, container widths.
   - **Type** — the ramp: how many distinct sizes/weights, their apparent scale ratio.
   - **Color** — the role palette (bg layers, text hierarchy, brand, borders, semantic).
   - **Spacing** — the base unit the design seems to snap to (usually 4 or 8px).
   - **Radius & shadows** — corner scale and elevation treatment.
3. **Materialize tokens** — write those inferred values into `tokens.css` / `tokens.json`
   per `references/tokens.md`. Now the design has a contract even though it came from an image.
4. **Generate token-driven code** — build the components consuming those tokens (default:
   React + Tailwind v4 wired to the CSS variables). Reproduce the layout faithfully but with
   *no hardcoded values* — every color/space/radius references a token.
5. **Verify against the reference** — compare your render to the source. Check: layout match,
   type hierarchy, spacing rhythm, and that every interactive element has its states
   (hover/focus/active) even if the static image didn't show them.

## Multimodal handling
When the reference is provided as an image or PDF, read it directly. For a Figma export or a
screenshot, treat it as ground truth for *static* appearance only — you must add the states,
motion, and accessibility the still image can't convey.

## Fidelity honesty
- A still image shows one state. You are responsible for designing the missing states
  (hover, focus-visible, active, disabled, loading, empty, error) — don't ship a dead clone.
- If the reference has motion (it's a video or a known animated component), infer it and pass
  the intent to `references/motion.md`; most clones drop motion entirely and that's the tell.
- State what you inferred vs. what you saw, so the user can correct wrong guesses.

## Hand-off
Output flows into Components → Motion → Audit like any other build. The image just replaced
the Intelligence + Brand stages as the source of the system.
