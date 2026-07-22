# Web Stack — React + Tailwind v4 + shadcn/ui

The default target for **web** builds. This binds the token contract (`references/tokens.md`)
to the exact primitives of this stack so nothing is hardcoded and shadcn theming stays intact.

## The wiring, top to bottom
Design tokens (CSS variables) → Tailwind v4 `@theme` → shadcn semantic tokens → components.
Change a value in one place (the `:root` variables) and it propagates everywhere.

## Tailwind v4 — CSS-first config
v4 has **no `tailwind.config.js`** for theme. Configure in CSS with `@theme`. Tokens become
utilities automatically (`--color-brand` → `bg-brand`, `text-brand`, `border-brand`).

```css
/* app.css */
@import "tailwindcss";

/* Map design tokens into Tailwind's theme. Anything under @theme generates utilities. */
@theme {
  --color-brand: oklch(0.55 0.20 255);
  --radius-md: 0.625rem;              /* 10px */
  --font-display: "Space Grotesk", sans-serif;
  --font-sans: "Inter", sans-serif;
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
}
```

Use `@custom-variant dark` for shadcn's class-based dark mode:
```css
@custom-variant dark (&:is(.dark *));
```

## shadcn/ui semantic token layer
shadcn expects a fixed set of semantic CSS variables. Define them in `:root` and `.dark`,
sourcing values from your primitives. These are the **semantic** layer from `tokens.md`,
named the way shadcn consumes them:

```css
:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.20 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.20 0 0);
  --primary: var(--color-brand);
  --primary-foreground: oklch(0.98 0 0);
  --secondary: oklch(0.96 0 0);
  --muted: oklch(0.96 0 0);
  --muted-foreground: oklch(0.55 0 0);
  --accent: oklch(0.96 0 0);
  --destructive: oklch(0.58 0.22 27);
  --border: oklch(0.92 0 0);
  --input: oklch(0.92 0 0);
  --ring: var(--color-brand);
  --radius: 0.625rem;
}
.dark {
  --background: oklch(0.18 0 0);
  --foreground: oklch(0.98 0 0);
  --card: oklch(0.21 0 0);
  --primary: var(--color-brand);
  --border: oklch(1 0 0 / 0.12);
  --input: oklch(1 0 0 / 0.15);
  /* …dark resolutions for every token above… */
}

@theme inline {
  /* expose the shadcn vars to Tailwind so bg-background, text-foreground, etc. work */
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-border: var(--border);
  --color-ring: var(--ring);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
}
```
Nested-radii come free: derive `sm`/`md`/`lg` from one `--radius` so child ≤ parent.

## Component conventions
- Install primitives via the CLI (`npx shadcn@latest add button dialog …`); **edit the
  generated source** — shadcn is copy-in, not a dependency to fight.
- Variants with **CVA** (`class-variance-authority`); merge classes with `cn()`
  (`clsx` + `tailwind-merge`) so overrides don't collide.
- Reference semantic utilities (`bg-background`, `text-muted-foreground`, `border-border`,
  `ring-ring`) — never raw color utilities like `bg-zinc-900` in app code.
- Focus: rely on shadcn's `focus-visible:ring-ring` pattern; never remove the ring.
- Motion: use `tailwindcss-animate` / `tw-animate-css` + Motion (`motion/react`) per
  `references/motion.md`. Animate `transform`/`opacity`; no `transition-all`.

```tsx
// button.tsx — CVA + cn, consuming semantic tokens only
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-ring disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-border bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: { sm: "h-8 px-3", md: "h-9 px-4", lg: "h-10 px-6" },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);
```

## Audit hooks for this stack
When running the Audit stage on React/Tailwind/shadcn output, additionally check:
- No `bg-*`/`text-*` raw palette colors in app code — only semantic tokens.
- `cn()` used wherever class overrides are accepted (no naked string concatenation).
- Dark mode resolves every shadcn var (no missing `.dark` entries → invisible text).
- `focus-visible:ring-ring` present on every interactive element.
- No `transition-all`; list `transition-[transform,opacity]` or `transition-colors`.
- shadcn components edited in place rather than wrapped in brittle overrides.
