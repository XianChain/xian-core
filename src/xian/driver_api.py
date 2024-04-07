import xian.constants as c

from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal


def get_latest_block_hash(driver: ContractDriver):
    latest_hash = driver.get(c.LATEST_BLOCK_HASH_KEY)
    if latest_hash is None:
        return b""
    return latest_hash


def set_latest_block_hash(h, driver: ContractDriver):
    driver.set(c.LATEST_BLOCK_HASH_KEY, h)


def get_latest_block_height(driver: ContractDriver):
    h = driver.get(c.LATEST_BLOCK_HEIGHT_KEY, save=False)
    if h is None:
        return 0

    if type(h) == ContractingDecimal:
        h = int(h._d)

    return int(h)


def set_latest_block_height(h, driver: ContractDriver):
    driver.set(c.LATEST_BLOCK_HEIGHT_KEY, int(h))


def get_value_of_key(item: str, driver: ContractDriver):
    return driver.get(item)


def get_keys(driver, key):
    return driver.keys(key)


def get_contract(driver, contract):
    return driver.get_contract(contract)
