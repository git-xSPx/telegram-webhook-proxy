from fastapi import FastAPI, HTTPException, Response, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import httpx

# Завантаження налаштувань з файлу .env
class Settings(BaseSettings):
    my_secret_token: str
    telegram_bot_token: str

    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI()

# Модель з обов’язковими полями chat_id та text
class TelegramMessage(BaseModel):
    chat_id: int
    text: str
    parse_mode: str = None

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
        telegram_response = await client.post(TELEGRAM_SEND_MESSAGE_URL, json=message.dict())
    
    response.status_code = telegram_response.status_code
    return telegram_response.json()
