from peewee import *

from .base import BaseModel


class Position(BaseModel):
    id = PrimaryKeyField(null=False)
    symbol = FixedCharField(max_length=10)
    side = CharField(max_length=4)
    qty = IntegerField()
    entry_price = DecimalField(10, 2)
    market_price = DecimalField(10, 2)
    lastday_price = DecimalField(10, 2)
    created_at = TimestampField()
    updated_at = TimestampField()

    class Meta:
        db_table = 'position'


# class PositionDao(object):

# @staticmethod
async def create_position(symbol: str, side: str, qty: int, entry_price: float, market_price: float,
                          lastday_price: float, created_at, updated_at):
    position_object = Position(
        symbol=symbol,
        side=side,
        qty=qty,
        entry_price=entry_price,
        market_price=market_price,
        lastday_price=lastday_price,
        created_at=created_at,
        updated_at=updated_at
    )
    position_object.save()
    return position_object


# @staticmethod
def get_position(id: int):
    return Position.filter(Position.id == id).first()


# @staticmethod
def list_positions(skip: int = 0, limit: int = 100):
    return list(Position.select().offset(skip).limit(limit))


# @staticmethod
def delete_position(id: int):
    return Position.delete().where(Position.id == id).execute()
