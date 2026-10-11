import os
from fastapi import FastAPI, Request, Response
import requests

app = FastAPI()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.get("/")
async def root():
    return {"status": "AI Bot is running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        if text == "/start":
            send_message(chat_id, "Привет! Добро пожаловать в AI Uzbekistan. Чтобы получить доступ к закрытому каналу, оплатите подписку через Telegram Stars 🌟")
    return Response(status_code=200)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})
