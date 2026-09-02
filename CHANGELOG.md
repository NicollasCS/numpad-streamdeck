# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
