# Numpad Stream Deck

A Windows desktop app that turns one or more physical keyboards into configurable shortcut pads. Select a keyboard, assign keys to actions, and keep different workflows in separate presets.

## Features

- Physical keyboard selection using Windows Raw Input
- Keyboard test mode showing the device ID and pressed key
- Per-key names and per-key device identification
- Presets with create, switch, and delete operations
- Actions for websites, applications, folders, media, screenshots, lock, text, and shortcuts
- Shortcut recording for combinations such as `Alt+Left`
- Optional toggle, double-click, and activation delay for every key
- System tray support
- Optional startup with Windows
- Optional minimize-to-tray behavior
- Global `Ctrl+Alt+F12` enable/disable shortcut
- Single-instance protection to prevent duplicate helpers and tray icons

## Supported Actions

- Close Window
- Open Website
- Launch Application
- Open Folder
- Keyboard Shortcut
- Play/Pause
- Previous Track
- Next Track
- Volume Up
- Volume Down
- Mute
- Windows+Tab
- Alt+Tab
- Type Text+Enter
- Lock PC
- Screenshot

## Requirements

- Windows 10 or later
- Python 3.10 or later for running from source
- Visual Studio C++ build tools for compiling the Raw Input helper
- Inno Setup 6 only when building the installer

## Run From Source

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python numpad_streamdeck.py
```

The application stores user data at:

```text
%APPDATA%\NumpadStreamDeck\numpad_presets.json
```

## Physical Keyboard Filtering

The application uses `cpp/raw_input_filter.exe` to identify the physical keyboard that generated an event. Build it from a Visual Studio Developer Command Prompt:

```bat
cd cpp
build_raw_input_helper.bat
```

Then start the application and open **Settings**:

1. Click **Refresh keyboards**.
2. Select a keyboard from the list.
3. Use **Rename selected keyboard** if desired.
4. Use **Test keyboard** to verify the device and key.

The helper consumes legacy input for the selected Stream Deck keyboard so configured keys do not leak into the foreground application. Use a dedicated keyboard or numpad for this mode.

## Configure Keys

1. Open the **Presets** tab.
2. Click `+` to assign a physical key.
3. Click **Assign key**, then press the desired key.
4. Choose an action and fill in its value.
5. For **Keyboard Shortcut**, use **Record shortcut** or enter a combination such as `Alt+Left`.
6. Optionally set a key name, toggle mode, double-click mode, or delay in milliseconds.
7. Click **Save**.

Existing assignments can be edited, renamed, or moved to another physical key with **Change key**.

## Build

The release script installs Python dependencies, builds the executable, copies the Raw Input helper, and optionally creates the Inno Setup installer:

```bat
build_release.bat
```

Outputs:

```text
dist\NumpadStreamDeck.exe
dist\raw_input_filter.exe
installer\NumpadStreamDeck_Setup.exe
```

The installer build requires Inno Setup to be installed and available as `iscc` in `PATH`.

## Tests

Run the tests with the project virtual environment:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Project Structure

```text
numpad_streamdeck.py          Main Tkinter application
cpp/raw_input_filter.cpp     Windows Raw Input helper source
cpp/build_raw_input_helper.bat  Helper build script
tests/                       Keyboard filter and bridge tests
build_release.bat            Executable and installer build script
installer.iss                Inno Setup configuration
requirements.txt             Python dependencies
icon.ico                     Application icon
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
