import os
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID") # Ссылка или ID вашего закрытого канала

@app.get("/")
async def root():
    return {"status": "Payment Bot is running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # 1. Обработка обычных сообщений (Команда /start)
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            welcome_text = (
                "Привет! Добро пожаловать в AI Uzbekistan. 🇺🇿\n\n"
                "В нашем основном канале мы делимся бесплатными новостями.\n"
                "Но если вы хотите получить доступ к <b>VIP-клубу</b> с секретными инструкциями, "
                "платными нейросетями и закрытыми гайдами — подписывайтесь!\n\n"
                "Стоимость доступа: <b>50 Telegram Stars 🌟</b>"
            )
            # Отправляем кнопку для оплаты
            send_invoice(chat_id)
            send_message(chat_id, welcome_text)

    # 2. Обработка запроса на оплату (Pre-Checkout)
    if "pre_checkout_query" in data:
        chat_id = data["pre_checkout_query"]["id"]
        # Подтверждаем, что мы готовы принять оплату
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery"
        requests.post(url, json={"pre_checkout_query_id": chat_id, "ok": True})

    # 3. Обработка успешной оплаты (Successful Payment)
    if "message" in data and "successful_payment" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        
        # Генерируем одноразовую ссылку в закрытый канал
        invite_link = create_invite_link(chat_id)
        
        success_text = (
            "🎉 <b>Оплата прошла успешно!</b>\n\n"
            "Добро пожаловать в наш VIP-клуб. Вот ваша персональная ссылка для вступления:\n\n"
            f"{invite_link}\n\n"
            "До встречи в закрытом сообществе! 🚀"
        )
        send_message(chat_id, success_text)

    return Response(status_code=200)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def send_invoice(chat_id):
    """Отправляет счет на оплату в Telegram Stars."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": "Доступ в AI Uzbekistan VIP",
        "description": "Доступ к закрытому каналу с секретными AI-инструкциями и инструментами.",
        "payload": "vip_access_payment",
        "provider_token": "", # Для Stars поле оставляем пустым
        "currency": "XTR", # Код валюты для Telegram Stars
        "prices": [{"label": "VIP Access", "amount": 50}] # Цена: 50 Stars
    }
    requests.post(url, json=payload)

def create_invite_link(user_id):
    """Создает одноразовую ссылку в закрытый канал."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    payload = {
        "chat_id": VIP_CHANNEL_ID,
        "member_user_id": user_id,
        "member_limit": 1
    }
    res = requests.post(url, json=payload).json()
    return res.get("result", {}).get("invite_link", "Ошибка создания ссылки")
