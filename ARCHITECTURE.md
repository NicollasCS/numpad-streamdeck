# Architecture

This document explains the architecture and design of Numpad Stream Deck.

## Overview

Numpad Stream Deck is a Windows desktop application that provides global hotkey detection and action execution through the numeric keypad. The application runs continuously and responds to keypad input regardless of which application has focus.

## Project Structure

```
numpad-streamdeck/
├── numpad_streamdeck.py      # Main application file
├── installer.iss             # Inno Setup installer configuration
├── requirements.txt          # Python dependencies
├── icon.ico                  # Application icon
├── README.md                 # User documentation
├── WORKFLOW.md               # Git Flow workflow guide
├── CONTRIBUTING.md           # Contribution guidelines
├── CHANGELOG.md              # Version history
├── ARCHITECTURE.md           # This file
├── LICENSE                   # MIT License
└── .gitignore               # Git ignore rules
```

## Core Components

### 1. NumpadStreamDeckApp (Main Class)

The main application controller that orchestrates all functionality.

```python
class NumpadStreamDeckApp:
    def __init__(self, root):
        # Initialize UI, load presets, setup hotkeys
        
    def build_ui(self):
        # Create tabbed interface (Presets tab + Settings tab)
        
    def load_presets(self):
        # Load presets from JSON, normalize data
        
    def execute_action(self, action_type, action_value):
        # Route actions to appropriate handlers
        
    def setup_global_hotkeys(self):
        # Register CTRL+ALT+F12 and CTRL+ALT+1
```

### 2. UI Layer (Tkinter)

- **Main Window**: 980x720 with modern "clam" theme
- **Presets Tab**: Visual representation of numpad keys with 20 buttons
- **Settings Tab**: Configuration options, status display, hotkey documentation
- **Key Configuration Dialog**: Allows selecting action type and value for each key
- **System Tray**: Minimizes to tray, quick preset switching

### 3. Preset Management

Presets are stored as JSON in: `%APPDATA%\NumpadStreamDeck\numpad_presets.json`

```json
{
  "presets": {
    "Default": {
      "keys": {
        "Numpad 0": {
          "type": "open_url",
          "value": "https://example.com"
        },
        "Numpad 1": {
          "type": "media_control",
          "value": "play_pause"
        }
      }
    }
  }
}
```

**Key Features:**
- Automatic corruption recovery with `normalize_preset()`
- Single "Default" preset enforcement
- Supports up to 20 numpad keys

### 4. Action System

18 action types supported:

| Type | Handler | Purpose |
|------|---------|---------|
| `open_url` | `webbrowser.open()` | Open URL in default browser |
| `launch_app` | `subprocess.Popen()` | Execute application file |
| `open_folder` | `os.startfile()` | Open folder in Explorer |
| `execute_hotkey` | `keyboard.write()` | Send keyboard shortcut |
| `media_play` | `keyboard.send()` | Media control commands |
| `lock_pc` | `ctypes.windll.user32.LockWorkStation()` | Lock Windows |
| `screenshot_full` | PIL screenshot | Full screen capture |
| `screenshot_window` | PIL screenshot | Active window capture |
| `screenshot_region` | PIL screenshot | Selected region capture |
| `sleep_system` | Windows command | Sleep mode |
| `hibernate_system` | Windows command | Hibernate mode |
| `clipboard_text` | `pyperclip` | Paste text from clipboard |

### 5. Global Hotkey System

Uses `keyboard` library to detect key presses even when app is minimized:

- **CTRL+ALT+F12**: Toggle application enabled/disabled
- **CTRL+ALT+1**: Switch to next preset

## Data Flow

### Key Press Event

```
User presses Numpad key
  ↓
keyboard.on_press() callback triggered
  ↓
Check if app is enabled
  ↓
Look up action in current preset
  ↓
execute_action() with action_type + action_value
  ↓
Action handler executes (browser, subprocess, etc.)
  ↓
UI updates (if window is visible)
```

### Application Launch

```
numpad_streamdeck.py starts
  ↓
Load presets from JSON (with normalization)
  ↓
Initialize Tkinter GUI
  ↓
Setup global hotkeys (CTRL+ALT+F12, CTRL+ALT+1)
  ↓
Create system tray icon
  ↓
Wait for user input (key presses or UI interaction)
```

## Dependencies

### Python Libraries

- **tkinter**: GUI (ttk for modern styling)
- **keyboard**: Global hotkey detection
- **pystray**: System tray integration
- **Pillow (PIL)**: Icon creation and screenshot capture
- **Standard Library**: json, os, pathlib, subprocess, threading, time, ctypes, webbrowser

### External Tools

- **PyInstaller 6.21.0**: Bundle Python code into standalone .exe
- **Inno Setup 6.7.3**: Create Windows installer with uninstaller

## Threading Model

- **Main Thread**: Tkinter event loop and GUI
- **Keyboard Thread**: Continuous key press monitoring (blocking but non-CPU-intensive)
- **Action Execution**: Actions run on main thread to ensure UI consistency

## Error Handling

- **Corrupted JSON**: Automatically fixed with `normalize_preset()`
- **Missing files**: Default preset created on first run
- **Invalid actions**: Skipped silently (logged if debug enabled)
- **Permission errors**: Gracefully handled for privileged operations (lock PC)

## Configuration Files

### Installation

**Location**: `C:\Program Files\NumpadStreamDeck\`

Files:
- `NumpadStreamDeck.exe` (main executable)
- `icon.ico` (application icon)

### User Data

**Location**: `%APPDATA%\NumpadStreamDeck\`

Files:
- `numpad_presets.json` (preset configuration)

### Registry (Optional)

If "Startup with Windows" selected:
- `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\NumpadStreamDeck`

## Building & Distribution

### Build Executable

```bash
pyinstaller --onefile --windowed --icon=icon.ico numpad_streamdeck.py
```

Output: `dist/NumpadStreamDeck.exe` (~40-50MB)

### Create Installer

```bash
iscc installer.iss
```

Output: `installer/NumpadStreamDeck_Setup.exe`

Features:
- Two-step installation (desktop shortcut, startup option)
- Modern wizard UI
- Portuguese + English language support
- Automatic AppData cleanup on uninstall

## Performance Considerations

- **Key Detection**: Minimal CPU usage (~0.1% when idle)
- **Memory**: ~30-50MB footprint
- **Startup Time**: ~2-3 seconds
- **Responsiveness**: <50ms latency on key press

## Future Improvements

- [ ] Macro recording and playback
- [ ] Custom action scripting (Python/Lua)
- [ ] Cloud preset synchronization
- [ ] Per-application preset switching
- [ ] Network profile support
- [ ] Multi-monitor screenshot support

## Security Notes

- Application runs with user privileges (no admin required)
- Presets stored in plain JSON (no encryption)
- Global hotkeys are intercepted at OS level (potential for detection by malware)
- No network connections or telemetry
- Open source for community review

## Testing

Currently tested on:
- Windows 10 (21H2)
- Windows 11
- Python 3.14.5

Manual testing procedures:
1. Test each action type with various values
2. Verify preset persistence across application restarts
3. Confirm global hotkeys work across different applications
4. Test installation and uninstallation flow
5. Verify system tray functionality

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
