import json
import os
import random
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")
SUBSCRIBERS_FILE = Path("data/subscribers.json")

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


def load_subscribers() -> set[int]:
    if not SUBSCRIBERS_FILE.exists():
        return set()

    with SUBSCRIBERS_FILE.open("r", encoding="utf-8") as file:
        return {int(chat_id) for chat_id in json.load(file)}


def save_subscribers(chat_ids: set[int]) -> None:
    SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SUBSCRIBERS_FILE.open("w", encoding="utf-8") as file:
        json.dump(sorted(chat_ids), file, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    subscribers.add(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text(
        "سلام. از فردا هر روز ساعت 10 صبح به وقت استکهلم ذکر روز را می‌فرستم."
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    subscribers.discard(chat_id)
    save_subscribers(subscribers)

    await update.message.reply_text("ارسال ذکر روز برای این چت متوقف شد.")


def get_today_message() -> str:
    weekday = stockholm_now().strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    persian_weekday = PERSIAN_WEEKDAYS[weekday]
    return f"ذکر روز {persian_weekday}\n\n{zekr}"


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_today_message())


async def send_today_zekr(context: ContextTypes.DEFAULT_TYPE) -> None:
    message = get_today_message()

    for chat_id in load_subscribers():
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as exc:
            print(f"Could not send message to {chat_id}: {exc}")


def stockholm_now():
    from datetime import datetime

    return datetime.now(STOCKHOLM_TZ)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("today", today))

    app.job_queue.run_daily(
        send_today_zekr,
        time=time(hour=10, minute=0, tzinfo=STOCKHOLM_TZ),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_stockholm_zekr",
    )

    print("Bot is running. Send /start to the bot in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()
