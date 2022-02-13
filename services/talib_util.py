import pandas as pd


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
