import os
import random
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")

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


def build_message() -> str:
    weekday = datetime.now(STOCKHOLM_TZ).strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    return f"ذکر روز {PERSIAN_WEEKDAYS[weekday]}\n\n{zekr}"


def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    request = urllib.request.Request(url, data=payload, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


if __name__ == "__main__":
    send_message(build_message())
