from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, BaseSettings
from typing import Optional
import httpx

# Завантаження налаштувань з файлу .env
class Settings(BaseSettings):
    my_secret_token: str
    telegram_bot_token: str

    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI()

# Оновлена модель, де chat_id та text є обов'язковими полями
class TelegramMessage(BaseModel):
    chat_id: int
    text: str
    parse_mode: Optional[str] = None

TELEGRAM_SEND_MESSAGE_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

@app.post("/webhook/{token}")
async def webhook(token: str, message: TelegramMessage, response: Response):
    # Перевірка токена
    if token != settings.my_secret_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Перетворення даних моделі в словник
    data = message.dict(exclude_unset=True)
    
    # Якщо отримали порожній об’єкт, повертаємо 200 без дій
    if not data:
        return {"detail": "Empty payload received, no action taken."}
    
    # Пересилаємо дані до Telegram Bot API
    async with httpx.AsyncClient() as client:
        telegram_response = await client.post(TELEGRAM_SEND_MESSAGE_URL, json=data)
    
    # Встановлюємо статус відповіді як від Telegram API
    response.status_code = telegram_response.status_code
    
    # Повертаємо JSON-відповідь від Telegram
    return telegram_response.json()
