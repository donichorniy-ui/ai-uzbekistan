import os
import requests
import json
import feedparser
import google.generativeai as genai
from datetime import datetime

# --- НАСТРОЙКИ ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")

MODEL_NAME = "gemini-3.8-flash"

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://blog.google/technology/ai/rss/"
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def get_ai_adaptation(text):
    # ОБНОВЛЕННЫЙ ПРОМПТ: СТРОГИЕ ЛИМИТЫ ПО ДЛИНЕ
    prompt = f"""
    You are an expert AI journalist for the Uzbekistan market. 
    Analyze the following AI news text and provide a response in STRICT JSON format.
    
    News text: {text}
    
    The JSON must have these fields:
    - title_ru: Catchy title (max 10 words) in Russian
    - title_uz: Catchy title (max 10 words) in Uzbek
    - summary_ru: Very short summary (max 2 short sentences) in Russian
    - summary_uz: Very short summary (max 2 short sentences) in Uzbek
    - benefit_ru: Why this is useful for Uzbekistan (max 1 short sentence) in Russian
    - benefit_uz: Why this is useful for Uzbekistan (max 1 short sentence) in Uzbek
    - image_prompt: High-quality cinematic English prompt for AI image generator (max 15 words).
    
    IMPORTANT: Keep all texts very concise to fit in a Telegram caption.
    Return ONLY the JSON.
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Error adapting content: {e}")
        return None

def post_to_telegram(content, image_url, original_url):
    caption = (
        f"<b>{content['title_ru']}</b>\n\n"
        f"{content['summary_ru']}\n\n"
        f"🇺🇿 <b>Почему это важно:</b> {content['benefit_ru']}\n\n"
        f"------------------\n\n"
        f"<b>{content['title_uz']}</b>\n\n"
        f"{content['summary_uz']}\n\n"
        f"🇺🇿 <b>Nima uchun bu muhim:</b> {content['benefit_uz']}\n\n"
        f"🔗 <a href='{original_url}'>Читать оригинал / Aslini o'qish</a>"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        print(f"Request Error: {e}")
        return None

def main():
    print("Starting AI News Curator v2... 🚀")
    
    for feed_url in RSS_FEEDS:
        print(f"Checking feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        # ОГРАНИЧЕНИЕ: Берем только 1 новость из каждого источника для экономии квоты
        for entry in feed.entries[:1]: 
            print(f"Processing: {entry.title}")
            adaptation = get_ai_adaptation(entry.summary if 'summary' in entry else entry.title)
            
            if adaptation:
                image_prompt = adaptation['image_prompt'].replace(" ", "%20")
                image_url = f"https://image.pollinations.ai/prompt/{image_prompt}?width=1024&height=1024&nologo=true"
                
                result = post_to_telegram(adaptation, image_url, entry.link)
                
                if result and result.get("ok"):
                    print(f"Successfully posted: {entry.title}")
                else:
                    error_msg = result.get("description", "Unknown error") if result else "No response"
                    print(f"FAILED to post: {entry.title} | ERROR: {error_msg}")
            else:
                print(f"Could not adapt news: {entry.title}")

    print("Automation finished! ✅")

if __name__ == "__main__":
    main()
