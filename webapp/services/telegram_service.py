import telegram
from kink import inject


@inject
class TelegramService(object):

    def __init__(self):
        self.token = "5090781710:AAEiS27UFPnEd3GTbUyhni1zii4JJYk_YJk"
        self.bot = telegram.Bot(token=self.token)
        self.bot.set_webhook()
        telegram.Telegram()

    def respond_to_message(self, message):
        self.bot.reply_to(message, "Howdy, how are you doing?")
