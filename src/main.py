"""This is a sample Python script."""

import trio
from loguru import logger

from connection import ScryfallConnection


async def main():
    Thingy = ScryfallConnection()
    idents = [{"id": "683a5707-cddb-494d-9b41-51b4584ded69"}]
    datas = await Thingy.cards_collection(idents)
    logger.debug(datas.data)


trio.run(main)
