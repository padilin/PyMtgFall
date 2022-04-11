from __future__ import annotations

from typing import Any, Dict, List, Optional

import trio
from httpx import AsyncClient
from httpx_caching import CachingClient
from loguru import logger

from schema import BulkData, Cards, CardSymbols, Rulings, Sets


async def ratelimit_request(request):
    logger.warning("Self Rate Limiting for 500ms")
    await trio.sleep(0.5)


class ScryfallConnection:
    def __init__(self):
        self.url: str = "https://api.scryfall.com/"

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, return_data: Optional[str] = "data"
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        if params is None:
            params = dict()
        logger.info(f"GET to {self.url}{endpoint}")
        async with CachingClient(AsyncClient(event_hooks={"request": [ratelimit_request]})) as client:
            r = await client.get(f"{self.url}{endpoint}", params=sorted(params))
            logger.info(f"GET {r.status_code}")
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

    async def bulk_data(self) -> List[BulkData]:
        returnable_data = "data"
        bulk_data = await self.get("bulk-data", return_data=returnable_data)
        returnable = list()
        for item in bulk_data[returnable_data]:
            returnable.append(BulkData(**item))
        return returnable

    async def card_by_id(self, api_id: str) -> Cards:
        returnable_data = None
        card_data = await self.get(f"cards/{api_id}", return_data=returnable_data)
        return Cards(**card_data)

    async def set_by_id(self, api_id: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{api_id}", return_data=returnable_data)
        return Sets(**set_data)

    async def set_by_code(self, set_code: str) -> Sets:
        returnable_data = None
        set_data = await self.get(f"sets/{set_code}", return_data=returnable_data)
        return Sets(**set_data)

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
