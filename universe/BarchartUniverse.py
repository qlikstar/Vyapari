import json
import re
from typing import List

import pandas as pd
import requests
from urllib.parse import unquote

from kink import inject
from pandas import DataFrame

from universe.Universe import Universe

BARCHART_URL = "https://www.barchart.com/stocks/top-100-stocks?orderBy=weightedAlpha&orderDir=desc"
API_URL = ('https://www.barchart.com/proxies/core-api/v1/quotes/get?'
           'list=stocks.us.weighted_alpha.advances&fields=symbol%2CsymbolName%2CweightedAlpha%2CcurrentRankUs'
           'Top100%2CpreviousRank%2ClastPrice%2CpriceChange%2CpercentChange%2ChighPrice1y%2ClowPrice1y%2Cperc'
           'entChange1y%2CtradeTime%2CsymbolCode%2ChasOptions%2CsymbolType&orderBy=weightedAlpha&orderDir=des'
           'c&meta=field.shortName%2Cfield.type%2Cfield.description%2Clists.lastUpdate&hasOptions=true'
           '&page=1&limit=100&raw=1')

HEADERS = {
    'authority': 'www.barchart.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'sec-ch-ua': '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
}
# Define a pattern for extracting key-value pairs
PATTERN_MATCHER = r'(?P<key>[\w-]+)=(?P<value>[^;,]+)'


@inject
class BarchartUniverse(Universe):

    def __init__(self):
        self.cookie_dict = {}

    def make_request(self):
        response = requests.get(BARCHART_URL, headers=HEADERS)
        response_headers = response.headers

        cookie_string = response_headers.get("Set-Cookie", "")
        matches = re.findall(PATTERN_MATCHER, cookie_string)
        self.cookie_dict = dict(matches)
        return self.cookie_dict

    def make_api_request(self):
        self.make_request()
        headers = {
            'authority': 'www.barchart.com',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'cookie': f'laravel_token={self.cookie_dict.get("laravel_token")}; '
                      f'XSRF-TOKEN={self.cookie_dict.get("XSRF-TOKEN")}; '
                      f'laravel_session={self.cookie_dict.get("laravel_session")}; '
                      f'market={self.cookie_dict.get("market")};',
            'referer': 'https://www.barchart.com/stocks/top-100-stocks?orderBy=weightedAlpha&orderDir=desc',
            'sec-ch-ua': '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'x-xsrf-token': unquote(self.cookie_dict.get("XSRF-TOKEN"))
        }

        response = requests.get(API_URL, headers=headers)
        return json.loads(response.text)

    def get_stocks_df(self, params=None) -> DataFrame:
        json_data = self.make_api_request()
        df = pd.DataFrame(json_data['data'])
        df = df.drop("raw", axis=1)
        return df

    def get_stocks(self, params=None) -> List[str]:
        json_data = self.make_api_request()
        return [item['symbol'] for item in json_data['data']]
