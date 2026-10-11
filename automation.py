import os
import requests
import json
import google.generativeai as genai
import urllib.parse
import feedparser # Новая библиотека для чтения новостей

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

genai.configure(api_key=GEMINI_API_KEY)

def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models()]
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for m_name in priority:
            if m_name in available_models:
                return genai.GenerativeModel(m_name)
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        print(f"Error finding model: {e}")
        return None

def fetch_real_news():
    """Собирает настоящие новости из RSS-лент AI-порталов."""
    # Список проверенных источников новостей об ИИ
    feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "https://openai.com/news/rss.xml",
        "https://deepmind.google/blog/rss.xml"
    ]
    
    all_news = []
    for url in feeds:
        try:
            print(f"Fetching from: {url}")
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: # Берем по 3 последние новости из каждого источника
                all_news.append({
                    "title": entry.title,
                    "url": entry.link,
                    "content": entry.get('summary', entry.get('description', ''))
                })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    
    return all_//all_news = all_news[:5] # Ограничиваем до 5 новостей за один запуск, чтобы не спамить
    return all_news

def process_content(model, news_item):
    prompt = f"""
    You are an expert AI curator for Uzbekistan. 
    Translate and adapt the following news item into Russian and Uzbek.
    Original Title: {news_item['title']}
    Original Content: {news_item['content']}
    URL: {news_item['url']}

    Requirements:
    1. Catchy title in RU and UZ.
    2. Summary (2-3 sentences) in RU and UZ.
    3. 'Why this is useful for Uzbekistan' in RU and UZ.
    4. A short, descriptive English prompt for AI image generator.
    
    Return ONLY strict JSON:
    {{
        "title_ru": "...",
        "title_uz": "...",
        "summary_ru": "...",
        "summary_uz": "...",
        "benefit_ru": "...",
        "benefit_uz": "...",
        "image_prompt": "..."
    }}
    """
    response = model.generate_content(prompt)
    text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def post_to_telegram(content):
    encoded_prompt = urllib.parse.quote(content['image_prompt'])
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    message = (
        f"🌟 <b>{content['title_ru']}</b>\n\n{content['summary_ru']}\n\n"
        f"🇺🇿 <b>{content['title_uz']}</b>\n\n{content['summary_uz']}\n\n"
        f"💡 <b>Почему это важно:</b>\n{content['benefit_ru']}\n\n"
        f"🇺🇿 <b>Nima uchun muhim:</b>\n{content['benefit_uz']}\n\n"
        f"🔗 <a href='{content['url']}'>Читать оригинал / Aslini o'qish</a>"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "photo": image_url, "caption": message, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def main():
    print("Starting REAL-TIME AI News Curator... ")
    model = get_best_model()
    if not model: return
    
    raw_news = fetch_news()
    print(f"Found {len(raw_news)} news items.")
    
    for item in raw_news:
        try:
            print(f"Processing: {item['title']}")
            adapted = process_content(model, item)
            adapted['url'] = item['url']
            post_to_telegram(adapted)
            print(f"✅ Posted: {item['title']}")
        except Exception as e:
            print(f"Error processing {item['title']}: {e}")

if __name__ == "__main__":
    main()
