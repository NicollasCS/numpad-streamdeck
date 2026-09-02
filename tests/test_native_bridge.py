import unittest

from numpad_streamdeck import NumpadStreamDeckApp


class NativeBridgeTests(unittest.TestCase):
    def test_parse_native_event_line(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        payload = {
            "device": "Keyboard-0x1234",
            "handle": "0x1234",
            "vk": 13,
            "name": "enter",
            "pressed": True,
        }

        parsed = app._parse_native_event_line('{"device":"Keyboard-0x1234","handle":"0x1234","vk":13,"name":"enter","pressed":true}')

        self.assertEqual(parsed["device"], payload["device"])
        self.assertEqual(parsed["handle"], payload["handle"])
        self.assertEqual(parsed["vk"], payload["vk"])
        self.assertEqual(parsed["name"], payload["name"])
        self.assertTrue(parsed["pressed"])

    def test_native_event_matches_selected_device(self):
        app = NumpadStreamDeckApp.__new__(NumpadStreamDeckApp)
        app.keyboard_device_id = "0x1234"

        event = {
            "device": "Keyboard-0x1234",
            "handle": "0x1234",
            "name": "enter",
            "pressed": True,
        }

        self.assertTrue(app._native_event_matches_selected_device(event))

        other = {
            "device": "Keyboard-0x9999",
            "handle": "0x9999",
            "name": "enter",
            "pressed": True,
        }

        self.assertFalse(app._native_event_matches_selected_device(other))


if __name__ == "__main__":
    unittest.main()
