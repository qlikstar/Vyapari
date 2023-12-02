import abc
import json
import logging
import os
import time
from abc import ABC

import requests
from colorama import Fore, Style
from kink import inject, di

from core.telegram import Telegram

logger = logging.getLogger(__name__)


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


@inject  # (alias=Notification)
class PushoverNotification(Notification):
    def __init__(self):
        self.api_key = os.environ.get('PUSHOVER_API_KEY')
        self.token = os.environ.get('PUSHOVER_API_TOKEN')
        self.retry = 3

    def notify(self, message, trying=1):
        logger.info(f"Pushover message being sent: {message}")

        try:
            res = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": self.token,
                "user": self.api_key,
                "monospace": 1,
                "message": message
            })
            res.raise_for_status()  # Raise HTTPError for bad responses
        except requests.RequestException as e:
            logger.info(f"{Fore.RED}WARNING: Message not sent. {message}. {e}{Style.RESET_ALL}\n")
            return

        response = json.loads(res.text)
        if response.get('status') != 1:
            if trying < self.retry:
                time.sleep(10)
                logger.info(f"Retrying again ({trying}) in 10 seconds")
                self.notify(message, trying=trying + 1)
            else:
                logger.info(f"{Fore.RED}WARNING: Message not sent. {message}{Style.RESET_ALL}\n")

    def err_notify(self, message):
        logger.info(f"Pushover ERROR message sent: {message}")
        self.notify(message)


@inject(alias=Notification)
class TelegramNotification(Notification):
    def __init__(self):
        self.telegram: Telegram = di[Telegram]
        self.chat_id = self.telegram.chat_id
        self.bot = self.telegram.bot

    def notify(self, message):
        try:
            self.telegram.send_message(chat_id=self.chat_id, response=message)
        except Exception as ex:
            logger.error(f"Exception occurred while sending error notification: {ex}")
        logger.info(f"Telegram message sent: \n{message}")

    def err_notify(self, message):
        try:
            logger.error(f"EXCEPTION: {message}")
            self.telegram.send_message(chat_id=self.chat_id, response=message)
        except Exception as ex:
            logger.error(f"Exception occurred while sending error notification: {ex}")
