"""Бот оплаты VIP-клуба «AI Uzbekistan» (Telegram Stars).

Работает на Render командой:  uvicorn bot:app --host 0.0.0.0 --port $PORT

Переменные окружения (Render -> Environment):
  TELEGRAM_BOT_TOKEN  токен бота
  VIP_CHANNEL_ID      числовой ID закрытого канала, вида -1001234567890
  WEBHOOK_SECRET      любая строка из латинских букв и цифр; защищает вебхук от подделки
  ADMIN_CHAT_ID       (необязательно) ваш Telegram ID, чтобы бот писал о сбоях выдачи ссылки
  SUPPORT_CONTACT     (необязательно) например @username, для вопросов по оплате
"""
import hmac
import os
import time

import requests
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT") or "администратору канала"

VIP_PRICE_STARS = 50
INVOICE_PAYLOAD = "vip_access_payment"
INVITE_LIFETIME = 7 * 24 * 3600  # ссылка живёт 7 дней

# Уже обработанные платежи: Telegram может прислать одно событие повторно.
processed_payments = set()

if not WEBHOOK_SECRET:
    print("ВНИМАНИЕ: WEBHOOK_SECRET не задан. Любой, кто знает адрес /webhook, "
          "сможет подделать оплату и получить ссылку в VIP-канал.")


# ---------------------------------------------------------------- Telegram ---
def tg(method, **payload):
    """Вызов Telegram API. Не роняет бота и не пишет токен в логи."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=10
        )
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[tg] {method}: {type(e).__name__}")
        return {"ok": False}
    if not data.get("ok"):
        print(f"[tg] {method} не удался: {data.get('description')}")
    return data


def send_message(chat_id, text):
    tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")


def send_invoice(chat_id):
    """Счёт на оплату в Telegram Stars."""
    tg(
        "sendInvoice",
        chat_id=chat_id,
        title="Доступ в AI Uzbekistan VIP",
        description="Доступ к закрытому каналу с секретными AI-инструкциями и инструментами.",
        payload=INVOICE_PAYLOAD,
        provider_token="",  # для Stars поле остаётся пустым
        currency="XTR",
        prices=[{"label": "VIP Access", "amount": VIP_PRICE_STARS}],
    )


def create_invite_link():
    """Одноразовая ссылка в закрытый канал. Бот должен быть админом канала."""
    data = tg(
        "createChatInviteLink",
        chat_id=VIP_CHANNEL_ID,
        member_limit=1,
        expire_date=int(time.time()) + INVITE_LIFETIME,
        name="VIP payment",
    )
    return (data.get("result") or {}).get("invite_link")


def notify_admin(text):
    print(f"[admin] {text}")
    if ADMIN_CHAT_ID:
        send_message(ADMIN_CHAT_ID, text)


# ------------------------------------------------------------ Обработчики ----
def handle_successful_payment(message, payment):
    if payment.get("invoice_payload") != INVOICE_PAYLOAD:
        return
    charge_id = payment.get("telegram_payment_charge_id")
    if charge_id in processed_payments:
        return
    processed_payments.add(charge_id)

    chat_id = message["chat"]["id"]
    user_id = (message.get("from") or {}).get("id", chat_id)
    # charge_id нужен для возврата Stars, поэтому сохраняем его в логах.
    print(f"[payment] user={user_id} charge_id={charge_id} "
          f"amount={payment.get('total_amount')} {payment.get('currency')}")

    link = create_invite_link()
    if link:
        send_message(
            chat_id,
            "🎉 <b>Оплата прошла успешно!</b>\n\n"
            "Добро пожаловать в наш VIP-клуб. Вот ваша персональная ссылка для вступления "
            "(она одноразовая):\n\n"
            f"{link}\n\n"
            "До встречи в закрытом сообществе! 🚀",
        )
    else:
        send_message(
            chat_id,
            "✅ Оплата получена, но ссылку создать не удалось. "
            f"Напишите {SUPPORT_CONTACT}, и вам пришлют доступ вручную.",
        )
        notify_admin(
            f"⚠️ Оплата получена, но ссылка в VIP-канал не создана. "
            f"user_id={user_id}, charge_id={charge_id}. "
            "Проверьте VIP_CHANNEL_ID и права бота в канале."
        )


def handle_update(update):
    # 1) Telegram спрашивает, можно ли принять оплату. Ответить надо за 10 секунд.
    query = update.get("pre_checkout_query")
    if query:
        if query.get("invoice_payload") == INVOICE_PAYLOAD:
            tg("answerPreCheckoutQuery", pre_checkout_query_id=query["id"], ok=True)
        else:
            tg("answerPreCheckoutQuery", pre_checkout_query_id=query["id"], ok=False,
               error_message="Счёт устарел. Отправьте /start и попробуйте снова.")
        return

    message = update.get("message")
    if not message:
        return

    # 2) Оплата прошла.
    payment = message.get("successful_payment")
    if payment:
        handle_successful_payment(message, payment)
        return

    # 3) Команды (только в личной переписке с ботом).
    if (message.get("chat") or {}).get("type") != "private":
        return
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    command = text.split()[0].split("@")[0].lower() if text else ""

    if command == "/start":
        send_message(
            chat_id,
            "Привет! Добро пожаловать в AI Uzbekistan. 🇺🇿\n\n"
            "В нашем основном канале мы делимся бесплатными новостями.\n"
            "Но если вы хотите получить доступ к <b>VIP-клубу</b> с секретными инструкциями, "
            "платными нейросетями и закрытыми гайдами, оплатите доступ ниже.\n\n"
            f"Стоимость доступа: <b>{VIP_PRICE_STARS} Telegram Stars 🌟</b>",
        )
        send_invoice(chat_id)
    elif command == "/paysupport":
        send_message(
            chat_id,
            "По вопросам оплаты и возврата Stars напишите "
            f"{SUPPORT_CONTACT}. Укажите дату оплаты и, если есть, номер платежа.",
        )


# ------------------------------------------------------------------- Роуты ---
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Payment Bot is running"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if WEBHOOK_SECRET:
        received = request.headers.get("x-telegram-bot-api-secret-token", "")
        if not hmac.compare_digest(received, WEBHOOK_SECRET):
            return Response(status_code=403)
    try:
        update = await request.json()
        # requests - синхронная библиотека, поэтому запускаем в отдельном потоке.
        await run_in_threadpool(handle_update, update)
    except Exception as e:  # noqa: BLE001
        # Всегда отвечаем 200, иначе Telegram будет бесконечно слать то же событие.
        print(f"[webhook] ошибка: {type(e).__name__}: {e}")
    return Response(status_code=200)
