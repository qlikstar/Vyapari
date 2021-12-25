import logging

import telegram
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

URL = "https://vyapari.jprq.io/callback"
TOKEN = "5090781710:AAEiS27UFPnEd3GTbUyhni1zii4JJYk_YJk"

route = APIRouter(
    prefix="/callback",
    tags=["callback"]
)

bot = telegram.Bot(token=TOKEN)
s = bot.setWebhook(f'{URL}/{TOKEN}')


@route.post(f"/{TOKEN}", summary="Callback router for Telegram",
            description="Callback router for Telegram")
async def callback(info: Request):
    req_info = await info.json()
    update = telegram.Update.de_json(req_info, bot)

    # get the chat_id to be able to respond to the same user
    chat_id = update.message.chat.id
    # get the message id to be able to reply to this specific message
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    print("got text message :", text)

    # here we call our super AI
    response = "Some *boldtext* and some _italictext_\n" \
               "`inline fixed-width code`"

    # now just send the message back
    # notice how we specify the chat and the msg we reply to
    bot.sendMessage(chat_id=chat_id, text=response, reply_to_message_id=msg_id, parse_mode=telegram.ParseMode.MARKDOWN)

    return 'ok'
