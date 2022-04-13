"""This is a sample Python script."""

import trio
from loguru import logger

from connection import ScryfallConnection


async def main():
    Thingy = ScryfallConnection()
    datas = await Thingy.catalogs("powers")
    logger.debug(datas.data)


trio.run(main)
