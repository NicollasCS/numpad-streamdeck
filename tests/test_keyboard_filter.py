import ctypes
import unittest

from numpad_streamdeck import NumpadStreamDeckApp


class KeyboardFilterTests(unittest.TestCase):
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
