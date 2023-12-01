import logging
import time
from random import randint
from typing import List
from urllib.parse import urlparse

import requests
from kink import inject, di
from requests import ConnectTimeout, HTTPError, ReadTimeout, Timeout

from services.data_service import DataService

logger = logging.getLogger(__name__)


@inject
class WatchList(object):

    def __init__(self):
        self.data_service: DataService = di[DataService]

    def get_universe(self, volume_gt: int, beta_gt: float, price_gt=20, price_lt=1000, limit=5000) -> List[str]:

        all_stocks_df = self.data_service.screen_stocks(volume_gt=volume_gt, price_gt=price_gt, price_lt=price_lt,
                                                        beta_gt=beta_gt, limit=limit)
        all_stocks = list(all_stocks_df['symbol'])
        all_stocks.extend(get_high_vol_etfs())
        all_stocks.extend(get_high_vol_stocks())
        print(f"All stocks: {all_stocks}")
        return list(set(all_stocks))

    def get_nasdaq_buy_stocks(self):
        no_of_stocks = 4000
        stocks_type = ["mega", "large", "mid"]
        recommendation_type = ["strong_buy", "buy"] #, "sell", "strong_sell"
        nasdaq_url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true"
        nasdaq_api_url = "&".join([nasdaq_url, "=".join(["limit", str(no_of_stocks)]),
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
            # TODO: colorama
            print('NASDAQ CONNECTION ERROR: {}'.format(e))
            time.sleep(randint(2, 5))
            self.get_nasdaq_buy_stocks()


def get_high_vol_etfs() -> list[str]:
    return list(
        {'ARKF', 'ARKG', 'ARKK', 'ARKW', 'EEM', 'EFA', 'EWZ', 'FXI', 'GDX', 'HYG', 'IAU', 'ICLN', 'IDRV', 'IEF', 'IEMG',
         'IPO', 'IWM', 'JETS', 'KOLD', 'KWEB', 'LIT', 'LQD', 'MSOS', 'PBD', 'PBW', 'QID', 'QQQ', 'SCHA', 'SDS', 'SLV',
         'SMOG', 'SOXL', 'SOXS', 'SPXU', 'SPY', 'SQQQ', 'TAN', 'TLT', 'TNA', 'TQQQ', 'TZA', 'UVXY', 'VEA', 'VOO', 'VTI',
         'VUG', 'VWO', 'VXX', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV'})


def get_high_vol_stocks() -> list[str]:
    return list(
        {'AAL', 'AAPL', 'AMD', 'AMZN', 'ANET', 'BABA', 'CHPT', 'CMG', 'COST', 'CVS', 'DBX', 'DIS', 'EDIT',
         'FTEC', 'FTNT', 'GOOG', 'INTC', 'JD', 'LMT', 'M', 'MA', 'MDB', 'META', 'MSFT', 'NDAQ', 'NICE', 'NIO', 'NOA',
         'NOW', 'NVDA', 'NVTA', 'OKTA', 'PANW', 'PAYC', 'PYPL', 'QCOM', 'SEDG', 'SHOP', 'SQ', 'T', 'TCEHY', 'TEAM',
         'TSLA', 'TSM', 'TTWO', 'TWLO', 'V', 'VO', 'WDAY', 'WIX', 'WMT', 'ZM'})
