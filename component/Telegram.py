import logging
import os

import telegram
from kink import inject
from telegram.error import NetworkError

logger = logging.getLogger(__name__)


@inject
class Telegram(object):

    def __init__(self):
        self.url = os.environ.get('TELEGRAM_CALLBACK_URL')
        self.chat_id = os.environ.get('TELEGRAM_USER_CHAT_ID')
        self.bot = telegram.Bot(token=os.environ.get('TELEGRAM_API_KEY'))

    async def send_message(self, chat_id: str, response: str, reply_to_message_id: str = None):

        try:
            self.bot.send_message(chat_id=chat_id, text=self.format_message(response),
                                  reply_to_message_id=reply_to_message_id,
                                  parse_mode=telegram.ParseMode.MARKDOWN_V2)
        except NetworkError as network_err:
            logger.warning(f'Telegram NetworkError: {network_err.message}!')

    @staticmethod
    def format_message(message: str):
        to_be_escaped = ['_', '[', ']', '(', ')', '~', '<', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for esc in to_be_escaped:
            message = message.replace(esc, f'\\{esc}')

        return message

    # def fixed_width_message(self, message: str):
    #     to_be_escaped = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    #     for esc in to_be_escaped:
    #         message = message.replace(esc, f'\\{esc}')
    #
    #     return f'`{message}`'
