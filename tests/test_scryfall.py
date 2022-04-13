from loguru import logger

import httpx
import pytest

from httpx._exceptions import HTTPStatusError

import src
from src.connection import ScryfallConnection


@pytest.mark.trio
async def test_get_4xx_5xx_triggers(httpx_mock, monkeypatch):
    httpx_mock.add_response(
        url="https://api.scryfall.com/symbology",
        json={
            "object": "error",
            "code": "bad_request",
            "status": 404,
            "warnings": [
                "Invalid expression “is:slick” was ignored. Checking if cards are “slick” is not supported",
                "Invalid expression “cmc>cmc” was ignored. The sides of your comparison must be different.",
            ],
            "details": "All of your terms were ignored.",
        },
        status_code=404,
    )

    test_conn = ScryfallConnection()
    with pytest.raises(HTTPStatusError) as e_info:
        data = await test_conn.get("symbology")
        logger.info(data)
