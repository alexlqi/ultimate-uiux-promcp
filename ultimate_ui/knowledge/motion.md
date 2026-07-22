# Motion — Add Motion

*Source lineage: emilkowalski/skill — "Add Motion" (Emil Kowalski, Design Engineer at Linear,
ex-Vercel; creator of Sonner and Vaul)*

Purpose: add motion that clarifies cause-and-effect or adds *deliberate* delight — never
motion for its own sake. The defining skill is knowing **when NOT to animate**.

## The frequency rule (decide IF before deciding HOW)
Animation appropriateness scales inversely with interaction frequency:
- **High-frequency actions** (a button used constantly, a command palette, a tool used all
  day) → little to **no** motion. Users with clear goals don't want to be delighted; they want
  frictionless speed. The Raycast example: constant-use tools benefit from zero animation.
- **Low-frequency / meaningful moments** (a success confirmation, onboarding, a modal open,
  a first-time reveal) → considered motion is welcome.

Ask "how often will the user trigger this?" before adding any animation.

## Speed
- **Keep UI animations under ~300ms.** A 180ms animation feels more responsive than 400ms.
  Speed *is* perceived performance. When in doubt, go faster.
- Immediate feedback beats smooth-but-slow.

## Recipes (token-driven)
Reference motion tokens from `tokens.css` (`--dur-fast`, `--dur-base`, `--ease-out`), never
raw values.

Press feedback — subtle scale-down for instant tactile response:
```jsx
<motion.button
  whileTap={{ scale: 0.97 }}
  transition={{ type: "spring", stiffness: 400, damping: 25 }}
/>
```
Never animate *from* `scale(0)` — it reads as unnatural. Start near the final size.

Enter/exit:
```jsx
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: 4 }}
  transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
/>
```

Staggered lists — small stagger, not a slow cascade:
```jsx
<motion.ul initial="hidden" animate="visible"
  variants={{ visible: { transition: { staggerChildren: 0.04 } } }}>
  {items.map(i => (
    <motion.li key={i.id}
      variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }} />
  ))}
</motion.ul>
```

View transitions with `AnimatePresence mode="wait"` and a short (~150ms) crossfade.

Springs interpolate naturally because nothing in the real world changes instantly:
`{ stiffness: 300, damping: 30 }` is a solid default. `clip-path: inset(...)` is a powerful,
underused reveal primitive.

## Non-negotiables (also enforced by the audit stage)
- **Honor `prefers-reduced-motion`.** Always provide a reduced variant:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
- **Compositor-only properties.** Animate `transform` and `opacity`; avoid `width`, `height`,
  `top`, `left` (they trigger reflow/jank).
- **Never `transition: all`.** List exactly the properties you animate.
- **Interruptible & input-driven.** Animations cancel on user input; avoid autoplay.
- **Correct `transform-origin`.** Anchor motion where it physically starts.
- **`will-change` sparingly** — apply before, remove after; never leave it on permanently.
- **Don't animate layout on mobile;** test on a low-end device, not just an M-series Mac.
- Prefer CSS > Web Animations API > JS libraries, in that order.

## The philosophy
"The goal is not to animate for animation's sake, it's to build great user interfaces." When
a feature works as the user assumes, they proceed without a second thought — that's the goal.
Polished interactions shouldn't be *noticed*; they should just feel right. Restraint is the
craft.
