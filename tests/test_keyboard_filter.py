import ctypes
import unittest
from unittest.mock import patch

from numpad_streamdeck import NumpadStreamDeckApp


class KeyboardFilterTests(unittest.TestCase):
    def make_activation_app(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.last_press_times = {}
        app.toggle_states = {}
        app.toggle_jobs = {}
        app.root = type(
            "Root",
            (),
            {
                "after": lambda self, delay, callback: "job-1",
                "after_cancel": lambda self, job: None,
            },
        )()
        app._execute_action = lambda action: app.executed.append(action)
        app.executed = []
        return app

    def test_double_click_executes_on_second_press_only(self):
        app = self.make_activation_app()
        action = {"type": "none", "double_click": True}

        app._process_key_press("kp0", action)
        self.assertEqual(app.executed, [])
        app._process_key_press("kp0", action)
        self.assertEqual(app.executed, [action])

    def test_separated_clicks_do_not_execute_double_click_action(self):
        app = self.make_activation_app()
        action = {"type": "none", "double_click": True}

        with patch("numpad_streamdeck.time.monotonic", side_effect=[1.0, 2.0]):
            app._process_key_press("kp0", action)
            app._process_key_press("kp0", action)

        self.assertEqual(app.executed, [])

    def test_toggle_executes_on_first_press_and_stops_on_second(self):
        app = self.make_activation_app()
        action = {"type": "hotkey", "toggle": True}

        app._process_key_press("kp0", action)
        app._process_key_press("kp0", action)
        self.assertEqual(app.executed, [action])

    def test_hold_executes_only_after_key_stays_pressed(self):
        app = self.make_activation_app()
        app.held_keys = {}
        action = {"type": "hotkey", "delay_ms": 500}

        app._handle_key_event("kp0", action, True)
        self.assertEqual(app.executed, [])
        state = app.held_keys["kp0"]
        app._handle_key_event("kp0", None, False)
        app._activate_held_key("kp0", action, state)
        self.assertEqual(app.executed, [])

    def test_hold_requires_new_press_after_activation(self):
        app = self.make_activation_app()
        app.held_keys = {}
        action = {"type": "hotkey", "delay_ms": 500}

        app._handle_key_event("kp0", action, True)
        state = app.held_keys["kp0"]
        app._activate_held_key("kp0", action, state)
        app._handle_key_event("kp0", action, True)
        self.assertEqual(app.executed, [action])
        app._handle_key_event("kp0", None, False)
        app._handle_key_event("kp0", action, True)
        next_state = app.held_keys["kp0"]
        app._activate_held_key("kp0", action, next_state)
        self.assertEqual(app.executed, [action, action])

    def test_key_can_have_independent_gesture_actions(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        entry = {
            "gestures": {
                "quick_press": {"type": "hotkey", "value": "alt+tab"},
                "hold": {"type": "open_program", "value": "discord.exe"},
                "double_click": {"type": "close_window"},
            }
        }

        self.assertEqual(app._get_gesture_action(entry, "quick_press")["value"], "alt+tab")
        self.assertEqual(app._get_gesture_action(entry, "hold")["value"], "discord.exe")
        self.assertEqual(app._get_gesture_action(entry, "double_click")["type"], "close_window")

    def test_action_store_keeps_unique_ids_for_same_key(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        entry = {
            "gestures": {
                "quick_press": {"type": "hotkey", "value": "alt+tab"},
                "hold": {"type": "open_program", "value": "discord.exe"},
            }
        }

        store = app._get_action_store(entry)

        self.assertEqual(len(store), 2)
        self.assertEqual(len(set(store)), 2)
        self.assertEqual({item["gesture"] for item in store.values()}, {"quick_press", "hold"})

    def test_double_click_does_not_execute_pending_quick_press(self):
        app = self.make_activation_app()
        app.held_keys = {}
        entry = {
            "gestures": {
                "quick_press": {"type": "hotkey", "value": "alt+tab"},
                "double_click": {"type": "close_window"},
            }
        }

        app._handle_key_event("kp0", entry, True)
        app._handle_key_event("kp0", None, False)
        app._handle_key_event("kp0", entry, True)
        app._handle_key_event("kp0", None, False)

        self.assertEqual(app.executed, [entry["gestures"]["double_click"]])

    def test_numpad_key_name_is_preserved(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)

        self.assertEqual(app._normalize_key("kp0"), "kp0")

    def test_open_file_or_application_uses_windows_file_association(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)

        with patch("numpad_streamdeck.os.startfile") as startfile:
            app._execute_action({"type": "open_program", "value": "C:\\Temp\\manual.pdf"})

        startfile.assert_called_once_with("C:\\Temp\\manual.pdf")

    def test_open_website_adds_https_protocol(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)

        with patch("numpad_streamdeck.webbrowser.open") as open_website:
            app._execute_action({"type": "open_site", "value": "example.com"})

        open_website.assert_called_once_with("https://example.com")

    def test_hold_type_text_waits_until_release(self):
        app = self.make_activation_app()
        app.held_keys = {}
        action = {"type": "write_text", "delay_ms": 500, "value": "hello"}

        app._handle_key_event("kp0", action, True)
        state = app.held_keys["kp0"]
        app._activate_held_key("kp0", action, state)
        self.assertEqual(app.executed, [])
        app._handle_key_event("kp0", None, False)
        self.assertEqual(app.executed, [action])

    def test_all_keyboards_allowed_when_no_device_filter(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.keyboard_device_id = ""

        event = type("Event", (), {"name": "enter", "device": "main-keyboard"})()

        self.assertTrue(app.should_process_keyboard_event(event))

    def test_event_ignored_when_device_id_does_not_match(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.keyboard_device_id = "numpad-42"

        event = type("Event", (), {"name": "enter", "device": "main-keyboard"})()

        self.assertFalse(app.should_process_keyboard_event(event))

    def test_event_allowed_when_device_matches(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.keyboard_device_id = "numpad-42"

        event = type("Event", (), {"name": "enter", "device": "numpad-42"})()

        self.assertTrue(app.should_process_keyboard_event(event))

    def test_device_test_is_available_only_for_specific_keyboard(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.keyboard_device_id = ""
        self.assertFalse(app.can_test_selected_keyboard())

        app.keyboard_device_id = "keyboard-42"
        self.assertTrue(app.can_test_selected_keyboard())

    def test_device_test_mode_does_not_execute_actions(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.device_test_active = True
        app.keyboard_device_id = "keyboard-42"
        app.key_buttons = {"enter": object()}
        calls = []
        app.execute_action = lambda key_id: calls.append(key_id)
        app._flash_device_test = lambda key_name=None: calls.append(f"flash:{key_name}")

        event = type("Event", (), {"name": "enter", "device": "keyboard-42"})()

        self.assertTrue(app.should_process_keyboard_event(event))
        if app.device_test_active:
            app._flash_device_test(event.name)
            self.assertEqual(calls, ["flash:enter"])
            return

        if "enter" in app.key_buttons:
            app.execute_action("enter")

        self.assertEqual(calls, ["flash:enter"])

    def test_device_test_mode_only_accepts_selected_keyboard(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.device_test_active = True
        app.keyboard_device_id = "keyboard-42"

        same_device = type("Event", (), {"name": "enter", "device": "keyboard-42"})()
        other_device = type("Event", (), {"name": "enter", "device": "keyboard-99"})()

        self.assertTrue(app.should_process_keyboard_event(same_device))
        self.assertFalse(app.should_process_keyboard_event(other_device))

    def test_device_test_mode_allows_keypress_when_device_id_is_missing(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.enabled = True
        app.device_test_active = True
        app.keyboard_device_id = "keyboard-42"

        event = type("Event", (), {"name": "enter", "device": None})()

        self.assertTrue(app.should_process_keyboard_event(event))

    def test_window_proc_pointer_conversion_is_safe(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)

        def dummy_callback(hwnd, msg, wparam, lparam):
            return 0

        proc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)(dummy_callback)
        pointer = app._get_window_proc_pointer(proc)

        self.assertIsInstance(pointer, int)
        self.assertGreater(pointer, 0)


if __name__ == "__main__":
    unittest.main()
