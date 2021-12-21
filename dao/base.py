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
