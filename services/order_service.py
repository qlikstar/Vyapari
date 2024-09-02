import time
from datetime import datetime, date, timedelta
from random import randint
from typing import List
from uuid import UUID

import pytz
from alpaca.common import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading import Order, OrderRequest, OrderSide, OrderType, TimeInForce, OrderClass, TakeProfitRequest, \
    StopLossRequest, Position, TrailingStopOrderRequest, MarketOrderRequest, Clock
from kink import inject, di

from core.broker import AlpacaBroker
from core.database import Database
from core.db_tables import OrderEntity
from core.logger import logger
from services.notification_service import Notification

timezone = pytz.timezone('America/Los_Angeles')


@inject
class OrderService(object):

    def __init__(self):
        self.api: TradingClient = di[AlpacaBroker].get_instance()
        self.db: Database = di[Database]
        self.notification: Notification = di[Notification]

    # TODO: Do not use until multithreading is implemented
    def await_market_open(self) -> None:
        while not self.is_market_open():
            logger.info("{} waiting for market to open ... ".format(datetime.today().ctime()))
            time.sleep(60)
        logger.info("{}: Market is open ! ".format(datetime.today().ctime()))

    # TODO: Do not use until multithreading is implemented
    def await_market_close(self) -> None:
        while self.is_market_open():
            logger.info("{} waiting for market to close ... ".format(datetime.today().ctime()))
            time.sleep(60)
        logger.info("{}: Market is closed now ! ".format(datetime.today().ctime()))

    def is_tradable(self, symbol: str) -> bool:
        try:
            return self.api.get_asset(symbol).tradable
        except Exception as ex:
            logger.info(f"Cannot find symbol: {symbol}: {ex}")
            return False

    def is_shortable(self, symbol: str) -> bool:
        return self.api.get_asset(symbol).shortable

    def is_market_open(self, check_local=True) -> bool:
        if check_local:
            now = datetime.today()
            military_time_now = (now.hour * 100) + now.minute
            return now.weekday() < 5 and 630 <= military_time_now < 1300
        else:
            clock: Clock = self.api.get_clock()
            return clock.is_open

    def market_buy(self, symbol: str, qty: int):
        return self._place_market_order(symbol, qty, OrderSide.BUY)

    def market_sell(self, symbol: str, qty: int):
        return self._place_market_order(symbol, qty, OrderSide.SELL)

    def _place_market_order(self, symbol, qty, side: OrderSide) -> UUID:
        if self.is_market_open():

            logger.info(f"Placing market order to {side}: {symbol} : {qty}")
            order_data: OrderRequest = MarketOrderRequest(symbol=symbol, qty=qty, side=side,
                                                          time_in_force=TimeInForce.GTC)

            try:
                order: Order = self.api.submit_order(order_data)
                self.notification.notify(f"Market order to {side}: {qty} shares of {symbol} placed")
                self._save_order(order)
                return order.id
            except APIError as api_error:
                self.notification.err_notify(f"Market order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")
        else:
            logger.info(f"{side} Order could not be placed ...Market is NOT open.. !")

    def place_limit_order(self, symbol: str, side: str, qty: int, limit_price: float) -> List[OrderEntity]:
        logger.info("Placing limit order to {}: {} shares of {}".format(side, qty, symbol))
        if self.is_market_open():
            order_data: OrderRequest = OrderRequest(symbol=symbol, qty=qty, side=side,
                                                    type=OrderType.LIMIT,
                                                    time_in_force=TimeInForce.GTC,
                                                    limit_price=limit_price
                                                    )

            try:
                order: Order = self.api.submit_order(order_data)
                logger.info(f"Limit order to {side}: {qty} shares of {symbol} placed @ {limit_price}")
                return self._save_order(order)
            except APIError as api_error:
                self.notification.err_notify(f"Bracket order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")

        else:
            logger.info(f"Order to {side} could not be placed ...Market is NOT open.. !")

    def place_bracket_order(self, symbol: str, side: str, qty: int,
                            stop_loss: float, take_profit: float) -> List[OrderEntity]:
        logger.info("Placing bracket order to {}: {} shares of {}".format(side, qty, symbol))
        if self.is_market_open():
            order_data: OrderRequest = OrderRequest(symbol=symbol, qty=qty, side=side,
                                                    type=OrderType.MARKET,
                                                    time_in_force=TimeInForce.GTC,
                                                    order_class=OrderClass.BRACKET,
                                                    take_profit=TakeProfitRequest(take_profit=take_profit),
                                                    stop_loss=StopLossRequest(stop_loss=stop_loss)
                                                    )

            try:
                order: Order = self.api.submit_order(order_data)
                logger.info(f"Bracket order to {side}: {qty} shares of {symbol} placed")
                return self._save_order(order)
            except APIError as api_error:
                self.notification.err_notify(f"Bracket order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")

        else:
            logger.info(f"Order to {side} could not be placed ...Market is NOT open.. !")

    def place_trailing_bracket_order(self, symbol: str, side: OrderSide, qty: int, trail_price: float) -> UUID:

        if self.is_market_open():
            logger.info(f"Placing trailing bracket order with ${trail_price} to {side}: {symbol} : {qty} ")
            count = 10

            order_id = self._place_market_order(symbol, qty, side)
            trailing_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY

            while self.get_order(str(order_id)).status != "filled" and count > 0:
                time.sleep(1)
                count = count - 1
                logger.info(f"Waiting to fill market order... {count} more seconds")

            ts_order_id = self.place_trailing_stop_order(symbol, trailing_side, qty, trail_price)
            logger.info(f"Bracket trailing stop order placed for: {symbol}")
            return ts_order_id
        else:
            logger.info(f"{side} Trailing bracket order could not be placed ...Market is NOT open.. !")

    def place_trailing_stop_order(self, symbol: str, side: str, qty: int, trail_price: float) -> UUID:

        if self.is_market_open():
            order_data: OrderRequest = TrailingStopOrderRequest(symbol=symbol, qty=qty, side=side,
                                                                type=OrderType.TRAILING_STOP,
                                                                time_in_force=TimeInForce.GTC,
                                                                trail_price=trail_price
                                                                )
            try:
                order = self.api.submit_order(order_data)
                logger.info(f"{symbol}: Trailing stop order submitted : {order.id}")
                self._save_order(order)
                return order.id
            except APIError as api_error:
                self.notification.err_notify(f"Trailing stop order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
        else:
            logger.info(f"{side} Trailing stop order could not be placed ...Market is NOT open.. !")

    def get_order(self, order_id: str):
        return self.update_saved_order(order_id)

    def cancel_order(self, order_id: str):
        try:
            return self.api.cancel_order_by_id(order_id)
        except APIError as api_error:
            self.notification.err_notify(f"Order Id: {order_id} could not be cancelled: {api_error}")

    def close_all(self):
        if self.is_market_open():
            self.update_all_open_orders()

            # Close all open orders
            logger.info("Closing all open orders ...")
            try:
                self.api.cancel_orders()
                time.sleep(randint(1, 3))
            except APIError as api_error:
                self.notification.err_notify(f"Could not cancel all open orders: {api_error}")

            # Get all open positions
            positions: List[Position] = []
            logger.info("Getting all open positions ...")
            try:
                positions: List[Position] = self.api.get_all_positions()
            except APIError as api_error:
                self.notification.err_notify(f"Could not cancel all open orders: {api_error}")

            # Close all open positions
            logger.info("Closing all open positions ...")
            for position in positions:
                if position.side == 'long':
                    self.market_sell(position.symbol, abs(int(position.qty)))
                else:
                    self.market_buy(position.symbol, abs(int(position.qty)))
            self.update_all_open_orders()

        else:
            logger.info("Could not cancel open orders ...Market is NOT open.. !")

    def get_open_orders(self) -> List[OrderEntity]:
        return list(self.db.get_open_orders())

    def get_all_todays_orders(self) -> List[OrderEntity]:
        return list(self.db.get_all_orders(date.today()))

    def get_all_orders(self, for_date: date) -> List[OrderEntity]:
        return list(self.db.get_all_orders(for_date))

    def get_all_filled_orders_today(self) -> List[OrderEntity]:
        day_number = date.today().isoweekday()
        if day_number > 5:
            return list(self.db.get_all_filled_orders_for_date(date.today() - timedelta(days=day_number - 5)))
        return list(self.db.get_all_filled_orders_for_date(date.today()))

    def update_all_open_orders(self) -> List[Order]:
        logger.info("Updating all open orders ...")
        updated_orders: List[Order] = []
        for order in self.db.get_open_orders():
            updated_orders.append(self.update_saved_order(order.id))
        return updated_orders

    def _save_order(self, order: Order) -> List[OrderEntity]:
        parent_order_id = order.id
        order_qty = self._check_float(order.qty)
        trail_percent = self._check_float(order.trail_percent)
        trail_price = self._check_float(order.trail_price)
        stop_price = self._check_float(order.stop_price)
        filled_avg_price = self._check_float(order.filled_avg_price)
        filled_qty = self._check_float(order.filled_qty)
        hwm = self._check_float(order.hwm)
        limit_price = self._check_float(order.limit_price)

        self.db.create_order(str(order.id), str(parent_order_id), order.symbol, order.side, order_qty,
                             order.time_in_force,
                             order.order_class, order.type, trail_percent, trail_price, stop_price, stop_price,
                             filled_avg_price, filled_qty, hwm, limit_price, str(order.replaced_by),
                             order.extended_hours,
                             order.status, self._pst(order.failed_at), self._pst(order.filled_at),
                             self._pst(order.canceled_at), self._pst(order.expired_at), self._pst(order.replaced_at),
                             self._pst(order.submitted_at), self._pst(order.created_at), self._pst(order.updated_at))

        if order.legs is not None:
            for leg in order.legs:
                order_qty = self._check_float(leg.qty)
                trail_percent = self._check_float(leg.trail_percent)
                trail_price = self._check_float(leg.trail_price)
                stop_price = self._check_float(leg.stop_price)
                filled_avg_price = self._check_float(leg.filled_avg_price)
                filled_qty = self._check_float(leg.filled_qty)
                hwm = self._check_float(leg.hwm)
                limit_price = self._check_float(leg.limit_price)

                self.db.create_order(str(leg.id), str(parent_order_id), leg.symbol, leg.side, order_qty,
                                     leg.time_in_force,
                                     leg.order_class, leg.type, trail_percent, trail_price, stop_price, stop_price,
                                     filled_avg_price, filled_qty, hwm, limit_price, str(leg.replaced_by),
                                     leg.extended_hours, leg.status, self._pst(leg.failed_at), self._pst(leg.filled_at),
                                     self._pst(leg.canceled_at), self._pst(leg.expired_at), self._pst(leg.replaced_at),
                                     self._pst(leg.submitted_at), self._pst(leg.created_at), self._pst(leg.updated_at))

        logger.info(f"Saved order id: {parent_order_id}")
        return self.db.get_by_parent_id(str(parent_order_id))

    def update_saved_order(self, order_id: str) -> Order:
        order = self.api.get_order_by_id(order_id)

        updated_stop_price = self._check_float(order.stop_price)
        filled_avg_price = self._check_float(order.filled_avg_price)
        filled_qty = self._check_float(order.filled_qty)
        hwm = self._check_float(order.hwm)
        self.db.update_order(order_id, updated_stop_price, filled_avg_price, filled_qty, hwm, str(order.replaced_by),
                             order.extended_hours, order.status, self._pst(order.failed_at), self._pst(order.filled_at),
                             self._pst(order.canceled_at), self._pst(order.expired_at), self._pst(order.replaced_at))

        logger.info(f"Updated order id: {order.id}")
        return order

    @staticmethod
    def _check_float(value):
        return 0.00 if value is None else float(value)

    @staticmethod
    def _pst(timestamp):
        if timestamp is None:
            return None
        ts = timestamp.astimezone(timezone)
        return datetime.fromtimestamp(ts.timestamp())
