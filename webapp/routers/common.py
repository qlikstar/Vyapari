from typing import Any

import peewee
from pydantic import BaseModel
from pydantic.utils import GetterDict


class PeeweeGetterDict(GetterDict):
    def get(self, key: Any, default: Any = None):
        res = getattr(self._obj, key, default)
        if isinstance(res, peewee.ModelSelect):
            return list(res)
        return res


class PositionModel(BaseModel):
    symbol: str
    side: str
    qty: int
    entry_price: float
    market_price: float
    lastday_price: float
    created_at: Any

    class Config:
        orm_mode = True
        getter_dict = PeeweeGetterDict
