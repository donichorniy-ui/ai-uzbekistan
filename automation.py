import os
import requests
import json
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_ai_news():
    return [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models and improved performance."},
        {"title": "New AI research on Uzbek language", "url": "https://example.com/uzbek-ai", "content": "Researchers have developed a new LLM optimized for Uzbek syntax."},
    ]

def process_content(news_item):
    prompt = f"""
    Translate and adapt the following news item into Russian and Uzbek for Uzbekistan audience.
    Title: {news_item['title']}
    Content: {news_item['content']}
    URL: {news_item['url']}
    Return JSON: {{"title_ru": "...", "title_uz": "...", "summary_ru": "...", "summary_uz": "...", "benefit_ru": "...", "benefit_uz": "..."}}
    """
    response = model.generate_content(prompt)
    text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def post_to_telegram(content):
    message = f"🌟 {content['title_ru']}\n\n{content['summary_ru']}\n\n🇺🇿 {content['title_uz']}\n\n{content['summary_uz']}\n\n💡 {content['benefit_ru']}\n\n🔗 Read more: {content['url']}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": message, "parse_mode": "HTML"}
    
    # Теперь мы проверяем ответ от Telegram!
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(f"✅ SUCCESS: News '{content['title_ru']}' posted to channel!")
    else:
        print(f"❌ ERROR: Failed to post news. Telegram responded with {response.status_code}: {response.text}")

def main():
    print("Starting AI News Curator... ")
    raw_news = fetch_ai_news()
    for item in raw_news:
        print(f"Processing: {item['title']}")
        try:
            adapted = process_content(item)
            adapted['url'] = item['url']
            post_to_telegram(adapted)
        except Exception as e:
            print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
