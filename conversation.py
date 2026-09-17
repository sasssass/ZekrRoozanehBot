"""Reads what a message is asking for, so the bot answers it instead of
picking a phrase at random.

Each intent is a few patterns and a few answers. The first intent that matches
wins, so the list is ordered from the most specific to the most general. When
nothing matches, the caller falls back to the old random phrase.

The bot understands Persian only. A message written in the Latin alphabet is
told so instead, before any intent is tried.

Patterns are matched against the message twice: once with the spellings folded
and once with repeated letters squashed, so سلاااام hits the same rule as سلام
without every pattern having to spell out the stretching.

Shared by bot.py and send_daily_zekr.py. worker/index.js carries the static
half of this in JavaScript; keep the two in step when editing either one.
"""

import random
import re
from datetime import date
from typing import Callable, Optional, Union

from moderation import fold, squash
from occasions import format_occasions
from poems import format_poem
from zekr import zekr_message


NO_OCCASION_TEXT = "امروز مناسبت خاصی ثبت نشده است."

# Latin letters and no Persian ones. Finglish counts as English here, which is
# the point: the answer asks for Persian script either way.
ENGLISH_ANSWERS = (
    "ببخشید برادر، انگلیسی بلد نیستم. فارسی بنویس.",
    "من فقط فارسی می‌فهمم. لطفاً فارسی بنویس.",
    "انگلیسی سرم نمی‌شود برادر. به فارسی بگو.",
    "فارسی بنویس تا جوابت را بدهم.",
)

_LATIN = re.compile(r"[a-z]", re.IGNORECASE)
_PERSIAN = re.compile(r"[ء-ی]")

Answers = Union[tuple[str, ...], Callable[[date], str]]

# (name, patterns, answers). Answers are either phrases to pick from, or a
# function of the day for the ones that have to look something up.
INTENTS: tuple[tuple[str, tuple[str, ...], Answers], ...] = (
    (
        "poem_request",
        (r"شعر", r"بیت بگو"),
        format_poem,
    ),
    (
        "zekr_request",
        (r"ذکر",),
        zekr_message,
    ),
    (
        "occasion_request",
        (r"مناسبت", r"چه روزیه", r"چه روزی است"),
        lambda day: format_occasions(day) or NO_OCCASION_TEXT,
    ),
    (
        "good_morning",
        (r"صبح ?(?:ت|شما)? ?بخیر",),
        (
            "صبح تو هم بخیر برادر",
            "صبحت بخیر و برکت",
            "صبح بخیر. روز خوبی داشته باشی",
        ),
    ),
    (
        "good_night",
        (r"شب ?(?:ت|شما)? ?بخیر", r"شب خوش"),
        (
            "شب تو هم بخیر",
            "شبت خوش برادر",
            "شب بخیر. خواب راحت",
        ),
    ),
    (
        "how_are_you",
        (r"چطوری", r"چطوره?ی", r"خوبی", r"حالت چطور", r"چه خبر", r"احوال", r"چه می‌کنی", r"چیکار می‌کنی"),
        (
            "شکر خدا خوبم برادر. تو چطوری؟",
            "الحمدلله. تو خوبی؟",
            "سلامتی. ممنون که پرسیدی",
            "بد نیستم، تا خدا چه بخواهد. احوال تو؟",
        ),
    ),
    (
        "thanks",
        (r"مرسی", r"ممنون", r"مچکر", r"متشکر", r"تشکر", r"سپاس", r"دمت گرم", r"لطف کردی"),
        (
            "خواهش می‌کنم برادر",
            "قابلی نداشت",
            "سلامت باشی",
            "خدا خیرت بدهد",
        ),
    ),
    (
        "goodbye",
        (r"خداحافظ", r"خدافظ", r"خدا نگهدار", r"فعلا", r"بدرود"),
        (
            "خدا نگهدار برادر",
            "به امان خدا",
            "در پناه حق",
            "فعلا. یا علی",
        ),
    ),
    (
        "who_are_you",
        (r"کی هستی", r"تو چی هستی", r"چه کاره‌ای", r"ربات", r"بات"),
        (
            "بنده ربات ذکر روزانه هستم. هر روز ذکر و شعر و مناسبت می‌فرستم.",
            "ربات ذکر روزانه‌ام برادر. با /today ذکر امروز را می‌گیری.",
        ),
    ),
    (
        "laughter",
        (r"خخ", r"ههه", r"جوک", r"😂", r"🤣", r"😹"),
        (
            "خنده بر هر درد بی‌درمان دواست",
            "خدا همیشه خندان نگهت دارد",
            "قربان خنده‌ات برادر",
        ),
    ),
    (
        "prayer_request",
        (r"التماس دعا", r"دعا کن", r"یا علی", r"یا حسین", r"صلوات"),
        (
            "اللهم صل علی محمد و آل محمد",
            "دعاگویت هستم برادر",
            "التماس دعا. یا علی مدد",
        ),
    ),
    (
        "greeting",
        (r"سلام", r"سلم", r"درود", r"هلو", r"عليك"),
        (
            "سلام برادر",
            "علیک سلام",
            "سلام و رحمت خدا بر تو",
            "سلام بر شما. خوش آمدی",
        ),
    ),
    (
        "affirmation",
        (r"\bاره\b", r"\bبله\b", r"\bباشه\b", r"\bاوکی\b", r"\bچشم\b"),
        (
            "قربانت",
            "چشم برادر",
            "ارادت",
        ),
    ),
)

_COMPILED = tuple(
    (name, tuple(re.compile(pattern) for pattern in patterns), answers)
    for name, patterns, answers in INTENTS
)


def is_english(text: str) -> bool:
    return bool(_LATIN.search(text)) and not _PERSIAN.search(text)


def _variants(text: str) -> tuple[str, str]:
    """The message with its spellings folded, and with stretching squashed."""
    folded = fold(text)
    return folded, squash(folded)


def match_intent(text: str) -> Optional[str]:
    """The name of the first intent the message matches, if any."""
    if not text:
        return None

    variants = _variants(text)
    for name, patterns, _ in _COMPILED:
        if any(pattern.search(variant) for pattern in patterns for variant in variants):
            return name

    return None


def answer_for(text: str, day: date) -> Optional[str]:
    """What to say back, or None when nothing in the message is recognisable."""
    if is_english(text):
        return random.choice(ENGLISH_ANSWERS)

    name = match_intent(text)
    if name is None:
        return None

    answers = next(answers for intent, _, answers in _COMPILED if intent == name)
    return answers(day) if callable(answers) else random.choice(answers)
