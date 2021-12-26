import logging
from typing import Any

import peewee
from pydantic.utils import GetterDict

# Set configurations for logger
logging.basicConfig(format='[%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %I:%M:%S %p]',
                    level=logging.INFO)


class PeeweeGetterDict(GetterDict):
    def get(self, key: Any, default: Any = None):
        res = getattr(self._obj, key, default)
        if isinstance(res, peewee.ModelSelect):
            return list(res)
        return res
