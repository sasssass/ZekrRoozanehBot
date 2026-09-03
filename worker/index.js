// Cloudflare Worker: answers instantly when a user replies to one of the
// bot's messages. Telegram pushes each update here, so there is no polling
// and nothing to keep running between replies.
//
// The phrases are duplicated from replies.py on purpose: this file is pasted
// into the Cloudflare dashboard editor, which cannot import from the repo.
// Keep the two lists in step when editing either one.

const REPLY_PHRASES = [
  "سلام برادر",
  "سلام علیکم",
  "علیک سلام",
  "سلام رفیق",
  "سلام بر شما",
  "سلام و رحمت خدا بر تو",
  "سلامت باشی برادر",
  "زنده باشی",
  "خدا قوت",
  "دمت گرم",
  "قربانت",
  "چاکریم برادر",
  "مخلصیم برادر",
  "ارادت داریم",
  "احسنت",
  "ماشاءالله",
  "خدا خیرت بدهد",
  "خدا حفظت کند",
  "خدا نگهدارت",
  "در پناه حق باشی",
  "یا علی مدد",
  "التماس دعا",
  "دعاگویت هستم برادر",
  "جانم برادر",
  "برادر عزیز، سلام",
  "صفا آوردی",
  "حال دلت خوش باشد",
  "صلوات بفرست برادر",
  "ذکر روزانه یادت نرود",
  "اجرت با صاحب الزمان",
];

async function telegram(token, method, payload) {
  const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });

  return response.json();
}

// Cached per isolate so a busy group costs one getMe, not one per reply.
let botIdPromise = null;

function botId(token) {
  if (!botIdPromise) {
    botIdPromise = telegram(token, "getMe", {})
      .then((body) => {
        if (!body.ok) {
          throw new Error(`getMe failed: ${body.error_code} ${body.description}`);
        }

        return body.result.id;
      })
      .catch((error) => {
        botIdPromise = null; // don't cache a failure
        throw error;
      });
  }

  return botIdPromise;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Zekr reply worker is up.", { status: 200 });
    }

    // Telegram echoes this header back on every call. Without it, anyone who
    // guessed the URL could make the bot post.
    if (request.headers.get("x-telegram-bot-api-secret-token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("bad request", { status: 400 });
    }

    const message = update.message;
    // Always 200 from here on: a non-2xx makes Telegram retry the same update.
    if (!message || !message.reply_to_message) return new Response("ignored");
    if (message.from?.is_bot) return new Response("ignored");

    try {
      // Asked only once we know this is a reply, so ordinary traffic is free.
      if (message.reply_to_message.from?.id !== (await botId(env.BOT_TOKEN))) {
        return new Response("ignored: reply to someone else");
      }

      const phrase = REPLY_PHRASES[Math.floor(Math.random() * REPLY_PHRASES.length)];
      const sent = await telegram(env.BOT_TOKEN, "sendMessage", {
        chat_id: message.chat.id,
        text: phrase,
        reply_to_message_id: message.message_id,
      });

      if (!sent.ok) {
        return new Response(`sendMessage failed: ${sent.error_code} ${sent.description}`);
      }

      return new Response("replied");
    } catch (error) {
      // The caller is already past the secret check, so it is safe to say why.
      return new Response(`error: ${error.message}`);
    }
  },
};
