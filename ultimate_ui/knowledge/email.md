# Email vertical — bulletproof HTML email

The email arm of the pipeline. Deterministic target: `read_generated_tokens(spec,
targets=['email'])` → `email.html`. That file is a complete, production-grade newsletter
skeleton with every hard compatibility decision already made: it renders in Outlook's Word
engine, survives Gmail clipping, adapts to dark mode, and stacks on mobile. Widgets don't read a
theme here — the spec's colors/spacing/radius/fonts are baked into inline styles. Run
`read_preflight('email')` first (no toolchain to install; it reminds you to test cross-client).

*Authority: Litmus + Email on Acid (Sinch) rendering research · Campaign Monitor "CSS support in
email" · caniemail.com · Cerberus / MJML responsive patterns. The generated file targets the
strictest common denominator, then progressively enhances.*

## The core mental model
Email HTML is **not** web HTML. Assume 2007-era rules with modern progressive enhancement on top:
- **Tables for layout, inline styles for everything, `<style>` is progressive enhancement only.**
  Gmail strips `<head>`/`<style>` for some accounts and clips the whole message past ~102 KB;
  anything that *must* render lives inline.
- **Outlook (Windows) renders with Microsoft Word (EMF), not a browser.** No flexbox, grid,
  float, position, `max-width` on `<div>`, background-image (without VML), or border-radius on
  most elements. Design to Word, then enhance for the capable clients.
- The generated file is the strict baseline; treat it as the floor, not the ceiling.

## What the emitter gives you (and how to consume it)
- A single `email.html`: XHTML 1.0 doctype + `xmlns:v`/`xmlns:o` namespaces, full `<head>` meta,
  MSO conditional DPI fix, reset `<style>`, hidden preheader, 600px centered container with MSO
  **ghost tables**, a **bulletproof VML button**, a **fluid-hybrid two-column** row that stacks,
  a divider, and a **CAN-SPAM/GDPR footer** with `{{unsubscribe_url}}` / `{{preferences_url}}` /
  `{{view_in_browser_url}}` merge tags to fill from your ESP.
- Every color is a spec role: `bg`→card, `canvas`/`muted`→page background, `fg`→text,
  `muted-fg`→secondary, `brand`→wordmark + button fill, `on-brand`→button label, `border`→divider.
- `dark` roles feed both dark-mode mechanisms (`prefers-color-scheme` + `[data-ogsc]`/`[data-ogsb]`).

## Deterministic, checkable rules
- **Doctype**: XHTML 1.0 Transitional (stabilizes box model in Word/Outlook). Namespaces
  `xmlns:v` + `xmlns:o` are required for VML.
- **Head meta**: `charset utf-8`, `viewport`, `X-UA-Compatible IE=edge`,
  `x-apple-disable-message-reformatting` (stops iOS auto-resizing), `color-scheme` +
  `supported-color-schemes` = `light dark`, `format-detection` off (no auto-linked phones/dates).
- **MSO DPI fix**: `<o:OfficeDocumentSettings><o:PixelsPerInch>96` inside `[if mso]` — without it
  Outlook scales images/tables to 120 DPI and everything bloats.
- **Layout**: `role="presentation"` on every layout table, `cellpadding=0 cellspacing=0 border=0`,
  content width **600px** (safe up to 640). Center with a full-width wrapper table.
- **Ghost tables**: `<!--[if mso]><table width="600">…<![endif]-->` gives Outlook a fixed width
  while non-Outlook clients get the fluid `max-width:600px` table — the hybrid/spongy technique.
- **Typography**: **px only** (never rem/em), unitless or exact `line-height` with
  `mso-line-height-rule:exactly` (Word inflates line-height otherwise). Body ≥14–16px. Email-safe
  stack ending in `Arial, 'Helvetica Neue', Helvetica, sans-serif` — web fonts silently fail in
  Outlook/Gmail, so the system tail is mandatory.
- **Bulletproof button**: `[if mso]` `v:roundrect` (fill/stroke = brand, `w:anchorlock`, centered
  label) + a non-mso padded `<a>` with `background`, `border-radius`, `line-height` as height.
  Touch target ≥44px (emitter uses 48).
- **Images**: `display:block`, `border=0`, explicit `width`/`height`, real `alt`. Retina by
  authoring 2× and constraining `width`. Never ship an image-only email — image blocking (Outlook
  default) would leave a blank message; keep a high text-to-image ratio.
- **Dark mode**: `prefers-color-scheme` (Apple Mail, iOS, Outlook mac) + `[data-ogsc]`
  (text) / `[data-ogsb]` (background) for Outlook.com/Windows. Avoid pure `#000`/`#fff` (clients
  force-invert them unpredictably); use near-black/near-white from the spec's `dark` roles.
- **Preheader**: hidden `display:none;mso-hide:all` preview text, padded with zero-width chars so
  Gmail doesn't pull body copy into the inbox snippet.

## Responsive strategy (defense in depth)
1. **Media queries** (`max-width:620px`) for capable clients — stack columns, grow the CTA,
   shrink the H1. 2. **Fluid-hybrid** `inline-block` columns with `max-width` so the layout still
stacks in the **Gmail app on a non-Gmail account (GANGA)**, where media queries are stripped.
Both are in the generated file; never rely on media queries alone.

## Compliance (belongs in the body — non-negotiable)
- **CAN-SPAM**: a valid **physical postal address**, a clear/working **unsubscribe** honored ≤10
  days, honest From/Subject, no deceptive headers. **GDPR/CASL**: consent + easy opt-out +
  identity. The footer scaffolds all of this — fill the address and wire the merge tags; do not
  ship with the placeholder address.

## Anti-slop gate (email)
Reject: image-only emails; `<div>`-based layout (breaks in Outlook); web fonts with no system
fallback; buttons that are plain `<a>` with no VML (invisible fill in Outlook); missing
preheader; pure-black-on-white that dark mode inverts to mush; `rem`/`em` sizing; missing
physical address or unsubscribe; walls of low-contrast gray text; more than one primary CTA.
Aim for: one unmistakable action, real selectable text, ≥AA/APCA contrast (the token check
verifies it), generous spacing on the 8px rhythm, and a design that degrades gracefully to the
Word engine before it delights Apple Mail.
