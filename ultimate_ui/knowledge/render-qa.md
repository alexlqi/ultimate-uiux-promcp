# Rendered QA — verify the build in a real browser (Playwright)

Static audits (`read_ui_audit`) read source; they cannot see layout, computed colour, or what
fails at runtime. `read_rendered_audit(target)` renders the page in headless Chromium at
mobile (375), tablet (768) and desktop (1280) and reports what the browser did. Nothing is
written or clicked. Requires Playwright (`pip install playwright && playwright install chromium`);
`can_do(['render_qa'])` reports whether it is available.

## Targets

- A public or local-dev URL (`http://localhost:3000`).
- A file path — including the generated artifacts: `email.html` from the email vertical, a
  Flutter-web build's `index.html`, a static export. Files are opened via `file://`.
- For the email vertical also check 375 and 600px: horizontal overflow there is the classic
  "fluid-hybrid column broke" signal (Outlook/MSO rendering still needs Litmus/Email on Acid).

## What it reports (severity)

| Rule | Severity | Meaning |
| --- | --- | --- |
| `overflow-x` | Critical | Content wider than the viewport → horizontal scroll |
| `control-label` | Critical | Button/link/input with no accessible name |
| `console-error`, `failed-request` | Major | JS errors, 4xx/5xx or failed network requests |
| `meta-lang`, `meta-viewport` | Major | Missing `lang`, missing viewport meta |
| `img-alt` | Major | `<img>` with no `alt` attribute |
| `text-contrast` | Major | Computed text colour vs its real effective background fails WCAG (4.5:1 normal, 3:1 large) |
| `target-size` | Major (mobile) / Minor | Interactive target < 24px (WCAG 2.2 AA floor); aim for 44pt iOS / 48dp Android |
| `meta-title`, `heading-h1`, `heading-skip` | Minor | Title, single `<h1>`, no skipped heading levels |

Identical findings across viewports are merged (`viewport: "multiple"`).

## Screenshots

`do_capture_screenshots(target, output_dir, idempotency_key)` writes one PNG per viewport (the only
write in this stage; idempotent by key, `compensation_hint: rm -f <pngs>`). Use for visual review
or PR evidence, after the audit is clean.

## Extraction round-trip

`read_extracted_design_system(url)` now also returns `type_scale` (per-tag size/weight/line-height/
tracking), `spacing_scale` (values + dominant 4/8 base unit and on-grid ratio) and `design_md`, a
DESIGN.md of the site that `read_design_md`'s parser reads back. Save it beside your tokens to
document a reference.

## Loop

1. `read_rendered_audit(target)` → fix Critical, then Major.
2. `read_ui_audit(files)` for source-level `tell-*`, `react-*`, `a11y-*` findings.
3. Re-run until Critical = 0 and Major are justified. Contrast numbers can be re-checked with
   `read_contrast`; fix at the **token** (then regenerate), not in the component.
