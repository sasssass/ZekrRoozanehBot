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

// Answers to the things people actually write. The first match wins, so this
// runs from the most specific rule to the most general. The worker cannot read
// the poem, zekr or occasion tables (they are Python), so those three point at
// the command instead of answering directly.
const INTENTS = [
  ["poem_request", [/شعر/u, /بیت بگو/u], ["شعر امروز را با دستور /poem بگیر برادر."]],
  ["zekr_request", [/ذکر/u], ["ذکر امروز را با دستور /today بگیر برادر."]],
  ["occasion_request", [/مناسبت/u, /چه روزیه/u], ["مناسبت امروز را با دستور /monasebat بگیر برادر."]],
  ["good_morning", [/صبح ?(?:ت|شما)? ?بخیر/u], ["صبح تو هم بخیر برادر", "صبحت بخیر و برکت", "صبح بخیر. روز خوبی داشته باشی"]],
  ["good_night", [/شب ?(?:ت|شما)? ?بخیر/u, /شب خوش/u], ["شب تو هم بخیر", "شبت خوش برادر", "شب بخیر. خواب راحت"]],
  ["how_are_you", [/چطوری/u, /چطوره?ی/u, /خوبی/u, /حالت چطور/u, /چه خبر/u, /احوال/u], ["شکر خدا خوبم برادر. تو چطوری؟", "الحمدلله. تو خوبی؟", "سلامتی. ممنون که پرسیدی", "بد نیستم، تا خدا چه بخواهد. احوال تو؟"]],
  ["thanks", [/مرسی/u, /ممنون/u, /مچکر/u, /متشکر/u, /تشکر/u, /سپاس/u, /دمت گرم/u], ["خواهش می‌کنم برادر", "قابلی نداشت", "سلامت باشی", "خدا خیرت بدهد"]],
  ["goodbye", [/خداحافظ/u, /خدافظ/u, /خدا نگهدار/u, /فعلا/u, /بدرود/u], ["خدا نگهدار برادر", "به امان خدا", "در پناه حق", "فعلا. یا علی"]],
  ["who_are_you", [/کی هستی/u, /تو چی هستی/u, /ربات/u, /بات/u], ["بنده ربات ذکر روزانه هستم. هر روز ذکر و شعر و مناسبت می‌فرستم.", "ربات ذکر روزانه‌ام برادر. با /today ذکر امروز را می‌گیری."]],
  ["laughter", [/خخ/u, /ههه/u, /جوک/u, /😂/u, /🤣/u, /😹/u], ["خنده بر هر درد بی‌درمان دواست", "خدا همیشه خندان نگهت دارد", "قربان خنده‌ات برادر"]],
  ["prayer_request", [/التماس دعا/u, /دعا کن/u, /یا علی/u, /یا حسین/u, /صلوات/u], ["اللهم صل علی محمد و آل محمد", "دعاگویت هستم برادر", "التماس دعا. یا علی مدد"]],
  ["greeting", [/سلام/u, /سلم/u, /درود/u, /هلو/u], ["سلام برادر", "علیک سلام", "سلام و رحمت خدا بر تو", "سلام بر شما. خوش آمدی"]],
  ["affirmation", [/\bاره\b/u, /\bبله\b/u, /\bباشه\b/u, /\bاوکی\b/u, /\bچشم\b/u], ["قربانت", "چشم برادر", "ارادت"]],
];

// The bot understands Persian only. Latin letters and no Persian ones - which
// catches Finglish too - get told so before any intent is tried.
const ENGLISH_ANSWERS = [
  "ببخشید برادر، انگلیسی بلد نیستم. فارسی بنویس.",
  "من فقط فارسی می‌فهمم. لطفاً فارسی بنویس.",
  "انگلیسی سرم نمی‌شود برادر. به فارسی بگو.",
  "فارسی بنویس تا جوابت را بدهم.",
];

// What the bot says back when the swearing is aimed at it. Polite on the
// surface, and it still hands the insult back.
const COMEBACK_PHRASES = [
  "با کمال احترام، همین را برای خودت آرزو می‌کنم.",
  "تشکر از محبتت برادر. عوضش برایت دعا می‌کنم.",
  "بنده که چیزی نگفتم. گویا در آینه نگاه می‌کردی.",
  "خدا از بزرگی کمت نکند. ادب هم چیز خوبی است.",
  "قربانت. هر چه گفتی نصف نصف.",
  "ما که رباتیم و دل نداریم، ولی جای تو خجالت کشیدیم.",
  "شما لطف داری. بنده هم متقابلا برایت آرزوی ادب می‌کنم.",
  "چشم برادر، پیامت رسید. جوابش را به خودت واگذار می‌کنم.",
  "درست است که ربات هستم، اما تربیت دارم. شما هم داشته باش.",
  "حرف بزرگ‌تر از دهانت است برادر. صلوات بفرست.",
];

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

// Fold the spellings that mean the same thing, leaving the letters alone.
// Repeated letters survive this, because ممنون and مکرر are ordinary words.
function fold(text) {
  return text
    .replace(/[\u200b-\u200f\u0640]/gu, "")
    .replace(/[\u064b-\u0652\u0670]/gu, "")
    .replace(/[\u0621-\u06cc]/gu, (char) => ARABIC_LETTERS[char] || char)
    .replace(/(?<=[\u0621-\u06cc])[.\-_*+](?=[\u0621-\u06cc])/gu, "");
}

// Collapse stretched letters, so کییییر and سلاااام read as one word.
function squash(text) {
  return text.replace(/(.)\1+/gu, "$1");
}

function normalize(text) {
  return squash(fold(text));
}

function isEnglish(text) {
  return /[a-z]/iu.test(text) && !/[\u0621-\u06cc]/u.test(text);
}

// Patterns are tried against the folded message and the squashed one, so
// سلاااام hits the same rule as سلام.
function answerFor(text) {
  if (!text) return null;
  if (isEnglish(text)) return pick(ENGLISH_ANSWERS);

  const folded = fold(text);
  const variants = [folded, squash(folded)];
  for (const [, patterns, answers] of INTENTS) {
    if (patterns.some((pattern) => variants.some((variant) => pattern.test(variant)))) {
      return pick(answers);
    }
  }

  return null;
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

      const text = message.text || message.caption || "";
      const privateChat = message.chat?.type === "private";
      // Asked only once we need it, so ordinary group traffic is free.
      const aimedAtUs =
        privateChat ||
        (Boolean(message.reply_to_message) &&
          message.reply_to_message.from?.id === (await botId(env.BOT_TOKEN)));

      // Swearing outranks everything else. Aimed at the bot it gets a comeback,
      // anywhere else in the chat it gets the warning.
      if (containsProfanity(text)) {
        phrase = aimedAtUs ? pick(COMEBACK_PHRASES) : pick(WARNING_PHRASES);
        outcome = aimedAtUs ? "answered back" : "warned";
      } else if (!aimedAtUs) {
        return new Response("ignored");
      } else if (isGif(message)) {
        phrase = GIF_REPLY;
        outcome = "answered a gif";
      } else {
        // Answer what was actually asked, and fall back to a phrase when the
        // message is not something the bot knows how to read.
        phrase = answerFor(text) || pick(REPLY_PHRASES);
        outcome = "replied";
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
