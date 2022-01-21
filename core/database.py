import datetime
import logging
from datetime import datetime
from typing import List

from kink import inject
from peewee import OperationalError

from core.db_tables import OrderEntity, PositionEntity, StockEntity, AccountEntity, db
from datetime import date

logger = logging.getLogger(__name__)


def _open_db_conn():
    try:
        db.connect(reuse_if_open=True)
    except OperationalError as oex:
        logger.error(f'Failed to connect to DB: {oex}')


def _close_db_connection():
    if not db.is_closed():
        db.close()


def wrap(func):
    _open_db_conn()
    res = func
    _close_db_connection()
    return res


@inject
class Database(object):

    # *** Ping ***
    @staticmethod
    def ping():
        return wrap(True)

    # *** Account ****

    @staticmethod
    def upsert_account(run_date, initial_portfolio_value: float, final_portfolio_value: float):
        return wrap(AccountEntity.insert(run_date=run_date,
                                         initial_portfolio_value=initial_portfolio_value,
                                         final_portfolio_value=final_portfolio_value,
                                         created_at=datetime.now(),
                                         updated_at=datetime.now())
                    .on_conflict(preserve=[AccountEntity.run_date],
                                 update={AccountEntity.final_portfolio_value: final_portfolio_value,
                                         AccountEntity.updated_at: datetime.now()})
                    .execute())

    @staticmethod
    def get_portfolio_history(limit: int = 10) -> List[AccountEntity]:
        return list(wrap(AccountEntity.select().order_by(AccountEntity.created_at.desc()).limit(limit)))

    # *** Orders ****

    @staticmethod
    def create_order(order_id: str, parent_id: str, symbol: str, side: str, order_qty: float, time_in_force: str,
                     order_class: str, order_type: str, trail_percent: float, trail_price: float,
                     initial_stop_price: float, updated_stop_price: float, filled_avg_price: float, filled_qty: float,
                     hwm: float, limit_price: float, replaced_by: str, extended_hours: bool, status: str,
                     failed_at: datetime, filled_at: datetime, canceled_at: datetime, expired_at: datetime,
                     replaced_at: datetime, submitted_at: datetime, created_at: datetime, updated_at: datetime):
        insert_stmt = OrderEntity.insert(id=order_id,
                                         parent_id=parent_id,
                                         symbol=symbol,
                                         side=side,
                                         order_qty=order_qty,
                                         time_in_force=time_in_force,
                                         order_class=order_class,
                                         order_type=order_type,
                                         trail_percent=trail_percent,
                                         trail_price=trail_price,
                                         initial_stop_price=initial_stop_price,
                                         updated_stop_price=updated_stop_price,
                                         filled_avg_price=filled_avg_price,
                                         filled_qty=filled_qty,
                                         hwm=hwm,
                                         limit_price=limit_price,
                                         replaced_by=replaced_by,
                                         extended_hours=extended_hours,
                                         status=status,

                                         failed_at=failed_at,
                                         filled_at=filled_at,
                                         canceled_at=canceled_at,
                                         expired_at=expired_at,
                                         replaced_at=replaced_at,
                                         submitted_at=submitted_at,
                                         created_at=created_at,
                                         updated_at=updated_at)
        order_object = wrap(insert_stmt.execute())
        return order_object

    @staticmethod
    def update_order(order_id: str, updated_stop_price: float, filled_avg_price: float, filled_qty: float, hwm: float,
                     replaced_by: str, extended_hours: bool, status: str,
                     failed_at: datetime, filled_at: datetime, canceled_at: datetime,
                     expired_at: datetime, replaced_at: datetime):
        wrap(OrderEntity.update(updated_stop_price=updated_stop_price,
                                filled_avg_price=filled_avg_price,
                                filled_qty=filled_qty,
                                hwm=hwm,
                                replaced_by=replaced_by,
                                extended_hours=extended_hours,
                                status=status,
                                failed_at=failed_at,
                                filled_at=filled_at,
                                canceled_at=canceled_at,
                                expired_at=expired_at,
                                replaced_at=replaced_at)
             .where(OrderEntity.id == order_id)
             .execute())

    @staticmethod
    def get_open_orders() -> List[OrderEntity]:
        return wrap(OrderEntity.select().where(~(OrderEntity.status << ['canceled', 'rejected', 'filled', 'replaced'])))

    @staticmethod
    def get_all_orders(for_date: date) -> List[OrderEntity]:
        return wrap(OrderEntity
                    .select()
                    .where(~(OrderEntity.status << ['canceled', 'rejected']),
                           OrderEntity.updated_at.day == for_date.day,
                           OrderEntity.updated_at.month == for_date.month,
                           OrderEntity.updated_at.year == for_date.year)
                    .order_by(OrderEntity.symbol.asc(), OrderEntity.created_at.asc()))

    @staticmethod
    def get_all_filled_orders_today() -> List[OrderEntity]:
        for_date = date.today()
        return wrap(OrderEntity
                    .select()
                    .where(OrderEntity.filled_at.day == for_date.day,
                           OrderEntity.filled_at.month == for_date.month,
                           OrderEntity.filled_at.year == for_date.year)
                    .filter(OrderEntity.status == 'filled')
                    .order_by(OrderEntity.symbol.asc(), OrderEntity.filled_at.asc()))

    @staticmethod
    def get_by_id(order_id: str) -> OrderEntity:
        return wrap(OrderEntity.select().where(OrderEntity.id == order_id))

    @staticmethod
    def get_by_parent_id(parent_order_id: str) -> List[OrderEntity]:
        return list(wrap(OrderEntity.select()
                    .where(~(OrderEntity.status << ['canceled', 'rejected']))
                    .where(OrderEntity.parent_id == parent_order_id)))

    @staticmethod
    def list_orders(skip: int = 0, limit: int = 100) -> List[OrderEntity]:
        return list(wrap(OrderEntity.select().offset(skip).limit(limit)))

    @staticmethod
    def delete_order(order_id: str):
        return wrap(OrderEntity.delete().where(OrderEntity.id == order_id).execute())

    # *** Positions ****

    @staticmethod
    def get_position(symbol: str):
        return wrap(PositionEntity.select().filter(PositionEntity.symbol == symbol)
                    .order_by(PositionEntity.run_date.desc()).first())

    @staticmethod
    def list_todays_positions():
        return list(wrap(PositionEntity.select()
                         .filter(PositionEntity.run_date == datetime.date(datetime.today()))
                         .offset(0).limit(10)))

    @staticmethod
    def delete_position(position_id: int):
        return wrap(PositionEntity.delete().where(PositionEntity.id == position_id).execute())

    @staticmethod
    def create_position(run_date, symbol: str, side: str, qty: int, entry_price: float,
                        market_price: float, lastday_price: float):
        position_object = PositionEntity(
            run_date=run_date,
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=entry_price,
            market_price=market_price,
            lastday_price=lastday_price,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        wrap(position_object.save())
        return position_object

    @staticmethod
    def upsert_position(run_date, symbol: str, side: str, qty: int, entry_price: float,
                        market_price: float, lastday_price: float):
        return wrap(PositionEntity.insert(run_date=run_date,
                                          symbol=symbol,
                                          side=side,
                                          qty=qty,
                                          entry_price=entry_price,
                                          market_price=market_price,
                                          lastday_price=lastday_price,
                                          created_at=datetime.now(),
                                          updated_at=datetime.now())
                    .on_conflict(preserve=[PositionEntity.run_date, PositionEntity.symbol, PositionEntity.side],
                                 update={PositionEntity.market_price: market_price,
                                         PositionEntity.updated_at: datetime.now()})
                    .execute())

    # *** Stock ****

    @staticmethod
    def create_stock(symbol: str, timeframe: str, ohlcv_at: datetime, open: float,
                     high: float, low: float, close: float, volume: int):
        stock_object = StockEntity(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv_at=ohlcv_at,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            created_at=datetime.now()
        )
        wrap(stock_object.save())
        return stock_object

    @staticmethod
    def get_stock_data(symbol: str, timeframe: str, from_time: datetime, to_time: datetime) -> List[StockEntity]:
        return list(wrap(StockEntity.select()
                         .filter(StockEntity.symbol == symbol, StockEntity.timeframe == timeframe)
                         .between(from_time, to_time)
                         .order_by(StockEntity.ohlcv_at)))
