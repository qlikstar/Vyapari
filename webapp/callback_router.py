import logging
import random
import string

from fastapi import APIRouter, Request
from kink import di

from services.reporting_service import TelegramService

logger = logging.getLogger(__name__)

URI = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(64))

route = APIRouter(
    prefix="/callback",
    tags=["callback"]
)

telegram_service = TelegramService(URI)
di[TelegramService] = telegram_service


@route.post(f"/{URI}", summary="Callback router for Telegram",
            description="Callback router for Telegram")
async def callback(request: Request):
    await telegram_service.respond(request)
    return {"status": "delivered"}
