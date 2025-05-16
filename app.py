from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import httpx

# Завантаження налаштувань з файлу .env
class Settings(BaseSettings):
    my_secret_token: str
    telegram_bot_token: str
    new_user_telegram_group_chat_id: str

    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI()

# Моделі для inline-клавіатури
class InlineKeyboardButton(BaseModel):
    text: str
    url: str

class InlineKeyboardMarkup(BaseModel):
    inline_keyboard: List[List[InlineKeyboardButton]]

# Оновлена модель TelegramMessage із reply_markup
class TelegramMessage(BaseModel):
    chat_id: int
    text: str
    parse_mode: Optional[str] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None

TELEGRAM_SEND_MESSAGE_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request, response: Response):
    # Перевірка токена
    if token != settings.my_secret_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Отримуємо сирий JSON із запиту
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid JSON") from e
    
    # Якщо об’єкт порожній, повертаємо 200 без подальших дій
    if not payload:
        return {"detail": "Empty payload received, no action taken."}
    
    # Спроба валідації payload за допомогою моделі TelegramMessage
    try:
        message = TelegramMessage(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid payload") from e

    # Пересилаємо дані до Telegram Bot API
    async with httpx.AsyncClient() as client:
        telegram_response = await client.post(TELEGRAM_SEND_MESSAGE_URL, json=message.dict(exclude_none=True))

    response.status_code = telegram_response.status_code
    return telegram_response.json()

@app.post("/telegram/update/{token}")
async def telegram_update(token: str, request: Request, response: Response):
    """
    Endpoint для отримання update від Telegram.
    Якщо update містить команду /start (тобто користувач стартував бота),
    то надсилається повідомлення про нового підписника до вказаної групи.
    """
    # Перевірка токена
    if token != settings.my_secret_token:
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        update = await request.json()
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid JSON") from e

    # Перевірка, чи це update з повідомленням
    message_data = update.get("message")
    if message_data:
        text = message_data.get("text", "")
        # Якщо користувач надіслав /start, це може означати, що він підписався
        if text == "/start":
            user = message_data.get("from", {})
            first_name = user.get("first_name", "")
            username = user.get("username", "")
            user_id = user.get("id", "")
            
            # Формування повідомлення для групи
            group_text = (
                f"<b>Новий підписник на чатбота!</b>\n"
                f"ID: {user_id}\n"
                f"Ім'я: {first_name}\n"
                f"Username: {username}"
            )
            
            group_message = TelegramMessage(
                chat_id=settings.new_user_telegram_group_chat_id,
                text=group_text,
                parse_mode="HTML"
            )
            
            async with httpx.AsyncClient() as client:
                telegram_response = await client.post(
                    TELEGRAM_SEND_MESSAGE_URL, json=group_message.dict(exclude_none=True)
                )
            response.status_code = telegram_response.status_code
            return telegram_response.json()

    # Якщо update не містить потрібних даних, нічого не робимо
    return {"detail": "No subscription event detected"}