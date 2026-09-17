"""Stdlib-only tests: `python -m unittest tests`.

They cover the two pieces with real logic in them - the swear-word matcher and
the calendar lookups. Everything else is a Telegram call.
"""

import unittest
from datetime import date, timedelta

from calendars import gregorian_to_hijri, gregorian_to_jalali
from conversation import answer_for, is_english, match_intent
from moderation import contains_profanity
from occasions import append_occasions, format_occasions, occasions_for
from poems import POEMS, format_poem, poem_for


class ProfanityTest(unittest.TestCase):
    def test_flags_swearing(self):
        for text in (
            "کیر",
            "کس",
            "کون",
            "کیری",
            "کونی",
            "کسکش",
            "کس کش",
            "کص",
            "برو کونتو بده",
            "چه کیری",
            "کسخل",
        ):
            with self.subTest(text=text):
                self.assertTrue(contains_profanity(text))

    def test_sees_through_evasions(self):
        # Stretched, dotted, Arabic-spelled and zero-width-split writings.
        for text in ("کییییییر", "ک.ی.ر", "کــــیر", "كير", "کس‌کش"):
            with self.subTest(text=text):
                self.assertTrue(contains_profanity(text))

    def test_leaves_innocent_words_alone(self):
        for text in (
            "عکس",
            "کسی",
            "هیچ کس",
            "هر کس",
            "هیچ‌کس",
            "کسب و کار",
            "مسکونی",
            "کسل",
            "کسری",
            "اکنون",
            "تاکسی",
            "انعکاس",
            "سلام برادر",
            "ذکر روزانه فراموش نشود",
        ):
            with self.subTest(text=text):
                self.assertFalse(contains_profanity(text))

    def test_ignores_empty_text(self):
        self.assertFalse(contains_profanity(""))


class CalendarTest(unittest.TestCase):
    def test_jalali_new_year(self):
        self.assertEqual(gregorian_to_jalali(date(2026, 3, 21)), (1405, 1, 1))
        self.assertEqual(gregorian_to_jalali(date(2026, 3, 20)), (1404, 12, 29))

    def test_jalali_known_dates(self):
        self.assertEqual(gregorian_to_jalali(date(2026, 2, 11)), (1404, 11, 22))
        self.assertEqual(gregorian_to_jalali(date(2025, 12, 21)), (1404, 9, 30))

    def test_hijri_months_stay_in_range(self):
        for offset in range(0, 1200, 7):
            year, month, day = gregorian_to_hijri(date(2026, 1, 1) + timedelta(days=offset))
            with self.subTest(offset=offset):
                self.assertTrue(1 <= month <= 12)
                self.assertTrue(1 <= day <= 30)
                self.assertTrue(1440 < year < 1460)


class OccasionsTest(unittest.TestCase):
    def test_nowruz_is_listed(self):
        self.assertIn("عید نوروز و آغاز سال نو", occasions_for(date(2026, 3, 21)))

    def test_ordinary_day_has_no_block(self):
        self.assertEqual(format_occasions(date(2026, 9, 16)), "")
        self.assertEqual(append_occasions("ذکر روز", date(2026, 9, 16)), "ذکر روز")

    def test_block_is_appended_when_there_is_one(self):
        message = append_occasions("ذکر روز", date(2026, 3, 21))
        self.assertTrue(message.startswith("ذکر روز\n\n"))
        self.assertIn("عید نوروز", message)


class PoemTest(unittest.TestCase):
    def test_same_day_gives_the_same_poem(self):
        self.assertEqual(poem_for(date(2026, 9, 16)), poem_for(date(2026, 9, 16)))

    def test_a_full_pass_uses_every_poem_once(self):
        # Start where a pass does, so the window is one whole trip through the list.
        start = date(2026, 9, 16)
        start += timedelta(days=(-start.toordinal()) % len(POEMS))
        picked = [poem_for(start + timedelta(days=offset)) for offset in range(len(POEMS))]
        self.assertEqual(len(set(picked)), len(POEMS))

    def test_message_carries_the_poem_and_the_poet(self):
        message = format_poem(date(2026, 9, 16))
        poet, lines = poem_for(date(2026, 9, 16))
        self.assertTrue(message.startswith("شعر امروز\n\n"))
        for line in lines:
            self.assertIn(line, message)
        self.assertTrue(message.endswith(f"— {poet}"))


class ConversationTest(unittest.TestCase):
    def test_reads_the_common_openings(self):
        expected = {
            "سلام": "greeting",
            "سلاااام": "greeting",
            "علیک سلام": "greeting",
            "چطوری؟": "how_are_you",
            "خوبی داداش": "how_are_you",
            "ممنون برادر": "thanks",
            "مرسی": "thanks",
            "خداحافظ": "goodbye",
            "صبح بخیر": "good_morning",
            "شبت بخیر": "good_night",
            "خخخخخ": "laughter",
            "التماس دعا": "prayer_request",
            "تو کی هستی؟": "who_are_you",
            "باشه": "affirmation",
        }
        for text, intent in expected.items():
            with self.subTest(text=text):
                self.assertEqual(match_intent(text), intent)

    def test_asking_for_something_answers_with_it(self):
        day = date(2026, 3, 21)
        self.assertIn("شعر امروز", answer_for("یه شعر بگو", day))
        self.assertIn("ذکر روز", answer_for("ذکر امروز چیه؟", day))
        self.assertIn("عید نوروز", answer_for("مناسبت امروز چیه؟", day))

    def test_english_is_turned_away_in_persian(self):
        self.assertTrue(is_english("hello"))
        self.assertTrue(is_english("salam chetori"))
        self.assertFalse(is_english("سلام"))
        self.assertFalse(is_english("سلام hello"))
        self.assertIn("فارسی", answer_for("how are you", date(2026, 9, 17)))

    def test_unreadable_message_gets_no_answer(self):
        self.assertIsNone(answer_for("یه چیز کاملا نامربوط", date(2026, 9, 17)))
        self.assertIsNone(answer_for("", date(2026, 9, 17)))


if __name__ == "__main__":
    unittest.main()
