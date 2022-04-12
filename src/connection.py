from __future__ import annotations

from typing import Any, Dict, List, Optional

import trio
from httpx import AsyncClient
from httpx_caching import CachingClient
from loguru import logger

from schema import APIList, BulkData, Cards, CardSymbols, Rulings, Sets


async def ratelimit_request(request):
    logger.warning("Self Rate Limiting for 500ms")
    await trio.sleep(0.5)


async def raise_on_4xx_5xx(response):
    if response.status_code >= 400:
        error_response = await response.aread()
        logger.error(f"Direct API error: {error_response.decode('utf-8')}")
    response.raise_for_status()


class ScryfallConnection:
    def __init__(self):
        self.url: str = "https://api.scryfall.com/"
        self.platforms: List[str] = ["multiverse", "mtgo", "arena", "tcgplayer", "cardmarket"]

    # Utilities

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        return_data: Optional[str] = "data",
        pagination: bool = True,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        if params is None:
            params = dict()
        logger.info(f"GET to {self.url}{endpoint}")
        async with CachingClient(
            AsyncClient(event_hooks={"request": [ratelimit_request], "response": [raise_on_4xx_5xx]})
        ) as client:
            r = await client.get(f"{self.url}{endpoint}", params=params)
            logger.info(f"GET {r.status_code} at {r.url}")
            sanitized = await self.sanitize_data(r.json())
            if pagination:
                returnable = await self.pagination_list(return_data, sanitized)
                return returnable
            return sanitized

    async def post(self, endpoint: str, json_data: Dict[str, Any], return_data: Optional[str] = "data"):
        logger.info(f"POST to {self.url}{endpoint}")
        async with CachingClient(
            AsyncClient(event_hooks={"request": [ratelimit_request], "response": [raise_on_4xx_5xx]})
        ) as client:
            r = await client.post(f"{self.url}{endpoint}", json=json_data)
            logger.info(f"POST {r.status_code} at {r.url}")
            sanitized = await self.sanitize_data(r.json())
            returnable = await self.pagination_list(return_data, sanitized)
            return returnable

    async def sanitize_data(self, data: Dict[str, Any] | List[Dict[str, Any]]) -> Dict[str, Any] | List[Dict[str, Any]]:
        if isinstance(data, list):
            returnable = list()
            for item in data:
                if isinstance(item, dict):
                    returnable.append(await self.sanitize_data(item))
                else:
                    returnable.append(item)
            return returnable
        elif isinstance(data, dict):
            if "id" in data:
                data["api_id"] = data.pop("id")
            if "object" in data:
                data["obj"] = data.pop("object")
            returnable = dict()
            for k, v in data.items():
                returnable[k] = await self.sanitize_data(v)
            return returnable
        else:
            return data

    async def pagination_list(
        self, return_data: Optional[str], returnable: Dict[str, Any] | List[Dict[str, Any]]
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        if "has_more" in returnable and "next_page" in returnable:
            has_more = True
            url = returnable["next_page"].replace(self.url, "")
            while has_more:
                pagination = await self.get(url, pagination=False)
                returnable[return_data] += pagination[return_data]
                has_more = pagination["has_more"]
                if "next_page" in pagination:
                    url = pagination["next_page"].replace(self.url, "")
            return returnable
        else:
            return returnable

    # Bulk Data / Catalog

    async def bulk_data(self) -> APIList:
        returnable_data = "data"
        bulk_data = await self.get("bulk-data", return_data=returnable_data)
        returnable = APIList(**bulk_data)
        return returnable

    # Cards

    async def cards_search(
        self,
        q: str,
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
            "q": q,
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
        if format != "json":
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
        else:
            return None

    async def cards_autocomplete(self, q: str) -> Dict[str, List[str] | str | int]:  # TODO: double check this
        returnable_data = "data"
        params = {"q": q}
        return await self.get("cards/autocomplete", params=params, return_data=returnable_data)

    async def cards_random(self, q: str, format_response: str = "json", face: str = None, version: str = None) -> Cards:
        if format_response is not "json":
            raise NotImplementedError
        returnable_data = None
        params = {
            "q": q,
            "format": format_response,
            "face": face,
            "version": version,
        }
        random_card = await self.get("cards/random", params=params, return_data=returnable_data)
        return Cards(**random_card)

    async def cards_collection(self, identifiers: List[Dict[str, str]]) -> APIList:
        returnable_data = "data"
        data = {"identifiers": identifiers}
        list_of_cards = await self.post("cards/collection", json_data=data)
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
        else:
            return None

    async def card_by_platform_id(
        self, platform: str, platform_id: str, format_response: str = "json", face: str = None, version: str = None
    ) -> Optional[Cards]:
        if format_response != "json":
            raise NotImplementedError
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
        else:
            return None

    async def card_by_api_id(self, api_id: str) -> Cards:
        returnable_data = None
        card_data = await self.get(f"cards/{api_id}", return_data=returnable_data)
        return Cards(**card_data)

    # Sets

    async def set_by_id(self, api_id: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{api_id}", return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_code(self, set_code: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{set_code}", return_data=returnable_data)
        return Sets(**set_data)

    # Misc

    async def symbology(self) -> APIList:
        returnable_data = "data"
        symbol_data = await self.get("symbology")
        returnable = APIList(**symbol_data)
        return returnable

    async def rulings(self, set_code: str, card_num: str | int) -> APIList:
        returnable_data = "data"
        card_rulings = await self.get(f"cards/{set_code}/{card_num}/rulings")
        returnable = APIList(**card_rulings)
        return returnable
