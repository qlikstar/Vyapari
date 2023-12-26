import time
from enum import Enum
from random import randint
from typing import List
from urllib.parse import urlparse

import requests
from kink import inject
from requests import ConnectTimeout, HTTPError, ReadTimeout, Timeout

from core.logger import logger
from universe.Universe import Universe


class StockType(Enum):
    MEGA = "mega"
    LARGE = "large"
    MID = "mid"
    SMALL = "small"


class RecommendationType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@inject
class NasdaqUniverse(Universe):

    def __init__(self,
                 stock_types: List[StockType] = [StockType.MEGA, StockType.LARGE, StockType.MID],
                 reco_types: List[RecommendationType] = [RecommendationType.BUY, RecommendationType.STRONG_BUY],
                 ):
        self.nasdaq_url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true"
        self.stock_types = stock_types
        self.reco_types = reco_types

    def get_stocks(self, params=None):
        no_of_stocks = 4000
        stocks_type = [s_type.value for s_type in self.stock_types]
        recommendation_type = [r_type.value for r_type in self.reco_types]

        nasdaq_api_url = "&".join([self.nasdaq_url, "=".join(["limit", str(no_of_stocks)]),
                                   "=".join(["marketcap", "|".join(stocks_type)]),
                                   "=".join(["recommendation", "|".join(recommendation_type)])
                                   ])
        # api used by https://www.nasdaq.com/market-activity/stocks/screener
        parsed_uri = urlparse(nasdaq_api_url)
        # stagger requests to avoid connection issues to nasdaq.com
        time.sleep(randint(1, 3))
        headers = {
            'authority': parsed_uri.netloc,
            'method': 'GET',
            'scheme': 'https',
            'path': parsed_uri.path + '?' + parsed_uri.params,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-laguage': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-fetch-dest': 'document',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        }
        try:
            return requests.get(nasdaq_api_url, headers=headers).json()
        except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError) as e:
            logger.warning('NASDAQ CONNECTION ERROR: {}'.format(e))
            time.sleep(randint(2, 5))
            self.get_stocks()

    def get_stocks_df(self, params=None):
        raise NotImplementedError("This function is not implemented yet")