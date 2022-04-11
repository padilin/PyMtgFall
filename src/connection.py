from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import trio
from httpx import AsyncClient
from httpx_caching import CachingClient
from loguru import logger

from schema import BulkData, Cards, CardSymbols, Rulings, Sets


async def ratelimit_request(request):
    logger.warning("Self Rate Limiting for 500ms")
    await trio.sleep(0.5)


async def raise_on_4xx_5xx(response):
    response.raise_for_status()


class ScryfallConnection:
    def __init__(self):
        self.url: str = "https://api.scryfall.com/"

    # Utilities

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, return_data: Optional[str] = "data"
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
        if "has_more" in returnable:
            if returnable["has_more"] and "next_page" in returnable:
                url = returnable["next_page"].replace(self.url, "")
                pagination = await self.get(url)
                if return_data:
                    returnable[return_data].append(pagination[return_data])
                else:
                    returnable.append(pagination)
            return returnable
        else:
            return returnable

    # Bulk Data / Catalog

    async def bulk_data(self) -> List[BulkData]:
        returnable_data = "data"
        bulk_data = await self.get("bulk-data", return_data=returnable_data)
        returnable = list()
        for item in bulk_data[returnable_data]:
            returnable.append(BulkData(**item))
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
    ) -> List[Cards]:
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
        search_data = await self.get("/cards/search", params=params, return_data=returnable_data)
        returnable = list()
        for item in search_data[returnable_data]:
            returnable.append(Cards(**item))
        return returnable

    async def cards_named(
        self,
        exact: Optional[str] = None,
        fuzzy: Optional[str] = None,
        set_code: Optional[str] = None,
        format: str = "json",
        face: str = None,
        version: str = None,
    ) -> Optional[Cards]:
        if format is not "json":
            raise NotImplementedError
        returnable_date = None
        params = {
            "exact": exact,
            "fuzzy": fuzzy,
            "set": set_code,
            "format": format,
            "face": face,
            "version": version,
        }
        named_card_data = await self.get("cards/named", params=params, return_data=returnable_date)
        if named_card_data:
            return Cards(**named_card_data)
        else:
            return None

    async def cards_autocomplete(self, query: str) -> Dict[str, List[str] | str | int]:
        returnable_data = "data"
        params = {"q": query}
        return await self.get("cards/autocomplete", params=params, return_data=returnable_data)

    async def card_by_id(self, api_id: str) -> Cards:
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

    async def symbology(self) -> List[CardSymbols]:
        returnable_data = "data"
        symbol_data = await self.get("symbology")
        returnable = list()
        for item in symbol_data[returnable_data]:
            returnable.append(CardSymbols(**item))
        return returnable

    async def rulings(self, set_code: str, card_num: str | int) -> List[Rulings]:
        returnable_data = "data"
        card_rulings = await self.get(f"cards/{set_code}/{card_num}/rulings")
        returnable = list()
        for item in card_rulings[returnable_data]:
            returnable.append(Rulings(**item))
        return returnable
