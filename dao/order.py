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
    failed_at = TimestampField()
    filled_at = TimestampField()
    filled_avg_price = DecimalField(10, 2)
    filled_qty = IntegerField()
    hwm = DecimalField(10, 2)
    limit_price = DecimalField(10, 2)
    replaced_by = CharField(max_length=40)
    extended_hours = BooleanField()
    status = CharField(max_length=16)

    cancelled_at = TimestampField()
    expired_at = TimestampField()
    replaced_at = TimestampField()
    submitted_at = TimestampField()
    created_at = TimestampField()
    updated_at = TimestampField()

    class Meta:
        db_table = 'position'


async def create_order(id, parent_id, symbol, side, order_qty, time_in_force, order_class, order_type, trail_percent,
                       trail_price, initial_stop_price, updated_stop_price, failed_at, filled_at,
                       filled_avg_price, filled_qty, hwm, limit_price, replaced_by, extended_hours, status,
                       cancelled_at, expired_at, replaced_at, submitted_at, created_at, updated_at):
    order_object = Order(id=id,
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
                         failed_at=failed_at,
                         filled_at=filled_at,
                         filled_avg_price=filled_avg_price,
                         filled_qty=filled_qty,
                         hwm=hwm,
                         limit_price=limit_price,
                         replaced_by=replaced_by,
                         extended_hours=extended_hours,
                         status=status,

                         cancelled_at=cancelled_at,
                         expired_at=expired_at,
                         replaced_at=replaced_at,
                         submitted_at=submitted_at,
                         created_at=created_at,
                         updated_at=updated_at)
    order_object.save()
    return order_object


def get_order(id: str):
    return Order.filter(Order.id == id).first()


def list_orders(skip: int = 0, limit: int = 100):
    return list(Order.select().offset(skip).limit(limit))


def delete_order(id: str):
    return Order.delete().where(Order.id == id).execute()
