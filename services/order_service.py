import logging
import time
from datetime import datetime, date
from random import randint
from typing import List

import alpaca_trade_api as alpaca_api
from alpaca_trade_api.entity import Order, Position
from alpaca_trade_api.rest import APIError
from kink import inject, di

from core.database import Database
from core.db_tables import OrderEntity
from services.notification_service import Notification

logger = logging.getLogger(__name__)


@inject
class OrderService(object):

    def __init__(self):
        self.api = alpaca_api.REST()
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
        return self.api.get_asset(symbol).tradable

    def is_shortable(self, symbol: str) -> bool:
        return self.api.get_asset(symbol).shortable

    @staticmethod
    def is_market_open() -> bool:
        now = datetime.today()
        military_time_now = (now.hour * 100) + now.minute
        return now.weekday() < 5 and 630 <= military_time_now < 1300

    def market_buy(self, symbol: str, qty: int):
        return self._place_market_order(symbol, qty, "buy")

    def market_sell(self, symbol: str, qty: int):
        return self._place_market_order(symbol, qty, "sell")

    def _place_market_order(self, symbol, qty, side) -> List[OrderEntity]:
        if self.is_market_open():

            logger.info(f"Placing market order to {side}: {symbol} : {qty}")
            try:
                order = self.api.submit_order(symbol, qty, side, "market", "gtc")
                self.notification.notify("Market order to *{}*: *{}* shares of *{}* placed".format(side, qty, symbol))
                return self._save_order(order)
            except APIError as api_error:
                self.notification.err_notify(f"Market rder to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")
        else:
            logger.info(f"{side} Order could not be placed ...Market is NOT open.. !")

    def place_bracket_order(self, symbol: str, side: str, qty: int,
                            stop_loss: float, take_profit: float) -> List[OrderEntity]:
        logger.info("Placing bracket order to {}: {} shares of {}".format(side, qty, symbol))
        if self.is_market_open():
            try:
                order = self.api.submit_order(symbol, qty, side, "market", "gtc",
                                              order_class="bracket",
                                              take_profit={"limit_price": take_profit},
                                              stop_loss={"stop_price": stop_loss})

                self.notification.notify("Bracket order to *{}*: *{}* shares of *{}* placed".format(side, qty, symbol))
                return self._save_order(order)
            except APIError as api_error:
                self.notification.err_notify(f"Bracket order to {side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing bracket order: {ex}")

        else:
            logger.info("Order to {} could not be placed ...Market is NOT open.. !".format(side))

    def place_trailing_bracket_order(self, symbol: str, side: str, qty: int,  trail_percent: float) -> None:
        if self.is_market_open():

            logger.info(f"Placing trailing stop order to {side}: {symbol} : {qty} with {trail_percent}%")
            trailing_side = 'sell' if side == 'buy' else 'buy'

            try:
                self._place_market_order(symbol, qty, side)
                order = self.api.submit_order(symbol, qty, trailing_side, type='trailing_stop',
                                              trail_percent=str(trail_percent), time_in_force='gtc')
                self.notification.notify("Trailing bracket order to *{}*: *{}* shares of *{}* with {}% placed"
                                         .format(trailing_side, qty, symbol, trail_percent))
                self._save_order(order)
            except APIError as api_error:
                # TODO: Handle if one request succeeds and other fails
                self.notification.err_notify(f"Trailing bracket order to {trailing_side}: {qty} shares of {symbol} "
                                             f"could not be placed: {api_error}")
            except Exception as ex:
                logger.error(f"Error while placing trailing bracket order: {ex}")
        else:
            logger.info(f"{side} Trailing bracket order could not be placed ...Market is NOT open.. !")

    def get_order(self, order_id: str) -> OrderEntity:
        return self.db.get_by_id(order_id)

    def close_all(self):
        if self.is_market_open():
            self.update_all_open_orders()

            # Close all open orders
            logger.info("Closing all open orders ...")
            try:
                self.api.cancel_all_orders()
                time.sleep(randint(1, 3))
            except APIError as api_error:
                self.notification.err_notify(f"Could not cancel all open orders: {api_error}")

            # Get all open positions
            positions: List[Position] = []
            logger.info("Getting all open positions ...")
            try:
                positions: List[Position] = self.api.list_positions()
            except APIError as api_error:
                self.notification.err_notify(f"Could not cancel all open orders: {api_error}")

            # Close all open positions
            logger.info("Closing all open positions ...")
            for position in positions:
                if position.side == 'long':
                    self.market_sell(position.symbol, abs(float(position.qty)))
                else:
                    self.market_buy(position.symbol, abs(float(position.qty)))
            self.update_all_open_orders()

        else:
            logger.info("Could not cancel open orders ...Market is NOT open.. !")

    def get_open_orders(self) -> List[OrderEntity]:
        return list(self.db.get_open_orders())

    def get_all_todays_orders(self) -> List[OrderEntity]:
        return list(self.db.get_all_orders(date.today()))

    def get_all_orders(self, for_date: date) -> List[OrderEntity]:
        return list(self.db.get_all_orders(for_date))

    def get_all_filled_orders_ever(self) -> List[OrderEntity]:
        return list(self.db.get_all_filled_orders_today())

    def update_all_open_orders(self) -> None:
        logger.info("Updating all open orders ...")
        for order in self.db.get_open_orders():
            self._update_saved_order(order.id)

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

        self.db.create_order(order.id, parent_order_id, order.symbol, order.side, order_qty, order.time_in_force,
                             order.order_class, order.type, trail_percent, trail_price, stop_price, stop_price,
                             filled_avg_price, filled_qty, hwm, limit_price, order.replaced_by, order.extended_hours,
                             order.status, order.failed_at, order.filled_at, order.canceled_at, order.expired_at,
                             order.replaced_at, order.submitted_at, order.created_at, order.updated_at)

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

                self.db.create_order(leg.id, parent_order_id, leg.symbol, leg.side, order_qty, leg.time_in_force,
                                     leg.order_class, leg.type, trail_percent, trail_price, stop_price, stop_price,
                                     filled_avg_price, filled_qty, hwm, limit_price, leg.replaced_by,
                                     leg.extended_hours, leg.status, leg.failed_at, leg.filled_at, leg.canceled_at,
                                     leg.expired_at, leg.replaced_at, leg.submitted_at, leg.created_at, leg.updated_at)

        logger.info(f"Saved order id: {parent_order_id}")
        return self.db.get_by_parent_id(parent_order_id)

    def _update_saved_order(self, order_id: str) -> None:
        order = self.api.get_order(order_id)
        updated_stop_price = self._check_float(order.stop_price)
        filled_avg_price = self._check_float(order.filled_avg_price)
        filled_qty = self._check_float(order.filled_qty)
        hwm = self._check_float(order.hwm)
        self.db.update_order(order_id, updated_stop_price, filled_avg_price, filled_qty, hwm, order.replaced_by,
                             order.extended_hours, order.status, order.failed_at, order.filled_at, order.canceled_at,
                             order.expired_at, order.replaced_at)

        logger.info(f"Updated order id: {order.id}")

    @staticmethod
    def _check_float(value):
        return 0.00 if value is None else float(value)
