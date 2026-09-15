# Morning Zekr Roozaneh Telegram Bot

This bot sends two messages a day, Stockholm time:

- `10:00` - that day's ذکر روز
- `14:00` - a reminder: ذکر روزانه فراموش نشود

## No-server setup with GitHub Actions

You can run this without buying a server. GitHub Actions wakes up every 30 minutes, checks whether the bot was added to any groups, saves those group IDs, and sends each of the two daily messages once per day.

1. Open your GitHub repository.
2. Go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Add these repository secrets:

```text
BOT_TOKEN=your_telegram_bot_token_here
```

4. Go to the `Actions` tab.
5. Open the `Daily Zekr` workflow.
6. Click `Run workflow` once to test it.

After that, GitHub runs `.github/workflows/daily-zekr.yml` every 30 minutes. Each message is sent on the first run at or after its hour in `Europe/Stockholm`, and `data/state.json` records what already went out so nothing repeats.

Note that GitHub throttles scheduled workflows and can delay a run by hours, so a message may arrive well after its nominal time. If you need punctual delivery, run `bot.py` on an always-on machine instead.

### How fast replies arrive

`bot.py` answers a reply within seconds, because it holds an open connection to Telegram. The GitHub Actions path only answers on its next poll, so an answer can lag by hours. If conversational replies matter, run `bot.py` on an always-on machine.

To send to groups:

1. Add the bot to each Telegram group.
2. Make sure the bot is allowed to send messages.
3. Send any message in the group, or mention the bot.
4. GitHub Actions will discover and save the group ID automatically on its next run.

## What the bot does

- Users subscribe by sending `/start` to the bot.
- Users unsubscribe by sending `/stop`.
- Users can test immediately with `/today`.
- Users can ask for today's مناسبت with `/monasebat`.
- Every day at `10:00 Europe/Stockholm`, the bot sends that day's zikr to every subscribed chat, with the day's مناسبت‌ها under it when there are any.
- Every day at `14:00 Europe/Stockholm`, it sends the reminder ذکر روزانه فراموش نشود.
- When someone replies to one of the bot's messages, it answers with a random phrase from `replies.py` (30 of them, e.g. سلام برادر). It ignores replies aimed at other people and never answers another bot.
- When someone swears, it answers with a polite warning from `moderation.py` instead. The warning wins over the greeting, so a rude reply gets told off rather than thanked.
- It works for private chats and groups, as long as `/start` is sent in that chat.

## مناسبت‌های روز

`occasions.py` holds the occasions - births, martyrdoms, eids and the solar-calendar days. Lunar ones are keyed by `(Hijri month, day)` and solar ones by `(Jalali month, day)`, and `calendars.py` converts today's date into both. Adding an occasion is one line in the matching table.

The Persian solar conversion is exact. The Hijri one uses the tabular calendar, which can land a day off the calendar your group follows, because the real one waits for the new moon to be seen. If every lunar date looks one day early or late, set this environment variable wherever the bot runs:

```text
HIJRI_OFFSET_DAYS=1
```

`-1` shifts the other way. It moves every lunar occasion at once.

## Warning about bad language

`moderation.py` matches the roots کیر، کس، کص and کون, each only as a whole word with a known ending, so عکس، کسی، هیچ‌کس and مسکونی are left alone. Before matching it folds the usual evasions: Arabic spellings (`ي`, `ك`), diacritics, zero-width joiners, stretched letters (کیییییر) and dots between letters (ک.ی.ر).

To add a word, add its root to `_ROOT_SUFFIXES` in `moderation.py`. To change what the bot says, edit `WARNING_PHRASES` in the same file.

For this to work in a group, the bot has to see ordinary messages. Open BotFather, run `/setprivacy` for your bot and choose `Disable`. Otherwise Telegram only forwards commands and replies to the bot, and swearing in a plain message goes unnoticed.

`worker/index.js` carries a JavaScript copy of both the phrases and these rules, because the Cloudflare editor cannot import from the repo. Keep the two in step when editing either side.

## Tests

```bash
python -m unittest tests
```

They cover the swear-word matcher and the calendar lookups. No dependencies needed.

## Local setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the bot:

```bash
python bot.py
```

4. Open Telegram and send `/start` to your bot.

After that, leave the script running. The bot will send the zikr at 10:00 and the reminder at 14:00, Stockholm time.

## Deploying

For the bot to work every day, it must run continuously on an always-on computer or server.

Good options:

- Your computer, if it stays on
- A VPS
- Railway
- Render background worker
- Fly.io
- Raspberry Pi

When deploying, set this environment variable:

```text
BOT_TOKEN=your_telegram_bot_token_here
```

Do not publish the real `.env` file. It contains the bot token.
