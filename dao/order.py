from datetime import datetime

from peewee import *

from .base import BaseModel


class Order(BaseModel):
    id = FixedCharField(40, unique=True, index=True)
    parent_id = FixedCharField(40)
    symbol = CharField(max_length=10)
    side = CharField(max_length=4)
    order_qty = IntegerField()
    time_in_force = CharField(max_length=6)

    order_class = CharField(max_length=10)
    order_type = CharField(max_length=16)
    trail_percent = DecimalField(10, 2)
    trail_price = DecimalField(10, 2)
    initial_stop_price = DecimalField(10, 2)
    updated_stop_price = DecimalField(10, 2)
    failed_at = DateTimeField()
    filled_at = DateTimeField()
    filled_avg_price = DecimalField(10, 2)
    filled_qty = IntegerField()
    hwm = DecimalField(10, 2)
    limit_price = DecimalField(10, 2)
    replaced_by = CharField(max_length=40)
    extended_hours = BooleanField()
    status = CharField(max_length=16)

    canceled_at = DateTimeField()
    expired_at = DateTimeField()
    replaced_at = DateTimeField()
    submitted_at = DateTimeField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        db_table = 'order'


def create_order(order_id: str, parent_id: str, symbol: str, side: str, order_qty: float, time_in_force: str,
                 order_class: str, order_type: str, trail_percent: float, trail_price: float,
                 initial_stop_price: float, updated_stop_price: float,  filled_avg_price: float, filled_qty: float,
                 hwm: float, limit_price: float, replaced_by: str, extended_hours: bool, status: str,
                 failed_at: datetime, filled_at: datetime, canceled_at: datetime, expired_at: datetime,
                 replaced_at: datetime, submitted_at: datetime, created_at: datetime, updated_at: datetime):
    insert_stmt = Order.insert(id=order_id,
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
    order_object = insert_stmt.execute()
    return order_object


def update_order(order_id: str, updated_stop_price: float, filled_avg_price: float, filled_qty: float, hwm: float,
                 replaced_by: str, extended_hours: bool, status: str,
                 failed_at: datetime, filled_at: datetime, canceled_at: datetime,
                 expired_at: datetime, replaced_at: datetime):

    Order.update(updated_stop_price=updated_stop_price,
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
                 replaced_at=replaced_at)\
        .where(Order.id == order_id)\
        .execute()


def get_open_orders():
    return Order.select().where(~(Order.status << ['canceled', 'rejected', 'filled']))


def list_orders(skip: int = 0, limit: int = 100):
    return list(Order.select().offset(skip).limit(limit))


def delete_order(id: str):
    return Order.delete().where(Order.id == id).execute()
