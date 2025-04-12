import json

from logger_config import logger

CONFIG_PATH = "configs/config.json"


def load_config(filename=CONFIG_PATH) -> dict:
    logger.info(f"Load config from {filename}")
    with open(filename, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

def save_config(config, filename=CONFIG_PATH) -> dict:
    logger.info(f'Save config in {filename}')
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=4)
