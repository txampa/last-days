"""
Leak Detector Lead Monitor
Busca posts en TikTok sobre gasto en suscripciones (1000+ views).
Genera 3 replies variados con OpenAI y los envía por Telegram.
Horario: 8h, 11h, 14h, 17h, 20h, 23h (hora España)
"""

import os
import sqlite3
import requests
import time
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
SCRAPECREATORS_KEY = os.environ["SCRAPECREATORS_API_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_KEY         = os.environ["OPENAI_API_KEY"]
GUMROAD_URL        = "https://bravepicks.gumroad.com/l/ysrqd"
DB_PATH            = os.environ.get("DB_PATH", "seen_posts.db")

HEADERS_SC    = {"x-api-key": SCRAPECREATORS_KEY}
HEADERS_OAI   = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}

# ── Palabras clave ────────────────────────────────────────────────────────────
QUERIES = [
    "how much do you spend on subscriptions",
    "too many subscriptions wasting money",
    "subscription audit save money",
    "cancel subscriptions monthly spending",
    "subscription creep spending",
    "forgot about subscriptions paying",
    "cuanto gastas en suscripciones",
    "demasiadas suscripciones ahorro",
]

INTENT_WORDS = [
    "subscri", "suscri", "subscription", "suscripcion",
    "cancel", "cancela", "unsubscri",
    "monthly spend", "monthly cost", "monthly bill",
    "how much do you spend", "cuanto gastas",
    "wasting money", "saving money on",
    "audit", "tracker", "too many apps",
]

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

def is_seen(conn, post_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM seen WHERE post_id=?", (post_id,)
    ).fetchone() is not None

def mark_seen(conn, post_id: str, platform: str):
    conn.execute(
        "INSERT OR IGNORE INTO seen (post_id, platform, seen_at) VALUES (?,?,?)",
        (post_id, platform, datetime.now().isoformat())
    )
    conn.commit()

# ── Filtro de intención ───────────────────────────────────────────────────────
def has_intent(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in INTENT_WORDS)

# ── Claude: generar 3 replies variados ───────────────────────────────────────
def generate_replies(platform: str, content: str) -> tuple[str, str, str]:
    """Genera 3 replies distintos para un post dado usando OpenAI gpt-4o-mini."""
    lang_hint = "Spanish" if any(w in content.lower() for w in ["suscri", "gastas", "ahorro", "mes"]) else "English"

    prompt = f"""You are helping promote a FREE spreadsheet template called "The €1.000 Leak Detector" that helps people audit their monthly subscriptions and find hidden money leaks.

Gumroad link: {GUMROAD_URL}

Platform: {platform}
Post/caption: "{content}"
Reply language: {lang_hint}

Write exactly 3 reply variations. Each must:
- Feel natural and human, NOT like an ad
- Reference something specific from the post (show you read it)
- Include the Gumroad link organically
- NOT start with "Hey!" or "Great post!"
- NOT use emojis excessively (max 1)

Format your response EXACTLY like this (nothing else):
OPTION_A: [short reply, 1 sentence, casual/relatable tone]
OPTION_B: [medium reply, 2-3 sentences, adds a useful stat or insight]
OPTION_C: [starts with a genuine question, then offers the resource]"""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=HEADERS_OAI,
            json={
                "model": "gpt-4o-mini",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]
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
        a = lines.get("OPTION_A", f"I found a free spreadsheet that audits exactly this: {GUMROAD_URL}")
        b = lines.get("OPTION_B", f"Most people underestimate their subscription spend by 2-3x. Free audit: {GUMROAD_URL}")
        c = lines.get("OPTION_C", f"Have you ever counted all your active subscriptions? Free tool: {GUMROAD_URL}")
        return a, b, c
    except Exception as e:
        print(f"[OpenAI] Error: {e}")
        fallback_a = f"Same thing happened to me — I built a free spreadsheet to audit this: {GUMROAD_URL}"
        fallback_b = f"The average person underestimates their subscription spend by $133/month. Free audit sheet: {GUMROAD_URL}"
        fallback_c = f"Have you actually counted all your active subscriptions? Most people are shocked. Free tool: {GUMROAD_URL}"
        return fallback_a, fallback_b, fallback_c

MIN_VIEWS = 1000

# ── TikTok ────────────────────────────────────────────────────────────────────
def search_tiktok(query: str) -> list:
    try:
        resp = requests.get(
            "https://api.scrapecreators.com/v1/tiktok/search/keyword",
            params={"query": query},
            headers=HEADERS_SC,
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json().get("search_item_list", [])
        return [item["aweme_info"] for item in raw if "aweme_info" in item]
    except Exception as e:
        print(f"[TikTok] Error: {e}")
        return []

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(text: str):
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

# ── Mensajes Telegram ─────────────────────────────────────────────────────────
def build_reddit_message(post: dict, replies: tuple) -> str:
    title     = post.get("title", "")
    subreddit = post.get("subreddit", "")
    score     = post.get("score", post.get("ups", 0))
    url       = post.get("url", post.get("permalink", ""))
    if url and not url.startswith("http"):
        url = f"https://www.reddit.com{url}"
    a, b, c = replies
    return (
        f"🟠 <b>Reddit Lead</b> · r/{subreddit} · {score} pts\n"
        f"📝 {title}\n"
        f"🔗 {url}\n\n"
        f"<b>A)</b> <code>{a}</code>\n\n"
        f"<b>B)</b> <code>{b}</code>\n\n"
        f"<b>C)</b> <code>{c}</code>"
    )

def build_tiktok_message(video: dict, replies: tuple) -> str:
    desc   = video.get("desc", "")[:200]
    author = video.get("author", {})
    handle = author.get("unique_id", "") if isinstance(author, dict) else str(author)
    stats  = video.get("statistics", {})
    views  = stats.get("play_count", 0) if isinstance(stats, dict) else 0
    url    = video.get("share_url", f"https://tiktok.com/@{handle}")
    a, b, c = replies
    return (
        f"🎵 <b>TikTok Lead</b> · @{handle} · {views:,} views\n"
        f"📝 {desc}\n"
        f"🔗 {url}\n\n"
        f"<b>A)</b> <code>{a}</code>\n\n"
        f"<b>B)</b> <code>{b}</code>\n\n"
        f"<b>C)</b> <code>{c}</code>"
    )

# ── Motor principal ───────────────────────────────────────────────────────────
def run():
    conn = init_db()
    total_new = 0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando busqueda...")

    for query in QUERIES:

        # ── TikTok ──
        for video in search_tiktok(query):
            vid_id = str(video.get("aweme_id", ""))
            if not vid_id:
                continue

            # Filtro de views mínimas
            stats = video.get("statistics", {})
            views = stats.get("play_count", 0) if isinstance(stats, dict) else 0
            if views < MIN_VIEWS:
                continue

            caption = video.get("desc", "")
            if not has_intent(caption):
                continue
            uid = f"tiktok_{vid_id}"
            if is_seen(conn, uid):
                continue

            replies = generate_replies("TikTok", caption)
            mark_seen(conn, uid, "tiktok")
            send_telegram(build_tiktok_message(video, replies))
            total_new += 1
            print(f"  [TikTok] {views:,}v — {caption[:60]}".encode("ascii", "replace").decode())
            time.sleep(1)

    conn.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Listo — {total_new} leads nuevos")

if __name__ == "__main__":
    run()
