import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo


BOT_TOKEN = os.environ["BOT_TOKEN"]
STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")
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

    request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(result)

    return result


def build_message() -> str:
    weekday = datetime.now(STOCKHOLM_TZ).strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    return f"ذکر روز {PERSIAN_WEEKDAYS[weekday]}\n\n{zekr}"


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


def forget_group(groups: dict, chat: dict) -> None:
    group = normalize_group(chat)
    if group:
        groups.pop(group["id"], None)


def collect_group_updates(state: dict, groups: dict) -> None:
    offset = state.get("last_update_id", 0) + 1
    response = telegram_api(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": json.dumps(["message", "my_chat_member"]),
        },
    )

    for update in response["result"]:
        state["last_update_id"] = max(state.get("last_update_id", 0), update["update_id"])

        if "message" in update:
            remember_group(groups, update["message"]["chat"])

        if "my_chat_member" in update:
            chat_member = update["my_chat_member"]
            status = chat_member["new_chat_member"]["status"]
            if status in {"member", "administrator"}:
                remember_group(groups, chat_member["chat"])
            elif status in {"left", "kicked"}:
                forget_group(groups, chat_member["chat"])


def send_message(chat_id: str, text: str) -> bool:
    try:
        telegram_api("sendMessage", {"chat_id": chat_id, "text": text})
        return True
    except urllib.error.HTTPError as exc:
        print(f"Could not send to {chat_id}: HTTP {exc.code} {exc.read().decode('utf-8')}")
        return False
    except Exception as exc:
        print(f"Could not send to {chat_id}: {exc}")
        return False


def should_send_now(state: dict, now: datetime) -> bool:
    force_send = os.environ.get("FORCE_SEND", "").lower() == "true"
    already_sent_today = state.get("last_sent_date") == now.date().isoformat()
    scheduled_window = now.hour == 10

    if force_send:
        return True

    return scheduled_window and not already_sent_today


def send_daily_zekr(state: dict, groups: dict, now: datetime) -> None:
    if not groups:
        print("No groups saved yet.")
        return

    message = build_message()
    sent_any = False

    for chat_id in sorted(groups):
        sent_any = send_message(chat_id, message) or sent_any

    if sent_any and os.environ.get("FORCE_SEND", "").lower() != "true":
        state["last_sent_date"] = now.date().isoformat()


def main() -> None:
    state = read_json(STATE_FILE, {})
    groups = read_json(GROUPS_FILE, {})

    collect_group_updates(state, groups)

    now = datetime.now(STOCKHOLM_TZ)
    if should_send_now(state, now):
        send_daily_zekr(state, groups, now)

    write_json(STATE_FILE, state)
    write_json(GROUPS_FILE, groups)
    print(f"Saved {len(groups)} group(s).")


if __name__ == "__main__":
    main()
