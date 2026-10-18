# React Native / Expo (cross-platform app vertical, JS side)

Distilled from vercel-labs/agent-skills `react-native-skills` (MIT). `react-native` is a first-class paradigm (alongside `flutter-material` / `flutter-cupertino`):
`read_design_brief(..., 'react-native')` -> `read_generated_tokens(spec, paradigm='react-native')` emits ONE
typed `theme.ts` (light/dark colour roles in camelCase, `spacing`, `radius`, `duration`, `minTarget` = 44pt
iOS / 48dp Android, and a `useTokens()` hook following the system colour scheme);
`do_write_token_files(..., paradigm='react-native')` persists it. Verified: the generated file plus a
token-driven FlatList screen pass `tsc --strict` against react-native 0.76.
`read_agent_skill_rule('react-native-skills', '<rule>')` fetches any rule below.

## Priority order

| # | Category | Impact | Rules |
| - | --- | --- | --- |
| 1 | List performance | CRITICAL | `list-performance-virtualize` (FlashList for large lists), `-item-memo`, `-callbacks` (stable refs), `-inline-objects` (no inline style objects), `-function-references`, `-images`, `-item-expensive` (hoist work out of items), `-item-types` (heterogeneous lists) |
| 2 | Animation | HIGH | `animation-gpu-properties` (transform + opacity only), `animation-derived-value` (useDerivedValue), `animation-gesture-detector-press` (Gesture.Tap over Pressable for animated press) |
| 3 | Navigation | HIGH | `navigation-native-navigators` (native stack/tabs over JS navigators) |
| 4 | UI patterns | HIGH | `ui-expo-image` (all images), `ui-pressable` (not TouchableOpacity), `ui-safe-area-scroll`, `ui-scrollview-content-inset`, `ui-menus` / `ui-native-modals` (native over custom), `ui-measure-views` (onLayout), `ui-styling` (StyleSheet.create or Nativewind) |
| 5 | State | MEDIUM | `react-state-minimize`, `react-state-dispatcher`, `react-state-fallback`, React-Compiler-safe destructuring |
| 6 | Rendering | MEDIUM | `rendering-text-in-text-component` (strings must live in `<Text>`), `rendering-no-falsy-and` (`0 && <X/>` crashes/renders 0) |
| 7 | Monorepo | MEDIUM | native deps live in the app package; one version per dependency across packages |
| 8 | Config | LOW | fonts via config plugin; design-system folder imports; hoist `Intl` objects |

## Decisions that matter most

- **Lists**: a `ScrollView` + `.map()` renders every row — use FlashList/FlatList with stable
  `keyExtractor`, memoized rows, no inline style/closure creation in `renderItem`.
- **Animation**: never animate layout (`width/height/top/left`); drive `transform`/`opacity` on the
  UI thread (Reanimated) — the same rule as the web `motion` stage.
- **Native feel**: native stack/tabs, native modals/menus, `Pressable`, `expo-image`; safe-area
  handling in scrollable screens; respect platform idiom (iOS HIG vs Material) like the Flutter stages.
- **Tokens**: no raw hex or magic numbers in components — import from the generated theme.

`read_ui_audit` flags `rn-scrollview-map`, `rn-flatlist`, `rn-touchable` mechanically.
