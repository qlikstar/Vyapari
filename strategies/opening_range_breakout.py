from strategies.strategy import Strategy

'''
References:
    1. https://www.youtube.com/watch?v=ULWtFOuUiHw : How To Trade OPENING RANGE BREAKOUT STRATEGY 
       And How To Select Stocks (Intraday Trading)
    2. https://www.youtube.com/watch?v=RZ_4OI_K6Aw: Python implementation 
    
Rules:
    1. when market opens, determine the range of the breakout during the first 15/30 min.
    This range is the breakout range.
    2. In oder to avoid false breakouts, check for volume. It MUST be higher than the recent volumes.
    3. Better chances are there if the closing price is above VWAP 
    4. Make sure Volatility range  > 18
    4. Stop Loss: Use session low as stop loss. However, 2 step Stop loss approach is better.
       a. Sell half of the stocks when the price reaches the upper limit.
       b. Hold rest of the stocks and apply Chandelier stop loss and continue moving
       c. Sell all at 12 PM
'''


class OpeningRangeBreakout(Strategy):

    def get_algo_name(self) -> str:
        return type(self).__name__

    def get_universe(self) -> None:
        pass

    def download_data(self):
        pass

    def define_buy_sell(self, data):
        pass