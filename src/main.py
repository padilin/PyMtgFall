"""This is a sample Python script."""

import trio
from loguru import logger

from connection import ScryfallConnection


async def main():
    Thingy = ScryfallConnection()
    datas = await Thingy.cards_search("c:white cmc:1")
    logger.debug(len(datas.data))


trio.run(main)
