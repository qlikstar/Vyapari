from datetime import date
from random import choice
from typing import List

from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from kink import di

from app import templates
from services.account_service import AccountService
from services.order_service import OrderService
from services.position_service import PositionService, Position

route = APIRouter(
    prefix="/ui",
    tags=["ui"]
)

position_service: PositionService = di[PositionService]
account_service: AccountService = di[AccountService]
order_service: OrderService = di[OrderService]

colors = ['green', 'blue', 'orange', 'red', 'purple', 'yellow', 'olive', 'teal', 'violet', 'pink', 'grey']


def get_history() -> []:
    result = []
    for item in account_service.get_portfolio_history():
        gain = item.final_portfolio_value - item.initial_portfolio_value
        result.append({
            "date": date(item.run_date.year, item.run_date.month, item.run_date.day).strftime("%b %d, %Y"),
            "initial": f"{item.initial_portfolio_value: 10.2f}",
            "final": f"{item.final_portfolio_value: 10.2f}",
            "gain": f"{gain: 10.2f}",
            "gain_pc": f"{float((gain / item.initial_portfolio_value) * 100): 6.2f}%",
            "pl_color": "green" if gain >= 0 else "red"
        })
    return result


def current_positions() -> []:
    curr_positions = []
    all_positions: List[Position] = position_service.get_all_pos()

    for count, position in enumerate(all_positions):
        curr_positions.append({
            "color": choice(colors),
            "symbol": position.symbol,
            "exchange": position.exchange,
            "type": position.side,
            "position_size": position.qty,
            "entry_price": float(position.entry_price),
            "current_price": float(position.current_price),
            "profit": f"${float(position.unrealized_profit): 6.2f}",
            "pl_color": "olive" if float(position.unrealized_profit) > 0 else "orange",
            "filled_at": position.order_filled_at.strftime(
                "%Y-%m-%d %I:%M %p") if position.order_filled_at is not None else 'Not found'
        })
    return curr_positions


def calculate_profit(records):
    profit = 0
    invested_amt = records[0]["filled_qty"] * records[0]["filled_price"]
    for record in records:
        if record["side"] == "buy":
            profit = profit - (record["filled_qty"] * record["filled_price"])
        else:
            profit = profit + (record["filled_qty"] * record["filled_price"])

    if abs(profit) / abs(invested_amt) < 0.5:
        return round(profit, 2)
    return 0


def stocks_closed() -> []:
    result = []
    prev_sym = None
    records = []
    for order in order_service.get_all_filled_orders_today():
        if prev_sym != order.symbol:
            records = [{
                "side": order.side,
                "side_color": "green" if order.side == "buy" else "red",
                "order_type": order.order_type,
                "order_color": _get_order_type_color(order.order_type),
                "filled_qty": order.filled_qty,
                "limit_price": order.limit_price,
                "filled_price": order.filled_avg_price,
                "filled_at": order.filled_at
            }]
        else:
            records.append({
                "side": order.side,
                "side_color": "green" if order.side == "buy" else "red",
                "order_type": order.order_type,
                "order_color": _get_order_type_color(order.order_type),
                "filled_qty": order.filled_qty,
                "limit_price": order.limit_price,
                "filled_price": order.filled_avg_price,
                "filled_at": order.filled_at
            })
            # result.pop()

        profit = calculate_profit(records)
        if profit != 0:
            result.append({
                "symbol": order.symbol,
                "color": choice(colors),
                "records": records,
                "pl_color": "green" if profit > 0 else "red",
                "profit": profit
            })
        prev_sym = order.symbol
    return result


def _get_order_type_color(order_type: str) -> str:
    if order_type == 'market':
        return "blue"
    if order_type == 'stop':
        return "red"
    if order_type == 'limit':
        return "green"
    if order_type == 'trailing_stop':
        return "orange"
    else:
        return "gray"


@route.get("/index", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html",
                                      {
                                          "request": request,
                                          "data": {
                                              "current_positions": current_positions(),
                                              "history": get_history(),
                                              "closed_positions": stocks_closed()
                                          }
                                      })
