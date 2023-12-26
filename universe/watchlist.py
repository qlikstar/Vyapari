from typing import List

from kink import inject, di

from core.logger import logger
from services.data_service import DataService


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
        logger.info(f"All stocks: {all_stocks}")
        return list(set(all_stocks))


def get_high_vol_etfs() -> list[str]:
    return list(
        {'AIQ', 'ARKF', 'ARKG', 'ARKK', 'ARKW', 'BOTZ', 'EEM', 'EFA', 'EWZ', 'FXI', 'GDX', 'HYG', 'IAU', 'ICLN',
         'IDRV', 'IEF', 'IEMG', 'IPO', 'IWM', 'IXN', 'IYW', 'JETS', 'KOLD', 'KWEB', 'LIT', 'LQD', 'METV', 'MSOS',
         'PBD', 'PBW', 'PNQI', 'QID', 'QQQ', 'ROBT', 'SCHA', 'SDS', 'SLV', 'SMOG', 'SOXL', 'SOXS', 'SPXU', 'SPY',
         'SQQQ', 'TAN', 'TECB', 'TLT', 'TNA', 'TQQQ', 'TZA', 'UVXY', 'VEA', 'VOO', 'VTI', 'VUG', 'VWO', 'VXX', 'XLE',
         'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV'})


def get_high_vol_stocks() -> list[str]:
    return list(
        {'AAL', 'AAPL', 'AMD', 'AMZN', 'ANET', 'BABA', 'CHPT', 'CMG', 'COST', 'CVS', 'DBX', 'DDOG', 'DIS', 'DKNG',
         'EDIT', 'FSLR', 'FTEC', 'FTNT', 'GOOG', 'GRAB', 'INTC', 'JD', 'LMT', 'M', 'MA', 'MDB', 'META', 'MSFT', 'NDAQ',
         'NICE', 'NIO', 'NOA', 'NOW', 'NVDA', 'NVTA', 'OKTA', 'PANW', 'PAYC', 'PYPL', 'QCOM', 'SEDG', 'SHOP', 'SNOW',
         'SOFI', 'SQ', 'T', 'TCEHY', 'TEAM', 'TSLA', 'TSM', 'TTWO', 'TWLO', 'V', 'VO', 'WDAY', 'WIX', 'WMT', 'ZM',
         'ZS'})
