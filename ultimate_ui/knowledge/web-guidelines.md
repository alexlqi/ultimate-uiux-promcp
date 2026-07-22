# Audit — Web Design Guidelines

*Source lineage: vercel-labs/agent-skills — "web-design-guidelines", which fetches the live
vercel-labs/web-interface-guidelines. Fetch the latest rules before a serious review:*
`https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`

Purpose: audit generated or existing UI code against a checklist of hundreds of small
correct-by-default choices. Run this as the **final gate** on any build, and as the whole job
when the user just says "review my UI." Report findings in terse `file:line — issue` format,
grouped by severity (Critical → Major → Minor → Enhancement). Fetch fresh rules each run so
the review reflects current guidance rather than a stale snapshot.

The checklist below is the durable core. It's non-exhaustive — for a thorough audit, fetch
the live command.md.

## Interactions
- Every flow is keyboard-operable; follow WAI-ARIA Authoring Patterns.
- Visible focus ring on every focusable element; prefer `:focus-visible` over `:focus`.
- Manage focus: traps, move & return focus in dialogs/menus.
- Hit target ≥ 24px (≥ 44px on mobile); expand if the visual is smaller.
- Mobile `<input>` font-size ≥ 16px to stop iOS Safari auto-zoom.
- Never disable browser zoom. Never block paste. Don't disable submit pre-emptively.
- Loading buttons keep their label and show a spinner; add ~150–300ms show-delay and
  ~300–500ms minimum visible time to avoid flicker.
- Persist state in the URL (filters, tabs, pagination, expanded panels) so share/refresh/
  back-forward work.
- Optimistic updates when success is likely; roll back or offer Undo on failure.
- Confirm destructive actions or provide Undo with a safe window.
- Use `<a>`/`<Link>` for navigation (Cmd/middle/right-click must work) — never a `<div>`.
- `touch-action: manipulation` to prevent double-tap zoom on controls.
- No dead zones: if it looks interactive, it is interactive.
- Announce async updates with polite `aria-live`.

## Animations
(See `references/motion.md` for the full treatment.)
- Honor `prefers-reduced-motion`. Prefer CSS > WAAPI > JS libs.
- Animate compositor-friendly `transform`/`opacity`; avoid reflow properties.
- Never `transition: all`. Interruptible, input-driven, correct transform-origin.

## Layout
- Optical alignment: adjust ±1px when perception beats geometry.
- Every element aligns to something intentional (grid, baseline, edge, optical center).
- Verify mobile, laptop, and ultra-wide (zoom to 50% to simulate ultra-wide).
- Respect safe areas (notches/insets) with `env()` variables.
- Prefer flex/grid/intrinsic layout over measuring in JS; let the browser size things.
- No unwanted scrollbars.

## Content
- Prefer inline help over tooltips.
- Skeletons mirror final content exactly (no layout shift).
- `<title>` reflects the current context.
- Every screen has a next step — no dead ends.
- Design all states: empty, sparse, dense, error.
- Curly typographic quotes; real ellipsis character `…`.
- Tabular numbers (`font-variant-numeric: tabular-nums`) for figures that compare/align.
- Never rely on color alone for status — add a text/icon label.
- Icon-only buttons have a descriptive `aria-label`; decoration is `aria-hidden`.
- Semantics before ARIA: prefer `button`, `a`, `label`, `table` before `aria-*`.
- Hierarchical `<h1>–<h6>` and a "Skip to content" link.
- Locale-aware date/number/currency formatting; detect language via `Accept-Language`, not IP.

## Forms
- Enter submits (single-input, or the last control in a multi-control form).
- In `<textarea>`, ⌘/⌃+Enter submits; Enter inserts a newline.
- Every control has a `<label>`; clicking the label focuses the control.
- Keep submit enabled until submission starts; then disable, show spinner, use idempotency key.
- Don't block typing — allow any input and show validation feedback instead.
- Show errors next to their field; on submit, focus the first error.
- Set `autocomplete` and meaningful `name` for autofill; correct `type`/`inputmode`.
- Allow pasting one-time codes; be password-manager compatible.
- Warn before navigating away from unsaved changes.

## Performance
- `POST/PATCH/DELETE` under ~500ms; budget network latency.
- Minimize and speed up re-renders (React DevTools / React Scan); test with CPU throttling.
- Virtualize large lists; use `content-visibility: auto` where apt.
- No image-caused CLS: set explicit dimensions, reserve space.
- Preload above-the-fold images and critical fonts; lazy-load the rest; subset fonts.
- Move long tasks off the main thread (Web Workers).

## Design details
- Layered shadows (≥ 2 layers: ambient + direct light).
- Combine borders + shadows; semi-transparent borders sharpen edges.
- Nested radii: child radius ≤ parent, concentric so curves align.
- Tint borders/shadows/text toward the background hue on non-neutral backgrounds.
- Minimum contrast: prefer APCA over WCAG 2. `:hover`/`:active`/`:focus` have *more* contrast
  than rest.
- Set `<meta name="theme-color">` and `color-scheme` so browser UI matches the page.
- Color-blind-friendly chart palettes.

## Output format
```
src/components/Button.tsx:42 — [Critical] Icon-only button missing aria-label
src/app/page.tsx:88 — [Major] transition: all animates layout; list transform/opacity only
src/ui/Card.tsx:15 — [Minor] child radius (12px) exceeds parent (10px); breaks concentricity
```
Group by severity, keep each line terse, cite `file:line`, and end with the count of issues
by severity so the user knows the shape of the work.
