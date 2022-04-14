"""This is a sample Python script."""

import trio
from loguru import logger

import src.connection


async def main():
    """Main function for testing"""
    thingy = src.connection.ScryfallConnection()
    idents = [{"id": "683a5707-cddb-494d-9b41-51b4584ded69"}]
    datas = await thingy.cards_collection(idents)
    logger.debug(datas.data)


trio.run(main)
