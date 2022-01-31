"""
    This is a combination of Turtle trading and Breakout strategy:
    - Donchian Channel indicator and breakout to determine entry signals. (100 days)
    - Trailing Stop loss of (ATR) of 14 days
    - Do pyramiding: Add to position if the stock reaches (entry + ATR)
    - Do not risk more than 2% of your capital in one stock

    More Rules:
    For Long:
    - In a 100 day period, BUY only if the last 50 days Donchian high (or if higher highs for last 50 days) is broken.
    - The more the better.
    - Exit the strategy if the price closes below the 21-day EMA. There will be plenty of options
    - For a start trade only good stocks: GOOG, TSLA, AMZN, MSFT QQQ etc.
"""