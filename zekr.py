"""The ذکر روز table, and the message built from it.

It used to sit in both senders. It lives here so bot.py, send_daily_zekr.py and
the conversation answers all read the same list.
"""

import random
from datetime import date


ZEKR_BY_WEEKDAY = {
    "Saturday": ["یا رَبَّ الْعالَمین"],
    "Sunday": ["یا ذَاالْجَلالِ وَالْإِکْرام"],
    "Monday": ["یا قاضِیَ الْحاجات"],
    "Tuesday": ["یا أَرْحَمَ الرَّاحِمین"],
    "Wednesday": ["یا حَیُّ یا قَیّوم"],
    "Thursday": ["لا إِلهَ إِلَّا اللَّهُ الْمَلِکُ الْحَقُّ الْمُبین"],
    "Friday": ["اللَّهُمَّ صَلِّ عَلَی مُحَمَّدٍ وَ آلِ مُحَمَّدٍ وَ عَجِّلْ فَرَجَهُمْ"],
}

PERSIAN_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}


def zekr_message(day: date) -> str:
    weekday = day.strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    return f"ذکر روز {PERSIAN_WEEKDAYS[weekday]}\n\n{zekr}"
