"""This is a sample Python script."""

import trio
from loguru import logger
import io
from PIL import Image

import pymtgfall.connection


async def main():
    """Main function for testing"""
    thingy = pymtgfall.connection.ScryfallConnection()
    datas = await thingy.cards_named_image(exact="Wandering Archaic")
    image = Image.open(io.BytesIO(datas))
    image.show()


trio.run(main)
