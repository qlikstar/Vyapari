import abc
import asyncio
import logging
from abc import ABC
from kink import inject, di

from core.pushover import Pushover
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


@inject(alias=Notification)
class TelegramNotification(Notification):
    def __init__(self):
        self.telegram: Telegram = di[Telegram]
        self.chat_id = self.telegram.chat_id
        self.bot = self.telegram.bot

        # Backup notification for failures
        self.pushover: Pushover = di[Pushover]

    def notify(self, message):
        logger.info(f"Telegram message sent: {message}")
        asyncio.run(self.telegram.send_message(chat_id=self.chat_id, response=message))

    def err_notify(self, message):
        try:
            logger.error(f"EXCEPTION: {message}")
            asyncio.run(self.telegram.send_message(chat_id=self.chat_id, response=message))
        except Exception as ex:
            logger.error(f"Exception occurred while sending error notification: {ex}")
            self.pushover.err_notify(f"ERR: {message}")
