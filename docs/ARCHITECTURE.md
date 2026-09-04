# Numpad Stream Deck 3.0 alpha

## Boundaries

- `core`: key contracts and deterministic gesture recognition.
- `profiles`: profiles, pages, and key assignments.
- `actions`: action interface and registered built-ins.
- `storage`: versioned JSON serialization through Qt 6.
- `input`: Windows Raw Input adapter exposed as Qt signals.
- `ui`: Qt Widgets presentation and editing surface.

Raw Input never calls the UI directly. It emits `KeyEvent`; the gesture
detector resolves the configured gesture; `ActionManager` dispatches only
registered action IDs.

## Migration

The Python/Tkinter application and its helper remain untouched as the legacy
implementation. The v2 CMake target is additive and can be built separately.
This allows profiles and behavior to be migrated incrementally without making
the existing installation unusable.

## Security

Configuration stores action references, not shell commands. Built-in actions
must be explicitly registered before they can execute. File, URL, application,
macro, shutdown, and restart actions should be added as validated action
implementations rather than interpreted as arbitrary configuration text.

## Packaging

`scripts/build_release.bat` creates `dist-v2` after running `windeployqt`.
`installer_v2.iss` packages that directory with the Qt runtime. The original
`installer.iss` continues to package the legacy Python application.

## Alpha scope

The alpha includes the Qt application shell, native Raw Input event adapter,
gesture detection, profiles/pages, JSON persistence, system tray, migrated
keyboard/mouse/media/system/application actions, and C++/Python regression
tests. Shortcut recording, visual macro editing, automatic foreground-app
profiles, device enumeration/filtering and a complete production installer
remain follow-up work for later alpha releases.