# from playhouse.shortcuts import model_to_dict
#
# from dao.position import PositionDao
# from utils.broker import Broker
#
#
# class PositionService(object):
#
#     def __init__(self, broker: Broker, position_dao: PositionDao):
#         self.broker = broker,
#         self.position_dao = position_dao
#
#     def get_current_positions(self):
#         positions = self.broker.get_positions()
#         for pos in positions:
#             print(pos)
#             self.position_dao.create_position(pos.symbol, pos.side, pos.qty, pos.entry_price, pos.market_price,
#                                               pos.lastday_price, pos.created_at, pos.updated_at)
#
#         return self.position_dao.list_positions()
