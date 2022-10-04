from __future__ import annotations

from io import BytesIO
from typing import Any

import httpx
import trio
from httpx import AsyncClient
from httpx_caching import CachingClient
from loguru import logger

from .schema import (
    APIList,
    BulkData,
    Cards,
    Catalogs,
    List_of_Card_Identifiers,
    List_of_Catalogs,
    List_of_Platforms,
    ManaCost,
    Rulings_Platforms,
    Sets,
)


class ScryfallConnection:
    def __init__(self):
        self.url: str = "https://api.scryfall.com/"
        self.platforms: list[str] = ["multiverse", "mtgo", "arena", "tcgplayer", "cardmarket"]
        self.sleep: float = 0.5

    # Utilities

    @staticmethod
    async def raise_on_4xx_5xx(response):
        if response.status_code >= 400:
            error_response = await response.aread()
            logger.error(f"Direct API error: {error_response.decode('utf-8')}")
            response.raise_for_status()

    async def ratelimit_request(self, request: httpx.Request):
        sleep = self.sleep
        logger.warning(f"Self Rate Limiting for {sleep * 1000}ms for {request.method} {request.url}")
        await trio.sleep(seconds=sleep)

    async def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        follow_redirects: bool = False,
    ):
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        logger.info(f"GET to {url}")
        async with CachingClient(
            AsyncClient(
                event_hooks={"request": [self.ratelimit_request], "response": [self.raise_on_4xx_5xx]},
                follow_redirects=follow_redirects,
            )
        ) as client:
            resp = await client.get(url, params=params, headers=headers)
            logger.info(f"GET {resp.status_code} at {resp.url}")
            return resp

    async def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        return_data: str | None = "data",
        pagination: bool = True,
    ) -> dict[str, Any]:
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        resp = await self._get(url=url, params=params, headers=headers)
        sanitized = await self.sanitize_data(resp.json())
        if pagination:
            returnable = await self.pagination_list(return_data, sanitized)
            return returnable
        return sanitized

    async def get_image(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> BytesIO:
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        resp = await self._get(url=url, params=params, headers=headers, follow_redirects=True)
        return BytesIO(resp.content)

    async def post(self, endpoint: str, json_data: dict[str, Any], return_data: str | None = "data"):
        logger.info(f"POST to {self.url}{endpoint}")
        async with CachingClient(
            AsyncClient(event_hooks={"request": [self.ratelimit_request], "response": [self.raise_on_4xx_5xx]})
        ) as client:
            resp = await client.post(f"{self.url}{endpoint}", json=json_data)
            logger.info(f"POST {resp.status_code} at {resp.url}")
            sanitized = await self.sanitize_data(resp.json())
            returnable = await self.pagination_list(return_data, sanitized)
            return returnable

    async def sanitize_data(self, data: Any) -> Any:
        if isinstance(data, list):
            returnable_list: list[Any] = []
            for item in data:
                if isinstance(item, dict):
                    returnable_list.append(await self.sanitize_data(item))
                else:
                    returnable_list.append(item)
            return returnable_list
        if isinstance(data, dict):
            if "id" in data:
                data["api_id"] = data.pop("id")
            if "object" in data:
                data["obj"] = data.pop("object")
            returnable_dict = {}
            for key, value in data.items():
                returnable_dict[key] = await self.sanitize_data(value)
            return returnable_dict
        return data

    async def pagination_list(self, return_data: str | None, returnable: dict[str, Any]) -> dict[str, Any]:
        if "has_more" in returnable and "next_page" in returnable and isinstance(return_data, str):
            has_more = True
            url = returnable["next_page"].replace(self.url, "")
            while has_more:
                pagination = await self.get_json(url, pagination=False)
                returnable[return_data] += pagination[return_data]
                has_more = pagination["has_more"]
                if "next_page" in pagination:
                    url = pagination["next_page"].replace(self.url, "")
            return returnable
        return returnable

    # Sets

    async def sets(self) -> APIList:
        returnable_data = "data"
        url = f"{self.url}sets"
        all_sets = await self.get_json(url, return_data=returnable_data)
        logger.debug(all_sets)
        return APIList(**all_sets)

    async def set_by_code(self, set_code: str) -> Sets:
        returnable_data = None
        url = f"{self.url}sets/{set_code}"
        set_data = await self.get_json(url, return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_tcgplayer(self, tcgplayer_id: str) -> Sets:
        returnable_data = None
        url = f"{self.url}sets/tcgplayer/{tcgplayer_id}"
        set_data = await self.get_json(url, return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_id(self, api_id: str) -> Sets:
        returnable_data = None
        url = f"{self.url}sets/{api_id}"
        set_data = await self.get_json(url, return_data=returnable_data)
        return Sets(**set_data)

    # Cards

    async def cards_search(
        self,
        query: str,
        unique: str = "cards",
        order: str = "name",
        direction: str = "auto",
        include_extras: bool = False,
        include_multilinqual: bool = False,
        include_variations: bool = False,
    ) -> APIList:
        """https://scryfall.com/docs/api/cards/search"""
        returnable_data = "data"
        url = f"{self.url}cards/search"
        params = {
            "q": query,
            "unique": unique,
            "order": order,
            "dir": direction,
            "include_extras": include_extras,
            "include_multilinqual": include_multilinqual,
            "include_variations": include_variations,
        }
        search_data = await self.get_json(url, params=params, return_data=returnable_data)
        returnable = APIList(**search_data)
        return returnable

    async def cards_named(
        self,
        exact: str | None = None,
        fuzzy: str | None = None,
        set_code: str | None = None,
        face: str | None = None,
        version: str | None = None,
    ) -> Cards:
        returnable_data = None
        url = f"{self.url}cards/named"
        params = {
            "exact": exact,
            "fuzzy": fuzzy,
            "set": set_code,
            "format": "json",
            "face": face,
            "version": version,
        }
        card_data = await self.get_json(url, params=params, return_data=returnable_data)
        return Cards(**card_data)

    async def cards_named_image(
        self,
        exact: str | None = None,
        fuzzy: str | None = None,
        set_code: str | None = None,
        face: str | None = None,
        version: str | None = None,
    ) -> BytesIO:
        url = f"{self.url}cards/named"
        params = {
            "exact": exact,
            "fuzzy": fuzzy,
            "set": set_code,
            "format": "image",
            "face": face,
            "version": version,
        }
        return await self.get_image(url, params=params)

    async def cards_autocomplete(self, query: str) -> Catalogs:
        returnable_data = "data"
        url = f"{self.url}cards/autocomplete"
        if len(query) <= 2:
            raise ValueError("Must query for more than 2 characters.")
        params = {"q": query}
        autocompletes = await self.get_json(url, params=params, return_data=returnable_data)
        return Catalogs(**autocompletes)

    async def cards_random(self, query: str, face: str | None = None, version: str | None = None) -> Cards:
        returnable_data = None
        url = f"{self.url}cards/random"
        params = {
            "q": query,
            "format": "json",
            "face": face,
            "version": version,
        }
        card_data = await self.get_json(url, params=params, return_data=returnable_data)
        return Cards(**card_data)

    async def cards_random_image(self, query: str, face: str | None = None, version: str | None = None) -> BytesIO:
        url = f"{self.url}cards/random"
        params = {
            "q": query,
            "format": "image",
            "face": face,
            "version": version,
        }
        return await self.get_image(url, params=params)

    async def cards_collection(self, identifiers: list[dict[str, str | int]]) -> APIList:
        returnable_data = "data"
        url = f"{self.url}cards/collection"
        for identifier in identifiers:
            for k in identifier:
                if k not in List_of_Card_Identifiers:
                    raise ValueError(f"{k} is not a valid card identifier to search")
                if k == "set":
                    logger.info(f"name set: {'name' not in identifier}")
                    logger.info(f"set number: {'collector_number' not in identifier}")
                    if not ("name" in identifier or "collector_number" in identifier):
                        raise ValueError(f"{identifier} must include 'set' and 'name' or 'set' and 'collector_number'")
                if k == "collector_number" and "set" not in identifier:
                    raise ValueError(f"{k} must also include 'set'")
        data = {"identifiers": identifiers}
        list_of_cards = await self.post(url, json_data=data, return_data=returnable_data)
        returnable = APIList(**list_of_cards)
        return returnable

    async def card_set_number(
        self,
        set_code: str,
        number: int,
        lang: str | None = None,
        face: str | None = None,
        version: str | None = None,
    ) -> Cards:
        returnable_data = None
        url = f"{self.url}cards/{set_code}/{number}/{lang}"
        params = {
            "format": "json",
            "face": face,
            "version": version,
        }
        card_data = await self.get_json(
            url,
            params=params,
            return_data=returnable_data,
        )
        return Cards(**card_data)

    async def card_set_number_image(
        self, set_code: str, number: int, lang: str | None = "", face: str | None = None, version: str | None = None
    ) -> BytesIO:
        url = f"{self.url}cards/{set_code}/{number}/{lang}"
        params = {
            "format": "image",
            "face": face,
            "version": version,
        }
        return await self.get_image(url, params=params)

    async def card_by_platform_id(
        self, platform: str, platform_id: str, face: str | None = None, version: str | None = None
    ) -> Cards:
        if platform_id not in List_of_Platforms:
            raise ValueError(f"{platform} is not a valid platform to pull ID's from")
        if platform not in self.platforms:
            raise ValueError(f"{platform} not in {self.platforms}")
        returnable_data = None
        url = f"{self.url}cards/{platform}/{platform_id}"
        params = {
            "format": "json",
            "face": face,
            "version": version,
        }
        card_data = await self.get_json(
            url,
            params=params,
            return_data=returnable_data,
        )
        return Cards(**card_data)

    async def card_by_platform_id_image(
        self, platform: str, platform_id: str, face: str | None = None, version: str | None = None
    ) -> BytesIO:
        if platform_id not in List_of_Platforms:
            raise ValueError(f"{platform} is not a valid platform to pull ID's from")
        if platform not in self.platforms:
            raise ValueError(f"{platform} not in {self.platforms}")
        url = f"{self.url}cards/{platform}/{platform_id}"
        params = {
            "format": "json",
            "face": face,
            "version": version,
        }
        return await self.get_image(url, params=params)

    async def card_by_api_id(self, api_id: str) -> Cards:
        returnable_data = None
        url = f"{self.url}cards/{api_id}"
        card_data = await self.get_json(url, return_data=returnable_data)
        return Cards(**card_data)

    # Misc

    async def rulings_by_platform_id(self, platform: str, api_id: str) -> APIList:
        returnable_data = "data"
        url = f"{self.url}cards/{platform}/{api_id}/rulings"
        if platform not in Rulings_Platforms:
            raise ValueError(f"{platform} not a valid platform for IDs")
        card_rulings = await self.get_json(url, return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def rulings_by_set_number(self, set_code: str, set_number: str) -> APIList:
        returnable_data = "data"
        url = f"{self.url}cards/{set_code}/{set_number}/rulings"
        card_rulings = await self.get_json(url, return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def rulings_by_api_id(self, set_code: str, card_num: str | int) -> APIList:
        returnable_data = "data"
        url = f"{self.url}cards/{set_code}/{card_num}/rulings"
        card_rulings = await self.get_json(url, return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def symbology(self) -> APIList:
        returnable_data = "data"
        url = f"{self.url}symbology"
        symbol_data = await self.get_json(url, return_data=returnable_data)
        returnable = APIList(**symbol_data)
        return returnable

    async def parse_mana(self, cost: str) -> ManaCost:
        returnable_data = None
        url = f"{self.url}symbology/parse-mana"
        params = {"cost": cost}
        mana_cost = await self.get_json(url, params=params, return_data=returnable_data)
        return ManaCost(**mana_cost)

    async def catalogs(self, catalog: str) -> Catalogs:
        if catalog not in List_of_Catalogs:
            raise ValueError(f"{catalog} is not a valid catalog")
        returnable_data = None
        url = f"{self.url}catalog/{catalog}"
        returnable = await self.get_json(url, return_data=returnable_data)
        return Catalogs(**returnable)

    # Bulk Data / Catalog

    async def bulk_data(self) -> APIList:
        returnable_data = "data"
        url = f"{self.url}/bulk-data"
        bulk_data_list = await self.get_json(url, return_data=returnable_data)
        returnable = APIList(**bulk_data_list)
        return returnable

    async def bulk_data_by_id(self, api_id: str) -> BulkData:
        returnable_data = None
        url = f"{self.url}bulk-data/{api_id}"
        bulk_data = await self.get_json(url, return_data=returnable_data)
        return BulkData(**bulk_data)

    async def bulk_data_by_type(self, api_type: str) -> BulkData:
        returnable_data = None
        url = f"{self.url}bulk-data/{api_type}"
        bulk_data = await self.get_json(url, return_data=returnable_data)
        return BulkData(**bulk_data)
