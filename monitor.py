"""
Leak Detector Lead Monitor — Twitter Edition (Scweet)
Busca tweets sobre: suscripciones, control financiero, monetización YouTube/TikTok.
Solo tweets en inglés. Genera 3 replies con OpenAI y envía por Telegram.
Horario: 7h, 10h, 13h, 16h, 19h, 22h (hora España)
"""

import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
from Scweet import Scweet

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_KEY       = os.environ["OPENAI_API_KEY"]
TWITTER_TOKEN    = os.environ["TWITTER_AUTH_TOKEN"]
GUMROAD_URL      = "https://templates.bravepicks.com/templates/the-1000-leak-detector"
DB_PATH          = os.environ.get("DB_PATH", "seen_posts.db")

HEADERS_OAI = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

MIN_LIKES = 2
SINCE     = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# ── Topic 1: Subscription Spending ───────────────────────────────────────────
SUBSCRIPTION_QUERIES = [
    "too many subscriptions lang:en",
    "subscription spending monthly lang:en",
    "cancel subscriptions save money lang:en",
    "forgot I was paying subscription lang:en",
    "hidden monthly charges apps lang:en",
]

SUBSCRIPTION_INTENT = [
    "subscri", "cancel", "monthly bill", "monthly cost", "monthly spend",
    "wasting money", "audit", "forgot", "hidden charge", "too many apps",
    "netflix", "spotify", "streaming", "overpaying", "money leak",
]

SUBSCRIPTION_PROMPT = """You are helping promote a FREE spreadsheet called "The €1.000 Leak Detector" that helps people audit their monthly subscriptions and spot money leaks.

Gumroad link: {gumroad_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Reference something specific from the tweet (show you read it)
- Include the Gumroad link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds a useful stat or insight]
OPTION_C: [starts with a genuine question, then offers the resource]"""

# ── Topic 2: Personal Financial Control ──────────────────────────────────────
FINANCE_QUERIES = [
    "personal finance budget tracker lang:en",
    "track monthly expenses budget lang:en",
    "money leaks personal finance lang:en",
    "control monthly spending lang:en",
    "financial audit personal budget lang:en",
]

FINANCE_INTENT = [
    "budget", "expense", "tracker", "spending", "financial", "money",
    "audit", "control", "monthly", "personal finance", "track", "save",
    "savings", "cash flow", "money management", "bills",
]

FINANCE_PROMPT = """You are helping promote a FREE spreadsheet called "The €1.000 Leak Detector" that helps people take control of their personal finances by auditing all monthly expenses and finding hidden money leaks.

Gumroad link: {gumroad_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Reference something specific from the tweet
- Include the Gumroad link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds a useful stat or insight]
OPTION_C: [starts with a genuine question about spending habits, then offers the resource]"""

# ── Topic 3: Monetize YouTube / TikTok ───────────────────────────────────────
CREATOR_QUERIES = [
    "how to monetize youtube channel lang:en",
    "youtube monetization tips lang:en",
    "tiktok monetization strategy lang:en",
    "make money youtube channel lang:en",
    "monetize tiktok videos creator lang:en",
]

CREATOR_INTENT = [
    "monetize", "monetization", "youtube", "tiktok", "revenue", "earnings",
    "adsense", "creator fund", "make money", "income from", "channel",
    "shorts", "grow channel", "youtube income",
]

CREATOR_PROMPT = """You are helping promote a FREE spreadsheet called "The €1.000 Leak Detector" that helps content creators audit all their monthly tool subscriptions (editing software, analytics, stock footage, etc.) to reduce overhead and maximize net revenue.

Gumroad link: {gumroad_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Connect to the creator angle: tool costs eat into revenue, knowing overhead is key to real profit
- Reference something specific from the tweet
- Include the Gumroad link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds insight about creator tool costs vs revenue]
OPTION_C: [starts with a genuine question about their tool stack, then offers the resource]"""

# ── Base de datos ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            post_id  TEXT PRIMARY KEY,
            platform TEXT,
            seen_at  TEXT
        )
    """)
    conn.commit()
    return conn

def is_seen(conn, post_id):
    return conn.execute(
        "SELECT 1 FROM seen WHERE post_id=?", (post_id,)
    ).fetchone() is not None

def mark_seen(conn, post_id, platform):
    conn.execute(
        "INSERT OR IGNORE INTO seen (post_id, platform, seen_at) VALUES (?,?,?)",
        (post_id, platform, datetime.now().isoformat())
    )
    conn.commit()

# ── Filtro de intención ───────────────────────────────────────────────────────
def has_intent(text, intent_words):
    t = text.lower()
    return any(w in t for w in intent_words)

# ── OpenAI: generar 3 replies ─────────────────────────────────────────────────
def generate_replies(prompt_template, tweet_text, username):
    prompt = prompt_template.format(
        gumroad_url=GUMROAD_URL,
        tweet_text=tweet_text[:400],
        username=username,
    )
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=HEADERS_OAI,
            json={
                "model": "gpt-4o-mini",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        lines = {
            line.split(": ", 1)[0]: line.split(": ", 1)[1]
            for line in text.splitlines()
            if ": " in line and line.startswith("OPTION_")
        }
        a = lines.get("OPTION_A", f"Built a FREE spreadsheet that audits exactly this: {GUMROAD_URL}")
        b = lines.get("OPTION_B", f"Most people underestimate their subscription spend by 2-3x. FREE audit: {GUMROAD_URL}")
        c = lines.get("OPTION_C", f"Have you counted all your active subscriptions? FREE tool: {GUMROAD_URL}")
        return a, b, c
    except Exception as e:
        print(f"[OpenAI] Error: {e}")
        return (
            f"Same thing happened to me — built a FREE spreadsheet to audit this: {GUMROAD_URL}",
            f"The average person underestimates subscription spend by $133/month. FREE audit sheet: {GUMROAD_URL}",
            f"Have you counted all your active subscriptions? Most people are shocked. FREE tool: {GUMROAD_URL}",
        )

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[Telegram] Error: {e}")

def build_message(tweet, replies, label):
    username = tweet["user"]["screen_name"]
    text     = tweet["text"][:280]
    likes    = tweet.get("likes", 0) or 0
    url      = tweet.get("tweet_url", "")
    a, b, c  = replies
    return (
        f"🐦 <b>Twitter Lead</b> [{label}] · @{username} · ❤️ {likes}\n"
        f"📝 {text}\n"
        f"🔗 {url}\n\n"
        f"<b>A)</b> <code>{a}</code>\n\n"
        f"<b>B)</b> <code>{b}</code>\n\n"
        f"<b>C)</b> <code>{c}</code>"
    )

# ── Motor principal ───────────────────────────────────────────────────────────
def scan(client, conn, queries, intent_words, prompt_template, label):
    total = 0
    for query in queries:
        try:
            tweets = client.search(query, since=SINCE, limit=15, save=False) or []
        except Exception as e:
            print(f"[Twitter] '{query}' — Error: {e}")
            time.sleep(5)
            continue

        for tweet in tweets:
            tweet_id = str(tweet.get("tweet_id", ""))
            if not tweet_id:
                continue

            likes = tweet.get("likes", 0) or 0
            if likes < MIN_LIKES:
                continue

            tweet_text = tweet.get("text", "")
            if not has_intent(tweet_text, intent_words):
                continue

            uid = f"twitter_{tweet_id}"
            if is_seen(conn, uid):
                continue

            username = tweet["user"]["screen_name"]
            replies  = generate_replies(prompt_template, tweet_text, username)
            mark_seen(conn, uid, "twitter")
            send_telegram(build_message(tweet, replies, label))
            total += 1
            print(f"  [{label}] @{username} likes={likes} -- {tweet_text[:60].encode('ascii','replace').decode()}")
            time.sleep(2)

        time.sleep(3)
    return total

def run():
    conn   = init_db()
    client = Scweet(auth_token=TWITTER_TOKEN)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Buscando tweets desde {SINCE}...")

    total  = scan(client, conn, SUBSCRIPTION_QUERIES, SUBSCRIPTION_INTENT, SUBSCRIPTION_PROMPT, "Subscriptions")
    total += scan(client, conn, FINANCE_QUERIES,      FINANCE_INTENT,      FINANCE_PROMPT,      "Finance")
    total += scan(client, conn, CREATOR_QUERIES,      CREATOR_INTENT,      CREATOR_PROMPT,      "Creators")

    conn.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Listo — {total} leads nuevos")

if __name__ == "__main__":
    run()
