# Morning Zekr Roozaneh Telegram Bot

This bot sends the daily ذکر روز every morning at 10:00 AM Stockholm time.

## No-server setup with GitHub Actions

You can run this without buying a server. GitHub Actions wakes up every 5 minutes, checks whether the bot was added to any groups, saves those group IDs, and sends once each day during the 10:00 Stockholm hour.

1. Open your GitHub repository.
2. Go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Add these repository secrets:

```text
BOT_TOKEN=your_telegram_bot_token_here
```

4. Go to the `Actions` tab.
5. Open the `Daily Zekr` workflow.
6. Click `Run workflow` once to test it.

After that, GitHub runs `.github/workflows/daily-zekr.yml` every 5 minutes. It sends the zikr once per day during the `10:00 Europe/Stockholm` hour.

To send to groups:

1. Add the bot to each Telegram group.
2. Make sure the bot is allowed to send messages.
3. Send any message in the group, or mention the bot.
4. GitHub Actions will discover and save the group ID automatically on its next run.

## What the bot does

- Users subscribe by sending `/start` to the bot.
- Users unsubscribe by sending `/stop`.
- Users can test immediately with `/today`.
- Every day at `10:00 Europe/Stockholm`, the bot sends that day's zikr to every subscribed chat.
- It works for private chats and groups, as long as `/start` is sent in that chat.

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

After that, leave the script running. The bot will send the zikr every morning at 10:00 Stockholm time.

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
