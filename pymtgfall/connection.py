from __future__ import annotations

from typing import Any, Dict, List, Optional

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
        self.platforms: List[str] = ["multiverse", "mtgo", "arena", "tcgplayer", "cardmarket"]
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

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        return_data: Optional[str] = "data",
        pagination: bool = True,
    ) -> Dict[str, Any]:
        if params is None:
            params = {}
        logger.info(f"GET to {self.url}{endpoint}")
        async with CachingClient(
            AsyncClient(event_hooks={"request": [self.ratelimit_request], "response": [self.raise_on_4xx_5xx]})
        ) as client:
            resp = await client.get(f"{self.url}{endpoint}", params=params)
            logger.info(f"GET {resp.status_code} at {resp.url}")
            sanitized = await self.sanitize_data(resp.json())
            if pagination:
                returnable = await self.pagination_list(return_data, sanitized)
                return returnable
            return sanitized

    async def post(self, endpoint: str, json_data: Dict[str, Any], return_data: Optional[str] = "data"):
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
            returnable_list: List[Any] = []
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

    async def pagination_list(self, return_data: Optional[str], returnable: Dict[str, Any]) -> Dict[str, Any]:
        if "has_more" in returnable and "next_page" in returnable and isinstance(return_data, str):
            has_more = True
            url = returnable["next_page"].replace(self.url, "")
            while has_more:
                pagination = await self.get(url, pagination=False)
                returnable[return_data] += pagination[return_data]
                has_more = pagination["has_more"]
                if "next_page" in pagination:
                    url = pagination["next_page"].replace(self.url, "")
            return returnable
        return returnable

    # Sets

    async def sets(self) -> APIList:
        returnable_data = "data"
        all_sets = await self.get("sets", return_data=returnable_data)
        return APIList(**all_sets)

    async def set_by_code(self, set_code: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{set_code}", return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_tcgplayer(self, tcgplayer_id: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/tcgplayer/{tcgplayer_id}", return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_id(self, api_id: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{api_id}", return_data=returnable_data)
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
        params = {
            "q": query,
            "unique": unique,
            "order": order,
            "dir": direction,
            "include_extras": include_extras,
            "include_multilinqual": include_multilinqual,
            "include_variations": include_variations,
        }
        search_data = await self.get("cards/search", params=params, return_data=returnable_data)
        returnable = APIList(**search_data)
        return returnable

    async def cards_named(
        self,
        exact: Optional[str] = None,
        fuzzy: Optional[str] = None,
        set_code: Optional[str] = None,
        format_response: str = "json",
        face: str = None,
        version: str = None,
    ) -> Optional[Cards]:
        if format_response != "json":
            raise NotImplementedError
        returnable_data = None
        params = {
            "exact": exact,
            "fuzzy": fuzzy,
            "set": set_code,
            "format": format_response,
            "face": face,
            "version": version,
        }
        named_card_data = await self.get("cards/named", params=params, return_data=returnable_data)
        if named_card_data:
            return Cards(**named_card_data)
        return None

    async def cards_autocomplete(self, query: str) -> Catalogs:
        returnable_data = "data"
        if len(query) <= 2:
            raise ValueError("Must query for more than 2 characters.")
        params = {"q": query}
        autocompletes = await self.get("cards/autocomplete", params=params, return_data=returnable_data)
        return Catalogs(**autocompletes)

    async def cards_random(
        self, query: str, format_response: str = "json", face: str = None, version: str = None
    ) -> Cards:
        if format_response != "json":
            raise NotImplementedError
        returnable_data = None
        params = {
            "q": query,
            "format": format_response,
            "face": face,
            "version": version,
        }
        random_card = await self.get("cards/random", params=params, return_data=returnable_data)
        return Cards(**random_card)

    async def cards_collection(self, identifiers: List[Dict[str, str | int]]) -> APIList:
        returnable_data = "data"
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
        list_of_cards = await self.post("cards/collection", json_data=data, return_data=returnable_data)
        returnable = APIList(**list_of_cards)
        return returnable

    async def card_set_number(
        self,
        set_code: str,
        number: int,
        lang: Optional[str] = "",
        format_response: str = "json",
        face: str = None,
        version: str = None,
    ) -> Optional[Cards]:
        if format_response != "json":
            raise NotImplementedError
        returnable_data = None
        params = {
            "format": format_response,
            "face": face,
            "version": version,
        }
        named_card_data = await self.get(
            f"cards/{set_code}/{number}/{lang}", params=params, return_data=returnable_data
        )
        if named_card_data:
            return Cards(**named_card_data)
        return None

    async def card_by_platform_id(
        self, platform: str, platform_id: str, format_response: str = "json", face: str = None, version: str = None
    ) -> Optional[Cards]:
        if format_response != "json":
            raise NotImplementedError
        if platform_id not in List_of_Platforms:
            raise ValueError(f"{platform} is not a valid platform to pull ID's from")
        if platform not in self.platforms:
            raise ValueError(f"{platform} not in {self.platforms}")
        returnable_data = None
        params = {
            "format": format_response,
            "face": face,
            "version": version,
        }
        named_card_data = await self.get(f"cards/{platform}/{platform_id}", params=params, return_data=returnable_data)
        if named_card_data:
            return Cards(**named_card_data)
        return None

    async def card_by_api_id(self, api_id: str) -> Cards:
        returnable_data = None
        card_data = await self.get(f"cards/{api_id}", return_data=returnable_data)
        return Cards(**card_data)

    # Misc

    async def rulings_by_platform_id(self, platform: str, api_id: str) -> APIList:
        returnable_data = "data"
        if platform not in Rulings_Platforms:
            raise ValueError(f"{platform} not a valid platform for IDs")
        card_rulings = await self.get(f"cards/{platform}/{api_id}/rulings", return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def rulings_by_set_number(self, set_code: str, set_number: str) -> APIList:
        returnable_data = "data"
        card_rulings = await self.get(f"cards/{set_code}/{set_number}/rulings", return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def rulings_by_api_id(self, set_code: str, card_num: str | int) -> APIList:
        returnable_data = "data"
        card_rulings = await self.get(f"cards/{set_code}/{card_num}/rulings", return_data=returnable_data)
        returnable = APIList(**card_rulings)
        return returnable

    async def symbology(self) -> APIList:
        returnable_data = "data"
        symbol_data = await self.get("symbology", return_data=returnable_data)
        returnable = APIList(**symbol_data)
        return returnable

    async def parse_mana(self, cost: str) -> ManaCost:
        returnable_data = None
        params = {"cost": cost}
        mana_cost = await self.get("/symbology/parse-mana", params=params, return_data=returnable_data)
        return ManaCost(**mana_cost)

    async def catalogs(self, catalog: str) -> Catalogs:
        if catalog not in List_of_Catalogs:
            raise ValueError(f"{catalog} is not a valid catalog")
        returnable_data = None
        returnable = await self.get(f"catalog/{catalog}", return_data=returnable_data)
        return Catalogs(**returnable)

    # Bulk Data / Catalog

    async def bulk_data(self) -> APIList:
        returnable_data = "data"
        bulk_data_list = await self.get("bulk-data", return_data=returnable_data)
        returnable = APIList(**bulk_data_list)
        return returnable

    async def bulk_data_by_id(self, api_id: str) -> BulkData:
        returnable_data = None
        bulk_data = await self.get(f"bulk-data/{api_id}", return_data=returnable_data)
        return BulkData(**bulk_data)

    async def bulk_data_by_type(self, api_type: str) -> BulkData:
        returnable_data = None
        bulk_data = await self.get(f"bulk-data/{api_type}", return_data=returnable_data)
        return BulkData(**bulk_data)
