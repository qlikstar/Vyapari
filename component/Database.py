import datetime

from dao.order import create_order


class Database(object):

    @staticmethod
    def create_order(order_id: str, parent_id: str, symbol: str, side: str, order_qty: float, time_in_force: str,
                     order_class: str, order_type: str, trail_percent: float, trail_price: float,
                     initial_stop_price: float, updated_stop_price: float, filled_avg_price: float, filled_qty: float,
                     hwm: float, limit_price: float, replaced_by: str, extended_hours: bool, status: str,
                     failed_at: datetime, filled_at: datetime, canceled_at: datetime, expired_at: datetime,
                     replaced_at: datetime, submitted_at: datetime, created_at: datetime, updated_at: datetime):

        return create_order(order_id, parent_id, symbol, side, order_qty, time_in_force, order_class, order_type,
                            trail_percent, trail_price, initial_stop_price, updated_stop_price, filled_avg_price,
                            filled_qty, hwm, limit_price, replaced_by, extended_hours, status, failed_at, filled_at,
                            canceled_at, expired_at, replaced_at, submitted_at, created_at, updated_at)

