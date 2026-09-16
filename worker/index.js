// Cloudflare Worker: answers instantly when a user replies to one of the
// bot's messages. Telegram pushes each update here, so there is no polling
// and nothing to keep running between replies.
//
// It also warns, politely, when someone swears.
//
// The phrases and the swear-word rules are duplicated from replies.py and
// moderation.py on purpose: this file is pasted into the Cloudflare dashboard
// editor, which cannot import from the repo. Keep them in step when editing
// either side.

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

// The one answer a GIF gets, whatever the GIF is.
const GIF_REPLY = "کیرخر";

// Telegram sends a GIF as an animation, or as a document on older clients.
const GIF_MIME_TYPES = ["image/gif", "video/mp4"];

function isGif(message) {
  return Boolean(message.animation) || GIF_MIME_TYPES.includes(message.document?.mime_type);
}

const WARNING_PHRASES = [
  "برادر، مودب باش. اینجا جای این حرف‌ها نیست.",
  "لطفاً ادب را رعایت کن.",
  "استغفرالله! زبانت را پاک نگه دار.",
  "با این ادبیات نه. محترمانه صحبت کن.",
  "برادر، حرف زشت نزن. صلوات بفرست.",
  "اینجا گروه ذکر است، نه فحش. مودب باش.",
  "زبان آدم آینه ادب اوست. مواظب باش.",
  "لطفاً محترمانه بنویس. کسی ناراحت می‌شود.",
  "این کلمه را پاک کن برادر. حرمت جمع را نگه دار.",
  "الکلام کالدواء؛ حرف خوب بزن برادر.",
];

const ARABIC_LETTERS = { "ي": "ی", "ك": "ک", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ۀ": "ه" };

const LETTER = "\u0621-\u06cc";
const COMPOUND = "(?:کش(?:ی)?|خل|خور|ده|بده|بازی|مادر)";
const PRONOUN = "(?:یی|ی|م|ت|ش|مان|تان|شان|ها|هات|های|تو|شو|مو|رو|و|ه)";

// کس is the one root that is also an ordinary word (کسی، هیچ‌کس، کس و کار), so
// it only matches bare or in a compound - never with a pronoun ending. Every
// root is anchored between non-letters, which keeps عکس and مسکونی out of it.
const PROFANITY = [
  ["کیر", `(?:${PRONOUN}|${COMPOUND})?`],
  ["کص", `(?:${PRONOUN}|${COMPOUND})?`],
  ["کون", `(?:${PRONOUN}|${COMPOUND})?`],
  ["کس", `${COMPOUND}?`],
].map(([root, suffix]) => new RegExp(`(?<![${LETTER}])${root}${suffix}(?![${LETTER}])`, "u"));

const INNOCENT_BEFORE_KOS = /(?:هر|هیچ|همان|ان|این|هم|نا)\s+(?:کس)(?![\u0621-\u06cc])/gu;

// Fold the spellings and evasions that mean the same word.
function normalize(text) {
  return text
    .replace(/[\u200b-\u200f\u0640]/gu, "")
    .replace(/[\u064b-\u0652\u0670]/gu, "")
    .replace(/[\u0621-\u06cc]/gu, (char) => ARABIC_LETTERS[char] || char)
    .replace(/(?<=[\u0621-\u06cc])[.\-_*+](?=[\u0621-\u06cc])/gu, "")
    .replace(/(.)\1+/gu, "$1");
}

function containsProfanity(text) {
  if (!text) return false;

  const normalized = normalize(text).replace(INNOCENT_BEFORE_KOS, " ");
  return PROFANITY.some((pattern) => pattern.test(normalized));
}

function pick(phrases) {
  return phrases[Math.floor(Math.random() * phrases.length)];
}

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
    if (!message) return new Response("ignored");
    if (message.from?.is_bot) return new Response("ignored");

    try {
      let phrase;
      let outcome;

      // A warning outranks everything else, so someone who swears in a reply or
      // in a GIF caption gets told off rather than answered.
      if (containsProfanity(message.text || message.caption || "")) {
        phrase = pick(WARNING_PHRASES);
        outcome = "warned";
      } else if (!message.reply_to_message) {
        return new Response("ignored");
      } else {
        // Asked only once we know this is a reply, so ordinary traffic is free.
        if (message.reply_to_message.from?.id !== (await botId(env.BOT_TOKEN))) {
          return new Response("ignored: reply to someone else");
        }

        phrase = isGif(message) ? GIF_REPLY : pick(REPLY_PHRASES);
        outcome = isGif(message) ? "answered a gif" : "replied";
      }

      const sent = await telegram(env.BOT_TOKEN, "sendMessage", {
        chat_id: message.chat.id,
        text: phrase,
        reply_to_message_id: message.message_id,
        // If the message we are answering has been deleted, send the phrase
        // unthreaded rather than losing it.
        allow_sending_without_reply: true,
      });

      if (!sent.ok) {
        return new Response(`sendMessage failed: ${sent.error_code} ${sent.description}`);
      }

      return new Response(outcome);
    } catch (error) {
      // The caller is already past the secret check, so it is safe to say why.
      return new Response(`error: ${error.message}`);
    }
  },
};
