from abc import ABC
from typing import List

from pandas import DataFrame


class Universe(ABC):

    def get_stocks_df(self, params: {} = None) -> DataFrame:
        pass

    def get_stocks(self, params: {} = None) -> List[str]:
        pass
