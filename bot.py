import json
import os
import random
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from moderation import contains_profanity, warning_phrase
from occasions import append_occasions, format_occasions
from poems import format_poem
from replies import GIF_REPLY, REPLY_PHRASES


load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")
SUBSCRIBERS_FILE = Path("data/subscribers.json")
REMINDER_TEXT = "ذکر روزانه فراموش نشود"
NO_OCCASION_TEXT = "امروز مناسبت خاصی ثبت نشده است."
POEM_HOUR = 18
GIF_MIME_TYPES = {"image/gif", "video/mp4"}

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
    now = stockholm_now()
    weekday = now.strftime("%A")
    zekr = random.choice(ZEKR_BY_WEEKDAY[weekday])
    persian_weekday = PERSIAN_WEEKDAYS[weekday]
    return append_occasions(f"ذکر روز {persian_weekday}\n\n{zekr}", now.date())


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_today_message())


async def poem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_poem(stockholm_now().date()))


async def monasebat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        format_occasions(stockholm_now().date()) or NO_OCCASION_TEXT
    )


def is_gif(message) -> bool:
    """Telegram sends a GIF as an animation, or as a document on older clients."""
    if message.animation:
        return True

    document = message.document
    return bool(document and document.mime_type in GIF_MIME_TYPES)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    # Never answer another bot, including ourselves.
    if message.from_user and message.from_user.is_bot:
        return

    # A warning outranks everything else, so someone who swears in a reply or in
    # a GIF caption gets told off rather than answered.
    if contains_profanity(message.text or message.caption or ""):
        await message.reply_text(warning_phrase())
        return

    replied_to = message.reply_to_message
    if not replied_to:
        return

    # Only answer a human replying to something this bot said.
    if not replied_to.from_user or replied_to.from_user.id != context.bot.id:
        return

    await message.reply_text(GIF_REPLY if is_gif(message) else random.choice(REPLY_PHRASES))


async def broadcast(context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    for chat_id in load_subscribers():
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as exc:
            print(f"Could not send message to {chat_id}: {exc}")


async def send_today_zekr(context: ContextTypes.DEFAULT_TYPE) -> None:
    await broadcast(context, get_today_message())


async def send_zekr_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    await broadcast(context, REMINDER_TEXT)


async def send_daily_poem(context: ContextTypes.DEFAULT_TYPE) -> None:
    await broadcast(context, format_poem(stockholm_now().date()))


def stockholm_now():
    from datetime import datetime

    return datetime.now(STOCKHOLM_TZ)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("monasebat", monasebat))
    app.add_handler(CommandHandler("poem", poem))
    # Every text message, not just replies: the warning has to see them all.
    # Animations and documents come along for the GIF answer.
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.ANIMATION | filters.Document.ALL) & ~filters.COMMAND,
            handle_message,
        )
    )

    app.job_queue.run_daily(
        send_today_zekr,
        time=time(hour=10, minute=0, tzinfo=STOCKHOLM_TZ),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_stockholm_zekr",
    )

    app.job_queue.run_daily(
        send_zekr_reminder,
        time=time(hour=14, minute=0, tzinfo=STOCKHOLM_TZ),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_stockholm_zekr_reminder",
    )

    app.job_queue.run_daily(
        send_daily_poem,
        time=time(hour=POEM_HOUR, minute=0, tzinfo=STOCKHOLM_TZ),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_stockholm_poem",
    )

    print("Bot is running. Send /start to the bot in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()
