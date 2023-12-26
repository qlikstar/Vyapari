import datetime
from datetime import date
from datetime import datetime
from typing import List

from kink import inject
from peewee import fn

from core.db_tables import OrderEntity, PositionEntity, StockEntity, AccountEntity, db
from core.logger import logger


@inject
class Database(object):

    def __init__(self):
        self.db = db

    def wrap(self, func):
        result = None
        try:
            self.db.connect(reuse_if_open=True)
            result = func()
        except Exception as oex:
            logger.error(f'Failed to connect to DB: {oex}')
            if not self.db.is_closed():
                self.db.close()
            self.db.connect(reuse_if_open=True)
            result = func()
        finally:
            self.db.close()
            return result

    # *** Ping ***
    def ping(self):
        return self.wrap(lambda: AccountEntity.select().limit(1))

    # *** Account ****
    def upsert_account(self, run_date, initial_portfolio_value: float, final_portfolio_value: float):
        return self.wrap(lambda: AccountEntity.insert(run_date=run_date,
                                                      initial_portfolio_value=initial_portfolio_value,
                                                      final_portfolio_value=final_portfolio_value,
                                                      created_at=datetime.now(),
                                                      updated_at=datetime.now())
                         .on_conflict(preserve=[AccountEntity.run_date],
                                      update={AccountEntity.final_portfolio_value: final_portfolio_value,
                                              AccountEntity.updated_at: datetime.now()})
                         .execute())

    def get_portfolio_history(self, limit: int = 10) -> List[AccountEntity]:
        return self.wrap(lambda: list(AccountEntity.select().order_by(AccountEntity.created_at.desc()).limit(limit)))

    # *** Orders ****
    def create_order(self, order_id: str, parent_id: str, symbol: str, side: str, order_qty: float, time_in_force: str,
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
        order_object = self.wrap(lambda: insert_stmt.execute())
        return order_object

    def update_order(self, order_id: str, updated_stop_price: float, filled_avg_price: float, filled_qty: float,
                     hwm: float,
                     replaced_by: str, extended_hours: bool, status: str,
                     failed_at: datetime, filled_at: datetime, canceled_at: datetime,
                     expired_at: datetime, replaced_at: datetime):
        self.wrap(lambda: OrderEntity.update(updated_stop_price=updated_stop_price,
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

    def get_open_orders(self) -> List[OrderEntity]:
        return self.wrap(lambda:
                         OrderEntity.select().where(
                             ~(OrderEntity.status << ['canceled', 'rejected', 'filled', 'replaced'])))

    def get_all_orders(self, for_date: date) -> List[OrderEntity]:
        return self.wrap(lambda: OrderEntity
                         .select()
                         .where(~(OrderEntity.status << ['canceled', 'rejected']),
                                OrderEntity.updated_at.day == for_date.day,
                                OrderEntity.updated_at.month == for_date.month,
                                OrderEntity.updated_at.year == for_date.year)
                         .order_by(OrderEntity.symbol.asc(), OrderEntity.created_at.asc()))

    def get_all_filled_orders_for_date(self, for_date=date.today()) -> List[OrderEntity]:
        return self.wrap(lambda: OrderEntity
                         .select()
                         .where(OrderEntity.filled_at.day == for_date.day,
                                OrderEntity.filled_at.month == for_date.month,
                                OrderEntity.filled_at.year == for_date.year)
                         .filter(OrderEntity.status == 'filled')
                         .order_by(OrderEntity.symbol.asc(), OrderEntity.filled_at.asc()))

    def get_by_id(self, order_id: str) -> OrderEntity:
        return self.wrap(lambda: OrderEntity.get_by_id(order_id))

    def get_latest_filled_dt(self, symbol: str) -> datetime:
        return self.wrap(lambda: OrderEntity.select(fn.MAX(OrderEntity.filled_at))
                         .where(OrderEntity.symbol == symbol).scalar())

    def get_by_parent_id(self, parent_order_id: str) -> List[OrderEntity]:
        return self.wrap(lambda: list(OrderEntity.select()
                                      .where(~(OrderEntity.status << ['canceled', 'rejected']))
                                      .where(OrderEntity.parent_id == parent_order_id)))

    def list_orders(self, skip: int = 0, limit: int = 100) -> List[OrderEntity]:
        return self.wrap(lambda: list(OrderEntity.select().offset(skip).limit(limit)))

    def delete_order(self, order_id: str):
        return self.wrap(lambda: OrderEntity.delete().where(OrderEntity.id == order_id).execute())

    # *** Positions ****
    def get_position(self, symbol: str):
        return self.wrap(lambda: PositionEntity.select().filter(PositionEntity.symbol == symbol)
                         .order_by(PositionEntity.run_date.desc()).first())

    def list_todays_positions(self):
        return self.wrap(lambda: list(PositionEntity.select()
                                      .filter(PositionEntity.run_date == datetime.date(datetime.today()))
                                      .offset(0).limit(10)))

    def delete_position(self, position_id: int):
        return self.wrap(lambda: PositionEntity.delete().where(PositionEntity.id == position_id).execute())

    def create_position(self, run_date, symbol: str, side: str, qty: int, entry_price: float,
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
        self.wrap(lambda: position_object.save())
        return position_object

    def upsert_position(self, run_date, symbol: str, side: str, qty: int, entry_price: float,
                        market_price: float, lastday_price: float):
        return self.wrap(lambda: PositionEntity.insert(run_date=run_date,
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
    def create_stock(self, symbol: str, timeframe: str, ohlcv_at: datetime, open: float,
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
        self.wrap(lambda: stock_object.save())
        return stock_object

    def get_stock_data(self, symbol: str, timeframe: str, from_time: datetime, to_time: datetime) -> List[StockEntity]:
        return self.wrap(lambda: list(StockEntity.select()
                                      .filter(StockEntity.symbol == symbol, StockEntity.timeframe == timeframe)
                                      .between(from_time, to_time)
                                      .order_by(StockEntity.ohlcv_at)))
