import logging
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)


class Trend(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    INDECISIVE = "INDECISIVE"


class TalibUtil:

    @classmethod
    def vwap(cls, df):
        vol = df['volume'].values
        tp = (df['low'] + df['close'] + df['high']).div(3).values
        return df.assign(VWAP=(tp * vol).cumsum() / vol.cumsum())

    @classmethod
    def heikenashi(cls, df):
        heikinashi_df = pd.DataFrame(index=df.index.values, columns=['open', 'high', 'low', 'close'])
        heikinashi_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

        for i in range(len(df)):
            if i == 0:
                heikinashi_df.iat[0, 0] = df['open'].iloc[0]
            else:
                heikinashi_df.iat[i, 0] = (heikinashi_df.iat[i - 1, 0] + heikinashi_df.iat[i - 1, 3]) / 2

        heikinashi_df['high'] = heikinashi_df.loc[:, ['open', 'close']].join(df['high']).max(axis=1)
        heikinashi_df['low'] = heikinashi_df.loc[:, ['open', 'close']].join(df['low']).min(axis=1)

        return heikinashi_df

    @classmethod
    def get_ha_trend(cls, latest_row) -> Trend:

        if latest_row['open'] == latest_row['low'] and latest_row['high'] > latest_row['close']:
            return Trend.BULL
        elif latest_row['open'] == latest_row['high'] and latest_row['low'] < latest_row['close']:
            return Trend.BEAR
        else:
            return Trend.INDECISIVE

    @classmethod
    def check_strong_trend(cls, ha_df, count_of_rows: int) -> Trend:
        result = []
        for i in range(count_of_rows):
            result.append(cls.get_ha_trend(ha_df.iloc[-i]))

        if len(set(result)) == 1:
            return result[0]
        else:
            return Trend.INDECISIVE
