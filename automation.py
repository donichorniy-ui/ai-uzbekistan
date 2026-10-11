import os
import requests
import json
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

genai.configure(api_key=GEMINI_API_KEY)

def get_best_model():
    """Автоматически находит доступную модель для вашего API ключа."""
    try:
        print("Fetching available models from Google...")
        available_models = [m.name for m in genai.list_models()]
        print(f"Available models: {available_models}")
        
        # Приоритетный список моделей
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        
        for model_name in priority:
            if model_name in available_models:
                print(f"✅ Found best model: {model_name}")
                return genai.GenerativeModel(model_name)
        
        # Если приоритетных нет, берем первую попавшуюся, которая поддерживает генерацию контента
        for m in available_//m = genai.GenerativeModel(available_models[0])
        return m
    except Exception as e:
        print(f"❌ Error finding model: {e}")
        return None

def fetch_news():
    return [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models."},
        {"title": "AI in Uzbekistan", "url": "https://example.com/uz", "content": "New LLM for Uzbek language developed."},
    ]

def main():
    print("Starting AI News Curator... ")
    model = get_//model = get_best_model()
    if not model:
        print("❌ CRITICAL ERROR: No accessible models found. Check your API key."); return
    
    for item in fetch_news():
        try:
            print(f"Processing: {item['title']}")
            prompt = f"Translate to RU and UZ for Uzbekistan: {item['title']} {item['content']}. Return JSON: {{\"title_ru\":\"\",\"title_uz\":\"\",\"summary_ru\":\"\",\"summary_uz\":\"\",\"benefit_ru\":\"\",\"benefit_uz\":\"\"}}"
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
            msg = f"🌟 <b>{data['title_ru']}</b>\n\n{data['summary_ru']}\n\n🇺🇿 <b>{data['title_uz']}</b>\n\n{data['summary_uz']}\n\n💡 {data['benefit_ru']}\n\n🔗 <a href='{item['url']}'>Read more</a>"
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            print(f"✅ Posted: {item['title']}")
        except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
