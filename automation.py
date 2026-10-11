import os
import requests
import json
import google.generativeai as genai

# Настройки из секретов GitHub
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")

# Настройка Gemini AI (Используем стабильную модель gemini-pro)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def fetch_ai_news():
    """
    Имитация сбора новостей. В будущем здесь будет настоящий парсер сайтов.
    """
    return [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models and improved performance."},
        {"title": "New AI research on Uzbek language", "url": "https://example.com/uzbek-ai", "content": "Researchers have developed a new LLM optimized for Uzbek syntax."},
        {"title": "Free AI Tools for 2026", "url": "https://example.com/free-tools", "content": "A list of the best free AI tools for productivity and coding in 2026."},
    ]

def process_content(news_item):
    """
    Используем ИИ для перевода и адаптации новости под Узбекистан.
    """
    prompt = f"""
    You are an expert AI curator for Uzbekistan.
    Translate and adapt the following news item into Russian and Uzbek.

    Original Title: {news_item['title']}
    Original Content: {news_item['content']}
    URL: {news_item['url']}

    Requirements:
    1. Create a catchy title in RU and UZ.
    2. Write a summary (2-3 sentences) in RU and UZ.
    3. Add a section 'Why this is useful for Uzbekistan' in RU and UZ.
    4. Format the output as strict JSON.

    JSON Format:
    {{
        "title_ru": "...",
        "title_uz": "...",
        "summary_ru": "...",
        "summary_uz": "...",
        "benefit_ru": "...",
        "benefit_uz": "..."
    }}
    """
    response = model.generate_content(prompt)
    # Очистка ответа от лишних символов markdown (```json ... ```)
    text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def post_to_telegram(content):
    """
    Отправка готового поста в Telegram-канал.
    """
    message = (
        f"🌟 <b>{content['title_ru']}</b>\n\n{content['summary_ru']}\n\n"
        f"🇺🇿 <b>{content['title_uz']}</b>\n\n{content['summary_uz']}\n\n"
        f"💡 <b>Почему это важно:</b>\n{content['benefit_ru']}\n\n"
        f"🇺🇿 <b>Nima uchun muhim:</b>\n{content['benefit_uz']}\n\n"
        f"🔗 <a href='{content['url']}'>Читать оригинал / Aslini o'qish</a>"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": message, "parse_mode": "HTML"}
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"✅ SUCCESS: News '{content['title_ru']}' posted to channel!")
    else:
        print(f"❌ ERROR: Telegram responded with {response.status_code}: {response.text}")

def main():
    print("Starting AI News Curator... ")
    try:
        raw_news = fetch_ai_news()
        for item in raw_news:
            print(f"Processing: {item['title']}")
            try:
                adapted = process_content(item)
                adapted['url'] = item['url']
                post_to_telegram(adapted)
            except Exception as e:
                print(f"Error processing {item['title']}: {e}")
    except Exception as e:
        print(f"Critical System Error: {e}")

if __name__ == "__main__":
    main()
