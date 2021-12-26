import logging
import random
import string

import telegram
from fastapi import APIRouter, Request
from kink import di

from webapp.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

# URL = "https://vyapari.jprq.io/callback"
# TOKEN = "5090781710:AAEiS27UFPnEd3GTbUyhni1zii4JJYk_YJk"

route = APIRouter(
    prefix="/callback",
    tags=["callback"]
)

# bot = telegram.Bot(token=TOKEN)
# s = bot.setWebhook(f'{URL}/{RANDOM_URI}')

telegram_service = TelegramService()
di[TelegramService] = telegram_service


@route.post(f"/{telegram_service.get_uri()}", summary="Callback router for Telegram",
            description="Callback router for Telegram")
async def callback(request: Request):
    await telegram_service.respond_to_message(request)
    return {"status": "delivered"}
