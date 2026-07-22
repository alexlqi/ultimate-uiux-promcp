# Tokens — the single source of truth

Every other stage reads from here. Tokens are defined once and consumed everywhere. Three
layers, in order of abstraction:

1. **Primitive** — raw values. `--blue-500: oklch(0.55 0.2 255)`. No meaning, just the ramp.
2. **Semantic** — role bindings. `--color-bg`, `--color-fg`, `--color-brand`,
   `--color-border`, `--color-danger`. These reference primitives, never raw values.
3. **Component** — optional, per-component overrides. `--button-bg: var(--color-brand)`.

Components consume **semantic** tokens. If a component needs a value that has no semantic
token, that's a signal the system is incomplete — add the token, don't hardcode.

## Emit two files

### `tokens.json` (W3C DTCG shape)
```json
{
  "color": {
    "brand": { "$type": "color", "$value": "{color.blue.500}" },
    "bg":    { "$type": "color", "$value": "{color.neutral.50}" },
    "fg":    { "$type": "color", "$value": "{color.neutral.900}" }
  },
  "space": {
    "1": { "$type": "dimension", "$value": "4px" },
    "2": { "$type": "dimension", "$value": "8px" },
    "4": { "$type": "dimension", "$value": "16px" }
  },
  "radius": {
    "sm": { "$type": "dimension", "$value": "6px" },
    "md": { "$type": "dimension", "$value": "10px" }
  },
  "shadow": {
    "md": {
      "$type": "shadow",
      "$value": [
        { "color": "rgb(0 0 0 / 0.04)", "offsetY": "1px", "blur": "2px" },
        { "color": "rgb(0 0 0 / 0.08)", "offsetY": "4px", "blur": "12px" }
      ]
    }
  }
}
```
Note the shadow has **two layers** (ambient + direct) — never a single flat shadow.
Note colors resolve through aliases (`{color.blue.500}`) so themes are swappable.

### `tokens.css` (runtime)
```css
:root {
  color-scheme: light dark;

  /* primitives */
  --blue-500: oklch(0.55 0.20 255);
  --neutral-50: oklch(0.98 0 0);
  --neutral-900: oklch(0.20 0 0);

  /* semantic */
  --color-brand: var(--blue-500);
  --color-bg: var(--neutral-50);
  --color-fg: var(--neutral-900);
  --color-border: oklch(0.85 0 0);

  /* space (base 4px) */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;  --space-4: 16px;
  --space-6: 24px; --space-8: 32px;

  /* radius — nested-safe scale */
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px;

  /* motion (see motion.md) */
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --dur-fast: 150ms; --dur-base: 200ms;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: var(--neutral-900);
    --color-fg: var(--neutral-50);
    --color-border: oklch(0.35 0 0);
  }
}
```

## Rules
- **Use OKLCH** for color so lightness steps are perceptually even and you can generate
  ramps programmatically.
- **Nested radii**: child radius ≤ parent radius; keep them concentric so curves align.
- **Layered shadows**: at least two layers to mimic ambient + direct light.
- **Contrast is measured, not assumed**: check every semantic fg/bg pair on its real
  background. Prefer APCA over WCAG 2 for perceptual accuracy; AA is the floor.
- **Both modes**: every color token has a light and dark resolution that both pass contrast.
