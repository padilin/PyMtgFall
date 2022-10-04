import json
from typing import Any

import httpx
import pytest
from httpx import HTTPStatusError
from loguru import logger
from pytest_httpx import HTTPXMock

from pymtgfall.connection import ScryfallConnection
from pymtgfall.schema import APIList, Sets, Object_Map


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
        data = await scryfall_conn._get("https://api.scryfall.com/symbology")
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
        assert (
            await scryfall_conn.pagination_list(return_data=None, returnable=non_paginated_response)
            == non_paginated_response
        )


async def endpoint_tester(
    resp_json: str,
    name_of_func_to_test: callable,
    func_kwargs: dict[str, Any],
    test_json,
    httpx_mock: HTTPXMock,
    scryfall_conn: ScryfallConnection,
):
    resp = json.loads(resp_json)
    httpx_mock.add_response(json=resp)
    try:
        func_to_test = getattr(scryfall_conn, name_of_func_to_test)
        func_resp = await func_to_test(**func_kwargs)
        expected_resp = Object_Map[test_json["obj"]](**test_json)
        return func_resp, expected_resp
    except AttributeError:
        raise ValueError("Passed wrong name of method to test.")


class TestsSets:
    sets_json = """{
    "object": "list",
    "has_more": false,
    "data": [
      {
        "object": "set",
        "id": "b314f553-8f07-4ba9-96c8-16be7784eff3",
        "code": "unf",
        "tcgplayer_id": 2958,
        "name": "Unfinity",
        "uri": "https://api.scryfall.com/sets/b314f553-8f07-4ba9-96c8-16be7784eff3",
        "scryfall_uri": "https://scryfall.com/sets/unf",
        "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Aunf&unique=prints",
        "released_at": "2022-12-31",
        "set_type": "funny",
        "card_count": 26,
        "digital": false,
        "nonfoil_only": false,
        "foil_only": false,
        "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/unf.svg?1650859200"
      },
      {
        "object": "set",
        "id": "a60124f9-8002-4769-ac16-387b61fa2bc6",
        "code": "tunf",
        "name": "Unfinity Tokens",
        "uri": "https://api.scryfall.com/sets/a60124f9-8002-4769-ac16-387b61fa2bc6",
        "scryfall_uri": "https://scryfall.com/sets/tunf",
        "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Atunf&unique=prints",
        "released_at": "2022-12-31",
        "set_type": "token",
        "card_count": 0,
        "parent_set_code": "unf",
        "digital": false,
        "nonfoil_only": true,
        "foil_only": true,
        "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/unf.svg?1650859200"
      }
      ]
      }"""
    sets_json_processed = {
        "obj": "list",
        "has_more": False,
        "data": [
            {
                "obj": "set",
                "api_id": "b314f553-8f07-4ba9-96c8-16be7784eff3",
                "code": "unf",
                "tcgplayer_id": 2958,
                "name": "Unfinity",
                "uri": "https://api.scryfall.com/sets/b314f553-8f07-4ba9-96c8-16be7784eff3",
                "scryfall_uri": "https://scryfall.com/sets/unf",
                "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Aunf&unique=prints",
                "released_at": "2022-12-31",
                "set_type": "funny",
                "card_count": 26,
                "digital": False,
                "nonfoil_only": False,
                "foil_only": False,
                "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/unf.svg?1650859200",
            },
            {
                "obj": "set",
                "api_id": "a60124f9-8002-4769-ac16-387b61fa2bc6",
                "code": "tunf",
                "name": "Unfinity Tokens",
                "uri": "https://api.scryfall.com/sets/a60124f9-8002-4769-ac16-387b61fa2bc6",
                "scryfall_uri": "https://scryfall.com/sets/tunf",
                "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Atunf&unique=prints",
                "released_at": "2022-12-31",
                "set_type": "token",
                "card_count": 0,
                "parent_set_code": "unf",
                "digital": False,
                "nonfoil_only": True,
                "foil_only": True,
                "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/unf.svg?1650859200",
            },
        ],
    }

    set_by_code_json = """{
  "object": "set",
  "id": "385e11a4-492b-4d07-b4a6-a1409ef829b8",
  "code": "mmq",
  "mtgo_code": "mm",
  "arena_code": "mm",
  "tcgplayer_id": 73,
  "name": "Mercadian Masques",
  "uri": "https://api.scryfall.com/sets/385e11a4-492b-4d07-b4a6-a1409ef829b8",
  "scryfall_uri": "https://scryfall.com/sets/mmq",
  "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Ammq&unique=prints",
  "released_at": "1999-10-04",
  "set_type": "expansion",
  "card_count": 350,
  "printed_size": 350,
  "digital": false,
  "nonfoil_only": false,
  "foil_only": false,
  "block_code": "mmq",
  "block": "Masques",
  "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/mmq.svg?1650859200"
}"""
    set_by_code_json_processed = {
        "obj": "set",
        "api_id": "385e11a4-492b-4d07-b4a6-a1409ef829b8",
        "code": "mmq",
        "mtgo_code": "mm",
        "arena_code": "mm",
        "tcgplayer_id": 73,
        "name": "Mercadian Masques",
        "uri": "https://api.scryfall.com/sets/385e11a4-492b-4d07-b4a6-a1409ef829b8",
        "scryfall_uri": "https://scryfall.com/sets/mmq",
        "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Ammq&unique=prints",
        "released_at": "1999-10-04",
        "set_type": "expansion",
        "card_count": 350,
        "printed_size": 350,
        "digital": False,
        "nonfoil_only": False,
        "foil_only": False,
        "block_code": "mmq",
        "block": "Masques",
        "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/mmq.svg?1650859200",
    }

    set_by_tcgplayer_json = """{
  "object": "set",
  "id": "c26402e7-838e-48db-a4b2-7abfc305998a",
  "code": "mp2",
  "mtgo_code": "ms3",
  "arena_code": "ms3",
  "tcgplayer_id": 1909,
  "name": "Amonkhet Invocations",
  "uri": "https://api.scryfall.com/sets/c26402e7-838e-48db-a4b2-7abfc305998a",
  "scryfall_uri": "https://scryfall.com/sets/mp2",
  "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Amp2&unique=prints",
  "released_at": "2017-04-28",
  "set_type": "masterpiece",
  "card_count": 54,
  "parent_set_code": "akh",
  "digital": false,
  "nonfoil_only": false,
  "foil_only": true,
  "block_code": "akh",
  "block": "Amonkhet",
  "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/mp2.svg?1650859200"
}"""
    set_by_tcgplayer_json_processed = {
        "obj": "set",
        "api_id": "c26402e7-838e-48db-a4b2-7abfc305998a",
        "code": "mp2",
        "mtgo_code": "ms3",
        "arena_code": "ms3",
        "tcgplayer_id": 1909,
        "name": "Amonkhet Invocations",
        "uri": "https://api.scryfall.com/sets/c26402e7-838e-48db-a4b2-7abfc305998a",
        "scryfall_uri": "https://scryfall.com/sets/mp2",
        "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Amp2&unique=prints",
        "released_at": "2017-04-28",
        "set_type": "masterpiece",
        "card_count": 54,
        "parent_set_code": "akh",
        "digital": False,
        "nonfoil_only": False,
        "foil_only": True,
        "block_code": "akh",
        "block": "Amonkhet",
        "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/mp2.svg?1650859200",
    }

    set_by_id_json = """{
  "object": "set",
  "id": "2ec77b94-6d47-4891-a480-5d0b4e5c9372",
  "code": "uma",
  "mtgo_code": "uma",
  "arena_code": "uma",
  "tcgplayer_id": 2360,
  "name": "Ultimate Masters",
  "uri": "https://api.scryfall.com/sets/2ec77b94-6d47-4891-a480-5d0b4e5c9372",
  "scryfall_uri": "https://scryfall.com/sets/uma",
  "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Auma&unique=prints",
  "released_at": "2018-12-07",
  "set_type": "masters",
  "card_count": 254,
  "printed_size": 254,
  "digital": false,
  "nonfoil_only": false,
  "foil_only": false,
  "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/uma.svg?1650859200"
}"""
    set_by_id_json_processed = {
        "obj": "set",
        "api_id": "2ec77b94-6d47-4891-a480-5d0b4e5c9372",
        "code": "uma",
        "mtgo_code": "uma",
        "arena_code": "uma",
        "tcgplayer_id": 2360,
        "name": "Ultimate Masters",
        "uri": "https://api.scryfall.com/sets/2ec77b94-6d47-4891-a480-5d0b4e5c9372",
        "scryfall_uri": "https://scryfall.com/sets/uma",
        "search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Auma&unique=prints",
        "released_at": "2018-12-07",
        "set_type": "masters",
        "card_count": 254,
        "printed_size": 254,
        "digital": False,
        "nonfoil_only": False,
        "foil_only": False,
        "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/uma.svg?1650859200",
    }

    @pytest.mark.trio
    @pytest.mark.parametrize(
        ("resp_json", "name_of_func_to_test", "func_kwargs", "test_json"),
        [
            (sets_json, "sets", {}, sets_json_processed),
            (set_by_code_json, "set_by_code", {"set_code": "mmq"}, set_by_code_json_processed),
            (set_by_tcgplayer_json, "set_by_tcgplayer", {"tcgplayer_id": 1909}, set_by_tcgplayer_json_processed),
            (set_by_id_json, "set_by_id", {"api_id": "2ec77b94-6d47-4891-a480-5d0b4e5c9372"}, set_by_id_json_processed),
        ],
        ids=["test_sets", "test_set_by_code", "test_set_by_tcgplayer", "test_set_by_id"],
    )
    async def test_sets(
        self,
        resp_json,
        name_of_func_to_test,
        func_kwargs,
        test_json,
        httpx_mock: HTTPXMock,
        scryfall_conn: ScryfallConnection,
        autojump_clock,
    ):
        func_resp, expected_resp = await endpoint_tester(
            resp_json, name_of_func_to_test, func_kwargs, test_json, httpx_mock, scryfall_conn
        )
        assert func_resp == expected_resp
