from datetime import datetime

from kink import inject, di

from core.database import Database
from services.broker_service import Broker


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
