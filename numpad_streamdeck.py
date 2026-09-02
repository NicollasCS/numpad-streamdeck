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

import keyboard
import pystray
from PIL import Image, ImageGrab

APP_NAME = "Numpad Stream Deck"
APPDATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "NumpadStreamDeck"
PRESET_FILE = APPDATA_DIR / "numpad_presets.json"

KEY_LAYOUT = [
    ["numlock", "/", "*", "-"],
    ["7", "8", "9", "+"],
    ["4", "5", "6", "backspace"],
    ["1", "2", "3", "del"],
    ["0", "000", "enter"],
]

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


def default_empty_preset():
    keys = {}
    for row in KEY_LAYOUT:
        for key in row:
            keys[key] = {"type": "none", "value": ""}
    return {"keys": keys}


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

        # Preset controls
        controls = ttk.Frame(self.tab_presets)
        controls.pack(fill="x", pady=(0, 16))

        ttk.Label(controls, text="Preset:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.preset_combo = ttk.Combobox(controls, textvariable=self.preset_var, state="readonly", width=22)
        self.preset_combo.pack(side="left", padx=(0, 12))
        self.preset_combo.bind("<<ComboboxSelected>>", lambda event: self.switch_preset(self.preset_var.get()))

        ttk.Button(controls, text="Add", command=self.create_preset).pack(side="left", padx=4)
        ttk.Button(controls, text="Duplicate", command=self.duplicate_preset).pack(side="left", padx=4)
        ttk.Button(controls, text="Rename", command=self.rename_preset).pack(side="left", padx=4)
        ttk.Button(controls, text="Delete", command=self.delete_preset).pack(side="left", padx=4)

        # Keyboard pad
        pad = ttk.Frame(self.tab_presets)
        pad.pack(fill="both", expand=True)

        pad.columnconfigure((0, 1, 2, 3), weight=1)
        for index in range(5):
            pad.rowconfigure(index, weight=1)

        key_specs = [
            ("numlock", 0, 0, 1, 1),
            ("/", 0, 1, 1, 1),
            ("*", 0, 2, 1, 1),
            ("-", 0, 3, 1, 1),
            ("7", 1, 0, 1, 1),
            ("8", 1, 1, 1, 1),
            ("9", 1, 2, 1, 1),
            ("+", 1, 3, 2, 1),
            ("4", 2, 0, 1, 1),
            ("5", 2, 1, 1, 1),
            ("6", 2, 2, 1, 1),
            ("backspace", 2, 3, 1, 1),
            ("1", 3, 0, 1, 1),
            ("2", 3, 1, 1, 1),
            ("3", 3, 2, 1, 1),
            ("del", 3, 3, 1, 1),
            ("0", 4, 0, 1, 1),
            ("000", 4, 1, 1, 1),
            ("enter", 4, 2, 2, 2),
        ]

        for key_id, row, col, row_span, col_span in key_specs:
            lb = ttk.Button(
                pad,
                text=self.get_key_label(key_id),
                command=lambda k=key_id: self.edit_key_action(k),
                style="Pad.TButton",
            )
            lb.grid(row=row, column=col, rowspan=row_span, columnspan=col_span, sticky="nsew", padx=6, pady=6)
            self.key_buttons[key_id] = lb

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
        items = list(self.presets.keys())
        self.preset_combo["values"] = items
        if self.current_preset_name in items:
            self.preset_var.set(self.current_preset_name)
            self.preset_combo.set(self.current_preset_name)
        elif items:
            self.current_preset_name = items[0]
            self.preset_var.set(self.current_preset_name)
            self.preset_combo.set(self.current_preset_name)

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

    def update_key_buttons(self):
        preset = self.get_current_preset()
        for key_id, button in self.key_buttons.items():
            action = preset["keys"].get(key_id, {"type": "none", "value": ""})
            button.configure(text=self.get_button_text(key_id, action))
            button.configure(style="PadActive.TButton" if action["type"] != "none" else "Pad.TButton")

    def get_button_text(self, key_id, action):
        label = self.get_key_label(key_id)
        action_type = action.get("type", "none")
        if action_type == "none":
            return label
        action_label = self.translate_type(action_type)
        if len(action_label) > 12:
            action_label = action_label[:10] + "..."
        return f"{label}\n{action_label}"

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
        dialog.geometry("420x280")
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
        ttk.Button(btn_row, text="Record Shortcut", command=record_shortcut).pack(side="left")

        def save_action():
            selected_label = mode_var.get()
            code = ACTION_MAP.get(selected_label, "none")
            preset["keys"][key_id] = {"type": code, "value": value_var.get()}
            self.save_presets()
            self.update_key_buttons()
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=save_action).pack(pady=8)

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
        self.preset_var.set(keys[next_index])
        self.preset_combo.set(keys[next_index])

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
        if not app.enabled:
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

        key_id = alias_map.get(normalized, normalized)
        if key_id in app.key_buttons:
            app.execute_action(key_id)

    keyboard.on_press(keyboard_handler)
    root.mainloop()
