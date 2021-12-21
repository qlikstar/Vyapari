from customscripts.Resistance import Resistance
from customscripts.DarvasBox import DarvasBox

# stock = input("Enter the stock symbol : ")
# algo = DarvasBox(stock, 252)
# algo.populate_results()


stock = input("Enter the stock symbol : ")
algo = Resistance(stock, 252)
algo.populate_results()
