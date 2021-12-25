from kink import di

from customscripts.Resistance import Resistance
from utils.notification import NoOpNotification, Notification

di[Notification] = NoOpNotification()


# stock = input("Enter the stock symbol : ")
# algo = DarvasBox(stock, 252)
# algo.populate_results()


stock = input("Enter the stock symbol : ")
algo = Resistance(stock, 252)
algo.populate_results()
