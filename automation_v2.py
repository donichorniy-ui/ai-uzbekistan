import html
import json
import os
import re
import sys
import time
import urllib.parse

import feedparser
import requests

# --- НАСТРОЙКИ ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_POSTS_PER_RUN = 3      # максимум постов за один запуск
CANDIDATES_PER_FEED = 3    # сколько свежих новостей пробуем из одного источника
POSTED_FILE = "posted.json"
CAPTION_LIMIT = 1024       # лимит Telegram на подпись к фото

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://blog.google/technology/ai/rss/",
]

REQUIRED_KEYS = [
    "title_ru", "title_uz", "summary_ru", "summary_uz",
    "benefit_ru", "benefit_uz", "image_prompt",
]
READ_MORE = "Читать оригинал / Aslini o'qish"


class QuotaError(Exception):
    """Лимит Gemini исчерпан, дальше в этом запуске пробовать бесполезно."""


# --- ЗАПОМИНАЕМ ОПУБЛИКОВАННОЕ ---
def load_posted():
    try:
        with open(POSTED_FILE, encoding="utf-8") as f:
            return list(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_posted(links):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(links[-500:], f, ensure_ascii=False, indent=1)


# --- ТЕКСТ ---
def clean_text(raw, limit=1500):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def visible_len(html_text):
    """Длина текста без HTML-тегов: именно её считает Telegram для подписи."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", html_text)))


# --- GEMINI ---
def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }
    for attempt in range(3):
        r = requests.post(url, json=body, headers=headers, timeout=60)
        if r.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"Gemini 429, жду {wait} c и пробую снова ({attempt + 1}/3)")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise QuotaError("Gemini: лимит запросов исчерпан")


def get_ai_adaptation(title, text):
    prompt = f"""
You are an expert AI journalist for the Uzbekistan market.
Rewrite the following AI news for a Telegram channel and answer in STRICT JSON.

Title: {title}
Text: {text}

JSON fields (all values are plain text, no HTML, no markdown):
- title_ru: catchy title, max 10 words, Russian
- title_uz: catchy title, max 10 words, Uzbek (Latin script)
- summary_ru: max 2 short sentences, Russian
- summary_uz: max 2 short sentences, Uzbek (Latin script)
- benefit_ru: why this matters for Uzbekistan, max 1 short sentence, Russian
- benefit_uz: why this matters for Uzbekistan, max 1 short sentence, Uzbek (Latin script)
- image_prompt: cinematic English prompt for an image generator, max 15 words

Keep every text concise. Return ONLY the JSON object.
"""
    raw = ask_gemini(prompt)
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    if isinstance(data, list) and data:
        data = data[0]
    missing = [k for k in REQUIRED_KEYS if not str(data.get(k, "")).strip()]
    if missing:
        raise ValueError(f"В ответе Gemini нет полей: {missing}")
    return data


# --- КАРТИНКА ---
def fetch_image(image_prompt):
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(image_prompt)
        + "?width=1024&height=1024&nologo=true"
    )
    try:
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return r.content
        print(f"Картинка не получена: HTTP {r.status_code}")
    except Exception as e:
        print(f"Картинка не получена: {e}")
    return None


# --- TELEGRAM ---
def tg(method, **kwargs):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        return requests.post(url, timeout=60, **kwargs).json()
    except Exception as e:
        return {"ok": False, "description": str(e).replace(TELEGRAM_BOT_TOKEN, "***")}


def build_texts(c, link):
    def esc(key):
        return html.escape(str(c[key]).strip())

    link_html = f'<a href="{html.escape(link, quote=True)}">{READ_MORE}</a>'
    full = (
        f"<b>{esc('title_ru')}</b>\n\n"
        f"{esc('summary_ru')}\n\n"
        f"🇺🇿 <b>Почему это важно:</b> {esc('benefit_ru')}\n\n"
        f"──────────\n\n"
        f"<b>{esc('title_uz')}</b>\n\n"
        f"{esc('summary_uz')}\n\n"
        f"🇺🇿 <b>Nima uchun bu muhim:</b> {esc('benefit_uz')}\n\n"
        f"🔗 {link_html}"
    )
    short = f"<b>{esc('title_ru')}</b>\n<b>{esc('title_uz')}</b>\n\n🔗 {link_html}"
    return full, short


def post_to_telegram(c, link, image):
    full, short = build_texts(c, link)

    if image:
        use_short = visible_len(full) > CAPTION_LIMIT
        caption = short if use_short else full
        res = tg(
            "sendPhoto",
            data={"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("news.jpg", image)},
        )
        if res.get("ok"):
            if use_short:  # полный текст не влез в подпись, отправляем следом
                tg("sendMessage", json={
                    "chat_id": TELEGRAM_CHANNEL_ID, "text": full,
                    "parse_mode": "HTML", "disable_web_page_preview": True,
                })
            return True
        print(f"sendPhoto не удался: {res.get('description')}")

    # запасной вариант: без картинки, обычным сообщением
    res = tg("sendMessage", json={
        "chat_id": TELEGRAM_CHANNEL_ID, "text": full, "parse_mode": "HTML",
    })
    if not res.get("ok"):
        print(f"sendMessage не удался: {res.get('description')}")
    return bool(res.get("ok"))


# --- ОСНОВНОЙ ЦИКЛ ---
def main():
    missing = [n for n in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID")
               if not os.getenv(n)]
    if missing:
        print(f"Не заданы секреты: {missing}")
        sys.exit(1)

    print("Starting AI News Curator v2... 🚀")
    posted = load_posted()
    seen = set(posted)
    count = 0

    try:
        for feed_url in RSS_FEEDS:
            if count >= MAX_POSTS_PER_RUN:
                break
            print(f"Checking feed: {feed_url}")
            feed = feedparser.parse(feed_url, agent="Mozilla/5.0 (compatible; AIUzbekistanBot/1.0)")
            fresh = [e for e in feed.entries[:10] if e.get("link") and e.link not in seen]
            if not fresh:
                print("Новых новостей нет")
                continue

            for entry in fresh[:CANDIDATES_PER_FEED]:
                print(f"Processing: {entry.title}")
                try:
                    text = clean_text(entry.get("summary") or entry.title)
                    adaptation = get_ai_adaptation(entry.title, text)
                except QuotaError:
                    raise
                except Exception as e:
                    print(f"Не удалось адаптировать: {e}")
                    continue

                image = fetch_image(adaptation["image_prompt"])
                if post_to_telegram(adaptation, entry.link, image):
                    print(f"Successfully posted: {entry.title}")
                    posted.append(entry.link)
                    seen.add(entry.link)
                    count += 1
                    time.sleep(3)
                    break
                print(f"FAILED to post: {entry.title}")
    except QuotaError as e:
        print(f"{e}. Останавливаюсь до следующего запуска.")
    finally:
        save_posted(posted)

    print(f"Automation finished! ✅ Опубликовано: {count}")


if __name__ == "__main__":
    main()
