import os
import requests
import json
import google.generativeai as genai

# Настройки из секретов GitHub
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

genai.configure(api_key=GEMINI_API_KEY)

def get_best_model():
    """Автоматически находит рабочую модель Gemini."""
    try:
        available_models = [m.name for m in genai.list_models()]
        # Приоритетные модели
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for m_name in priority:
            if m_name in available_models:
                return genai.GenerativeModel(m_name)
        # Если ничего из приоритетных нет, берем первую доступную
        if available_models:
            return genai.GenerativeModel(available_models[0])
    except Exception as e:
        print(f"Error finding model: {e}")
    return None

def fetch_news():
    """Тестовый набор новостей."""
    return [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models and improved performance."},
        {"title": "AI in Uzbekistan", "url": "https://example.com/uz", "content": "New LLM for Uzbek language developed."},
    ]

def main():
    print("Starting AI News Curator... ")
    model = get_best_model()
    if not model:
        print("❌ CRITICAL ERROR: No accessible Gemini models found."); return
    
    print(f"✅ Using model: {model.model_name}")
    
    for item in fetch_news():
        try:
            print(f"Processing: {item['title']}")
            prompt = f"Translate to RU and UZ for Uzbekistan: {item['title']} {item['content']}. Return JSON: {{\"title_ru\":\"\",\"title_uz\":\"\",\"summary_ru\":\"\",\"summary_uz\":\"\",\"benefit_ru\":\"\",\"benefit_uz\":\"\"}}"
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
            
            msg = (
                f"🌟 <b>{data['title_ru']}</b>\n\n{data['summary_ru']}\n\n"
                f"🇺🇿 <b>{data['title_uz']}</b>\n\n{data['summary_uz']}\n\n"
                f"💡 {data['benefit_ru']}\n\n"
                f"🔗 <a href='{item['url']}'>Read more</a>"
            )
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": TELEGRAM_CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            
            if r.status_code == 200:
                print(f"✅ Posted: {item['title']}")
            else:
                print(f"❌ Telegram Error {r.status_code}: {r.text}")
                
        except Exception as e:
            print(f"Error processing {item['title']}: {e}")

if __name__ == "__main__":
    main()
