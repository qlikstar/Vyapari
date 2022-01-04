import json
import logging
import os
import time

import requests
from colorama import Fore, Style
from kink import inject

logger = logging.getLogger(__name__)


@inject
class Pushover(object):
    def __init__(self):
        self.api_key = os.environ.get('PUSHOVER_API_KEY')
        self.token = os.environ.get('PUSHOVER_API_TOKEN')
        self.retry = 3

    def notify(self, message, trying=1):
        logger.info("Notifying: {}".format(message))
        try:
            res = requests.post("https://api.pushover.net/1/messages.json", data={
                "token": self.token,
                "user": self.api_key,
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
