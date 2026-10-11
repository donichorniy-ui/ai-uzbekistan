import os
import requests
import json
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

genai.configure(api_key=GEMINI_API_KEY)
# Используем новейшую версию, рекомендованную Google
MODEL_LIST = ['gemini-3.8-flash', 'gemini-1.5-flash', 'gemini-pro']

def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models()]
        for m_name in MODEL_LIST:
            # Приводим к формату models/name если нужно
            full_name = m_name if m_name.startswith('models/') else f'models/{m_name}'
            if full_name in available_models:
                return genai.GenerativeModel(full_name)
        return genai.GenerativeModel(available_models[0])
    except Exception as e:
        print(f"Error finding model: {e}")
        return None

def fetch_news():
    return [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models."},
        {"title": "AI in Uzbekistan", "url": "https://example.com/uz", "content": "New LLM for Uzbek language developed."},
    ]

def main():
    print("Starting AI News Curator... ")
    model = get_best_model()
    if not model:
        print("No model found"); return
    for item in fetch_news():
        try:
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
