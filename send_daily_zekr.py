import os
import random
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


BOT_TOKEN = os.environ["BOT_TOKEN"]
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


def get_chat_ids() -> list[str]:
    chat_ids = os.environ.get("CHAT_IDS") or os.environ.get("CHAT_ID")
    if not chat_ids:
        raise RuntimeError("Set CHAT_IDS, for example: -1001111111111,-1002222222222")

    return [chat_id.strip() for chat_id in chat_ids.split(",") if chat_id.strip()]


def send_message(chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(url, data=payload, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


if __name__ == "__main__":
    message = build_message()
    for chat_id in get_chat_ids():
        send_message(chat_id, message)
