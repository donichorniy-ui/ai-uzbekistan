import os
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()

# Настройки
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")  # ID закрытого канала, например -1001234567890


def tg(method, payload):
    """Вызов Telegram Bot API. Возвращает JSON-ответ (или пустой dict при сбое сети)."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        return requests.post(url, json=payload, timeout=10).json()
    except Exception as e:
        print(f"Telegram error in {method}: {str(e).replace(str(BOT_TOKEN), '***')}")
        return {}


@app.get("/")
async def root():
    return {"status": "Payment Bot is running"}


@app.head("/")
async def root_head():
    return Response(status_code=200)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    # 1. Команда /start
    message = data.get("message")
    if message and message.get("text") == "/start":
        chat_id = message["chat"]["id"]
        welcome_text = (
            "Привет! Добро пожаловать в AI Uzbekistan. 🇺🇿\n\n"
            "В нашем основном канале мы делимся бесплатными новостями.\n"
            "Но если вы хотите получить доступ к <b>VIP-клубу</b> с секретными инструкциями, "
            "платными нейросетями и закрытыми гайдами — подписывайтесь!\n\n"
            "Стоимость доступа: <b>50 Telegram Stars 🌟</b>"
        )
        send_message(chat_id, welcome_text)
        send_invoice(chat_id)

    # 2. Подтверждение оплаты (нужно ответить в течение 10 секунд)
    pre_checkout = data.get("pre_checkout_query")
    if pre_checkout:
        tg("answerPreCheckoutQuery", {"pre_checkout_query_id": pre_checkout["id"], "ok": True})

    # 3. Успешная оплата
    if message and "successful_payment" in message:
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        invite_link = create_invite_link(user_id)

        if invite_link:
            success_text = (
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Добро пожаловать в наш VIP-клуб. Вот ваша персональная ссылка для вступления:\n\n"
                f"{invite_link}\n\n"
                "Ссылка одноразовая. До встречи в закрытом сообществе! 🚀"
            )
        else:
            success_text = (
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Но ссылку создать не удалось. Напишите администратору, он выдаст доступ вручную."
            )
        send_message(chat_id, success_text)

    return Response(status_code=200)


def send_message(chat_id, text):
    tg("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})


def send_invoice(chat_id):
    """Отправляет счёт на оплату в Telegram Stars."""
    tg("sendInvoice", {
        "chat_id": chat_id,
        "title": "Доступ в AI Uzbekistan VIP",
        "description": "Доступ к закрытому каналу с секретными AI-инструкциями и инструментами.",
        "payload": "vip_access_payment",
        "provider_token": "",  # Для Stars поле пустое
        "currency": "XTR",  # Код валюты Telegram Stars
        "prices": [{"label": "VIP Access", "amount": 50}],
    })


def create_invite_link(user_id):
    """Создаёт одноразовую ссылку в закрытый канал. Бот должен быть админом канала."""
    res = tg("createChatInviteLink", {
        "chat_id": VIP_CHANNEL_ID,
        "member_limit": 1,
        "name": f"user {user_id}",
    })
    if not res.get("ok"):
        print(f"createChatInviteLink failed: {res.get('description', res)}")
        return None
    return res["result"]["invite_link"]
