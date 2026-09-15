import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from moderation import contains_profanity, warning_phrase
from occasions import append_occasions, format_occasions
from replies import REPLY_PHRASES


BOT_TOKEN = os.environ["BOT_TOKEN"]
STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")
ZEKR_HOUR = 10
REMINDER_HOUR = 14
REMINDER_TEXT = "ذکر روزانه فراموش نشود"
API_ATTEMPTS = 3
GROUPS_FILE = Path("data/group_chats.json")
STATE_FILE = Path("data/state.json")

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


def read_json(path: Path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")


def telegram_api(method: str, payload: Optional[dict] = None) -> dict:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = None
    if payload is not None:
        data = urllib.parse.urlencode(payload).encode()

    for attempt in range(1, API_ATTEMPTS + 1):
        request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == API_ATTEMPTS:
                raise
            print(f"{method} failed ({exc}); retrying ({attempt}/{API_ATTEMPTS - 1}).")
            time.sleep(2 * attempt)

    if not result.get("ok"):
        raise RuntimeError(result)

    return result


def build_zekr_message() -> str:
    now = datetime.now(STOCKHOLM_TZ)
    weekday = now.strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    return append_occasions(f"ذکر روز {PERSIAN_WEEKDAYS[weekday]}\n\n{zekr}", now.date())


def build_reminder_message() -> str:
    return REMINDER_TEXT


# One entry per daily message. Each slot dedupes on its own key, so a delayed
# run sends whatever the day still owes without repeating what already went out.
SCHEDULED_SENDS = (
    {"key": "zekr", "hour": ZEKR_HOUR, "build": build_zekr_message},
    {"key": "reminder", "hour": REMINDER_HOUR, "build": build_reminder_message},
)


@lru_cache(maxsize=1)
def bot_user_id() -> int:
    return telegram_api("getMe")["result"]["id"]


def is_reply_to_bot(message: dict) -> bool:
    replied_to = message.get("reply_to_message")
    if not replied_to:
        return False

    # Never answer another bot, including ourselves.
    if message.get("from", {}).get("is_bot"):
        return False

    return replied_to.get("from", {}).get("id") == bot_user_id()


def answer_reply(message: dict) -> None:
    phrase = random.choice(REPLY_PHRASES)
    chat_id = str(message["chat"]["id"])
    if send_message(chat_id, phrase, reply_to_message_id=message["message_id"]):
        print(f"Answered a reply in {chat_id}: {phrase}")


def warn_about_profanity(message: dict) -> None:
    phrase = warning_phrase()
    chat_id = str(message["chat"]["id"])
    if send_message(chat_id, phrase, reply_to_message_id=message["message_id"]):
        print(f"Warned about language in {chat_id}.")


def handle_message(message: dict) -> None:
    """Warn about swearing, otherwise greet a reply. A warning outranks a greeting."""
    if message.get("from", {}).get("is_bot"):
        return

    if contains_profanity(message.get("text", "")):
        warn_about_profanity(message)
        return

    if is_reply_to_bot(message):
        answer_reply(message)


def normalize_group(chat: dict) -> Optional[dict]:
    if chat.get("type") not in {"group", "supergroup"}:
        return None

    return {
        "id": str(chat["id"]),
        "title": chat.get("title", ""),
        "type": chat.get("type", ""),
    }


def remember_group(groups: dict, chat: dict) -> None:
    group = normalize_group(chat)
    if group:
        groups[group["id"]] = group
        print(f"Saved group: {group['title']} ({group['id']})")


def forget_group(groups: dict, chat: dict) -> None:
    group = normalize_group(chat)
    if group:
        groups.pop(group["id"], None)


def collect_group_updates(state: dict, groups: dict) -> None:
    offset = state.get("last_update_id", 0) + 1
    try:
        response = telegram_api(
            "getUpdates",
            {
                "offset": offset,
                "timeout": 0,
                "allowed_updates": json.dumps(["message", "my_chat_member"]),
            },
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            print("Webhook is active, so getUpdates is unavailable; it answers replies instead.")
            print("Using the saved group list for today's messages.")
            return

        raise

    print(f"Telegram returned {len(response['result'])} update(s).")

    for update in response["result"]:
        state["last_update_id"] = max(state.get("last_update_id", 0), update["update_id"])

        if "message" in update:
            message = update["message"]
            chat = message["chat"]
            print(f"Saw message in {chat.get('type')}: {chat.get('title') or chat.get('username') or chat.get('id')}")
            remember_group(groups, chat)

            handle_message(message)

        if "my_chat_member" in update:
            chat_member = update["my_chat_member"]
            status = chat_member["new_chat_member"]["status"]
            chat = chat_member["chat"]
            print(f"Saw bot membership update in {chat.get('type')}: {chat.get('title') or chat.get('id')} -> {status}")
            if status in {"member", "administrator"}:
                remember_group(groups, chat_member["chat"])
            elif status in {"left", "kicked"}:
                forget_group(groups, chat_member["chat"])


def send_message(chat_id: str, text: str, reply_to_message_id: Optional[int] = None) -> bool:
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
        # If the message we are answering is gone by the time we get here, send
        # the phrase unthreaded rather than losing it.
        payload["allow_sending_without_reply"] = "true"

    try:
        telegram_api("sendMessage", payload)
        return True
    except urllib.error.HTTPError as exc:
        print(f"Could not send to {chat_id}: HTTP {exc.code} {exc.read().decode('utf-8')}")
        return False
    except Exception as exc:
        print(f"Could not send to {chat_id}: {exc}")
        return False


def force_send() -> bool:
    return os.environ.get("FORCE_SEND", "").lower() == "true"


def sent_dates(state: dict) -> dict:
    """Per-slot last-sent dates, migrating the old single-slot key."""
    dates = state.setdefault("sent_dates", {})
    legacy = state.pop("last_sent_date", None)
    if legacy and "zekr" not in dates:
        dates["zekr"] = legacy

    return dates


def should_send_now(send: dict, dates: dict, now: datetime) -> bool:
    if force_send():
        return True

    if dates.get(send["key"]) == now.date().isoformat():
        print(f"{send['key']}: already sent on {now.date().isoformat()}.")
        return False

    if now.hour < send["hour"]:
        print(f"{send['key']}: too early ({now:%H:%M} local, sends from {send['hour']:02d}:00).")
        return False

    return True


def broadcast(groups: dict, text: str) -> bool:
    sent_any = False
    for chat_id in sorted(groups):
        sent_any = send_message(chat_id, text) or sent_any

    return sent_any


def run_scheduled_sends(state: dict, groups: dict, now: datetime) -> None:
    if not groups:
        print("No groups saved yet.")
        return

    dates = sent_dates(state)
    for send in SCHEDULED_SENDS:
        if not should_send_now(send, dates, now):
            continue

        if broadcast(groups, send["build"]()) and not force_send():
            dates[send["key"]] = now.date().isoformat()
            print(f"{send['key']}: sent.")


def main() -> None:
    state = read_json(STATE_FILE, {})
    groups = read_json(GROUPS_FILE, {})

    collect_group_updates(state, groups)

    run_scheduled_sends(state, groups, datetime.now(STOCKHOLM_TZ))

    write_json(STATE_FILE, state)
    write_json(GROUPS_FILE, groups)
    print(f"Saved {len(groups)} group(s).")


if __name__ == "__main__":
    main()
