# React / Next.js engineering rules (web vertical)

Distilled from vercel-labs/agent-skills (MIT): `react-best-practices` (70 rules),
`composition-patterns`, `react-view-transitions`. Apply while building web components; the
mechanical subset is enforced by `read_ui_audit` (`react-*`, `a11y-*`, `perf-*` ids).
`read_agent_skill_rule(skill)` (no rule) returns the FULL index of every rule (all 70+, incl.
composition-patterns, react-native-skills, react-view-transitions); `read_agent_skill_rule(skill, rule)`
fetches the upstream file with the
incorrect/correct code examples.

## Priority order (impact-ranked — fix top categories first)

| # | Category | Impact | Prefix | Key rules |
| - | --- | --- | --- | --- |
| 1 | Eliminating waterfalls | CRITICAL | `async-` | `async-parallel` (Promise.all independent work), `async-defer-await` (await only inside the branch that uses it), `async-suspense-boundaries` (stream with Suspense), `async-api-routes` (start early, await late) |
| 2 | Bundle size | CRITICAL | `bundle-` | `bundle-barrel-imports` (import the file, not the barrel), `bundle-dynamic-imports` (next/dynamic for heavy), `bundle-defer-third-party` (analytics after hydration), `bundle-conditional`, `bundle-preload` (on hover/focus) |
| 3 | Server-side | HIGH | `server-` | `server-auth-actions` (authenticate Server Actions like API routes), `server-cache-react` (React.cache per-request dedupe), `server-serialization` (minimize props crossing to client), `server-parallel-fetching`, `server-after-nonblocking` (after()) |
| 4 | Client data fetching | MED-HIGH | `client-` | `client-swr-dedup`, `client-passive-event-listeners`, `client-localstorage-schema` |
| 5 | Re-renders | MEDIUM | `rerender-` | `rerender-derived-state-no-effect` (derive during render), `rerender-functional-setstate`, `rerender-lazy-state-init`, `rerender-transitions` (startTransition), `rerender-no-inline-components`, `rerender-memo` |
| 6 | Rendering | MEDIUM | `rendering-` | `rendering-conditional-render` (ternary, not `&&` with numbers), `rendering-content-visibility` (long lists), `rendering-hoist-jsx`, `rendering-resource-hints`, `rendering-script-defer-async` |
| 7 | JS micro-perf | LOW-MED | `js-` | `js-set-map-lookups`, `js-index-maps`, `js-combine-iterations`, `js-early-exit`, `js-tosorted-immutable` |
| 8 | Advanced | LOW | `advanced-` | `advanced-init-once`, `advanced-use-latest`, `advanced-event-handler-refs` |

Rules of thumb that fall out of the table:
- Never fetch in `useEffect` when a Server Component, SWR, or React Query can; sequential
  `await` in a loop is a waterfall.
- Never import from a barrel (`lodash`, `@mui/icons-material`, `react-icons`) in app code.
- Keep the client boundary small: pass the minimum serializable props to `"use client"` components.
- Derive state during render; effects are for synchronizing with the outside world.

## Composition patterns (component APIs)

- **No boolean-prop proliferation.** `<Card compact bordered withFooter dark>` becomes explicit
  variants or composed children (`architecture-avoid-boolean-props`).
- **Compound components** with shared context (`<Tabs><Tabs.List/><Tabs.Panel/></Tabs>`) for anything
  with more than ~3 coordinated parts (`architecture-compound-components`).
- **Lift state into a provider**; the provider is the only place that knows how state is managed;
  UI consumes a generic `{state, actions, meta}` interface (`state-*`).
- **Children over render props**; explicit variant components over boolean modes (`patterns-*`).
- React 19: no `forwardRef`; use `use(Context)` instead of `useContext` (`react19-*`).

This composes naturally with shadcn/ui: tokens decide *how it looks*, composition decides *how it
is assembled* — neither belongs in prop flags.

## View Transitions (React `<ViewTransition>`)

Every transition must communicate a relationship; if you can't say which, omit it. Implement in
this order where applicable:

1. **Shared element** (`name`) — "same thing, going deeper" (list → detail).
2. **Suspense reveal** — "data loaded" (`enter`/`exit`).
3. **List identity** (per-item `key`) — "same items, new arrangement".
4. **State change** (`enter`/`exit`) — "something appeared/disappeared".
5. **Route change** — "going somewhere new".

Style: directional slides only for hierarchical navigation and ordered sequences
(`nav-forward` / `nav-back`); lateral tab changes get a fade or `default="none"`; background
revalidation is silent (`default="none"`). Always honour `prefers-reduced-motion`.
Pairs with the `motion` stage: animate `transform`/`opacity`, durations from motion tokens.
