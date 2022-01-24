from dataclasses import dataclass
from datetime import datetime
from typing import List

from kink import inject, di

from core.database import Database
from services.broker_service import Broker


@dataclass
class Position:
    symbol: str
    exchange: str
    side: str
    qty: int
    entry_price: float
    current_price: float
    unrealized_profit: float
    unrealized_profit_pc: float
    order_filled_at: datetime


@inject
class PositionService(object):

    def __init__(self):
        self.broker: Broker = di[Broker]
        self.db: Database = di[Database]

    def update_current_positions(self):
        positions = self.broker.get_positions()
        for pos in positions:
            self.db.upsert_position(datetime.date(datetime.today()), pos.symbol, pos.side, pos.qty,
                                    pos.avg_entry_price, pos.current_price, pos.lastday_price)

    def update_and_get_current_positions(self):
        self.update_current_positions()
        return self.db.list_todays_positions()

    def get_position(self, symbol: str):
        return self.db.get_position(symbol)

    def get_all_positions(self):
        return self.broker.get_positions()

    # TODO: merge this method with get_all_positions()
    def get_all_pos(self) -> List[Position]:
        result = []
        for pos in self.broker.get_positions():
            result.append(Position(pos.symbol, pos.exchange, pos.side.upper(),
                                   int(pos.qty), float(pos.avg_entry_price), float(pos.current_price),
                                   float(pos.unrealized_pl), float(pos.unrealized_plpc),
                                   self.db.get_latest_filled_dt(pos.symbol)))
        return result
