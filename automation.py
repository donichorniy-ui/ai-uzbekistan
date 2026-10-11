import os
import requests
import json
import google.generativeai as genai
import urllib.parse

# Настройки
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

genai.configure(api_key=GEMINI_API_KEY)

def main():
    print("Starting AI News Curator... ")
    
    # Используем модель, которую ТРЕБУЕТ Google в вашей ошибке
    try:
        model = genai.GenerativeModel('gemini-3.8-flash')
        print("✅ Using recommended model: gemini-3.8-flash")
    except Exception as e:
        print(f"❌ Model error: {e}")
        return

    news = [
        {"title": "Ollama 0.3 released", "url": "https://ollama.com/blog/ollama-0.3", "content": "Ollama 0.3 adds support for more models."},
        {"title": "AI in Uzbekistan", "url": "https://example.com/uz", "content": "New LLM for Uzbek language developed."},
    ]

    for item in news:
        try:
            print(f"Processing: {item['title']}")
            prompt = f"Translate to RU and UZ for Uzbekistan: {item['title']} {item['content']}. Return JSON: {{\"title_ru\":\"\",\"title_uz\":\"\",\"summary_ru\":\"\",\"summary_uz\":\"\",\"benefit_ru\":\"\",\"benefit_uz\":\"\",\"image_prompt\":\"\"}}"
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace('```json', '').replace('```', '').strip())
            
            # Генерация картинки
            prompt_enc = urllib.parse.quote(data.get('image_prompt', 'AI technology Uzbekistan'))
            img_url = f"https://image.pollinations.ai/prompt/{prompt_enc}?width=1024&height=1024&nologo=true"
            
            msg = (
                f"🌟 <b>{data['title_ru']}</b>\n\n{data['summary_ru']}\n\n"
                f"🇺🇿 <b>{data['title_uz']}</b>\n\n{data['summary_uz']}\n\n"
                f"💡 {data['benefit_ru']}\n\n"
                f"🔗 <a href='{item['url']}'>Read more</a>"
            )
            
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHANNEL_ID, "photo": img_url, "caption": msg, "parse_mode": "HTML"})
            print(f"✅ Posted: {item['title']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
