import os

import yaml
from alpaca.trading import TradingClient

CONF_ENV_YML = "conf/env.yml"


def load_env_variables():
    with open("%s" % CONF_ENV_YML) as f:
        config = yaml.safe_load(f)
        for key, value in config.items():
            os.environ[key] = str(value)


def load_app_variables(input_key):
    with open("%s" % CONF_ENV_YML) as f:
        config = yaml.safe_load(f)
        for key, value in config.items():
            if input_key == key:
                return value
        return None


def init_alpaca_client() -> TradingClient:
    api_key = os.environ.get("APCA-API-KEY-ID")
    secret_key = os.environ.get("APCA-API-SECRET-KEY")
    paper_str = os.environ.get("APCA-PAPER")
    if api_key is not None and secret_key is not None and paper_str is not None:
        # Convert paper_str to boolean
        paper = paper_str.lower() == "true"

        # Create TradingClient instance
        return TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
    else:
        raise ValueError("One or more required environment variables not set.")
