import abc
import json
import logging
import os
import time
from abc import ABC

import requests
import telegram
from colorama import Fore, Style
from kink import inject

logger = logging.getLogger(__name__)

PARSE_MODE = telegram.ParseMode.MARKDOWN_V2


class Notification(ABC):
    @abc.abstractmethod
    def notify(self, message):
        pass

    @abc.abstractmethod
    def err_notify(self, message):
        pass


class NoOpNotification(Notification):
    def notify(self, message):
        logger.info("Notifying: {}".format(message))

    def err_notify(self, message):
        logger.error("Notifying: {}".format(message))


class Pushover(Notification):
    def __init__(self):
        self.userkey = os.environ.get('PUSHOVER_API_KEY')
        self.token = os.environ.get('PUSHOVER_API_TOKEN')
        self.retry = 3

    def notify(self, message, trying=1):
        logger.info("Notifying: {}".format(message))
        try:
            res = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": self.token,
                "user": self.userkey,
                "message": message
            })
        except ConnectionError:
            logger.info(f"{Fore.RED}WARNING: Message not sent.{message}{Style.RESET_ALL}\n")
            return

        response = json.loads(res.text)
        if response['status'] != 1:
            if trying < self.retry:
                time.sleep(10)
                logger.info("Retrying again ({}) in 10 seconds".format(trying))
                self.notify(message, trying=trying + 1)
            else:
                logger.info(f"{Fore.RED}WARNING: Message not sent.{message}{Style.RESET_ALL}\n")

    def err_notify(self, message):
        self.notify(message)


@inject(alias=Notification)
class Telegram(Notification):
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_API_KEY')
        self.chat_id = os.environ.get('TELEGRAM_USER_CHAT_ID')
        self.bot = telegram.Bot(token=self.token)

    def notify(self, message):
        self.bot.sendMessage(chat_id=self.chat_id, text=self._format_message(message), parse_mode=PARSE_MODE)

    def err_notify(self, message):
        self.bot.sendMessage(chat_id=self.chat_id, text=self._format_err_message(message), parse_mode=PARSE_MODE)

    def _format_message(self, message: str):
        to_be_escaped = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for esc in to_be_escaped:
            message = message.replace(esc, f'\\{esc}')

        return f'`{message}`'

    def _format_err_message(self, message: str):
        return self._format_message(message)


