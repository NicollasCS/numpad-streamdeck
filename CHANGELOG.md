# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-09-02

### Added
- Independent `Quick press`, `Hold`, and `Double click` actions for the same key
- Unique action IDs so gesture functions do not overwrite one another
- Hold timing that activates once and requires releasing the key before another activation
- Optional Enter key when using `Type Text`
- Version and repository information in Settings
- 32-bit Windows compatibility warning during setup
- Application icon for the executable, shortcuts, tray, and installer

### Changed
- `Open File or Application` opens files with their Windows default application
- `Open Folder` uses a folder picker
- Quick press waits briefly to distinguish it from double click
- Installer includes the native keyboard helper and Microsoft Visual C++ Redistributable
- Build script uses the project virtual environment and the PyInstaller spec file

### Fixed
- Prevented the trigger key from being inserted before typed text
- Fixed stale Tkinter callbacks after closing key assignment dialogs
- Fixed website values without a protocol opening File Explorer
- Fixed the native helper to report key release events
- Fixed installer architecture detection on 64-bit Windows

## [1.0.0] - 2026-09-01

### Added
- Initial release of Numpad Stream Deck
- Global numpad key detection (works when app is minimized)
- Preset management system with default preset
- 18 configurable action types:
  - Open URL in browser
  - Launch applications
  - Open folders/directories
  - Execute keyboard shortcuts
  - Media controls (play, pause, next, previous, volume)
  - Lock PC
  - Take screenshots (full screen, window, region)
  - Sleep and hibernate system
  - Clipboard text input
- Clean tabbed interface with Presets and Settings tabs
- Persistent configuration stored in AppData
- System tray integration with quick access menu
- Global hotkeys:
  - CTRL+ALT+F12 to toggle enable/disable
  - CTRL+ALT+1 to switch presets
- Windows installer with optional startup configuration
- Professional uninstaller that cleans up user data
- MIT License

### Features
- No dependencies outside of Python standard library (except for UI/tray)
- JSON-based preset configuration with automatic corruption recovery
- Real-time key binding feedback
- Settings panel for configuration management
- Supports up to 20 numeric keypad keys
- Portuguese and English language support in installer

### Fixed
- Handled corrupted preset data with automatic normalization
- Fixed preset loading to enforce single default preset
- Ensured global hotkey detection works across all Windows applications

## [0.0.1] - 2026-08-01

### Added
- Project initialization
- Basic Python structure setup
- Initial UI design concepts

---

For release downloads and binaries, visit [Releases](https://github.com/NicollasCS/numpad-streamdeck/releases).
