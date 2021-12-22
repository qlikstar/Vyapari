from datetime import datetime

from peewee import *

from .base import BaseModel


class Position(BaseModel):
    run_date = DateField()
    symbol = FixedCharField(max_length=10)
    side = CharField(max_length=4)
    qty = IntegerField()
    entry_price = DecimalField(10, 2)
    market_price = DecimalField(10, 2)
    lastday_price = DecimalField(10, 2)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        db_table = 'position'
        primary_key = CompositeKey('run_date', 'symbol', 'side')


def get_position(symbol: str):
    return Position.select().filter(Position.symbol == symbol).order_by(Position.run_date.desc()).first()


def list_todays_positions():
    return list(Position.select().filter(Position.run_date == datetime.date(datetime.today())).offset(0).limit(10))


# def delete_position(id: int):
#     return Position.delete().where(Position.id == id).execute()


def create_position(run_date, symbol: str, side: str, qty: int, entry_price: float,
                    market_price: float, lastday_price: float):
    position_object = Position(
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
    position_object.save()
    return position_object


def upsert_position(run_date, symbol: str, side: str, qty: int, entry_price: float,
                    market_price: float, lastday_price: float):
    return Position.insert(run_date=run_date,
                           symbol=symbol,
                           side=side,
                           qty=qty,
                           entry_price=entry_price,
                           market_price=market_price,
                           lastday_price=lastday_price,
                           created_at=datetime.now(),
                           updated_at=datetime.now()) \
        .on_conflict(preserve=[Position.run_date, Position.symbol, Position.side],
                     update={Position.market_price: market_price,
                             Position.updated_at: datetime.now()}) \
        .execute()
