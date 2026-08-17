import unittest
from datetime import datetime

from intent import detect_intent, strip_intent_trigger
from obsidian_writer import _build_quick_note_path


class QuickNotePathTests(unittest.TestCase):
    def test_builds_sanitized_filename_with_date_prefix(self) -> None:
        created_on = datetime(2026, 7, 22, 14, 30)
        path = _build_quick_note_path("A / Very: Nice? Title", created_on)

        self.assertEqual(path.name, "2026-07-22 A Very Nice Title.md")
        self.assertTrue(path.parent.name == "0 Inbox")


class IntentTests(unittest.TestCase):
    def test_meeting_note_trigger_is_detected(self) -> None:
        transcript = "meeting note follow up from the planning call"

        self.assertEqual(detect_intent(transcript), "meeting_note")
        self.assertEqual(strip_intent_trigger(transcript), "follow up from the planning call")


if __name__ == "__main__":
    unittest.main()
