# iOS vertical — Flutter / Cupertino · Human Interface Guidelines

The iOS arm of the mobile pipeline. Deterministic target: `read_generated_tokens(spec,
targets=['flutter-cupertino'])` → `app_theme_cupertino.dart`. Widgets read the
`CupertinoTheme.of(context)` and the generated `AppTokensScope` — never raw literals. Run
`read_preflight('flutter-cupertino')` first (note: building/running iOS needs macOS + Xcode;
token generation is host-agnostic and works anywhere).

*Authority: Apple Human Interface Guidelines + the Cupertino library.*

## What the emitter gives you (and how to consume it)
- `AppTheme.light` / `AppTheme.dark` → `CupertinoThemeData`. Wire into
  `CupertinoApp(theme: AppTheme.light)` and swap by `MediaQuery.platformBrightnessOf(context)`.
- `AppTokens` (plain immutable) exposed through `AppTokensScope` — an `InheritedWidget`, because
  Cupertino has **no** `ThemeExtension`. Wrap your app in `AppTokensScope(tokens: …, child: …)`
  and read via `AppTokensScope.of(context)`.
- `AppSpacing`, `AppRadius`, `AppDurations`, `AppMinTarget.touch = 44.0`.

## HIG rules (deterministic, checkable)
- Principles: **Clarity, Deference, Depth, Consistency** — UI enhances content, never competes.
- **Touch targets 44×44 pt** minimum — enforce `AppMinTarget.touch`.
- **Continuous corners** (squircles), not plain circular radius — prefer superellipse /
  `SmoothRectangleBorder` for cards and sheets.
- **Type**: SF Pro via the system font; `CupertinoTextThemeData`; support **Dynamic Type** to
  200%. Hierarchy: Large Title → Title → Headline → Body → Caption.
- **Color**: prefer semantic `CupertinoColors` (`systemBackground`, `label`, `secondaryLabel`)
  that adapt to light/dark automatically; use frosted-glass/translucent materials for depth.
- **Navigation**: bottom tab bar (`CupertinoTabScaffold`); `CupertinoPageRoute` transitions;
  **never override** the swipe-from-left-edge back gesture.
- **Components**: `CupertinoNavigationBar`, `CupertinoButton`, `CupertinoListSection` (inset
  grouped), `CupertinoTextField`, `showCupertinoModalPopup`.
- **Motion**: spring physics (`Curves.easeOutBack`), Hero transitions, subtle parallax/depth.

## Anti-slop gate (iOS)
Reject: default unstyled widgets; Material patterns on iOS; plain circular radii where continuous
belongs; targets under 44 pt; missing dark mode; overriding the left-edge back gesture; ignored
safe areas (notch, Dynamic Island, home indicator); `Color(0x…)` literals when the theme exists.
Aim for: HIG-faithful but distinctive design, one signature moment per screen, depth through
translucency and layering, haptics (`HapticFeedback.lightImpact()` on selection).
