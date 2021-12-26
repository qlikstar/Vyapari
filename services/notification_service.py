import abc
import json
import os
import time

import requests
import telegram
from colorama import Fore, Style
from kink import inject

PARSE_MODE = telegram.ParseMode.MARKDOWN_V2


class Notification(object):
    @abc.abstractmethod
    def notify(self, message):
        pass


class NoOpNotification(Notification):
    def notify(self, message):
        print("Notifying: {}".format(message))


class Pushover(Notification):
    def __init__(self):
        self.userkey = os.environ.get('PUSHOVER_API_KEY')
        self.token = os.environ.get('PUSHOVER_API_TOKEN')
        self.retry = 3

    def notify(self, message, trying=1):
        print("Notifying: {}".format(message))
        try:
            res = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": self.token,
                "user": self.userkey,
                "message": message
            })
        except ConnectionError:
            print(f"{Fore.RED}WARNING: Message not sent.{message}{Style.RESET_ALL}\n")
            return

        response = json.loads(res.text)
        if response['status'] != 1:
            if trying < self.retry:
                time.sleep(10)
                print("Retrying again ({}) in 10 seconds".format(trying))
                self.notify(message, trying=trying + 1)
            else:
                print(f"{Fore.RED}WARNING: Message not sent.{message}{Style.RESET_ALL}\n")


@inject(alias=Notification)
class Telegram(Notification):
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_API_KEY')
        self.chat_id = os.environ.get('TELEGRAM_USER_CHAT_ID')
        self.bot = telegram.Bot(token=self.token)

    def notify(self, message):
        self.bot.sendMessage(chat_id=self.chat_id, text=self._format_message(message), parse_mode=PARSE_MODE)

    @staticmethod
    def _format_message(message: str):
        to_be_escaped = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for esc in to_be_escaped:
            message = message.replace(esc, f'\\{esc}')

        return f'`{message}`'


