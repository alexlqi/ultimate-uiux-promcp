# Taste — making a page read as designed, not generated

Distilled from taste-skill (github.com/Leonxlnx/taste-skill, MIT). Works across web and
app UIs. Pair it with the deterministic tools: `read_style_directions` (the idea),
`read_palette_suggestions` (measured colour), `read_ui_audit` (the mechanical `tell-*` rules),
`read_rendered_audit` (what the browser actually shows).

## Order of work (do not skip to checks)

1. **Find the idea from the subject.** A page that has every tell removed and nothing in their
   place is "an empty page with good manners" — itself a tell. Ask what the subject can do that
   no template can (its name, its object, its place, its product performing).
0. **Shortcut:** `read_design_brief(sector, tone, paradigm)` performs steps 2-4 in one call and
   returns a validated `spec_seed` plus hero/section blueprints and paradigm notes.
2. **Pick ONE art direction** — `read_style_directions(sector, tone)` returns ranked
   directions, each with composition, type classes, palette tags, imagery, motion, pitfalls.
   Commit to one; do not blend three.
3. **Deal a palette** — `read_palette_suggestions(tags)` using the direction's `paletteTags`.
   Every suggestion carries measured WCAG/APCA contrast and a `spec_seed`.
3b. **Deal type and layout** — `read_type_systems(direction.typeClasses)` for faces + a ≤5-step
   fluid scale; `read_blueprints('hero', direction)` and `read_blueprints('section', direction, role)`
   for each section so no two share a layout family.
4. **Persist as tokens** — `read_spec_validation` → `read_generated_tokens` → `do_write_token_files`.
5. **Build the sections with their own composition** — not the same layout family repeated.
6. **Audit last** — `read_ui_audit` (tells + a11y + react), `read_rendered_audit` (viewport QA).

## The tells registry (dated; each began as a good idea used by default)

| Wave | Tell | Instead |
| --- | --- | --- |
| 2023–24 | Violet/indigo gradients; gradient-filled headline text | Flat dealt palette; solid ink |
| 2023–24 | Glass panels (backdrop blur), glowing buttons, soft grey shadow under every card | Opaque surface one tone step from the ground |
| 2023–24 | Three identical feature cards with icon-in-rounded-square; emoji as icons | A composed section; real icons or words |
| 2025 | Eyebrow label above every heading; pill badge above hero ("New", "Beta") | Fold into the heading or delete |
| 2025 | Bento grid as the feature section; near-black + one neon accent + glow | Composed section; a dealt dark palette, no glow |
| 2025 | Floating blurred pill nav; fake dashboard hero of grey bars; pulsing "live" dot | Plain bar; a real interface fragment or no image |
| 2025–26 | Cream ground + terracotta accent; serif display as the "premium" shortcut | The dealt palette/type — warmth from stone, ink, photography |
| Gallery | Monospace micro-labels; 01/02/03 index numbering; hairline rules everywhere; crop-mark ornaments | Space, tone steps, filled shapes |
| Structure | Full-sentence display headline (3–4 lines); stock order hero→logos→features→testimonial→pricing | A ~5-word title; the order of the argument |
| Structure | Everything centred; one 12–16px radius on all; nine near-equal font sizes | Left-anchored + one centred moment; square or fully round, chosen once; **five sizes, far apart** |
| Copy | unlock / supercharge / seamless / elevate; "not just X, it's Y"; "Get started" / "Learn more" labels; invented social proof | Plain verbs naming the action; real proof or none |
| Motion | Identical fade-up on every block; hover lift on every card; bounce easing; meaningless loops | One signature move; motion tied to state |

"Avoid" lists rot: every published "use this instead" becomes next year's tell. Replacements are
**procedures** (draw from the library, derive from the subject), never fixed fonts/colours.

## Type

- Size contrast is the main lever; weight is not (about half of strong heroes are regular weight).
- Median hero ≈ 72px on desktop (≈40px on a phone), tracking ≈ -0.01em tightening with size,
  leading ≈ 1.0. Display ≥ 4× body on desktop. Body 16–19px.
- **Five sizes maximum**, clearly different, as `clamp()` steps: small / body / lead / head / display.
- Over 40px: tight tracking (-0.02 to -0.07em), leading 0.8–1.05, optical kerning, no wrap surprises.
- One or two families. Load fonts properly (`font-display: swap`, preload the display face).

## Colour

- A page is carried by **two or three values** (ground, ink, one accent). The accent appears on
  one thing per screen (the action, or one image frame).
- Body text ≥ 4.5:1 and CTA label on accent ≥ 4.5:1 — measured, not eyeballed
  (`read_contrast`). Muted text should still reach 3:1+.
- Dark mode is its own palette, not an inversion; keep ground one tone step from surface.

## Layout and motion

- Vary composition per section (split stage, contact sheet, pinned poster, editorial column…).
- Margins and rhythm from a scale (tokens), not per-section whim.
- Motion: one signature move per page; animate `transform`/`opacity` only; respect
  `prefers-reduced-motion`; no reveal that can fail and leave a blank band.

## Critique pass (before shipping)

1. Cover the logo — is the subject still recognisable from composition + type alone?
2. Count type sizes (≤5) and accent uses (≤1 per screen).
3. Run `read_ui_audit` — zero `tell-*` Majors; justify any Minor.
4. Run `read_rendered_audit` at mobile/tablet/desktop — zero Critical.
5. Read the copy aloud: any verb from the banned list? any invented proof?
