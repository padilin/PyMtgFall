import httpx
import pytest
from httpx import HTTPStatusError
from loguru import logger
from pytest_httpx import HTTPXMock

import pymtgfall
from pymtgfall.connection import ScryfallConnection


@pytest.fixture
def scryfall_conn():
    return ScryfallConnection()


@pytest.mark.trio
async def test_get_4xx_5xx_triggers(httpx_mock: HTTPXMock, scryfall_conn: ScryfallConnection, autojump_clock):
    httpx_mock.add_response(
        url="https://api.scryfall.com/symbology",
        json={
            "object": "error",
            "code": "bad_request",
            "status": 404,
            "warnings": [
                "Invalid expression is:slick was ignored. Checking if cards are slick is not supported",
                "Invalid expression cmc>cmc was ignored. The sides of your comparison must be different.",
            ],
            "details": "All of your terms were ignored.",
        },
        status_code=404,
    )

    with pytest.raises(HTTPStatusError) as e_info:
        data = await scryfall_conn.get("symbology")
        logger.info(data)


class TestSanitizeData:
    @pytest.mark.trio
    async def test_list_sanitize_data_pass(self, scryfall_conn: ScryfallConnection, autojump_clock):
        unsanitary_list_data = ["this", "is", {"name": "sparta", "id": 300, "object": "army"}, 300]
        sanitary_list_data = ["this", "is", {"name": "sparta", "api_id": 300, "obj": "army"}, 300]
        assert await scryfall_conn.sanitize_data(unsanitary_list_data) == sanitary_list_data

    @pytest.mark.trio
    async def test_dict_sanitize_data_pass(self, scryfall_conn: ScryfallConnection, autojump_clock):
        unsanitary_dict_data = {
            "name": "Sonic",
            "object": "creature",
            "id": 3000,
            "speed": {"id": 2, "object": "too", "name": "fast"},
        }
        sanitary_dict_data = {
            "name": "Sonic",
            "obj": "creature",
            "api_id": 3000,
            "speed": {"api_id": 2, "obj": "too", "name": "fast"},
        }
        assert await scryfall_conn.sanitize_data(unsanitary_dict_data) == sanitary_dict_data

    @pytest.mark.trio
    async def test_sanitary_data_passthrough_pass(self, scryfall_conn: ScryfallConnection, autojump_clock):
        sanitary_data = ["str", 147, ["hello", "sanitary"], {"good": "data", "is": 104}]
        assert await scryfall_conn.sanitize_data(sanitary_data) == sanitary_data


class TestPaginationList:
    @pytest.mark.trio
    async def test_not_paginated(self, scryfall_conn: ScryfallConnection, autojump_clock):
        non_paginated_response = {
            "name": "dr who",
            "vehicle": "tardis",
        }
        assert await scryfall_conn.pagination_list(return_data=None, returnable=non_paginated_response) == non_paginated_response
