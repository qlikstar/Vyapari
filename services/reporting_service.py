import logging
import os
from abc import ABC

import telegram
from fastapi import Request

logger = logging.getLogger(__name__)

PARSE_MODE = telegram.ParseMode.MARKDOWN_V2


class ReportingService(ABC):
    def respond(self, input):
        pass


class TelegramService(ReportingService):

    def __init__(self, uri: str):
        self.token = os.environ.get('TELEGRAM_API_KEY')
        self.url = os.environ.get('TELEGRAM_CALLBACK_URL')
        self.chat_id = os.environ.get('TELEGRAM_USER_CHAT_ID')
        self.uri = uri
        self.bot = telegram.Bot(token=self.token)
        self.bot.set_webhook(f'{self.url}/{self.uri}')

    async def respond(self, request: Request) -> None:
        req_info = await request.json()
        update = telegram.Update.de_json(req_info, self.bot)

        # get the chat_id to be able to respond to the same user
        chat_id = update.message.chat.id
        logger.info(f"chat id : {chat_id}")
        # get the message id to be able to reply to this specific message
        msg_id = update.message.message_id

        # Telegram understands UTF-8, so encode text for unicode compatibility
        command = update.message.text.encode('utf-8').decode().lower()
        logger.info(f"got text message :{command}")

        # here we call our super AI
        # response = "Some *boldtext* and some _italictext_\n" \
        #            "`inline fixed-width code`"

        response = CommandResponse().get_command(command)
        # now just send the message back
        # notice how we specify the chat and the msg we reply to
        self.bot.sendMessage(chat_id=chat_id, text=response, reply_to_message_id=msg_id, parse_mode=PARSE_MODE)

    async def notify(self, message):
        self.bot.sendMessage(chat_id=self.chat_id, text=message, parse_mode=PARSE_MODE)


class CommandResponse(object):
    def get_command(self, command: str):
        default = f"Could not understand: {command}"
        return getattr(self, command.strip("/"), lambda: default)()

    @staticmethod
    def help():
        return "Help to be written"

    @staticmethod
    def health():
        return "check heartbeat and return status"
