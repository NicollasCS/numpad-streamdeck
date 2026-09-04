# Numpad Stream Deck

## v3.0.0-alpha.1

The Qt 6 rewrite is available under `src/numpad_streamdeck`. It is an
incremental Windows desktop implementation using C++20, Qt 6, CMake and
native Windows Raw Input. The original Python application remains available
as the legacy implementation during migration.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module boundaries and
migration notes.

A Windows desktop app that turns one or more physical keyboards into configurable shortcut pads. Select a keyboard, assign keys to actions, and keep different workflows in separate presets.

## Features

- Physical keyboard selection using Windows Raw Input
- Keyboard test mode showing the device ID and pressed key
- Per-key names and per-key device identification
- Presets with create, switch, and delete operations
- Actions for websites, applications, folders, media, screenshots, lock, text, and shortcuts
- Shortcut recording for combinations such as `Alt+Left`
- Quick press, hold, and double-click actions for the same key
- System tray support
- Optional startup with Windows
- Optional minimize-to-tray behavior
- Global `Ctrl+Alt+F12` enable/disable shortcut
- Single-instance protection to prevent duplicate helpers and tray icons

## Supported Actions

- Close Window
- Open Website
- Open File or Application
- Open Folder
- Keyboard Shortcut
- Play/Pause
- Previous Track
- Next Track
- Volume Up
- Volume Down
- Mute
- Type Text
- Screenshot

## Requirements

- Windows 10 or later
- Visual Studio 2022 with Desktop development with C++
- Qt 6 for MSVC 2022 64-bit
- CMake 3.20 or newer
- Python 3.10 or later for running from source
- Inno Setup 6 only when building the installer

## Build the Qt application

Open **Developer Command Prompt for VS 2022**, then run one command at a time:

```bat
cd /d C:\Users\nicol\Documents\fodase
set CMAKE_PREFIX_PATH=C:\Qt\6.11.2\msvc2022_64
cmake --preset debug
cmake --build --preset debug-build
ctest --preset debug-test
build-v2\debug\Debug\NumpadStreamDeck.exe
```

The exact Qt path may differ on your machine. `windeployqt` copies the Qt
runtime beside the executable during the build.

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
6. Select a gesture: **Quick press**, **Hold**, or **Double click**.
7. For **Hold**, set the required hold time in milliseconds.
8. Click **Save**.
7. Click **Save**.

Existing assignments can be edited, renamed, or moved to another physical key with **Change key**.

## Legacy build

The release script installs Python dependencies, builds the executable, copies the Raw Input helper, and optionally creates the Inno Setup installer:

```bat
build_release.bat
```

Legacy outputs:

```text
dist\NumpadStreamDeck.exe
dist\raw_input_filter.exe
installer\NumpadStreamDeck_Setup.exe
```

The installer build requires Inno Setup to be installed. The release script also detects the default Inno Setup installation path automatically.

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

The v3 implementation is organized under `src/numpad_streamdeck` into core,
profiles, actions, storage, input and UI modules. The v2 CMake targets are
`NumpadStreamDeck` and `numpad_streamdeck_core_tests`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
