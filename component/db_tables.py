from peewee import *

user = 'root'
password = 'password'
db_name = 'vyapari'

conn = MySQLDatabase(
    db_name, user=user,
    password=password,
    host='localhost'
)


class BaseModel(Model):
    class Meta:
        database = conn


class OrderEntity(BaseModel):
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


class PositionEntity(BaseModel):
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