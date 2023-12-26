# import asyncio
# import decimal
# from collections import defaultdict
# from datetime import date
# from core.logger import logger
# from abc import ABC
# from dataclasses import dataclass
# from typing import List, Dict
#
# import telegram
# from alpaca.trading import TradeAccount
# from fastapi import Request
# from kink import di, inject
#
# from core.db_tables import OrderEntity, AccountEntity
# from core.telegram import Telegram
# from services.account_service import AccountService
# from services.data_service import DataService
# from services.order_service import OrderService
# from services.position_service import PositionService
#
#
# @dataclass
# class StockPerf:
#     symbol: str
#     open_position_count: int
#     investment: float
#     side: str
#     cost_basis: float
#     market_value: float
#     close_date: str
#
#
# class ChatService(ABC):
#     def respond(self, inp: str):
#         pass
#
#
# class TelegramService(ChatService):
#
#     def __init__(self, uri: str):
#         self.uri = uri
#         self.telegram: Telegram = di[Telegram]
#         self.command_response: CommandResponse = di[CommandResponse]
#
#         # Schedule the set_webhook coroutine to run asynchronously
#         asyncio.get_event_loop().create_task(self.set_webhook())
#
#     async def set_webhook(self):
#         await self.telegram.bot.set_webhook(f'{self.telegram.url}/{self.uri}')
#
#     async def respond(self, request: Request) -> None:
#         req_info = await request.json()
#         update = telegram.Update.de_json(req_info, self.telegram.bot)
#
#         # get the chat_id to be able to respond to the same user
#         chat_id = update.message.chat.id
#         logger.info(f"chat id : {chat_id}")
#         # get the message id to be able to reply to this specific message
#         msg_id = update.message.message_id
#
#         # Telegram understands UTF-8, so encode text for unicode compatibility
#         command = update.message.text.encode('utf-8').decode().lower()
#         logger.info(f"got text message :{command}")
#
#         response = self.command_response.get_command(command)
#         # now just send the message back
#         # notice how we specify the chat and the msg we reply to
#         await self.telegram.send_message(chat_id=str(chat_id), response=response, reply_to_message_id=str(msg_id))
#
#
# @inject
# class CommandResponse(object):
#
#     def __init__(self):
#         self.order_service: OrderService = di[OrderService]
#         self.position_service: PositionService = di[PositionService]
#         self.data_service: DataService = di[DataService]
#         self.account_service: AccountService = di[AccountService]
#
#     def get_command(self, command: str):
#         default = f"Could not understand: {command}"
#         return getattr(self, command.strip("/"), lambda: default)()
#
#     @staticmethod
#     def help() -> str:
#         return ("*/start    :* `Starts the trader`\n"
#                 "*/stop     :* `Stops the trader`\n"
#                 "*/health   :* `Detailed health of the app`\n"
#                 "*/status   :* `Lists all open trades`\n"
#                 "*/trades   :* `Lists last closed trades`\n"
#                 "*/profit [n]:* `Lists cumulative profit`\n"
#                 "*/forcesell [stock or all]:* `Instantly sells stock or all`\n"
#                 "*/current  :* `Show current open positions`\n"
#                 "*/realized :* `Shows today's realized profit or loss`\n"
#                 "*/balance  :* `Show account balance`\n"
#                 "*/history  :* `Shows portfolio history`\n"
#                 "*/help     :* `Help message`\n"
#                 "*/version  :* `Show version`")
#
#     @staticmethod
#     def start() -> str:
#         return "Not Implemented yet!"
#
#     @staticmethod
#     def stop() -> str:
#         return "Not Implemented yet!"
#
#     @staticmethod
#     def health() -> str:
#         return "Not Implemented yet!"
#
#     def realized(self) -> str:
#         realized_profit_list, unrealized_profit_list = self._get_all_balanced_positions()
#
#         if len(realized_profit_list) == 0:
#             return '`*** No closed positions found ***`'
#
#         total_realized_profit = 0
#         total_investment = 0
#         resp = "```\nDate         Symb  Inv.Amt  Gain   Gain%\n"
#         resp = resp + "-----------------------------------------\n"
#         for item in realized_profit_list:
#             realized_profit = item.market_value - item.cost_basis
#             percentage_profit = (realized_profit / item.investment) * 100
#             resp = resp + f'{item.close_date}  {item.symbol:<4}  {float(item.investment):7.2f} ' \
#                           f'{float(realized_profit): 6.2f}{float(percentage_profit): 6.2f}%\n'
#
#             total_realized_profit = total_realized_profit + realized_profit
#             total_investment = total_investment + item.investment
#
#         percentage_profit = (total_realized_profit / total_investment) * 100
#         resp = resp + f'-----------------------------------------\n'
#         resp = resp + f'Total Realized P/L : ${total_realized_profit:8,.2f} ({percentage_profit:4.2f}%)```'
#         return resp.replace('$-', '-$')
#
#     def current(self) -> str:
#         total_unrealized_pl = 0
#         all_positions = self.position_service.get_all_positions()
#
#         if len(all_positions) == 0:
#             return '`*** No current positions found ***`'
#
#         resp = "```\nSl Symbol  Price    Gain    Gain%\n"
#         resp = resp + "---------------------------------\n"
#         for count, position in enumerate(all_positions):
#             total_unrealized_pl = total_unrealized_pl + float(position.unrealized_pl)
#             resp = resp + (
#                 f"{(count + 1):<2} {position.symbol:<5}  ${float(position.current_price):7.2f} "
#                 f"{float(position.unrealized_pl): 6.2f} "
#                 f"{float(position.unrealized_plpc) * 100: 6.2f}%\n"
#             )
#
#         resp = resp + "---------------------------------\n"
#         resp = resp + f"Total unrealized P/L: ${total_unrealized_pl: .2f}```"
#         return resp.replace('$-', '-$')
#
#     def balance(self) -> str:
#         acc_details: TradeAccount = self.account_service.get_account_details()
#         actual_remaining_balance: float = float(acc_details.buying_power) / int(acc_details.multiplier)
#         portfolio_value: float = float(acc_details.portfolio_value)
#         invested_amount: float = portfolio_value - actual_remaining_balance
#         return (
#             f"```\n"
#             f"Remaining Balance: ${actual_remaining_balance:9,.2f}\n"
#             f"Invested Amount  : ${invested_amount:9,.2f}\n"
#             f"----------------------------\n"
#             f"Portfolio Value  : ${portfolio_value:9,.2f}"
#             f"```\n"
#         )
#
#     def history(self) -> str:
#         portfolio_hist: List[AccountEntity] = self.account_service.get_portfolio_history()
#
#         resp = "```\nDate         Investment  Gain     Gain%\n"
#         resp = resp + "---------------------------------------\n"
#         for item in portfolio_hist[::-1]:
#             run_date = date(item.run_date.year, item.run_date.month, item.run_date.day).strftime("%b %d %Y")
#             gain = item.final_portfolio_value - item.initial_portfolio_value
#             gain_percentage = float((gain / item.initial_portfolio_value) * 100)
#             resp = resp + f"{run_date}  ${item.initial_portfolio_value:.2f} {gain: 8.2f} {gain_percentage: 6.2f}%\n"
#         return resp + "```"
#
#     def _get_all_balanced_positions(self) -> (List[StockPerf], List[StockPerf]):
#         all_orders: List[OrderEntity] = self.order_service.get_all_filled_orders_today()
#
#         realized_profit_list: List[StockPerf] = []
#         unrealized_profit_list: List[StockPerf] = []
#
#         for sym, orders in self._get_filled_orders_for_symbols(all_orders).items():
#             current_stock_price = decimal.Decimal(self.data_service.get_current_price(sym))
#             running_perf = None
#             for index, order in enumerate(orders):
#                 filled_at = date(order.filled_at.year, order.filled_at.month, order.filled_at.day).strftime("%b %d %Y")
#                 if running_perf is None:
#                     if order.side == 'buy':
#                         running_perf = StockPerf(order.symbol, order.filled_qty,
#                                                  order.filled_qty * order.filled_avg_price,
#                                                  order.side,
#                                                  order.filled_qty * order.filled_avg_price,
#                                                  order.filled_qty * current_stock_price,
#                                                  filled_at)
#
#                     else:
#                         running_perf = StockPerf(order.symbol, - order.filled_qty,
#                                                  decimal.Decimal(0.00),  # Set this to 0, to prevent cancel buy and sell
#                                                  order.side,
#                                                  - order.filled_qty * order.filled_avg_price,
#                                                  - order.filled_qty * current_stock_price,
#                                                  filled_at)
#
#                 else:
#                     if order.side == 'buy':
#                         running_perf = StockPerf(running_perf.symbol,
#                                                  running_perf.open_position_count + order.filled_qty,
#                                                  running_perf.investment + (order.filled_qty * order.filled_avg_price),
#                                                  order.side,
#                                                  running_perf.cost_basis + (order.filled_qty * order.filled_avg_price),
#                                                  running_perf.market_value + (order.filled_qty * current_stock_price),
#                                                  filled_at)
#                     else:
#                         running_perf = StockPerf(running_perf.symbol,
#                                                  running_perf.open_position_count - order.filled_qty,
#                                                  running_perf.investment + decimal.Decimal(0.00),
#                                                  order.side,
#                                                  running_perf.cost_basis - (order.filled_qty * order.filled_avg_price),
#                                                  running_perf.market_value - (order.filled_qty * current_stock_price),
#                                                  filled_at)
#
#                 if index == len(orders) - 1:
#                     if running_perf.open_position_count == 0:
#                         realized_profit_list.append(running_perf)
#                     else:
#                         unrealized_profit_list.append(running_perf)
#
#         return realized_profit_list, unrealized_profit_list
#
#     @staticmethod
#     def _get_filled_orders_for_symbols(all_orders: List[OrderEntity]) -> Dict[str, List[OrderEntity]]:
#         dict_of_orders = defaultdict(list)
#         for order in all_orders:
#             dict_of_orders[order.symbol].append(order)
#         return dict_of_orders
