# Mobile Stack — Flutter (iOS + Android)

The target for **mobile** builds: distinctive, production-grade Flutter for phones, respecting
each platform's industry-standard design language. Target phones only (no tablets) unless asked.

*Source lineage: nylo-core/claude-code — "mobile-design" (platform-aware Flutter, the primary
dual-platform skill). Android authority: Material Design 3 / Material You (m3.material.io;
see also hamen/material-3-skill for a Compose-first MD3 audit). iOS authority: Apple Human
Interface Guidelines + Cupertino.*

## Decide the platform strategy first
- **iOS only** → Cupertino throughout (`CupertinoApp`, `CupertinoNavigationBar`, …).
- **Android only** → Material 3 throughout (`MaterialApp`, `NavigationBar`, `ColorScheme.fromSeed`).
- **Adaptive (both)** → branch by `Platform.isIOS` / `Theme.of(context).platform`, or use
  `.adaptive` constructors (`Switch.adaptive`, `Icon`s, `showAdaptiveDialog`). Never ship iOS
  patterns on Android or vice-versa — users expect their platform's conventions.

## Existing project first
Before anything, search `lib/` for `ThemeData`, `ColorScheme`, `CupertinoThemeData`, and color
constants (`colors.dart`, `theme.dart`, `app_theme.dart`). New screens must belong to the same
app. Extend the existing theme; use its variables and naming. Only introduce new tokens when no
system exists or a required semantic color is missing. This mirrors the token-contract rule:
`Theme.of(context)` **is** the token source — no `Color(0x…)` literals in widgets.

## iOS — Human Interface Guidelines + Cupertino
Principles: **Clarity, Deference, Depth, Consistency** — UI enhances content, never competes.
- Widgets: `CupertinoApp`, `CupertinoNavigationBar`, `CupertinoTabScaffold`, `CupertinoButton`,
  `CupertinoListSection` (inset grouped), `CupertinoTextField`, `showCupertinoModalPopup`.
- Touch targets: **44×44 pt** minimum.
- Navigation: bottom tab bar; **never override** swipe-from-left-edge back gesture; use
  `CupertinoPageRoute` for platform transitions.
- Type: SF Pro via system font; `CupertinoTextTheme`; support **Dynamic Type** up to 200%.
  Hierarchy: Large Title → Title → Headline → Body → Caption.
- Color: semantic `CupertinoColors` (`systemBackground`, `label`, `secondaryLabel`) that adapt
  to light/dark automatically. Translucent, blurred (frosted-glass) materials for depth.
- Corners: **continuous** curves (squircles), not plain circular radius.
- Motion: spring physics (`Curves.easeOutBack`), Hero transitions, subtle parallax/depth.

## Android — Material Design 3 / Material You
Principles: **Material is the metaphor; bold, graphic, intentional; motion provides meaning.**
- Widgets: `MaterialApp`, `Scaffold`, `NavigationBar`, `FloatingActionButton`, `Card`,
  `ListTile`, `showModalBottomSheet`, `TextField` (`OutlineInputBorder`). Set `useMaterial3: true`.
- Touch targets: **48×48 dp** minimum.
- Spacing: **8 dp grid** (8, 16, 24, 32, 40…); base values 4, 8, 12, 16, 24, 32, 48.
- Elevation: layered tonal surfaces (`surface`, `surfaceContainerHighest`); shadow steps
  1/3/6/8/12 dp.
- Type: Roboto via the Material type scale — Display → Headline → Title → Body → Label.
- Color: `ColorScheme.fromSeed(seedColor:)` generates the tonal palette; Material You can pull
  from wallpaper. Use `Theme.of(context).colorScheme` everywhere.
- Corners: 12–16 dp card radius. Motion: container transform, shared-axis, fade-through.
- (For a rigorous MD3 compliance pass, the hamen/material-3-skill audit scores 10 categories:
  color roles, type scale, shape, elevation, components, state layers, motion, layout, a11y,
  theming. Apply it as the Android arm of the Audit stage.)

## Tokens in Flutter
Express the token contract as a typed theme, not scattered literals:
- Android: build `ColorScheme.fromSeed` + a `TextTheme` + a `ThemeExtension` for custom tokens
  (brand, semantic, spacing) so `Theme.of(context).extension<AppTokens>()` is the source.
- iOS: `CupertinoThemeData` + a matching token extension; mirror semantic roles.
- One `AppSpacing`/`AppRadius`/`AppDurations` constants file replaces raw numbers (still on the
  8-pt grid). Widgets read tokens; they never inline values.

## Touch, thumb zones, safe areas
- Thumb zones: primary actions + nav in the **bottom third**; overflow/rare actions top corners.
- Never override system gestures (iOS left-edge back, Android system back, swipe-to-dismiss,
  pull-to-refresh).
- Always wrap in `SafeArea` / honor `MediaQuery.padding`: notch, Dynamic Island, punch-hole,
  home indicator, status bar. Design portrait-first for 19.5:9–21:9; avoid fixed heights.

## Motion (mobile)
Motion provides meaning — invest in a few signature moments, not scattered micro-interactions:
screen entrances (staggered reveals), Hero list→detail transitions, success celebrations,
shimmering skeletons over spinners. Timing **200–500 ms**; `Curves.easeOutCubic` /
`fastOutSlowIn`. Honor `MediaQuery.disableAnimations` (reduce-motion). See `references/motion.md`
for the frequency principle — it applies identically here.

## Accessibility & feel
- `Semantics` widgets with meaningful labels, logical focus order, announced changes.
- Test at **200% text scale**; layouts must not break. Contrast 4.5:1 (3:1 large/interactive).
- Never rely on color alone — pair with icon/text.
- Haptics: `HapticFeedback.lightImpact()` for selection, `mediumImpact()` for confirmation.

## Anti-slop gate (mobile)
Reject: unchanged default Flutter widget styling; iOS patterns on Android (or vice-versa);
purple→blue gradients as default; uniform card grids with identical spacing; timid grayscale
palettes; touch targets under 44 pt / 48 dp; system-gesture overrides; missing dark mode;
spinners instead of skeletons; ignored safe areas; `Color(0x…)` literals when a theme exists.
Aim for: existing-theme consistency, platform-appropriate-but-distinctive design, one signature
visual moment per screen, depth through layering, and motion that communicates state.
