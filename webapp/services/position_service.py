from datetime import datetime

from dao.position import list_todays_positions, upsert_position, get_position
from utils.broker import Broker


class PositionService(object):

    def __init__(self, broker: Broker):
        self.broker: Broker = broker

    def update_and_get_current_positions(self):
        positions = self.broker.get_positions()
        for pos in positions:
            upsert_position(datetime.date(datetime.today()), pos.symbol, pos.side, pos.qty, pos.avg_entry_price,
                            pos.current_price, pos.lastday_price)

        return list_todays_positions()

    def get_position(self, symbol: str):
        return get_position(symbol)
