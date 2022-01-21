import os

import yaml


def load_env_variables():
    with open("conf/env.yml") as f:
        config = yaml.safe_load(f)
        for key, value in config.items():
            os.environ[key] = str(value)


def load_app_variables(input_key):
    with open("conf/app.yml") as f:
        config = yaml.safe_load(f)
        for key, value in config.items():
            if input_key == key:
                return value
        return None
