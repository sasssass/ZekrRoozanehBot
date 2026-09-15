"""Warns, politely, when someone swears in a chat the bot is in.

The detector is deliberately narrow. Each root only matches as a whole word
with a known suffix, so عکس، کسی، هیچ‌کس، مسکونی and friends stay untouched.

Shared by bot.py and send_daily_zekr.py. worker/index.js carries the same
rules in JavaScript; keep the two in step when editing either one.
"""

import random
import re


WARNING_PHRASES = (
    "برادر، مودب باش. اینجا جای این حرف‌ها نیست.",
    "لطفاً ادب را رعایت کن.",
    "استغفرالله! زبانت را پاک نگه دار.",
    "با این ادبیات نه. محترمانه صحبت کن.",
    "برادر، حرف زشت نزن. صلوات بفرست.",
    "اینجا گروه ذکر است، نه فحش. مودب باش.",
    "زبان آدم آینه ادب اوست. مواظب باش.",
    "لطفاً محترمانه بنویس. کسی ناراحت می‌شود.",
    "این کلمه را پاک کن برادر. حرمت جمع را نگه دار.",
    "الکلام کالدواء؛ حرف خوب بزن برادر.",
)

# Characters people scatter through a word to slip past a filter.
_INVISIBLE = re.compile(r"[​-‏ـ]")
_DIACRITICS = re.compile(r"[ً-ْٰ]")
_INNER_SEPARATORS = re.compile(r"(?<=[ء-ی])[.\-_*+](?=[ء-ی])")
_REPEATS = re.compile(r"(.)\1+")

_ARABIC_LETTERS = {"ي": "ی", "ك": "ک", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ۀ": "ه"}

# A root only counts as swearing when it stands alone or carries one of these
# endings. Anything else glued to it means it is a different word.
_LETTER = r"\u0621-\u06cc"
_COMPOUND = r"(?:کش(?:ی)?|خل|خور|ده|بده|بازی|مادر)"
_PRONOUN = r"(?:یی|ی|م|ت|ش|مان|تان|شان|ها|هات|های|تو|شو|مو|رو|و|ه)"

# کس is the one root that is also an ordinary word (کسی، هیچ‌کس، کس و کار), so
# it only matches bare or in a compound - never with a pronoun ending.
_ROOT_SUFFIXES = {
    "کیر": rf"(?:{_PRONOUN}|{_COMPOUND})?",
    "کص": rf"(?:{_PRONOUN}|{_COMPOUND})?",
    "کون": rf"(?:{_PRONOUN}|{_COMPOUND})?",
    "کس": rf"{_COMPOUND}?",
}

_PROFANITY = tuple(
    re.compile(rf"(?<![{_LETTER}]){root}{suffixes}(?![{_LETTER}])")
    for root, suffixes in _ROOT_SUFFIXES.items()
)

# "هر کس" and "هیچ کس" are the innocent reading of a bare کس.
_INNOCENT_BEFORE_KOS = re.compile(r"(?:هر|هیچ|همان|ان|این|هم|نا)\s+(?:کس)(?![ء-ی])")


def normalize(text: str) -> str:
    """Fold the spellings and evasions that mean the same word."""
    text = _INVISIBLE.sub("", text)
    text = _DIACRITICS.sub("", text)
    text = "".join(_ARABIC_LETTERS.get(char, char) for char in text)
    text = _INNER_SEPARATORS.sub("", text)
    return _REPEATS.sub(r"\1", text)


def contains_profanity(text: str) -> bool:
    if not text:
        return False

    normalized = normalize(text)
    normalized = _INNOCENT_BEFORE_KOS.sub(" ", normalized)
    return any(pattern.search(normalized) for pattern in _PROFANITY)


def warning_phrase() -> str:
    return random.choice(WARNING_PHRASES)
