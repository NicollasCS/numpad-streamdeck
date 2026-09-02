import ctypes
import json
import os
import platform
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, Toplevel, messagebox
from tkinter import ttk
import tkinter as tk

import keyboard
import pystray
from PIL import Image, ImageGrab

try:
    from ctypes import wintypes
    import ctypes
except ImportError:  # pragma: no cover - only used on Windows
    wintypes = None
    ctypes = None

try:
    import win32api
    import win32con
    import win32gui
except ImportError:  # pragma: no cover - only used on Windows
    win32api = None
    win32con = None
    win32gui = None

APP_NAME = "Numpad Stream Deck"
APPDATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "NumpadStreamDeck"
PRESET_FILE = APPDATA_DIR / "numpad_presets.json"

KEY_LAYOUT = []

ACTION_TYPES = [
    "None",
    "Close Window",
    "Open Website",
    "Launch Application",
    "Open Folder",
    "Keyboard Shortcut",
    "Play/Pause",
    "Previous Track",
    "Next Track",
    "Volume Up",
    "Volume Down",
    "Mute",
    "Show Desktop",
    "Windows + Tab",
    "Alt + Tab",
    "Type Text + Enter",
    "Lock PC",
    "Screenshot",
]

ACTION_MAP = {
    "None": "none",
    "Close Window": "close_window",
    "Open Website": "open_site",
    "Launch Application": "open_program",
    "Open Folder": "open_folder",
    "Keyboard Shortcut": "hotkey",
    "Play/Pause": "play_pause",
    "Previous Track": "prev_track",
    "Next Track": "next_track",
    "Volume Up": "volume_up",
    "Volume Down": "volume_down",
    "Mute": "mute",
    "Show Desktop": "desktop",
    "Windows + Tab": "windows_tab",
    "Alt + Tab": "alt_tab",
    "Type Text + Enter": "write_text",
    "Lock PC": "lock_pc",
    "Screenshot": "screenshot",
}

DEFAULT_PRESET_NAMES = ["Default"]


def ensure_appdata_dir():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)


def safe_text(value):
    return str(value or "")


def flatten_key_layout():
    flattened = []
    for row in KEY_LAYOUT:
        for key in row:
            if key not in flattened:
                flattened.append(key)
    return flattened


def default_empty_preset():
    return {"keys": {}}


def normalize_preset(preset):
    if not isinstance(preset, dict):
        return default_empty_preset()
    keys = preset.get("keys")
    if isinstance(keys, dict):
        normalized = {"keys": {}}
        for key_id, action in keys.items():
            if isinstance(action, dict):
                normalized["keys"][key_id] = {
                    "type": action.get("type", "none"),
                    "value": safe_text(action.get("value", "")),
                }
            else:
                normalized["keys"][key_id] = {"type": "none", "value": ""}
        return normalized
    return default_empty_preset()


def build_default_presets():
    return {"Default": default_empty_preset()}


class NumpadStreamDeckApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x720")
        self.root.configure(bg="#eef3f8")
        self.root.minsize(900, 660)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Pad.TButton", background="#f3f5f7", foreground="#111827", borderwidth=1, relief="flat", padding=18, font=("Segoe UI", 12, "bold"))
        self.style.map("Pad.TButton", background=[("active", "#dfeaf6"), ("pressed", "#d5e3f3")], foreground=[("active", "#0f172a")])
        self.style.configure("PadActive.TButton", background="#dfefff", foreground="#0b5ed7", borderwidth=2, relief="flat", padding=18, font=("Segoe UI", 12, "bold"))
        self.style.map("PadActive.TButton", background=[("active", "#cfe3ff"), ("pressed", "#b9d6ff")], foreground=[("active", "#0a3d8f")])

        self.enabled = True
        self.current_preset_name = "Default"
        self.presets = {}
        self.recording_target = None
        self.recording_callback = None
        self.tray_icon = None
        self.key_buttons = {}
        self.keyboard_device_id = ""
        self.keyboard_device_var = StringVar(value="")
        self.available_keyboard_devices = []
        self.selected_keyboard_handle = None
        self.device_test_active = False
        self.device_test_status_var = StringVar(value="")
        self.device_test_button_var = StringVar(value="")
        self.native_raw_input_helper = Path(__file__).resolve().parent / "cpp" / "raw_input_filter.exe"
        self.native_raw_input_available = self.native_raw_input_helper.exists()
        self.raw_input_enabled = False
        self._raw_input_error = None
        self._raw_input_hook_installed = False
        self._raw_input_devices = []
        self._raw_input_window_proc = None
        self._raw_input_wndproc_original = None
        self._raw_input_message_hwnd = None
        self._raw_input_message_class = None
        self.native_bridge_process = None
        self.native_bridge_reader = None
        self.native_bridge_running = False
        self._setup_windows_raw_input()

        self.header_var = StringVar(value="Numpad Stream Deck")
        self.status_var = StringVar(value="Enabled")
        self.preset_var = StringVar()

        ensure_appdata_dir()
        self.load_presets()
        self.build_ui()
        self.refresh_preset_selector()
        self.update_key_buttons()
        self.update_status_display()
        self.setup_global_hotkeys()
        self.create_tray_icon()

    def build_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(main, padding=(18, 14, 18, 0))
        header.pack(fill="x")
        ttk.Label(header, textvariable=self.header_var, font=("Segoe UI", 20, "bold"), foreground="#0f172a").pack(side="left")
        self.status_label = ttk.Label(header, textvariable=self.status_var, font=("Segoe UI", 10, "bold"), foreground="#16a34a")
        self.status_label.pack(side="right")

        # Tabs
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=(12, 0))

        # Tab 1: Presets
        self.tab_presets = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(self.tab_presets, text="Presets")

        # Preset controls - simplified
        controls = ttk.Frame(self.tab_presets)
        controls.pack(fill="x", pady=(0, 16))

        ttk.Button(controls, text="+", command=self.assign_new_key, width=3).pack(side="left")

        # Keyboard pad
        pad = ttk.Frame(self.tab_presets)
        pad.pack(fill="both", expand=True)

        self.pad_frame = tk.Frame(pad, bg="#eef3f8")
        self.pad_frame.pack(fill="both", expand=True)

        self.key_list_container = ttk.Frame(self.pad_frame)
        self.key_list_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.update_key_buttons()

        # Tab 2: Settings
        self.tab_settings = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(self.tab_settings, text="Settings")
        self.build_settings_tab()

        self.root.bind("<Escape>", self.hide_window)

    def build_settings_tab(self):
        # Status section
        status_frame = ttk.LabelFrame(self.tab_settings, text="Application Status", padding=12)
        status_frame.pack(fill="x", pady=(0, 16))

        status_inner = ttk.Frame(status_frame)
        status_inner.pack(fill="x")
        ttk.Label(status_inner, text="State:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        ttk.Label(status_inner, textvariable=self.status_var, font=("Segoe UI", 10, "bold"), foreground="#16a34a").pack(side="left")

        toggle_frame = ttk.Frame(status_frame)
        toggle_frame.pack(fill="x", pady=(12, 0))
        ttk.Button(toggle_frame, text="Toggle Enabled/Disabled (CTRL+ALT+F12)", command=self.toggle_enabled).pack(side="left")

        keyboard_source_frame = ttk.LabelFrame(self.tab_settings, text="Keyboard source", padding=12)
        keyboard_source_frame.pack(fill="x", pady=(0, 16))

        self.keyboard_device_combo = ttk.Combobox(keyboard_source_frame, textvariable=self.keyboard_device_var, state="readonly", width=40)
        self.keyboard_device_combo.pack(fill="x", pady=(0, 8))

        device_row = ttk.Frame(keyboard_source_frame)
        device_row.pack(fill="x")
        ttk.Button(device_row, text="Refresh devices", command=self.refresh_keyboard_devices).pack(side="left")
        ttk.Button(device_row, text="Apply", command=self.apply_keyboard_device_filter).pack(side="left", padx=(8, 0))
        ttk.Button(device_row, text="Clear", command=self.clear_keyboard_device_filter).pack(side="left", padx=(4, 0))

        self.device_test_button = ttk.Button(keyboard_source_frame, text="Testar dispositivo", command=self.toggle_device_test_mode)
        self.device_test_button.pack(anchor="w", pady=(10, 6))
        self.device_test_button.state(["disabled"]) if not self.can_test_selected_keyboard() else None

        self.device_test_panel = ttk.Frame(keyboard_source_frame, padding=(12, 8), relief="solid", borderwidth=1)
        self.device_test_panel.pack(fill="x")
        self.device_test_status_var.set("Aguardando teste...")
        ttk.Label(self.device_test_panel, textvariable=self.device_test_status_var, font=("Segoe UI", 10, "bold"), foreground="#111827").pack(anchor="w")

        self.device_test_led = ttk.Label(self.device_test_panel, text="●", font=("Segoe UI", 28, "bold"), foreground="#cbd5e1")
        self.device_test_led.pack(anchor="w", pady=(4, 0))

        if self._raw_input_error:
            ttk.Label(
                keyboard_source_frame,
                text=self._raw_input_error,
                foreground="#b91c1c",
                font=("Segoe UI", 9),
                justify="left",
            ).pack(anchor="w", pady=(8, 0))
        else:
            ttk.Label(
                keyboard_source_frame,
                text="Selecione o teclado físico que deve responder aos atalhos. Deixe em branco para aceitar qualquer teclado.",
                foreground="#6b7280",
                font=("Segoe UI", 9),
                justify="left",
            ).pack(anchor="w", pady=(8, 0))

        self.refresh_keyboard_devices()
        if self.raw_input_enabled:
            self.setup_raw_input_listener()
            self.refresh_keyboard_devices()

        # Startup section
        startup_frame = ttk.LabelFrame(self.tab_settings, text="Startup", padding=12)
        startup_frame.pack(fill="x", pady=(0, 16))

        self.startup_var = BooleanVar(value=False)
        ttk.Checkbutton(startup_frame, text="Start with Windows", variable=self.startup_var).pack(anchor="w", pady=4)
        ttk.Label(startup_frame, text="The application will be added to Windows startup list.", foreground="#6b7280", font=("Segoe UI", 9)).pack(anchor="w")

        # Hotkeys section
        hotkeys_frame = ttk.LabelFrame(self.tab_settings, text="Keyboard Shortcuts", padding=12)
        hotkeys_frame.pack(fill="x", pady=(0, 16))

        hotkey_rows = [
            ("Toggle numpad:", "CTRL + ALT + F12"),
            ("Switch to Default preset:", "CTRL + ALT + 1"),
        ]

        for label, key in hotkey_rows:
            row = ttk.Frame(hotkeys_frame)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, font=("Segoe UI", 10)).pack(side="left", padx=(0, 12))
            ttk.Label(row, text=key, font=("Segoe UI", 10, "bold"), foreground="#0b5ed7").pack(side="left")

        # About section
        about_frame = ttk.LabelFrame(self.tab_settings, text="About", padding=12)
        about_frame.pack(fill="x", pady=(0, 0))

        ttk.Label(about_frame, text="Numpad Stream Deck", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(about_frame, text="Version 1.0.0", foreground="#6b7280").pack(anchor="w")
        ttk.Label(about_frame, text="A virtual numeric keypad for custom keyboard shortcuts.", foreground="#6b7280", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

    def get_key_label(self, key_id):
        label_map = {
            "numlock": "NumLock",
            "backspace": "Backspace",
            "del": "Del",
            "enter": "Enter",
            "000": "000",
        }
        return label_map.get(key_id, key_id)

    def load_presets(self):
        if not PRESET_FILE.exists():
            self.presets = build_default_presets()
            self.current_preset_name = "Default"
            self.save_presets()
            return

        try:
            with open(PRESET_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "presets" in data:
                self.presets = data["presets"]
                self.current_preset_name = data.get("current_preset", self.current_preset_name)
            else:
                self.presets = data if isinstance(data, dict) else build_default_presets()
                self.current_preset_name = self.current_preset_name if self.current_preset_name in self.presets else next(iter(self.presets))
        except Exception:
            self.presets = build_default_presets()
            self.current_preset_name = "Default"

        legacy_names = {"Gaming", "Discord", "BeamNG"}
        if any(name in self.presets for name in legacy_names):
            self.presets = {"Default": self.presets.get("Default", default_empty_preset())}
            self.current_preset_name = "Default"

        normalized_presets = {}
        for name, preset in self.presets.items():
            normalized_presets[name] = normalize_preset(preset)
        self.presets = normalized_presets

        if "Default" not in self.presets:
            self.presets["Default"] = default_empty_preset()

        if not self.current_preset_name or self.current_preset_name not in self.presets:
            self.current_preset_name = "Default"

        self.presets = {"Default": self.presets.get("Default", default_empty_preset())}
        self.current_preset_name = "Default"

    def save_presets(self):
        ensure_appdata_dir()
        payload = {
            "current_preset": self.current_preset_name,
            "presets": self.presets,
        }
        with open(PRESET_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    def refresh_preset_selector(self):
        # Simplified - no preset selector anymore
        items = list(self.presets.keys())
        if self.current_preset_name not in items:
            if items:
                self.current_preset_name = items[0]
            else:
                self.current_preset_name = "Default"

    def switch_preset(self, preset_name):
        if not preset_name or preset_name not in self.presets:
            return
        self.current_preset_name = preset_name
        self.save_presets()
        self.update_key_buttons()

    def create_preset(self):
        name = self.prompt_name("New Preset", "Enter preset name:")
        if not name:
            return
        if name in self.presets:
            messagebox.showerror(APP_NAME, "This preset already exists.")
            return
        self.presets[name] = default_empty_preset()
        self.current_preset_name = name
        self.save_presets()
        self.refresh_preset_selector()
        self.update_key_buttons()

    def duplicate_preset(self):
        source = self.current_preset_name
        duplicated = self.prompt_name("Duplicate Preset", f"Name for copy of '{source}':")
        if not duplicated:
            return
        if duplicated in self.presets:
            messagebox.showerror(APP_NAME, "A preset with this name already exists.")
            return
        self.presets[duplicated] = json.loads(json.dumps(self.presets[source]))
        self.current_preset_name = duplicated
        self.save_presets()
        self.refresh_preset_selector()
        self.update_key_buttons()

    def rename_preset(self):
        current = self.current_preset_name
        new_name = self.prompt_name("Rename Preset", "New name:", default=current)
        if not new_name or not new_name.strip():
            return
        if new_name in self.presets and new_name != current:
            messagebox.showerror(APP_NAME, "This name already exists.")
            return
        if new_name == current:
            return
        preset = self.presets.pop(current)
        self.presets[new_name] = preset
        self.current_preset_name = new_name
        self.save_presets()
        self.refresh_preset_selector()
        self.update_key_buttons()

    def delete_preset(self):
        if len(self.presets) <= 1:
            messagebox.showwarning(APP_NAME, "You must keep at least one preset.")
            return
        current = self.current_preset_name
        if messagebox.askyesno(APP_NAME, f"Delete preset '{current}'?"):
            del self.presets[current]
            self.current_preset_name = next(iter(self.presets))
            self.save_presets()
            self.refresh_preset_selector()
            self.update_key_buttons()

    def prompt_name(self, title, prompt, default=""):
        dialog = Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("380x120")
        ttk.Label(dialog, text=prompt).pack(anchor="w", padx=14, pady=(14, 6))
        value = StringVar(value=default)
        entry = ttk.Entry(dialog, textvariable=value, width=28)
        entry.pack(fill="x", padx=14, pady=(0, 12))
        entry.focus_set()

        def accept():
            result = value.get().strip()
            dialog.result = result
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=accept).pack(pady=8)
        dialog.result = ""
        dialog.wait_window(dialog)
        return dialog.result

    def get_current_preset(self):
        preset = self.presets.get(self.current_preset_name, default_empty_preset())
        cleaned = normalize_preset(preset)
        self.presets[self.current_preset_name] = cleaned
        return cleaned

    def apply_action_choice(self, key_id, selected_label):
        preset = self.get_current_preset()
        code = ACTION_MAP.get(selected_label, "none")
        if code == "none":
            preset["keys"][key_id] = {"type": "none", "value": ""}
        else:
            current = preset["keys"].get(key_id, {"type": "none", "value": ""})
            preset["keys"][key_id] = {
                "type": code,
                "value": current.get("value", ""),
            }
        self.save_presets()
        self.update_key_buttons()

    def update_key_buttons(self):
        preset = self.get_current_preset()
        if not hasattr(self, "key_list_container"):
            return

        for widget in list(self.key_list_container.winfo_children()):
            widget.destroy()
        self.key_buttons = {}

        key_ids = self.get_visible_key_ids(preset)
        if not key_ids:
            empty = ttk.Label(
                self.key_list_container,
                text="Nenhuma tecla atribuída ainda",
                foreground="#6b7280",
                font=("Segoe UI", 10),
            )
            empty.pack(anchor="center", pady=30)
            return

        for key_id in key_ids:
            action = preset["keys"].get(key_id, {"type": "none", "value": ""})
            action_type = action.get("type", "none")
            row = ttk.Frame(self.key_list_container, padding=(8, 6))
            row.pack(fill="x", pady=2)

            key_text = key_id if key_id.startswith("key") else self.get_key_label(key_id)
            key_label = ttk.Label(row, text=key_text, font=("Segoe UI", 12, "bold"), width=14)
            key_label.pack(side="left")

            function_var = StringVar(value="None" if action_type == "none" else self.translate_type(action_type))
            combo = ttk.Combobox(
                row,
                textvariable=function_var,
                values=["None"] + list(ACTION_MAP.keys())[1:],
                state="readonly",
                width=28,
            )
            combo.pack(side="left", padx=(20, 8), fill="x", expand=True)
            combo.bind("<<ComboboxSelected>>", lambda event, k=key_id, var=function_var: self.apply_action_choice(k, var.get()))

            edit_button = ttk.Button(row, text="Editar", command=lambda k=key_id: self.edit_key_action(k))
            edit_button.pack(side="right")

            if action_type == "none":
                key_label.configure(foreground="#6b7280")
            else:
                key_label.configure(foreground="#0b5ed7")

            self.key_buttons[key_id] = row

    def get_button_text(self, key_id, action):
        label = self.get_key_label(key_id)
        action_type = action.get("type", "none")
        if action_type == "none":
            return label
        action_label = self.translate_type(action_type)
        if len(action_label) > 12:
            action_label = action_label[:10] + "..."
        return f"{label}\n{action_label}"

    def get_visible_key_ids(self, preset=None):
        source = preset or self.get_current_preset()
        keys = []
        for key_id in sorted(source["keys"].keys()):
            if key_id:
                keys.append(key_id)
        return keys

    def _normalize_assigned_key_id(self, key_name=None, scan_code=None, vk_code=None):
        if scan_code is not None:
            return f"key{int(scan_code)}"
        if vk_code is not None:
            return f"key{int(vk_code)}"
        if key_name is None:
            return ""
        normalized = str(key_name).strip().lower()
        alias_map = {
            "kp0": "key0",
            "kp1": "key1",
            "kp2": "key2",
            "kp3": "key3",
            "kp4": "key4",
            "kp5": "key5",
            "kp6": "key6",
            "kp7": "key7",
            "kp8": "key8",
            "kp9": "key9",
            "num lock": "numlock",
            "numpad divide": "/",
            "numpad multiply": "*",
            "numpad minus": "-",
            "numpad plus": "+",
            "numpad enter": "enter",
            "space": "space",
        }
        if normalized in alias_map:
            return alias_map[normalized]
        return normalized

    def assign_new_key(self):
        dialog = Toplevel(self.root)
        dialog.title("Assign Key")
        dialog.geometry("380x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        detected_key_var = StringVar(value="")
        function_var = StringVar(value="None")
        
        # Key detection section
        ttk.Label(dialog, text="Press a key:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        key_label = ttk.Label(dialog, text="Waiting...", font=("Segoe UI", 11), foreground="#0b5ed7")
        key_label.pack(anchor="w", padx=14, pady=(0, 12))
        
        # Function selection section
        ttk.Label(dialog, text="Function:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(0, 4))
        combo = ttk.Combobox(dialog, textvariable=function_var, values=["None"] + list(ACTION_MAP.keys())[1:], state="readonly")
        combo.pack(fill="x", padx=14, pady=(0, 16))
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=14, pady=(0, 14))
        
        def save_action():
            key_id = detected_key_var.get().strip()
            if not key_id:
                messagebox.showwarning(APP_NAME, "Please detect a key first.")
                return
            
            preset = self.get_current_preset()
            selected_label = function_var.get()
            code = ACTION_MAP.get(selected_label, "none")
            preset["keys"][key_id] = {"type": code, "value": ""}
            self.save_presets()
            self.cancel_key_assignment()
            self.update_key_buttons()
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_action).pack(side="left", padx=(0, 4))
        ttk.Button(button_frame, text="Cancel", command=lambda: [self.cancel_key_assignment(), dialog.destroy()]).pack(side="left")
        
        # Start listening for key press
        self._pending_key_assignment = True
        self._assignment_dialog = dialog
        self._assignment_key_callback = keyboard.on_press(lambda event: self._handle_key_assignment_new(event, detected_key_var, key_label))
        
        # Handle dialog close
        def on_dialog_close():
            self.cancel_key_assignment()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

    def _handle_key_assignment(self, event):
        if not getattr(self, "_pending_key_assignment", False):
            return
        if getattr(event, "name", "").lower() in {"esc", "escape"}:
            self.cancel_key_assignment()
            return

        key_id = self._normalize_assigned_key_id(
            key_name=getattr(event, "name", None),
            scan_code=getattr(event, "scan_code", None),
            vk_code=getattr(event, "vk", None),
        )
        if not key_id:
            return

        preset = self.get_current_preset()
        preset["keys"][key_id] = {"type": "none", "value": ""}
        self.save_presets()
        self.cancel_key_assignment()
        self.update_key_buttons()
        self.edit_key_action(key_id)

    def _handle_key_assignment_new(self, event, detected_key_var, key_label):
        """Handle key detection in the compact assign dialog"""
        if not getattr(self, "_pending_key_assignment", False):
            return
        if getattr(event, "name", "").lower() in {"esc", "escape"}:
            self.cancel_key_assignment()
            if hasattr(self, "_assignment_dialog") and self._assignment_dialog.winfo_exists():
                self._assignment_dialog.destroy()
            return

        key_id = self._normalize_assigned_key_id(
            key_name=getattr(event, "name", None),
            scan_code=getattr(event, "scan_code", None),
            vk_code=getattr(event, "vk", None),
        )
        if not key_id:
            return
        
        # Update the dialog with detected key
        detected_key_var.set(key_id)
        key_label.configure(text=f"Detected: {self.get_key_label(key_id)}", foreground="#16a34a")

    def cancel_key_assignment(self):
        if getattr(self, "_assignment_key_callback", None) is not None:
            keyboard.unhook(self._assignment_key_callback)
            self._assignment_key_callback = None
        self._pending_key_assignment = False

    def translate_type(self, action_type):
        for label, code in ACTION_MAP.items():
            if code == action_type:
                return label
        return "Ação"

    def edit_key_action(self, key_id):
        preset = self.get_current_preset()
        action = preset["keys"].get(key_id, {"type": "none", "value": ""})
        dialog = Toplevel(self.root)
        dialog.title(f"Edit Action - {self.get_key_label(key_id)}")
        dialog.geometry("440x330")
        dialog.transient(self.root)
        dialog.grab_set()

        mode_var = StringVar(value=self.translate_type(action.get("type", "none")))
        value_var = StringVar(value=safe_text(action.get("value", "")))

        ttk.Label(dialog, text="Action:").pack(anchor="w", padx=14, pady=(14, 4))
        combo = ttk.Combobox(dialog, textvariable=mode_var, values=ACTION_TYPES, state="readonly", width=36)
        combo.pack(fill="x", padx=14)

        ttk.Label(dialog, text="Value / Path / Text:").pack(anchor="w", padx=14, pady=(12, 4))
        value_entry = ttk.Entry(dialog, textvariable=value_var, width=40)
        value_entry.pack(fill="x", padx=14)

        help_label = ttk.Label(dialog, text="For shortcuts, use format: ctrl+shift+s", foreground="#9ca3af")
        help_label.pack(anchor="w", padx=14, pady=(8, 10))

        def record_shortcut():
            self.record_shortcut(value_var)

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill="x", padx=14, pady=(0, 8))
        ttk.Button(btn_row, text="Record Shortcut", command=record_shortcut).pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="Delete", command=lambda: self.delete_key_action(key_id, dialog)).pack(side="left")

        def save_action():
            selected_label = mode_var.get()
            code = ACTION_MAP.get(selected_label, "none")
            preset["keys"][key_id] = {"type": code, "value": value_var.get()}
            self.save_presets()
            self.update_key_buttons()
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=14, pady=8)
        ttk.Button(button_frame, text="Save", command=save_action).pack(side="left", padx=(0, 4))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left")

    def record_shortcut(self, value_var):
        self.recording_target = value_var
        self.recording_callback = keyboard.on_press(self._handle_hotkey_record)
        messagebox.showinfo(APP_NAME, "Press the desired key combination.")

    def _handle_hotkey_record(self, event):
        if self.recording_target is None:
            return
        if event.name in {"esc", "enter", "space"}:
            self.cancel_recording()
            return
        # keyboard library delivers single-key names. Build a normalized combo.
        keys = []
        for item in ["ctrl", "alt", "shift", "win"]:
            if keyboard.is_pressed(item):
                keys.append(item)
        if event.name not in {"ctrl", "alt", "shift", "win"}:
            keys.append(event.name)
        combo = "+".join(keys)
        self.recording_target.set(combo)
        self.cancel_recording()

    def cancel_recording(self):
        if self.recording_callback is not None:
            keyboard.unhook(self.recording_callback)
            self.recording_callback = None
        self.recording_target = None

    def delete_key_action(self, key_id, dialog):
        """Delete a key assignment"""
        preset = self.get_current_preset()
        if key_id in preset["keys"]:
            del preset["keys"][key_id]
            self.save_presets()
            self.update_key_buttons()
        dialog.destroy()

    def _setup_windows_raw_input(self):
        if not platform.system().lower() == "windows":
            self.raw_input_enabled = False
            self._raw_input_error = "Este filtro de teclado físico só funciona no Windows."
            return
        if ctypes is None or wintypes is None:
            self.raw_input_enabled = False
            self._raw_input_error = "ctypes não está disponível no ambiente."
            return
        self.raw_input_enabled = True
        self._raw_input_error = None
        self.available_keyboard_devices = []
        self.selected_keyboard_handle = None
        self._raw_input_handle_names = {}
        self._raw_input_device_name_to_handle = {}

    def _enum_raw_input_devices(self):
        if not self.raw_input_enabled:
            return []

        class RAWINPUTDEVICELIST(ctypes.Structure):
            _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]

        try:
            num_devices = wintypes.UINT()
            ctypes.windll.user32.GetRawInputDeviceList(None, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST))
            if num_devices.value == 0:
                return []

            devices = (RAWINPUTDEVICELIST * num_devices.value)()
            count = ctypes.windll.user32.GetRawInputDeviceList(
                ctypes.cast(devices, ctypes.POINTER(RAWINPUTDEVICELIST)),
                ctypes.byref(num_devices),
                ctypes.sizeof(RAWINPUTDEVICELIST),
            )
            if count == 0 or count == 0xFFFFFFFF:
                return []

            result = []
            for device in devices[:count]:
                if device.dwType != 0x01:
                    continue
                handle = int(device.hDevice)
                name = self._get_raw_input_device_name(handle)
                label = name or f"Keyboard-{handle}"
                result.append({
                    "handle": str(handle),
                    "device": label,
                    "name": label,
                })
            return result
        except Exception as exc:  # pragma: no cover
            self._raw_input_error = f"Erro ao listar dispositivos Raw Input: {exc}"
            return []

    def _get_raw_input_device_name(self, handle):
        try:
            device_name = ctypes.create_unicode_buffer(256)
            size = wintypes.DWORD(256)
            result = ctypes.windll.user32.GetRawInputDeviceInfoW(
                handle,
                0x20000007,
                device_name,
                ctypes.byref(size),
            )
            if result <= 0:
                return None
            return device_name.value.strip()
        except Exception:
            return None

    def _get_window_proc_pointer(self, proc):
        if proc is None:
            return 0
        try:
            return int(ctypes.cast(proc, ctypes.c_void_p).value)
        except (AttributeError, OverflowError, ValueError):
            try:
                return int(proc.handle)
            except AttributeError:
                return int(proc)

    def _install_raw_input_hook(self):
        if not self.raw_input_enabled:
            return
        if self._raw_input_hook_installed:
            return

        try:
            self._raw_input_devices = []

            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)
            class_name = f"NumpadRawInput_{abs(hash(id(self)))}"
            self._raw_input_message_class = class_name

            h_instance = ctypes.windll.kernel32.GetModuleHandleW(None)

            class WNDCLASSEXW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.UINT),
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", ctypes.c_void_p),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HANDLE),
                    ("hCursor", wintypes.HANDLE),
                    ("hbrBackground", wintypes.HANDLE),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                    ("hIconSm", wintypes.HANDLE),
                ]

            wndproc_ptr = WNDPROC(self._raw_input_wnd_proc)
            wc = WNDCLASSEXW()
            wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
            wc.style = 0
            wc.lpfnWndProc = ctypes.cast(wndproc_ptr, ctypes.c_void_p)
            wc.hInstance = h_instance
            wc.lpszClassName = class_name

            atom = ctypes.windll.user32.RegisterClassExW(ctypes.byref(wc))
            if not atom:
                raise RuntimeError("RegisterClassExW falhou")

            hwnd = ctypes.windll.user32.CreateWindowExW(
                0,
                class_name,
                "",
                0,
                0,
                0,
                0,
                0,
                0xFFFF,
                None,
                h_instance,
                None,
            )
            if not hwnd:
                raise RuntimeError("CreateWindowExW falhou")

            self._raw_input_message_hwnd = hwnd

            class RAWINPUTDEVICE(ctypes.Structure):
                _fields_ = [
                    ("usUsagePage", wintypes.USHORT),
                    ("usUsage", wintypes.USHORT),
                    ("dwFlags", wintypes.DWORD),
                    ("hwndTarget", wintypes.HANDLE),
                ]

            rid = RAWINPUTDEVICE()
            rid.usUsagePage = 0x01
            rid.usUsage = 0x06
            rid.dwFlags = 0x00000100
            rid.hwndTarget = hwnd

            result = ctypes.windll.user32.RegisterRawInputDevices(
                ctypes.byref(rid),
                1,
                ctypes.sizeof(RAWINPUTDEVICE),
            )
            if not result:
                raise RuntimeError("RegisterRawInputDevices falhou")

            self._raw_input_hook_installed = True
            self._raw_input_error = None
            self._raw_input_device_name_to_handle = {
                device.get("device") or device.get("name") or f"Keyboard-{device.get('handle')}": device.get("handle")
                for device in self._enum_raw_input_devices()
            }
        except Exception as exc:  # pragma: no cover
            self.raw_input_enabled = False
            self._raw_input_error = f"Falha ao registrar Raw Input: {exc}"
            self._raw_input_hook_installed = False

    def _raw_input_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == 0x00FF:
            if lparam is not None:
                self._handle_raw_input_message(lparam)
            return 0
        return 0

    def _handle_raw_input_message(self, lparam):
        try:
            class RAWINPUTHEADER(ctypes.Structure):
                _fields_ = [
                    ("dwType", wintypes.DWORD),
                    ("dwSize", wintypes.DWORD),
                    ("hDevice", wintypes.HANDLE),
                    ("wParam", wintypes.DWORD),
                ]

            class RAWKEYBOARD(ctypes.Structure):
                _fields_ = [
                    ("MakeCode", wintypes.USHORT),
                    ("Flags", wintypes.USHORT),
                    ("Reserved", wintypes.USHORT),
                    ("VKey", wintypes.USHORT),
                    ("Message", wintypes.UINT),
                    ("ExtraInformation", wintypes.ULONG),
                ]

            class RAWINPUTUNION(ctypes.Union):
                _fields_ = [("keyboard", RAWKEYBOARD)]

            class RAWINPUT(ctypes.Structure):
                _fields_ = [("header", RAWINPUTHEADER), ("data", RAWINPUTUNION)]

            size = wintypes.UINT(ctypes.sizeof(RAWINPUT))
            buffer = (ctypes.c_byte * size.value)()
            result = ctypes.windll.user32.GetRawInputData(
                ctypes.c_void_p(lparam),
                0x10000003,
                buffer,
                ctypes.byref(size),
                ctypes.sizeof(RAWINPUTHEADER),
            )
            if result == 0xFFFFFFFF or not buffer:
                return

            raw = ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents
            if raw.header.dwType != 0x01:
                return

            device_handle = str(int(raw.header.hDevice))
            device_name = self._get_raw_input_device_name(raw.header.hDevice)
            if not device_name:
                device_name = f"Keyboard-{device_handle}"

            if self.selected_keyboard_handle is None:
                self.selected_keyboard_handle = device_name

            if not self.keyboard_device_id:
                self._process_raw_input_key(raw.data.keyboard.VKey, device_name)
                return

            selected = self.normalize_device_id(self.keyboard_device_id)
            current = self.normalize_device_id(device_name)
            if selected and (current == selected or selected in current or current in selected):
                self._process_raw_input_key(raw.data.keyboard.VKey, device_name)
        except Exception:
            return

    def _process_raw_input_key(self, vk_code, device_name=None):
        if not self.enabled:
            return

        key_name = self._vk_to_key_name(vk_code)
        if not key_name:
            return

        if self.device_test_active:
            self._flash_device_test(key_name)
            return

        if not self.keyboard_device_id:
            return

        selected = self.normalize_device_id(self.keyboard_device_id)
        current = self.normalize_device_id(device_name)
        if not selected:
            return
        if not current:
            return
        if not (current == selected or selected in current or current in selected):
            return

        key_id = self._normalize_key_id(key_name)
        if key_id in self.key_buttons:
            self.execute_action(key_id)

    def _normalize_key_id(self, key_name):
        normalized = (key_name or "").strip().lower()
        alias_map = {
            "kp0": "0",
            "kp1": "1",
            "kp2": "2",
            "kp3": "3",
            "kp4": "4",
            "kp5": "5",
            "kp6": "6",
            "kp7": "7",
            "kp8": "8",
            "kp9": "9",
            "numlock": "numlock",
            "slash": "/",
            "*": "*",
            "minus": "-",
            "backspace": "backspace",
            "del": "del",
            "enter": "enter",
            "return": "enter",
        }
        return alias_map.get(normalized, normalized)

    def _vk_to_key_name(self, vk_code):
        key_map = {
            0x08: "backspace",
            0x09: "tab",
            0x0D: "enter",
            0x10: "shift",
            0x11: "ctrl",
            0x12: "alt",
            0x14: "caps lock",
            0x20: "space",
            0x2E: "del",
            0x30: "0",
            0x31: "1",
            0x32: "2",
            0x33: "3",
            0x34: "4",
            0x35: "5",
            0x36: "6",
            0x37: "7",
            0x38: "8",
            0x39: "9",
            0x41: "a",
            0x42: "b",
            0x43: "c",
            0x44: "d",
            0x45: "e",
            0x46: "f",
            0x47: "g",
            0x48: "h",
            0x49: "i",
            0x4A: "j",
            0x4B: "k",
            0x4C: "l",
            0x4D: "m",
            0x4E: "n",
            0x4F: "o",
            0x50: "p",
            0x51: "q",
            0x52: "r",
            0x53: "s",
            0x54: "t",
            0x55: "u",
            0x56: "v",
            0x57: "w",
            0x58: "x",
            0x59: "y",
            0x5A: "z",
            0x6A: "*",
            0x6B: "+",
            0x6D: "-",
            0x6E: ".",
            0x6F: "/",
            0x60: "0",
            0x61: "1",
            0x62: "2",
            0x63: "3",
            0x64: "4",
            0x65: "5",
            0x66: "6",
            0x67: "7",
            0x68: "8",
            0x69: "9",
            0x6C: "/",
            0x6D: "-",
            0x6E: ".",
            0x6F: "/",
        }
        return key_map.get(vk_code, None)

    def _device_label(self, device):
        if isinstance(device, dict):
            handle = str(device.get("handle") or device.get("id") or "").strip()
            if handle:
                return f"Keyboard-{handle}"
            name = device.get("name") or device.get("device") or "Teclado"
            return str(name)
        return str(device)

    def _native_raw_input_devices(self):
        if not self.native_raw_input_available:
            return []

        try:
            completed = subprocess.run(
                [str(self.native_raw_input_helper), "--list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if completed.returncode != 0:
                return []

            devices = []
            for line in completed.stdout.splitlines():
                line = line.strip()
                if not line or "[" not in line or "handle=" not in line:
                    continue
                left = line.split("handle=", 1)[1]
                handle = left.split(" name=", 1)[0].strip()
                name = left.split(" name=", 1)[1].strip() if " name=" in left else handle
                devices.append({"handle": handle, "device": name, "name": name})
            return devices
        except Exception:
            return []

    def _parse_native_event_line(self, line):
        if not line or not str(line).strip():
            return None
        try:
            payload = json.loads(line)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        payload["device"] = str(payload.get("device") or payload.get("name") or "")
        payload["handle"] = str(payload.get("handle") or "")
        payload["name"] = str(payload.get("name") or payload.get("key") or "")
        payload["pressed"] = bool(payload.get("pressed", True))
        try:
            payload["vk"] = int(payload.get("vk", 0))
        except Exception:
            payload["vk"] = 0
        return payload

    def _native_event_matches_selected_device(self, event):
        if self.keyboard_device_id in {"", None}:
            return True

        if not isinstance(event, dict):
            return True

        selected = self.normalize_device_id(self.keyboard_device_id)
        event_handle = self.normalize_device_id(event.get("handle") or event.get("device") or "")
        event_device = self.normalize_device_id(event.get("device") or "")

        return (
            selected == event_handle
            or selected == event_device
            or selected in event_handle
            or selected in event_device
        )

    def _start_native_bridge(self):
        if not self.native_raw_input_available or self.native_bridge_running:
            return

        try:
            self.native_bridge_process = subprocess.Popen(
                [str(self.native_raw_input_helper), "--listen"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=0,
            )
            self.native_bridge_running = True

            def reader():
                if self.native_bridge_process is None or self.native_bridge_process.stdout is None:
                    return
                for raw_line in self.native_bridge_process.stdout:
                    payload = self._parse_native_event_line(raw_line)
                    if payload is None or not payload.get("pressed"):
                        continue
                    if not self._native_event_matches_selected_device(payload):
                        continue
                    vk_code = int(payload.get("vk", 0) or 0)
                    event_name = (payload.get("name") or "").lower()
                    key_id = self._vk_to_key_name(vk_code) or event_name
                    if self.device_test_active:
                        self.root.after(0, lambda _name=key_id: self._flash_device_test(_name))
                        continue
                    if key_id in self.key_buttons:
                        self.root.after(0, lambda _key_id=key_id: self.execute_action(_key_id))

            self.native_bridge_reader = threading.Thread(target=reader, daemon=True)
            self.native_bridge_reader.start()
        except Exception as exc:  # pragma: no cover
            self._raw_input_error = f"Falha ao iniciar raw input nativo: {exc}"
            self.native_bridge_running = False
            self.native_bridge_process = None

    def _stop_native_bridge(self):
        if self.native_bridge_process is not None:
            try:
                self.native_bridge_process.terminate()
                self.native_bridge_process.wait(timeout=2)
            except Exception:
                pass
        self.native_bridge_process = None
        self.native_bridge_reader = None
        self.native_bridge_running = False

    def refresh_keyboard_devices(self):
        if not hasattr(self, "keyboard_device_combo"):
            return

        if self.native_raw_input_available:
            devices = self._native_raw_input_devices()
            if devices:
                self.available_keyboard_devices = devices
                labels = [self._device_label(device) for device in devices]
                self.keyboard_device_combo["values"] = ["All keyboards"] + labels
                if not self.keyboard_device_id:
                    self.keyboard_device_var.set("All keyboards")
                    self.keyboard_device_id = ""
                    return
                for device in devices:
                    if str(device.get("handle") or "") == str(self.keyboard_device_id):
                        self.keyboard_device_var.set(self._device_label(device))
                        return
                self.keyboard_device_var.set("All keyboards")
                self.keyboard_device_id = ""
                return

        if not self.raw_input_enabled:
            self.available_keyboard_devices = []
            self.keyboard_device_combo["values"] = []
            self.keyboard_device_var.set("")
            self.keyboard_device_id = ""
            return

        devices = self._enum_raw_input_devices()
        if not devices:
            self.available_keyboard_devices = []
            self.keyboard_device_combo["values"] = ["All keyboards"]
            self.keyboard_device_var.set("All keyboards")
            self.keyboard_device_id = ""
            return

        self.available_keyboard_devices = devices
        labels = [self._device_label(device) for device in devices]
        self.keyboard_device_combo["values"] = ["All keyboards"] + labels

        if not self.keyboard_device_id:
            self.keyboard_device_var.set("All keyboards")
            self.keyboard_device_id = ""
            return

        for device in devices:
            if str(device.get("handle") or "") == str(self.keyboard_device_id):
                self.keyboard_device_var.set(self._device_label(device))
                return
        self.keyboard_device_var.set("All keyboards")
        self.keyboard_device_id = ""

    def normalize_device_id(self, value):
        if value is None:
            return ""
        value = str(value).strip().lower()
        if value in {"all keyboards", "all", ""}:
            return ""
        return value

    def can_test_selected_keyboard(self):
        return bool(self.keyboard_device_id and self.normalize_device_id(self.keyboard_device_id))

    def toggle_device_test_mode(self):
        if not self.can_test_selected_keyboard():
            self.device_test_status_var.set("Selecione um teclado antes de testar.")
            self.device_test_led.configure(foreground="#cbd5e1")
            return

        self.device_test_active = not self.device_test_active
        if self.device_test_active:
            self.device_test_status_var.set(f"Teste ativo: {self.keyboard_device_id}")
            self.device_test_led.configure(foreground="#f59e0b")
            self.device_test_button.configure(text="Parar teste")
        else:
            self.device_test_status_var.set("Teste parado.")
            self.device_test_led.configure(foreground="#cbd5e1")
            self.device_test_button.configure(text="Testar dispositivo")

    def _flash_device_test(self, key_name=None):
        if not self.device_test_active:
            return
        self.device_test_status_var.set(f"Tecla detectada: {key_name or 'qualquer'}")
        self.device_test_led.configure(foreground="#22c55e")
        self.root.after(220, lambda: self.device_test_led.configure(foreground="#f59e0b"))

    def apply_keyboard_device_filter(self):
        value = self.keyboard_device_var.get().strip()
        if value in {"", "All keyboards"}:
            self.keyboard_device_id = ""
            self.keyboard_device_var.set("All keyboards")
            self.device_test_active = False
            if hasattr(self, "device_test_button") and self.device_test_button.winfo_exists():
                self.device_test_button.configure(text="Testar dispositivo")
                self.device_test_button.state(["disabled"])
            if hasattr(self, "device_test_status_var"):
                self.device_test_status_var.set("Aguardando teste...")
            if hasattr(self, "device_test_led") and self.device_test_led.winfo_exists():
                self.device_test_led.configure(foreground="#cbd5e1")
            return ""

        device_handle = ""
        for device in self.available_keyboard_devices:
            if self._device_label(device) == value:
                device_handle = str(device.get("handle") or "")
                break

        if not device_handle:
            device_handle = value

        self.keyboard_device_id = device_handle
        self.selected_keyboard_handle = device_handle
        if hasattr(self, "device_test_button") and self.device_test_button.winfo_exists():
            self.device_test_button.state(["!disabled"])
        if hasattr(self, "device_test_status_var"):
            self.device_test_status_var.set(f"Teclado selecionado: {self._device_label({'handle': device_handle, 'name': device_handle})}")
        return device_handle

    def clear_keyboard_device_filter(self):
        self.keyboard_device_id = ""
        self.selected_keyboard_handle = None
        self.keyboard_device_var.set("All keyboards")

    def should_process_keyboard_event(self, event):
        if not getattr(self, "enabled", True):
            return False

        if isinstance(event, dict):
            event_device = event.get("device") or event.get("handle")
        else:
            event_device = getattr(event, "device", None)

        selected_device = self.normalize_device_id(getattr(self, "keyboard_device_id", ""))

        if getattr(self, "device_test_active", False):
            if not selected_device:
                return True
            if event_device is None:
                return True
            current_device = self.normalize_device_id(event_device)
            return current_device == selected_device or selected_device in current_device or current_device in selected_device

        if not selected_device:
            return True

        if event_device is None:
            return False

        current_device = self.normalize_device_id(event_device)
        if not current_device or not selected_device:
            return False

        return current_device == selected_device or selected_device in current_device or current_device in selected_device

    def update_status_display(self):
        text = "Enabled" if self.enabled else "Disabled"
        self.status_var.set(text)
        self.status_label.configure(foreground="#16a34a" if self.enabled else "#d97706")

    def toggle_enabled(self):
        self.enabled = not self.enabled
        self.update_status_display()
        self.root.update_idletasks()

    def hide_window(self):
        self.root.withdraw()
        if self.tray_icon is not None:
            self.tray_icon.visible = True

    def show_window(self):
        self.root.deiconify()
        self.root.focus_force()

    def create_tray_icon(self):
        image = self.make_tray_image()
        menu = (
            pystray.MenuItem("Open", self.show_window),
            pystray.MenuItem("Switch Preset", self.rotate_preset),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.exit_app),
        )
        self.tray_icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def make_tray_image(self):
        size = (64, 64)
        image = Image.new("RGBA", size, (17, 24, 39, 255))
        # dark rounded square
        for x in range(8, 56):
            for y in range(8, 56):
                if 8 <= x <= 56 and 8 <= y <= 56:
                    image.putpixel((x, y), (31, 41, 55, 255))
        # accent mark
        for x in range(18, 46):
            for y in range(18, 46):
                if x in range(21, 41) and y in range(21, 41):
                    image.putpixel((x, y), (61, 214, 141, 255))
        return image

    def rotate_preset(self):
        keys = list(self.presets.keys())
        if not keys:
            return
        current_index = keys.index(self.current_preset_name)
        next_index = (current_index + 1) % len(keys)
        self.switch_preset(keys[next_index])

    def exit_app(self):
        try:
            if self.tray_icon is not None:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()

    def setup_global_hotkeys(self):
        keyboard.add_hotkey("ctrl+alt+f12", self.toggle_enabled)
        keyboard.add_hotkey("ctrl+alt+1", lambda: self.switch_preset("Default"))
        keyboard.add_hotkey("ctrl+alt+2", lambda: self.switch_preset("Default"))
        keyboard.add_hotkey("ctrl+alt+3", lambda: self.switch_preset("Default"))

    def setup_raw_input_listener(self):
        if self.native_raw_input_available:
            self.raw_input_enabled = True
            self._raw_input_error = None
            self._raw_input_hook_installed = True
            self._start_native_bridge()
            self.refresh_keyboard_devices()
            return
        if not self.raw_input_enabled:
            return
        if not hasattr(self, "keyboard_device_combo"):
            return
        self._install_raw_input_hook()
        self.refresh_keyboard_devices()

    def execute_action(self, key_id):
        if not self.enabled:
            return
        preset = self.get_current_preset()
        action = preset["keys"].get(key_id, {"type": "none", "value": ""})
        action_type = action.get("type", "none")
        value = safe_text(action.get("value", ""))

        if action_type == "none":
            return
        elif action_type == "close_window":
            self.root.destroy()
        elif action_type == "open_site":
            webbrowser.open(value)
        elif action_type == "open_program":
            if value:
                subprocess.Popen(value)
        elif action_type == "open_folder":
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
        elif action_type == "desktop":
            os.system("explorer.exe shell:desktop")
        elif action_type == "windows_tab":
            keyboard.send("win+tab")
        elif action_type == "alt_tab":
            keyboard.send("alt+tab")
        elif action_type == "write_text":
            if value:
                keyboard.write(value)
                keyboard.press_and_release("enter")
        elif action_type == "lock_pc":
            ctypes.windll.user32.LockWorkStation()
        elif action_type == "screenshot":
            screenshot = ImageGrab.grab()
            desktop = Path.home() / "Desktop"
            desktop.mkdir(exist_ok=True)
            file_name = desktop / f"screenshot_{int(time.time())}.png"
            screenshot.save(file_name)


if __name__ == "__main__":
    root = Tk()
    app = NumpadStreamDeckApp(root)

    def keyboard_handler(event):
        if not app.should_process_keyboard_event(event):
            return

        normalized = event.name.lower()
        alias_map = {
            "kp0": "0",
            "kp1": "1",
            "kp2": "2",
            "kp3": "3",
            "kp4": "4",
            "kp5": "5",
            "kp6": "6",
            "kp7": "7",
            "kp8": "8",
            "kp9": "9",
            "num lock": "numlock",
            "slash": "/",
            "*": "*",
            "minus": "-",
            "backspace": "backspace",
            "del": "del",
            "enter": "enter",
        }

        if app.device_test_active:
            app._flash_device_test(normalized)
            return

        key_id = alias_map.get(normalized, normalized)
        if key_id in app.key_buttons:
            app.execute_action(key_id)

    if app.raw_input_enabled:
        app.setup_raw_input_listener()
        app.refresh_keyboard_devices()
    else:
        keyboard.on_press(keyboard_handler)

    def on_close():
        app._stop_native_bridge()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
