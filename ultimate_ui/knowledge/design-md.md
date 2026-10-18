# Brand DESIGN.md — design from a documented system

awesome-design-md (github.com/VoltAgent/awesome-design-md, MIT) is a catalog of ~84 brands'
design languages written as `DESIGN.md` files for LLMs (Stripe, Linear, Apple, Vercel, Supabase,
Notion, Spotify, Tesla, Airbnb, …). Use them as **references to learn a system's structure**, not
to clone a brand: borrow the *logic* (how restrained the accent is, how type scales, how depth is
built), then author your own tokens.

## Tools

- `read_design_md_catalog()` — brand slugs (live from GitHub, bundled snapshot when offline).
- `read_design_md(brand)` — the raw DESIGN.md **plus** a normalized `spec_seed` (colors → token
  roles, radii, font) with measured contrast and the brand's `native_mode` (light/dark).
- Then: `read_spec_validation(spec_seed, paradigm)` → `read_generated_tokens` → `do_write_token_files`.

## Document anatomy (what to read in each section)

1. **Overview / Visual theme** — the one-sentence idea and the "key characteristics" list.
2. **Colors** — roles (`primary`, `ink`, `canvas`, `hairline`, `on-primary`, semantic colors).
   Note how few chromatic colors there are and where the accent is *allowed*.
3. **Typography** — family, the display→body ramp, tracking per size (display is tightened,
   body is 0), tabular figures where numbers matter.
4. **Layout / Elevation / Shapes** — spacing scale, radius vocabulary (pill vs tight), how depth is
   made (shadow stack vs tone steps vs borders).
5. **Components** — button/input/card specs as token references.
6. **Do's and Don'ts** and **Responsive behavior** — the guardrails; copy these into your own
   anti-pattern list.
7. **Iteration guide / agent prompt guide** — how to extend the system consistently.

## Using a reference well

- Pick references that match your **sector and tone**, not your logo ambitions (a dev-tool →
  Linear/Vercel/Supabase; fintech → Stripe/Wise/Revolut; consumer → Airbnb/Spotify/Nike;
  editorial → The Verge/Wired).
- Extract 3 things: *accent discipline*, *type contrast*, *depth strategy*. Reuse the pattern with
  your own palette (`read_palette_suggestions`) and run `read_contrast` on the final pairs.
- A natively dark brand only gives you the dark half — author the light half (and vice versa); the
  seed warns when the other mode is just a copy.
- The seed is heuristic. If `warnings` mentions failed contrast or an odd role, read the document
  and set the role by hand. Never ship a brand's trademarks/fonts you don't license.
