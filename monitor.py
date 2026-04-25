"""
Leak Detector Lead Monitor — Twitter Edition (Scweet)
Busca tweets sobre: suscripciones, presupuesto, YouTube, TikTok, sellers Etsy/Shopify.
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
DB_PATH          = os.environ.get("DB_PATH", "seen_posts.db")

HEADERS_OAI = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

MIN_LIKES = 2
SINCE     = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# ── URLs por plantilla ────────────────────────────────────────────────────────
URL_LEAK_DETECTOR  = "https://templates.bravepicks.com/templates/the-1000-leak-detector"
URL_BUDGET_TRACKER = "https://templates.bravepicks.com/templates/budget-personal-finance-tracker"
URL_YOUTUBE        = "https://templates.bravepicks.com/templates/youtube-analytics-tracker-mini"
URL_TIKTOK         = "https://templates.bravepicks.com/templates/tiktok-content-planner"
URL_PROFIT         = "https://templates.bravepicks.com/templates/product-profit-calculator"

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

Template link: {template_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Reference something specific from the tweet (show you read it)
- Include the template link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds a useful stat or insight]
OPTION_C: [starts with a genuine question, then offers the resource]"""

# ── Topic 2: Budget & Personal Finance ───────────────────────────────────────
FINANCE_QUERIES = [
    "how to save money every month lang:en",
    "personal budget spreadsheet template lang:en",
    "track monthly expenses better lang:en",
    "control spending family budget lang:en",
    "personal finance plan savings goals lang:en",
]

FINANCE_INTENT = [
    "budget", "expense", "tracker", "spending", "financial", "money",
    "audit", "control", "monthly", "personal finance", "track", "save",
    "savings", "cash flow", "money management", "bills", "invest",
    "plan", "paycheck", "broke", "overspend", "afford",
]

FINANCE_PROMPT = """You are helping promote a FREE spreadsheet called "Budget & Personal Finance Tracker" that helps people take full control of their finances: track income, expenses by category, set savings goals, and plan month by month.

Template link: {template_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Reference something specific from the tweet
- Include the template link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds a useful stat or insight about budgeting]
OPTION_C: [starts with a genuine question about their spending habits, then offers the resource]"""

# ── Topic 3: YouTube Growth & Monetization ───────────────────────────────────
YOUTUBE_QUERIES = [
    "how to grow youtube channel lang:en",
    "youtube monetization tips strategy lang:en",
    "youtube analytics improve channel lang:en",
    "make money youtube channel lang:en",
    "youtube content plan schedule lang:en",
]

YOUTUBE_INTENT = [
    "youtube", "yt channel", "youtube channel", "monetize youtube", "monetization",
    "adsense", "views", "subscribers", "youtube income", "grow channel",
    "content plan youtube", "youtube analytics", "youtube revenue", "youtube strategy",
    "youtube growth", "content creator youtube", "youtube algorithm",
]

YOUTUBE_PROMPT = """You are helping promote a FREE spreadsheet called "YouTube Analytics Tracker" that helps YouTubers track views, revenue, RPM, CTR, and subscriber growth — all in one place — so they can make data-driven decisions and grow faster.

Template link: {template_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Connect to the YouTube angle: tracking the right metrics is what separates growing channels from stuck ones
- Reference something specific from the tweet
- Include the template link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds insight about tracking metrics to grow]
OPTION_C: [starts with a genuine question about their channel metrics, then offers the resource]"""

# ── Topic 4: TikTok Growth & Monetization ────────────────────────────────────
TIKTOK_QUERIES = [
    "how to grow tiktok account lang:en",
    "tiktok monetization strategy lang:en",
    "tiktok content plan schedule lang:en",
    "make money tiktok creator lang:en",
    "tiktok creator tips more views lang:en",
]

TIKTOK_INTENT = [
    "tiktok", "tik tok", "tiktok creator", "tiktok monetize", "tiktok income",
    "creator fund", "tiktok views", "tiktok followers", "tiktok content",
    "tiktok strategy", "tiktok growth", "tiktok plan", "tiktok algorithm",
    "tiktok posting", "tiktok schedule",
]

TIKTOK_PROMPT = """You are helping promote a FREE spreadsheet called "TikTok Content Planner" that helps TikTok creators plan their content calendar, track video performance, and build a consistent posting strategy to grow their audience and monetize faster.

Template link: {template_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Connect to the TikTok angle: consistency + tracking what works is how accounts break through
- Reference something specific from the tweet
- Include the template link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds insight about content planning for TikTok growth]
OPTION_C: [starts with a genuine question about their posting strategy, then offers the resource]"""

# ── Topic 5: Etsy / Shopify / Amazon Product Sellers ─────────────────────────
PRODUCT_QUERIES = [
    "etsy seller pricing margin profit lang:en",
    "how to price products etsy shopify lang:en",
    "product profit margin calculator lang:en",
    "etsy selling tips profitable product launch lang:en",
    "shopify amazon product margin break even lang:en",
]

PRODUCT_INTENT = [
    "etsy", "shopify", "amazon seller", "product margin", "profit margin",
    "pricing", "price my product", "break even", "cost of goods", "cogs",
    "selling product", "product launch", "inventory", "platform fees",
    "etsy seller", "etsy shop", "unit economics", "sell on etsy",
    "sell on shopify", "is this profitable",
]

PRODUCT_PROMPT = """You are helping promote a FREE spreadsheet called "Product Profit Calculator" that helps Etsy, Shopify, and Amazon sellers calculate their real profit per unit, actual margin %, and break-even point — before they commit to inventory.

Template link: {template_url}

Tweet: "{tweet_text}"
Author: @{username}

Write exactly 3 Twitter reply variations. Each must:
- Feel natural and human, NOT like an ad
- Connect to the seller angle: most people price by feel and discover the margin problem months later — after inventory, ads, and time are committed
- Reference something specific from the tweet
- Include the template link organically
- Include the word FREE in uppercase near the link
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)
- Be in English
- Be under 250 characters

Format EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2 sentences, adds insight about knowing your margin before launching]
OPTION_C: [starts with a genuine question about their product margins or pricing, then offers the resource]"""

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
def generate_replies(prompt_template, tweet_text, username, template_url):
    prompt = prompt_template.format(
        template_url=template_url,
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
        a = lines.get("OPTION_A", f"Built a FREE spreadsheet that helps with exactly this: {template_url}")
        b = lines.get("OPTION_B", f"Most people don't realize how much this is costing them. FREE tool: {template_url}")
        c = lines.get("OPTION_C", f"Have you actually tracked this? FREE spreadsheet: {template_url}")
        return a, b, c
    except Exception as e:
        print(f"[OpenAI] Error: {e}")
        return (
            f"Same here — built a FREE spreadsheet to fix this: {template_url}",
            f"Most people underestimate this by 2-3x. FREE tool: {template_url}",
            f"Have you ever tracked this properly? FREE spreadsheet: {template_url}",
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
def scan(client, conn, queries, intent_words, prompt_template, label, template_url):
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
            replies  = generate_replies(prompt_template, tweet_text, username, template_url)
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

    total  = scan(client, conn, SUBSCRIPTION_QUERIES, SUBSCRIPTION_INTENT, SUBSCRIPTION_PROMPT, "Subscriptions", URL_LEAK_DETECTOR)
    total += scan(client, conn, FINANCE_QUERIES,      FINANCE_INTENT,      FINANCE_PROMPT,      "Finance",       URL_BUDGET_TRACKER)
    total += scan(client, conn, YOUTUBE_QUERIES,      YOUTUBE_INTENT,      YOUTUBE_PROMPT,      "YouTube",       URL_YOUTUBE)
    total += scan(client, conn, TIKTOK_QUERIES,       TIKTOK_INTENT,       TIKTOK_PROMPT,       "TikTok",        URL_TIKTOK)
    total += scan(client, conn, PRODUCT_QUERIES,      PRODUCT_INTENT,      PRODUCT_PROMPT,      "Products",      URL_PROFIT)

    conn.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Listo — {total} leads nuevos")

if __name__ == "__main__":
    run()
