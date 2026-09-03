"""
Numpad Stream Deck - Simple Keyboard Shortcut Manager
Manage keyboard shortcuts with a clean, minimalist interface.
"""

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, Toplevel, filedialog, messagebox, simpledialog
from tkinter import ttk
import tkinter as tk

import keyboard
import pystray
from PIL import Image

# Configuration
APP_NAME = "Numpad Stream Deck"
APPDATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "NumpadStreamDeck"
PRESET_FILE = APPDATA_DIR / "numpad_presets.json"
APP_VERSION = "v2.2.0"
REPOSITORY_URL = "https://github.com/NicollasCS/numpad-streamdeck"
DOUBLE_CLICK_INTERVAL = 0.4
_instance_mutex = None


def acquire_single_instance():
    """Keep only one application process and tray icon running."""
    global _instance_mutex
    if os.name != "nt":
        return True
    kernel32 = ctypes.windll.kernel32
    _instance_mutex = kernel32.CreateMutexW(None, False, "Local\\NumpadStreamDeck")
    return kernel32.GetLastError() != 183


def resource_path(filename):
    """Resolve a bundled resource in source and PyInstaller builds."""
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_dir / filename

# Actions available
ACTION_TYPES = [
    "None",
    "Close Window",
    "Open Website",
    "Open File or Application",
    "Open Folder",
    "Keyboard Shortcut",
    "Play/Pause",
    "Previous Track",
    "Next Track",
    "Volume Up",
    "Volume Down",
    "Mute",
    "Type Text",
    "Screenshot",
]

ACTION_MAP = {
    "None": "none",
    "Close Window": "close_window",
    "Open Website": "open_site",
    "Open File or Application": "open_program",
    "Open Folder": "open_folder",
    "Keyboard Shortcut": "hotkey",
    "Play/Pause": "play_pause",
    "Previous Track": "prev_track",
    "Next Track": "next_track",
    "Volume Up": "volume_up",
    "Volume Down": "volume_down",
    "Mute": "mute",
    "Type Text": "write_text",
    "Screenshot": "screenshot",
}
TOGGLE_ACTION_TYPES = {"Keyboard Shortcut", "Type Text"}
BROWSE_ACTION_TYPES = {"Open File or Application", "Open Folder"}
GESTURE_TYPES = {
    "Quick press": "quick_press",
    "Hold": "hold",
    "Double click": "double_click",
}


def ensure_appdata_dir():
    """Ensure AppData directory exists"""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)


def default_preset():
    """Create empty preset"""
    return {"keys": {}}


class PresetManager:
    """Manage presets loading/saving"""

    def __init__(self):
        self.presets = {"Default": default_preset()}
        self.current = "Default"
        self.keyboard_names = {}
        self.settings = {}
        self.load()

    def load(self):
        """Load presets from file"""
        if not PRESET_FILE.exists():
            self.presets = {"Default": default_preset()}
            self.save()
            return

        try:
            with open(PRESET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "presets" in data:
                self.presets = data["presets"]
                self.current = data.get("current_preset", "Default")
                self.keyboard_names = data.get("keyboard_names", {})
                self.settings = data.get("settings", {})
            else:
                self.presets = data if isinstance(data, dict) else {"Default": default_preset()}
        except Exception:
            self.presets = {"Default": default_preset()}

        # Ensure Default preset exists
        if "Default" not in self.presets:
            self.presets["Default"] = default_preset()
        if self.current not in self.presets:
            self.current = "Default"
        if not isinstance(self.keyboard_names, dict):
            self.keyboard_names = {}
        if not isinstance(self.settings, dict):
            self.settings = {}

    def save(self):
        """Save presets to file"""
        ensure_appdata_dir()
        with open(PRESET_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "current_preset": self.current,
                    "presets": self.presets,
                    "keyboard_names": self.keyboard_names,
                    "settings": self.settings,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def get_current(self):
        """Get current preset"""
        return self.presets.get(self.current, default_preset())

    def switch(self, name):
        """Switch to preset"""
        if name in self.presets:
            self.current = name
            self.save()

    def create(self, name):
        """Create and select a new preset."""
        name = str(name or "").strip()
        if not name or name in self.presets:
            return False
        self.presets[name] = default_preset()
        self.current = name
        self.save()
        return True

    def delete(self, name):
        """Delete a preset while keeping Default available."""
        if name == "Default" or name not in self.presets:
            return False
        del self.presets[name]
        self.current = "Default"
        self.save()
        return True


class NumpadStreamDeckApp:
    """Main application"""

    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x650")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.presets = PresetManager()
        self.enabled = not bool(self.presets.settings.get("disabled", False))
        self.recording_key = None
        self.recording_callback = None
        self.keyboard_device_id = ""
        self.keyboard_device_var = StringVar(value="All keyboards")
        self.keyboard_full_id_var = StringVar(value="No keyboard selected")
        self.available_keyboard_devices = []
        app_directory = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        self.native_helper = app_directory / "cpp" / "raw_input_filter.exe"
        self.native_process = None
        self.native_reader = None
        self.shortcut_recording_callback = None
        self._assignment_generation = 0
        self._assignment_key_var = None
        self._assignment_key_label = None
        self.toggle_states = {}
        self.toggle_jobs = {}
        self.held_keys = {}
        self.pending_taps = {}
        self.last_press_times = {}
        self.device_test_active = False
        self.device_test_status_var = StringVar(value="")
        self.startup_var = BooleanVar(value=bool(self.presets.settings.get("startup", False)))
        self.minimize_on_close_var = BooleanVar(
            value=bool(self.presets.settings.get("minimize_on_close", False))
        )
        self.disable_streamdeck_var = BooleanVar(
            value=bool(self.presets.settings.get("disabled", False))
        )

        self.status_var = StringVar(value="Enabled" if self.enabled else "Disabled")
        self.preset_var = StringVar(value=self.presets.current)

        self._build_ui()
        self._setup_hotkeys()
        self._create_tray()
        self._listen_keys()

    def _build_ui(self):
        """Build UI"""
        # Header
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, font=("Arial", 16, "bold")).pack(side="left")
        self.status_label = ttk.Label(
            header, textvariable=self.status_var, font=("Arial", 10), foreground="#16a34a"
        )
        self.status_label.pack(side="right")

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=0)

        # Tab 1: Presets
        self.tab_presets = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_presets, text="Presets")
        self._build_presets_tab()

        # Tab 2: Settings
        self.tab_settings = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_settings, text="Settings")
        self._build_settings_tab()

    def _build_presets_tab(self):
        """Build presets tab"""
        # Presets selector
        presets_frame = ttk.LabelFrame(self.tab_presets, text="Presets", padding=10)
        presets_frame.pack(fill="x", pady=(0, 12))

        self.preset_combo = ttk.Combobox(
            presets_frame,
            textvariable=self.preset_var,
            values=list(self.presets.presets.keys()),
            state="readonly",
        )
        self.preset_combo.pack(fill="x")
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self._switch_preset())
        preset_controls = ttk.Frame(presets_frame)
        preset_controls.pack(fill="x", pady=(8, 0))
        ttk.Button(preset_controls, text="New preset", command=self._create_preset).pack(side="left")
        ttk.Button(preset_controls, text="Delete preset", command=self._delete_preset).pack(
            side="left", padx=(6, 0)
        )

        # Controls
        controls = ttk.Frame(self.tab_presets)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="Functions").pack(side="left", padx=(4, 8))
        ttk.Button(controls, text="+", width=3, command=self._assign_key).pack(side="left")

        # Keys list
        self.keys_container = ttk.Frame(self.tab_presets)
        self.keys_container.pack(fill="both", expand=True)

        self._refresh_keys()

    def _build_settings_tab(self):
        """Build settings tab"""
        device_frame = ttk.LabelFrame(self.tab_settings, text="Keyboard filter", padding=10)
        device_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(device_frame, text="Only process keys from:").pack(anchor="w")
        self.keyboard_device_combo = ttk.Combobox(
            device_frame, textvariable=self.keyboard_device_var, state="readonly"
        )
        self.keyboard_device_combo.pack(fill="x", pady=(4, 6))
        self.keyboard_device_combo.bind("<<ComboboxSelected>>", self._select_keyboard_device)
        ttk.Label(device_frame, text="Full device ID:").pack(anchor="w")
        ttk.Entry(
            device_frame,
            textvariable=self.keyboard_full_id_var,
            state="readonly",
        ).pack(fill="x", pady=(2, 6))
        ttk.Button(
            device_frame, text="Refresh keyboards", command=self._refresh_keyboard_devices
        ).pack(anchor="w")
        ttk.Button(
            device_frame, text="Rename selected keyboard", command=self._rename_keyboard
        ).pack(anchor="w", pady=(6, 0))
        self.device_test_button = ttk.Button(
            device_frame, text="Test keyboard", command=self._toggle_keyboard_test
        )
        self.device_test_button.pack(anchor="w", pady=(6, 0))
        ttk.Label(device_frame, textvariable=self.device_test_status_var).pack(
            anchor="w", pady=(4, 0)
        )
        self._refresh_keyboard_devices()

        preferences = ttk.LabelFrame(self.tab_settings, text="Application", padding=10)
        preferences.pack(fill="x", pady=(12, 0))
        ttk.Checkbutton(
            preferences,
            text="Start with Windows",
            variable=self.startup_var,
            command=self._set_start_with_windows,
        ).pack(anchor="w")
        ttk.Checkbutton(
            preferences,
            text="Minimize to tray when closing",
            variable=self.minimize_on_close_var,
            command=self._save_preferences,
        ).pack(anchor="w")
        ttk.Checkbutton(
            preferences,
            text="Disable Stream Deck",
            variable=self.disable_streamdeck_var,
            command=self._set_streamdeck_disabled,
        ).pack(anchor="w")
        ttk.Label(preferences, text="Toggle shortcut: CTRL+ALT+F12").pack(anchor="w", pady=(8, 0))
        ttk.Label(preferences, text=f"Version: {APP_VERSION}").pack(anchor="w", pady=(8, 0))
        ttk.Label(preferences, text=f"Repository: {REPOSITORY_URL}").pack(anchor="w")

    def _create_preset(self):
        name = simpledialog.askstring(APP_NAME, "Preset name:", parent=self.root)
        if self.presets.create(name):
            self.preset_var.set(self.presets.current)
            self.preset_combo["values"] = list(self.presets.presets)
            self._refresh_keys()
        elif name:
            messagebox.showwarning(APP_NAME, "A preset with that name already exists")

    def _delete_preset(self):
        name = self.presets.current
        if name == "Default":
            messagebox.showwarning(APP_NAME, "The Default preset cannot be deleted")
            return
        if messagebox.askyesno(APP_NAME, f"Delete preset '{name}'?", parent=self.root):
            self.presets.delete(name)
            self.preset_var.set(self.presets.current)
            self.preset_combo["values"] = list(self.presets.presets)
            self._refresh_keys()

    def _save_preferences(self):
        self.presets.settings["minimize_on_close"] = self.minimize_on_close_var.get()
        self.presets.settings["disabled"] = self.disable_streamdeck_var.get()
        self.presets.save()

    def _set_streamdeck_disabled(self):
        self.enabled = not self.disable_streamdeck_var.get()
        self._toggle_status_display()
        self._save_preferences()

    def _toggle_status_display(self):
        self.status_var.set("Enabled" if self.enabled else "Disabled")
        self.status_label.config(foreground="#16a34a" if self.enabled else "#d97706")

    def _set_start_with_windows(self):
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if self.startup_var.get():
                    if getattr(sys, "frozen", False):
                        startup_command = sys.executable
                    else:
                        startup_command = f'"{sys.executable}" "{Path(__file__).resolve()}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            self.presets.settings["startup"] = self.startup_var.get()
            self.presets.save()
        except (OSError, ImportError) as error:
            self.startup_var.set(False)
            messagebox.showerror(APP_NAME, f"Could not update Windows startup: {error}")

    def _refresh_keys(self):
        """Refresh keys list"""
        for w in self.keys_container.winfo_children():
            w.destroy()

        preset = self.presets.get_current()
        keys = preset.get("keys", {})

        if not keys:
            ttk.Label(self.keys_container, text="No keys assigned", foreground="#999").pack(
                pady=20
            )
            return

        for key_id, action in sorted(keys.items()):
            action_store = self._get_action_store(action)
            if action_store:
                for action_id, gesture_action in action_store.items():
                    self._add_key_row(
                        key_id,
                        action,
                        gesture_action,
                        gesture_action.get("gesture", "quick_press"),
                        action_id,
                    )
            else:
                self._add_key_row(key_id, action)

    def _add_key_row(self, key_id, key_entry, action=None, gesture="quick_press", action_id=None):
        """Add a key row"""
        action = action or self._get_gesture_action(key_entry, gesture) or key_entry
        row = ttk.Frame(self.keys_container)
        row.pack(fill="x", pady=4)

        # Key label
        key_label = ttk.Label(
            row,
            text=self._display_key_id(
                key_id, f"{gesture.replace('_', ' ').title()} : {self._display_action_name(action)}"
            ),
            font=("Arial", 10, "bold"),
            width=32,
        )
        key_label.pack(side="left")

        # Action combobox
        display_action = self._get_gesture_action(action, "quick_press") or action
        action_type = display_action.get("type", "none")
        action_label = self._get_action_label(action_type)

        action_var = StringVar(value=action_label)
        combo = ttk.Combobox(
            row,
            textvariable=action_var,
            values=["None"] + list(ACTION_MAP.keys())[1:],
            state="readonly",
            width=25,
        )
        combo.pack(side="left", padx=(20, 8), fill="x", expand=True)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._set_action(key_id, action_var.get(), gesture),
        )

        # Edit button
        ttk.Button(
            row,
            text="Edit",
            command=lambda: self._edit_key(key_id, gesture),
        ).pack(side="right", padx=(4, 0))

        # Delete button
        ttk.Button(
            row,
            text="-",
            width=2,
            command=lambda: self._delete_key(key_id, action_id),
        ).pack(side="right")

    def _assign_key(self):
        """Open assign key dialog"""
        dialog = Toplevel(self.root)
        dialog.title("Assign Key")
        dialog.geometry("460x600")
        dialog.minsize(460, 600)
        dialog.transient(self.root)
        dialog.grab_set()

        key_var = StringVar(value="")
        name_var = StringVar(value="")
        func_var = StringVar(value="None")
        value_var = StringVar(value="")
        toggle_var = BooleanVar(value=False)
        double_click_var = BooleanVar(value=False)
        delay_var = StringVar(value="0")
        toggle_interval_var = StringVar(value="1000")
        send_when_executed_var = BooleanVar(value=True)
        gesture_var = StringVar(value="Quick press")

        ttk.Label(dialog, text="Press a key:", font=("Arial", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        key_label = ttk.Label(dialog, text="Waiting...", font=("Arial", 11), foreground="#0066cc")
        key_label.pack(anchor="w", padx=14, pady=(0, 12))
        conflict_var = StringVar(value="")
        ttk.Label(dialog, textvariable=conflict_var, foreground="#d97706", wraplength=430).pack(
            anchor="w", padx=14, pady=(0, 8)
        )

        def update_key_conflict(*_args):
            selected_key = key_var.get()
            existing_action = self.presets.get_current().get("keys", {}).get(selected_key)
            if not existing_action:
                conflict_var.set("")
                return
            assignments = []
            for gesture_name, gesture_label in GESTURE_TYPES.items():
                gesture_action = self._get_gesture_action(existing_action, gesture_label)
                if gesture_action:
                    assigned_name = gesture_action.get("name", "").strip() or "Unnamed"
                    assigned_function = self._get_action_label(gesture_action.get("type", "none"))
                    assignments.append(f"{gesture_name}: {assigned_name} ({assigned_function})")
            conflict_var.set(
                f"Another function is already assigned to key {selected_key}: "
                f"{' ; '.join(assignments)}."
            )

        key_var.trace_add("write", update_key_conflict)
        key_action_row = ttk.Frame(dialog)
        key_action_row.pack(fill="x", padx=14, pady=(0, 12))
        assign_button = ttk.Button(
            key_action_row,
            text="Assign key",
            command=lambda: self._begin_key_capture(key_var, key_label, assign_button),
        )
        assign_button.pack(side="left")

        ttk.Label(dialog, text="Function:", font=("Arial", 10, "bold")).pack(anchor="w", padx=14, pady=(0, 4))
        func_combo = ttk.Combobox(
            dialog, textvariable=func_var, values=["None"] + list(ACTION_MAP.keys())[1:], state="readonly"
        )
        func_combo.pack(fill="x", padx=14, pady=(0, 16))
        ttk.Label(dialog, text="Gesture:").pack(anchor="w", padx=14, pady=(0, 4))
        ttk.Combobox(
            dialog, textvariable=gesture_var, values=list(GESTURE_TYPES), state="readonly"
        ).pack(fill="x", padx=14, pady=(0, 10))

        send_check = ttk.Checkbutton(
            key_action_row, text="Send when executed?", variable=send_when_executed_var
        )

        ttk.Label(dialog, text="Key name:").pack(anchor="w", padx=14, pady=(0, 4))
        ttk.Entry(dialog, textvariable=name_var).pack(fill="x", padx=14)
        ttk.Label(dialog, text="Value:").pack(anchor="w", padx=14, pady=(10, 4))
        value_entry = ttk.Entry(dialog, textvariable=value_var)
        value_entry.pack(fill="x", padx=14)
        browse_row = ttk.Frame(dialog)
        browse_row.pack(fill="x", padx=14, pady=(6, 0))
        shortcut_button = ttk.Button(
            browse_row,
            text="Record shortcut",
            command=lambda: self._start_shortcut_recording(value_var, shortcut_button),
        )
        browse_button = ttk.Button(browse_row, text="Browse", command=lambda: browse())
        browse_button.pack(side="left")

        def update_shortcut_controls(_event=None):
            is_text = func_var.get() == "Type Text"
            value_entry.state(["!disabled"] if is_text else ["disabled"])
            if func_var.get() == "Keyboard Shortcut":
                shortcut_button.pack(side="left", padx=(8, 0))
                shortcut_button.state(["!disabled"])
            else:
                shortcut_button.pack_forget()
            if is_text:
                send_check.pack(side="left", padx=(8, 0))
            else:
                send_check.pack_forget()
            browse_button.state(
                ["!disabled"] if func_var.get() in BROWSE_ACTION_TYPES else ["disabled"]
            )

        func_combo.bind("<<ComboboxSelected>>", update_shortcut_controls)
        update_shortcut_controls()
        hold_row = ttk.Frame(dialog)
        ttk.Label(hold_row, text="Hold for (ms):").pack(side="left")
        ttk.Entry(hold_row, textvariable=delay_var, width=10).pack(
            side="left", padx=(8, 0)
        )

        def update_action_controls(_event=None):
            if gesture_var.get() == "Hold":
                hold_row.pack(fill="x", padx=14, pady=(8, 0))
            else:
                hold_row.pack_forget()

        func_combo.bind("<<ComboboxSelected>>", update_action_controls, add="+")
        gesture_var.trace_add("write", lambda *_: update_action_controls())
        update_action_controls()

        def browse():
            if func_var.get() == "Open Folder":
                selected = filedialog.askdirectory()
            else:
                selected = filedialog.askopenfilename(
                    filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
                )
            if selected:
                value_var.set(selected)

        def on_key(event):
            if not getattr(self, "_assigning", False):
                return
            if event.name.lower() in {"esc", "escape"}:
                self._stop_assign()
                dialog.destroy()
                return
            key_id = self._normalize_key(event.name)
            if key_id:
                key_var.set(key_id)
                key_label.config(
                    text=f"Detected: {self._display_event_key({'name': event.name})}",
                    foreground="#00aa00",
                )

        def save():
            if not key_var.get():
                messagebox.showwarning(APP_NAME, "Please detect a key first")
                return
            preset = self.presets.get_current()
            code = ACTION_MAP.get(func_var.get(), "none")
            try:
                delay_ms = max(0, int(delay_var.get() or 0))
            except ValueError:
                messagebox.showwarning(APP_NAME, "Delay must be a whole number in milliseconds")
                return
            new_action = {
                "type": code,
                "value": value_var.get(),
                "name": name_var.get().strip(),
                "toggle": toggle_var.get(),
                "double_click": double_click_var.get(),
                "delay_ms": delay_ms,
                "toggle_interval_ms": max(1, int(toggle_interval_var.get() or 1000)),
                "send_when_executed": send_when_executed_var.get(),
            }
            key_entry = preset["keys"].get(key_var.get(), {})
            actions = self._get_action_store(key_entry)
            action_id = str(uuid.uuid4())
            new_action["id"] = action_id
            new_action["gesture"] = GESTURE_TYPES[gesture_var.get()]
            actions[action_id] = new_action
            preset["keys"][key_var.get()] = {"actions": actions}
            self.presets.save()
            self._stop_assign()
            self._refresh_keys()
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=14, pady=8)
        ttk.Button(button_frame, text="Save", command=save).pack(side="left", padx=(0, 4))
        ttk.Button(button_frame, text="Cancel", command=lambda: [self._stop_assign(), dialog.destroy()]).pack(side="left")

        self._assigning = False

        def on_close():
            self._stop_assign()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def _edit_key(self, key_id, gesture="quick_press"):
        """Edit key action"""
        dialog = Toplevel(self.root)
        dialog.title(f"Edit - {key_id}")
        dialog.geometry("460x560")
        dialog.minsize(460, 560)
        dialog.transient(self.root)
        dialog.grab_set()

        preset = self.presets.get_current()
        key_entry = preset.get("keys", {}).get(key_id, {"type": "none", "value": ""})
        action = self._get_gesture_action(key_entry, gesture) or {"type": "none", "value": ""}

        action_type = action.get("type", "none")
        action_label = self._get_action_label(action_type)

        action_var = StringVar(value=action_label)
        value_var = StringVar(value=action.get("value", ""))
        name_var = StringVar(value=action.get("name", ""))
        selected_key_var = StringVar(value=key_id)
        toggle_var = BooleanVar(value=bool(action.get("toggle", False)))
        double_click_var = BooleanVar(value=bool(action.get("double_click", False)))
        delay_var = StringVar(value=str(action.get("delay_ms", 0)))
        toggle_interval_var = StringVar(value=str(action.get("toggle_interval_ms", 1000)))
        send_when_executed_var = BooleanVar(value=action.get("send_when_executed", True))
        gesture_label = next(
            (label for label, value in GESTURE_TYPES.items() if value == gesture),
            "Quick press",
        )
        gesture_var = StringVar(value=gesture_label)
        gesture_drafts = {}
        current_gesture = "quick_press"

        key_capture_label = ttk.Label(dialog, text=self._display_key_id(key_id), foreground="#666")
        key_capture_label.pack(anchor="w", padx=14, pady=(14, 4))
        key_change_row = ttk.Frame(dialog)
        key_change_row.pack(fill="x", padx=14)
        ttk.Button(
            key_change_row,
            text="Change key",
            command=lambda: self._begin_key_capture(selected_key_var, key_capture_label),
        ).pack(side="left")

        send_check = ttk.Checkbutton(
            key_change_row, text="Send when executed?", variable=send_when_executed_var
        )

        ttk.Label(dialog, text="Action:", font=("Arial", 10)).pack(anchor="w", padx=14, pady=(12, 4))
        action_combo = ttk.Combobox(
            dialog, textvariable=action_var, values=ACTION_TYPES, state="readonly", width=35
        )
        action_combo.pack(fill="x", padx=14)
        ttk.Label(dialog, text="Gesture:").pack(anchor="w", padx=14, pady=(8, 4))
        gesture_combo = ttk.Combobox(
            dialog, textvariable=gesture_var, values=list(GESTURE_TYPES), state="readonly"
        )
        gesture_combo.pack(fill="x", padx=14)

        ttk.Label(dialog, text="Key name:", font=("Arial", 10)).pack(anchor="w", padx=14, pady=(10, 4))
        ttk.Entry(dialog, textvariable=name_var).pack(fill="x", padx=14)
        ttk.Label(dialog, text="Value:", font=("Arial", 10)).pack(anchor="w", padx=14, pady=(10, 4))
        value_entry = ttk.Entry(dialog, textvariable=value_var)
        value_entry.pack(fill="x", padx=14)

        browse_row = ttk.Frame(dialog)
        browse_row.pack(fill="x", padx=14, pady=(8, 4))

        shortcut_button = ttk.Button(
            browse_row,
            text="Record shortcut",
            command=lambda: self._start_shortcut_recording(value_var, shortcut_button),
        )
        browse_button = ttk.Button(browse_row, text="Browse", command=lambda: browse())
        browse_button.pack(side="left")

        def load_gesture(_event=None):
            nonlocal current_gesture
            gesture_drafts[current_gesture] = {
                "type": ACTION_MAP.get(action_var.get(), "none"),
                "value": value_var.get(),
                "toggle": toggle_var.get(),
                "double_click": double_click_var.get(),
                "delay_ms": delay_var.get(),
                "send_when_executed": send_when_executed_var.get(),
            }
            selected_gesture = GESTURE_TYPES[gesture_var.get()]
            current_gesture = selected_gesture
            selected_action = self._get_gesture_action(
                preset.get("keys", {}).get(key_id, key_entry),
                selected_gesture,
            )
            selected_action = gesture_drafts.get(selected_gesture, selected_action) or {
                "type": "none", "value": ""
            }
            action_var.set(self._get_action_label(selected_action.get("type", "none")))
            value_var.set(selected_action.get("value", ""))
            delay_var.set(str(selected_action.get("delay_ms", 0)))
            send_when_executed_var.set(selected_action.get("send_when_executed", True))
            update_shortcut_controls()
            update_action_controls()

        def update_shortcut_controls(_event=None):
            is_text = action_var.get() == "Type Text"
            is_shortcut = action_var.get() == "Keyboard Shortcut"
            value_entry.state(["!disabled"] if is_text else ["disabled"])
            if is_shortcut:
                shortcut_button.pack(side="left", padx=(8, 0))
                shortcut_button.state(["!disabled"])
            else:
                shortcut_button.pack_forget()
            if is_text:
                send_check.pack(side="left", padx=(8, 0))
            else:
                send_check.pack_forget()
            browse_button.state(
                ["!disabled"] if action_var.get() in BROWSE_ACTION_TYPES else ["disabled"]
            )

        action_combo.bind("<<ComboboxSelected>>", update_shortcut_controls)
        gesture_combo.bind("<<ComboboxSelected>>", load_gesture)

        hold_row = ttk.Frame(dialog)
        ttk.Label(hold_row, text="Hold for (ms):").pack(side="left")
        ttk.Entry(hold_row, textvariable=delay_var, width=10).pack(
            side="left", padx=(8, 0)
        )

        def update_action_controls(_event=None):
            if gesture_var.get() == "Hold":
                hold_row.pack(fill="x", padx=14, pady=(8, 0))
            else:
                hold_row.pack_forget()

        action_combo.bind("<<ComboboxSelected>>", update_action_controls, add="+")
        toggle_var.trace_add("write", lambda *_: update_action_controls())
        gesture_var.trace_add("write", lambda *_: update_action_controls())
        def browse():
            if action_var.get() == "Open Folder":
                f = filedialog.askdirectory()
            else:
                f = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
            if f:
                value_var.set(f)

        update_shortcut_controls()
        update_action_controls()

        def save():
            code = ACTION_MAP.get(action_var.get(), "none")
            try:
                delay_ms = max(0, int(delay_var.get() or 0))
            except ValueError:
                messagebox.showwarning(APP_NAME, "Delay must be a whole number in milliseconds")
                return
            updated_action = {
                "type": code,
                "value": value_var.get(),
                "name": name_var.get().strip(),
                "toggle": toggle_var.get(),
                "double_click": double_click_var.get(),
                "delay_ms": delay_ms,
                "toggle_interval_ms": max(1, int(toggle_interval_var.get() or 1000)),
                "send_when_executed": send_when_executed_var.get(),
            }
            new_key_id = selected_key_var.get().strip()
            if not new_key_id:
                messagebox.showwarning(APP_NAME, "Press a key before saving")
                return
            if new_key_id != key_id:
                if new_key_id in preset["keys"]:
                    messagebox.showwarning(APP_NAME, "That key is already assigned in this preset")
                    return
                preset["keys"].pop(key_id, None)
                self.toggle_states.pop(key_id, None)
                self.last_press_times.pop(key_id, None)
            existing_entry = preset["keys"].get(new_key_id, {})
            actions = self._get_action_store(existing_entry)
            selected_gesture = GESTURE_TYPES[gesture_var.get()]
            matching_action = next(
                (item for item in actions.values() if item.get("gesture") == selected_gesture),
                None,
            )
            action_id = str(matching_action.get("id") if matching_action else uuid.uuid4())
            updated_action["id"] = action_id
            updated_action["gesture"] = selected_gesture
            actions[action_id] = updated_action
            preset["keys"][new_key_id] = {"actions": actions}
            self.presets.save()
            self._stop_assign()
            self._stop_shortcut_recording()
            self._refresh_keys()
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=14, pady=8)
        ttk.Button(button_frame, text="Save", command=save).pack(side="left", padx=(0, 4))
        ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: (self._stop_assign(), self._stop_shortcut_recording(), dialog.destroy()),
        ).pack(side="left")

        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: (self._stop_assign(), self._stop_shortcut_recording(), dialog.destroy()),
        )

    def _start_shortcut_recording(self, value_var, button):
        """Capture a key combination such as alt+left."""
        self._stop_shortcut_recording()
        pressed = []
        captured = []
        button.configure(text="Press shortcut...")

        def on_event(event):
            name = self._normalize_shortcut_key(event.name)
            if not name:
                return
            if event.event_type == "down" and name not in pressed:
                pressed.append(name)
                if name not in captured:
                    captured.append(name)
            elif event.event_type == "up" and name in pressed:
                pressed.remove(name)
                if not pressed and captured:
                    shortcut = keyboard.get_hotkey_name(captured).replace(" + ", "+")
                    self.root.after(0, lambda: value_var.set(shortcut))
                    self._stop_shortcut_recording()
                    self.root.after(0, lambda: button.configure(text="Record shortcut"))

        self.shortcut_recording_callback = keyboard.hook(on_event)

    def _stop_shortcut_recording(self):
        callback = getattr(self, "shortcut_recording_callback", None)
        if callback:
            keyboard.unhook(callback)
            self.shortcut_recording_callback = None

    def _begin_key_capture(self, key_var, key_label, button=None):
        """Capture a physical key for a new or existing assignment."""
        self._stop_assign()
        self._assignment_generation += 1
        self._assigning = True
        self._assignment_key_var = key_var
        self._assignment_key_label = key_label
        if button is not None:
            button.focus_set()
            button.configure(text="Press a key...")

        if self.native_helper.exists():
            key_label.config(text="Press a key...", foreground="#0066cc")
            return

        def on_key(event):
            if not self._assigning:
                return
            key_id = self._normalize_key(event.name)
            if key_id:
                key_var.set(key_id)
                key_label.config(
                    text=f"Detected: {self._display_event_key({'name': event.name})}",
                    foreground="#00aa00",
                )
                self._stop_assign()
                if button is not None:
                    button.configure(text="Assign key")

        self.recording_callback = keyboard.on_press(on_key)

    def _delete_key(self, key_id, action_id=None):
        """Delete key"""
        if messagebox.askyesno(APP_NAME, f"Delete '{key_id}'?" if action_id is None else "Delete this function?"):
            preset = self.presets.get_current()
            if key_id in preset.get("keys", {}):
                if action_id is not None:
                    action_store = self._get_action_store(preset["keys"][key_id])
                    action_store.pop(str(action_id), None)
                    if action_store:
                        preset["keys"][key_id] = {"actions": action_store}
                    else:
                        del preset["keys"][key_id]
                else:
                    del preset["keys"][key_id]
                self._cancel_toggle(key_id)
                self.toggle_states.pop(key_id, None)
                self.last_press_times.pop(key_id, None)
                self.presets.save()
                self._refresh_keys()

    def _set_action(self, key_id, action_label, gesture="quick_press"):
        """Set action for key"""
        code = ACTION_MAP.get(action_label, "none")
        preset = self.presets.get_current()
        action = preset["keys"].get(key_id, {})
        if isinstance(action.get("actions"), dict) or isinstance(action.get("gestures"), dict):
            action_store = self._get_action_store(action)
            selected_id = next(
                (action_id for action_id, item in action_store.items() if item.get("gesture") == gesture),
                str(uuid.uuid4()),
            )
            selected_action = dict(action_store.get(selected_id, {}))
            selected_action.update({"id": selected_id, "gesture": gesture, "type": code})
            selected_action.setdefault("value", "")
            action_store[selected_id] = selected_action
            action["actions"] = action_store
            action.pop("gestures", None)
            self.presets.save()
            return
        action["type"] = code
        action.setdefault("value", "")
        preset["keys"][key_id] = action
        self.presets.save()

    def _display_action_name(self, action):
        """Return the configured name from the first available gesture."""
        for gesture in ("quick_press", "hold", "double_click"):
            gesture_action = self._get_gesture_action(action, gesture)
            if gesture_action and gesture_action.get("name"):
                return gesture_action["name"]
        return ""

    def _switch_preset(self):
        """Switch preset"""
        name = self.preset_var.get()
        self._clear_held_keys()
        for key_id in list(getattr(self, "toggle_jobs", {})):
            self._cancel_toggle(key_id)
        self.presets.switch(name)
        self.toggle_states.clear()
        self.last_press_times.clear()
        self._refresh_keys()

    def _listen_keys(self):
        """Listen for key presses"""

        if self.native_helper.exists():
            self._start_native_listener()
            return

        def handler(event):
            if not self.should_process_keyboard_event(event):
                return
            if self.device_test_active:
                self.device_test_status_var.set(
                    f"Keyboard {getattr(event, 'device', 'unknown')} : {self._normalize_key(event.name)}"
                )
                return
            key_id = self._normalize_key(event.name)
            preset = self.presets.get_current()
            action = preset.get("keys", {}).get(key_id)
            if action and event.event_type == "down":
                self._handle_key_event(key_id, action, True)
            elif event.event_type == "up":
                self._handle_key_event(key_id, None, False)

        threading.Thread(target=lambda: keyboard.hook(handler, suppress=True), daemon=True).start()

    def _refresh_keyboard_devices(self):
        """Load physical keyboards from the Raw Input helper."""
        if not self.native_helper.exists():
            self.keyboard_device_combo["values"] = ["All keyboards (native helper unavailable)"]
            self.keyboard_device_var.set("All keyboards (native helper unavailable)")
            self.keyboard_full_id_var.set("Native helper unavailable")
            return

        try:
            result = subprocess.run(
                [str(self.native_helper), "--list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            result = None

        devices = []
        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                if "handle=" not in line:
                    continue
                handle = line.split("handle=", 1)[1].split(" name=", 1)[0].strip()
                name = line.split(" name=", 1)[1].strip() if " name=" in line else handle
                devices.append((handle, name))

        self.available_keyboard_devices = devices
        labels = ["All keyboards"] + [self._keyboard_label(handle, name) for handle, name in devices]
        self.keyboard_device_combo["values"] = labels
        current = next(
            (self._keyboard_label(handle, name) for handle, name in devices if handle == self.keyboard_device_id),
            None,
        )
        self.keyboard_device_var.set(current or "All keyboards")
        self.keyboard_full_id_var.set(self.keyboard_device_id or "No keyboard selected")

    def _keyboard_label(self, handle, system_name):
        custom_name = self.presets.keyboard_names.get(handle, system_name)
        return f"Keyboard {handle[:5]} : {custom_name}"

    def _rename_keyboard(self):
        handle = self.keyboard_device_id
        if not handle:
            messagebox.showwarning(APP_NAME, "Select a keyboard first")
            return
        current = next((name for item_handle, name in self.available_keyboard_devices if item_handle == handle), "")
        name = simpledialog.askstring(
            APP_NAME,
            "Keyboard name:",
            initialvalue=self.presets.keyboard_names.get(handle, current),
            parent=self.root,
        )
        if name and name.strip():
            self.presets.keyboard_names[handle] = name.strip()
            self.presets.save()
            self._refresh_keyboard_devices()

    def _select_keyboard_device(self, _event=None):
        """Set the selected physical keyboard used by the native listener."""
        selected = self.keyboard_device_var.get()
        self.keyboard_device_id = next(
            (
                handle
                for handle, name in self.available_keyboard_devices
                if self._keyboard_label(handle, name) == selected
            ),
            "",
        )
        self.keyboard_full_id_var.set(self.keyboard_device_id or "No keyboard selected")

    def _toggle_keyboard_test(self):
        self.device_test_active = not self.device_test_active
        self.device_test_status_var.set(
            "Press a key on the keyboard to identify it..." if self.device_test_active else ""
        )
        self.device_test_button.configure(
            text="Stop keyboard test" if self.device_test_active else "Test keyboard"
        )

    def _show_keyboard_test_event(self, event):
        handle = str(event.get("handle") or event.get("device") or "unknown")
        key = self._normalize_key(event.get("name"))
        self.device_test_status_var.set(f"Keyboard {handle[:5]} : {handle} : {key}")

    def _start_native_listener(self):
        """Read Raw Input events from the helper."""
        try:
            self.native_process = subprocess.Popen(
                [str(self.native_helper), "--listen"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as error:
            print(f"Unable to start keyboard filter: {error}")
            self.native_process = None
            return

        def read_events():
            if not self.native_process or not self.native_process.stdout:
                return
            for line in self.native_process.stdout:
                event = self._parse_native_event_line(line)
                if not event:
                    continue
                if not self._native_event_matches_selected_device(event):
                    continue
                if not event.get("pressed"):
                    self.root.after(0, lambda item=event: self._handle_key_event(
                        self._event_key_id(item), None, False
                    ))
                    continue
                if getattr(self, "_assigning", False):
                    generation = self._assignment_generation
                    self.root.after(
                        0,
                        lambda item=event, token=generation: self._capture_native_key(item, token),
                    )
                    continue
                if self.device_test_active:
                    self.root.after(0, lambda item=event: self._show_keyboard_test_event(item))
                    continue
                key_id = self._normalize_key(event.get("name"))
                event_id = self._event_key_id(event)
                action = self.presets.get_current().get("keys", {}).get(
                    event_id,
                    self.presets.get_current().get("keys", {}).get(key_id),
                )
                if action:
                    self.root.after(
                        0,
                        lambda item_key=event_id, item=action: self._handle_key_event(
                            item_key, item, True
                        ),
                    )

        self.native_reader = threading.Thread(target=read_events, daemon=True)
        self.native_reader.start()

    def _stop_native_listener(self):
        """Stop the Raw Input helper when the application exits."""
        self._clear_held_keys()
        if self.native_process:
            self.native_process.terminate()
            self.native_process = None

    def _handle_key_event(self, key_id, action, pressed):
        """Track a physical key cycle and dispatch its configured gesture."""
        if not pressed:
            state = self.held_keys.pop(key_id, None)
            if state and state.get("job") is not None:
                try:
                    self.root.after_cancel(state["job"])
                except (AttributeError, tk.TclError):
                    pass
            if state and state.get("activated"):
                deferred_action = state.get("deferred_action")
                if deferred_action:
                    self._execute_action(deferred_action)
                return
            if state:
                self._register_tap(key_id, state.get("entry"))
            return
        if key_id in self.held_keys:
            return

        state = {"job": None, "activated": False, "entry": action}
        self.held_keys[key_id] = state
        hold_action = self._get_gesture_action(action, "hold")
        if hold_action:
            try:
                hold_ms = max(1, int(hold_action.get("delay_ms", 1000) or 1000))
            except (TypeError, ValueError):
                hold_ms = 1000
            state["job"] = self.root.after(
                hold_ms, lambda: self._activate_held_key(key_id, hold_action, state)
            )

    def _activate_held_key(self, key_id, action, state):
        """Activate a key after it remains pressed for the required time."""
        if self.held_keys.get(key_id) is not state:
            return
        state["job"] = None
        state["activated"] = True
        if action.get("type") == "write_text":
            state["deferred_action"] = action
            return
        self._execute_action(action)

    def _register_tap(self, key_id, key_entry):
        """Delay a single tap long enough to detect a second tap."""
        if not hasattr(self, "pending_taps"):
            self.pending_taps = {}
        pending = self.pending_taps.get(key_id)
        if pending:
            self.root.after_cancel(pending["job"])
            self.pending_taps.pop(key_id, None)
            double_action = self._get_gesture_action(key_entry, "double_click")
            if double_action:
                self._execute_action(double_action)
                return

        quick_action = self._get_gesture_action(key_entry, "quick_press")
        if not quick_action:
            return
        pending = {"job": None}
        pending["job"] = self.root.after(
            int(DOUBLE_CLICK_INTERVAL * 1000),
            lambda: self._execute_pending_tap(key_id, quick_action, pending),
        )
        self.pending_taps[key_id] = pending

    def _execute_pending_tap(self, key_id, action, pending):
        """Execute a tap after the double-click detection window expires."""
        if self.pending_taps.get(key_id) is not pending:
            return
        self.pending_taps.pop(key_id, None)
        self._execute_action(action)

    def _get_gesture_action(self, key_entry, gesture):
        """Return a gesture action, including migration for legacy assignments."""
        if not isinstance(key_entry, dict):
            return None
        actions = key_entry.get("actions") if isinstance(key_entry, dict) else None
        if isinstance(actions, dict):
            for action in actions.values():
                if action.get("gesture") == gesture and action.get("type") != "none":
                    return action
        gestures = key_entry.get("gestures")
        if isinstance(gestures, dict):
            action = gestures.get(gesture)
            return action if isinstance(action, dict) and action.get("type") != "none" else None
        if gesture == "quick_press" and key_entry.get("type", "none") != "none":
            return key_entry
        return None

    def _get_action_store(self, key_entry):
        """Return independent action records, migrating older key formats."""
        if isinstance(key_entry, dict) and isinstance(key_entry.get("actions"), dict):
            return {str(action_id): dict(action) for action_id, action in key_entry["actions"].items()}

        store = {}
        if isinstance(key_entry, dict) and isinstance(key_entry.get("gestures"), dict):
            for gesture, action in key_entry["gestures"].items():
                if isinstance(action, dict):
                    action_copy = dict(action)
                    action_copy["gesture"] = gesture
                    action_id = str(action_copy.get("id") or uuid.uuid4())
                    action_copy["id"] = action_id
                    store[action_id] = action_copy
        elif isinstance(key_entry, dict) and key_entry.get("type", "none") != "none":
            action_copy = dict(key_entry)
            action_copy["gesture"] = "quick_press"
            action_id = str(action_copy.get("id") or uuid.uuid4())
            action_copy["id"] = action_id
            store[action_id] = action_copy
        return store

    def _clear_held_keys(self):
        """Cancel pending hold timers and forget pressed keys."""
        for state in self.held_keys.values():
            if state.get("job") is not None:
                try:
                    self.root.after_cancel(state["job"])
                except (AttributeError, tk.TclError):
                    pass
        self.held_keys.clear()
        for pending in self.pending_taps.values():
            try:
                self.root.after_cancel(pending["job"])
            except (AttributeError, tk.TclError):
                pass
        self.pending_taps.clear()

    def _process_key_press(self, key_id, action):
        """Apply activation options before executing a configured action."""
        if not self.enabled:
            return

        if action.get("double_click", False):
            previous = self.last_press_times.get(key_id, 0)
            now = time.monotonic()
            if now - previous > DOUBLE_CLICK_INTERVAL:
                self.last_press_times[key_id] = now
                return
            self.last_press_times.pop(key_id, None)

        if action.get("toggle", False):
            self.toggle_states[key_id] = not self.toggle_states.get(key_id, False)
            if not self.toggle_states[key_id]:
                self._cancel_toggle(key_id)
                return
            self._repeat_toggle(key_id, action)
            return

        self._execute_with_delay(action)

    def _execute_with_delay(self, action):
        """Execute an action after its configured hold time."""
        try:
            delay_ms = max(0, int(action.get("delay_ms", 0) or 0))
        except (TypeError, ValueError):
            delay_ms = 0
        self._execute_action(action)

    def _repeat_toggle(self, key_id, action):
        """Execute a toggled action and schedule its next activation."""
        if not self.toggle_states.get(key_id, False):
            return
        self._execute_with_delay(action)
        try:
            interval_ms = max(1, int(action.get("toggle_interval_ms", 1000) or 1000))
        except (TypeError, ValueError):
            interval_ms = 1000
        self.toggle_jobs[key_id] = self.root.after(
            interval_ms, lambda: self._repeat_toggle(key_id, action)
        )

    def _cancel_toggle(self, key_id):
        """Cancel a pending repeated toggle activation."""
        job = getattr(self, "toggle_jobs", {}).pop(key_id, None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except (AttributeError, tk.TclError):
                pass

    def _execute_action(self, action):
        """Execute action"""
        action_type = action.get("type", "none")
        value = action.get("value", "")

        try:
            if action_type == "none":
                pass
            elif action_type == "close_window":
                self.root.destroy()
            elif action_type == "open_site":
                website = value.strip()
                if website and not website.lower().startswith(("http://", "https://")):
                    website = f"https://{website}"
                if website:
                    webbrowser.open(website)
            elif action_type in {"open_program", "open_folder"}:
                if value:
                    os.startfile(value)
            elif action_type == "hotkey":
                if value:
                    keyboard.press_and_release(value)
            elif action_type == "play_pause":
                keyboard.send("play/pause")
            elif action_type == "prev_track":
                keyboard.send("media_prev")
            elif action_type == "next_track":
                keyboard.send("media_next")
            elif action_type == "volume_up":
                keyboard.send("volume_up")
            elif action_type == "volume_down":
                keyboard.send("volume_down")
            elif action_type == "mute":
                keyboard.send("volume_mute")
            elif action_type == "write_text":
                if value:
                    keyboard.write(value)
                    if action.get("send_when_executed", True):
                        keyboard.press_and_release("enter")
            elif action_type == "screenshot":
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                desktop = Path.home() / "Desktop"
                desktop.mkdir(exist_ok=True)
                screenshot.save(desktop / f"screenshot_{int(time.time())}.png")
        except Exception as e:
            print(f"Error executing action: {e}")

    def _toggle_enabled(self):
        """Toggle enabled state"""
        self.enabled = not self.enabled
        self.disable_streamdeck_var.set(not self.enabled)
        self._toggle_status_display()
        self._save_preferences()

    def normalize_device_id(self, value):
        """Normalize device identifiers before comparing them."""
        return str(value or "").strip().lower()

    def can_test_selected_keyboard(self):
        """Return whether a concrete keyboard has been selected."""
        return bool(self.normalize_device_id(getattr(self, "keyboard_device_id", "")))

    def _get_window_proc_pointer(self, callback):
        """Convert a ctypes callback to a stable native pointer value."""
        pointer = ctypes.cast(callback, ctypes.c_void_p).value
        if pointer is None:
            raise ValueError("Unable to obtain window procedure pointer")
        return int(pointer)

    def should_process_keyboard_event(self, event):
        """Return whether an event belongs to the selected keyboard."""
        if not getattr(self, "enabled", True):
            return False

        if isinstance(event, dict):
            event_device = event.get("device") or event.get("handle")
        else:
            event_device = getattr(event, "device", None)

        selected_device = self.normalize_device_id(getattr(self, "keyboard_device_id", ""))
        if not selected_device:
            return True
        if event_device is None:
            return getattr(self, "device_test_active", False)

        current_device = self.normalize_device_id(event_device)
        return (
            current_device == selected_device
            or selected_device in current_device
            or current_device in selected_device
        )

    def _parse_native_event_line(self, line):
        """Parse and normalize one event emitted by the native helper."""
        if not line or not str(line).strip():
            return None
        try:
            payload = json.loads(line)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None

        payload["device"] = str(payload.get("device") or payload.get("name") or "")
        payload["handle"] = str(payload.get("handle") or "")
        payload["name"] = str(payload.get("name") or payload.get("key") or "")
        payload["pressed"] = bool(payload.get("pressed", True))
        try:
            payload["vk"] = int(payload.get("vk", 0))
        except (TypeError, ValueError):
            payload["vk"] = 0
        return payload

    def _native_event_matches_selected_device(self, event):
        """Match native events using either the handle or display name."""
        selected_device = self.normalize_device_id(getattr(self, "keyboard_device_id", ""))
        if not selected_device or not isinstance(event, dict):
            return True

        event_handle = self.normalize_device_id(event.get("handle"))
        event_device = self.normalize_device_id(event.get("device"))
        return any(
            selected_device == candidate
            or selected_device in candidate
            or candidate in selected_device
            for candidate in (event_handle, event_device)
            if candidate
        )

    def _setup_hotkeys(self):
        """Setup global hotkeys"""
        keyboard.add_hotkey("ctrl+alt+f12", self._toggle_enabled)

    def _create_tray(self):
        """Create tray icon"""
        icon_path = resource_path("icon.ico")
        try:
            image = Image.open(icon_path).convert("RGBA")
        except (OSError, ValueError):
            image = Image.new("RGBA", (64, 64), (30, 30, 40, 255))
        self.tray = pystray.Icon(APP_NAME, image, APP_NAME, menu=pystray.Menu(
            pystray.MenuItem("Open", lambda: self.root.deiconify()),
            pystray.MenuItem("Exit", self._exit_app),
        ))
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _exit_app(self):
        """Close the app and its native input helper."""
        self._stop_shortcut_recording()
        self._stop_native_listener()
        self.root.after(0, self.root.destroy)

    def _stop_assign(self):
        """Stop key assignment"""
        self._assigning = False
        self._assignment_generation = getattr(self, "_assignment_generation", 0) + 1
        self._assignment_key_var = None
        self._assignment_key_label = None
        if self.recording_callback:
            keyboard.unhook(self.recording_callback)
            self.recording_callback = None

    def _normalize_key(self, name):
        """Normalize key name"""
        normalized = (name or "").lower().strip()
        return normalized

    def _normalize_shortcut_key(self, name):
        """Normalize names emitted while recording a shortcut."""
        aliases = {
            "left alt": "alt",
            "right alt": "alt gr",
            "left ctrl": "ctrl",
            "right ctrl": "ctrl",
            "left shift": "shift",
            "right shift": "shift",
            "left windows": "win",
            "right windows": "win",
        }
        return aliases.get((name or "").lower().strip(), (name or "").lower().strip())

    def _event_key_id(self, event):
        """Build a stable key identifier that includes the physical device."""
        handle = self.normalize_device_id(event.get("handle") or event.get("device"))
        key = self._normalize_key(event.get("name"))
        return f"{handle}::{key}" if handle else key

    def _display_key_id(self, key_id, custom_name=""):
        """Format internal device/key identifiers for the key list."""
        if "::" not in key_id:
            return f"key {key_id} : {custom_name}" if custom_name else f"key {key_id}"
        device, key = key_id.split("::", 1)
        label = f"key {key}"
        return f"{label} : {custom_name}" if custom_name else f"{label} ({device[:5]})"

    def _display_event_key(self, event):
        """Format a captured event with its device and key information."""
        handle = self.normalize_device_id(event.get("handle"))
        key = self._normalize_key(event.get("name"))
        system_name = next(
            (name for item_handle, name in self.available_keyboard_devices if item_handle == handle),
            handle or "Unknown keyboard",
        )
        device_name = self.presets.keyboard_names.get(handle, system_name)
        key_number = event.get("vk") or key
        return f"{device_name} : key {key_number} : {key}"

    def _capture_native_key(self, event, generation=None):
        """Show the complete physical device and key during assignment."""
        if not getattr(self, "_assigning", False) or (
            generation is not None and generation != self._assignment_generation
        ):
            return
        key_var = self._assignment_key_var
        key_label = self._assignment_key_label
        if key_var is None or key_label is None:
            return
        key_id = self._event_key_id(event)
        try:
            key_var.set(key_id)
            key_label.config(
                text=f"Detected: {self._display_event_key(event)}", foreground="#00aa00"
            )
        except tk.TclError:
            self._stop_assign()
            return
        self._stop_assign()

    def _get_action_label(self, action_type):
        """Get action label from type"""
        for label, code in ACTION_MAP.items():
            if code == action_type:
                return label
        return "None"

    def hide_window(self):
        """Hide window to tray"""
        if self.minimize_on_close_var.get():
            self.root.withdraw()
        else:
            self._stop_shortcut_recording()
            self._stop_native_listener()
            self.root.destroy()


if __name__ == "__main__":
    if not acquire_single_instance():
        raise SystemExit(0)
    root = Tk()
    app = NumpadStreamDeckApp(root)
    root.mainloop()
