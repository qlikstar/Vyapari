import logging
import os

import telebot
from kink import inject
from telegram.constants import ParseMode
from telegram.error import NetworkError

logger = logging.getLogger(__name__)


@inject
class Telegram(object):

    def __init__(self):
        self.url = os.environ.get('TELEGRAM_CALLBACK_URL')
        self.chat_id = os.environ.get('TELEGRAM_USER_CHAT_ID')
        self.bot = telebot.TeleBot(os.environ.get('TELEGRAM_API_KEY'))

    def send_message(self, chat_id: str, response: str, reply_to_message_id: str = None):

        formatted_text = f"```\n{response}\n```"
        try:
            self.bot.send_message(chat_id=chat_id, text=formatted_text,
                                  reply_to_message_id=reply_to_message_id,
                                  parse_mode=ParseMode.MARKDOWN_V2)
        except NetworkError as network_err:
            logger.warning(f'Telegram NetworkError: {network_err.message}!')