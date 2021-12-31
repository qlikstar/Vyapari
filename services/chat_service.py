import logging
import os
from abc import ABC

import telegram
from fastapi import Request
from telegram.error import NetworkError

logger = logging.getLogger(__name__)


class ChatService(ABC):
    def respond(self, inp: str):
        pass


class TelegramService(ChatService):

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

        response = self._format_message(CommandResponse().get_command(command))
        # now just send the message back
        # notice how we specify the chat and the msg we reply to
        await self._send_message(chat_id=chat_id, response=response, reply_to_message_id=msg_id)

    async def _send_message(self, chat_id: str, response: str, reply_to_message_id: str = None):

        try:
            self.bot.send_message(chat_id=chat_id, text=response, reply_to_message_id=reply_to_message_id,
                                  parse_mode=telegram.ParseMode.MARKDOWN_V2)
        except NetworkError as network_err:
            logger.warning(f'Telegram NetworkError: {network_err.message}!')

    @staticmethod
    def _format_message(message: str):
        to_be_escaped = ['_', '[', ']', '(', ')', '~', '<', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for esc in to_be_escaped:
            message = message.replace(esc, f'\\{esc}')

        return message


class CommandResponse(object):
    def get_command(self, command: str):
        default = f"Could not understand: {command}"
        return getattr(self, command.strip("/"), lambda: default)()

    @staticmethod
    def help() -> str:
        return ("*/start:* `Starts the trader`\n"
                "*/stop:* `Stops the trader`\n"
                "*/status:* `Lists all open trades`\n"
                "*/trades [limit]:* `Lists last closed trades (default is 10)`\n"
                "*/profit [<n>]:* `Lists cumulative profit]`\n"
                "*/forcesell :* `Instantly sells the given trade or all trades`\n"
                "*/performance:* `Show performance of each finished trade grouped by stock`\n"
                "*/daily <n>:* `Shows profit or loss per day, over the last n days`\n"
                "*/balance:* `Show account balance`\n"
                "*/reload_config:* `Reload configuration file` \n"
                "*/show_config:* `Show running configuration` \n"
                "*/logs [limit]:* `Show latest logs - defaults to 10` \n"
                "*/help:* `This help message`\n"
                "*/version:* `Show version`")

    @staticmethod
    def health():
        return "check heartbeat and return status"
