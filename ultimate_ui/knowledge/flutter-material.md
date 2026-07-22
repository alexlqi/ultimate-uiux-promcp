# Android vertical — Flutter / Material 3 (Material You)

The Android arm of the mobile pipeline. Deterministic target: `read_generated_tokens(spec,
targets=['flutter-material'])` → `app_theme_material.dart`. That file is the contract; widgets
read `Theme.of(context)` and the generated `AppTokens` / `AppSpacing` / `AppRadius` — never raw
literals. Run `read_preflight('flutter-material')` first (flutter SDK + adb).

*Authority: Material Design 3 — m3.material.io. For a rigorous compliance pass, apply the
hamen/material-3-skill 10-category audit as the Android arm of the Audit stage.*

## What the emitter gives you (and how to consume it)
- `AppTheme.light()` / `AppTheme.dark()` → `ThemeData(useMaterial3: true)`. Wire into
  `MaterialApp(theme: AppTheme.light(), darkTheme: AppTheme.dark())`.
- `ColorScheme.fromSeed(seedColor: brand)` generates the tonal palette; the spec's `brand`,
  `bg`, `fg` are **pinned** over it via `.copyWith` so your brand identity survives the seeding.
- `AppTokens extends ThemeExtension<AppTokens>` carries every semantic role as a typed field.
  Read with `Theme.of(context).extension<AppTokens>()!`.
- `AppSpacing` (8-dp grid), `AppRadius`, `AppDurations`, `AppMinTarget.touch = 48.0`.

## Material 3 rules (deterministic, checkable)
- **Touch targets 48×48 dp** minimum — wrap interactive widgets; enforce `AppMinTarget.touch`.
- **8-dp grid** for all spacing (8, 16, 24, 32, 40…); base steps 4/8/12/16/24/32/48.
- **Elevation** = layered tonal surfaces (`surface`, `surfaceContainerHighest`), shadow steps
  1/3/6/8/12 dp. Prefer tonal elevation over heavy shadows.
- **Type**: the Material type scale — Display → Headline → Title → Body → Label (Roboto default).
- **Shape**: 12–16 dp card radius. **Motion**: container transform, shared-axis, fade-through;
  200–500 ms, `Curves.fastOutSlowIn`. Honor `MediaQuery.disableAnimations`.
- **Components**: `Scaffold`, `NavigationBar`, `FloatingActionButton`, `Card`, `ListTile`,
  `showModalBottomSheet`, `TextField(OutlineInputBorder)`.

## Anti-slop gate (Android)
Reject: default unstyled widgets; iOS patterns on Android; purple→blue default gradients;
uniform identical-spacing card grids; timid grayscale; targets under 48 dp; missing dark mode;
spinners instead of skeletons; ignored safe areas; `Color(0x…)` literals when the theme exists.
Aim for: existing-theme consistency, one signature visual moment per screen, tonal depth, motion
that communicates state. Never override Android system back / swipe-to-dismiss / pull-to-refresh.
