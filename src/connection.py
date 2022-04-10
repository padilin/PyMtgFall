from __future__ import annotations

import os.path
from typing import Any, Dict, List, Optional

from httpx import AsyncClient
from httpx_caching import CachingClient
from loguru import logger

from schema import BulkData, Card


class ScryfallConnection:
    def __init__(self):
        self.url = "https://api.scryfall.com/"

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, return_data: Optional[str] = "data"):
        if params is None:
            params = dict()
        logger.info(f"GET to {self.url}{endpoint}")
        async with CachingClient(AsyncClient()) as client:
            r = await client.get(f"{self.url}{endpoint}", params=sorted(params))
            logger.info(f"GET {r.status_code}")
            sanitized = await self.sanitize_data(r.json())
            # logger.debug(f"after sanitize {sanitized}")
            returnable = await self.pagination_list(return_data, sanitized)
            # logger.debug(f"after pagination {returnable}")
            return returnable

    async def sanitize_data(self, data: Dict[str, Any] | List[Dict[str, Any]]) -> Dict[str, Any] | List[Dict[str, Any]]:
        if isinstance(data, list):
            # logger.debug("Hit a list.")
            returnable = list()
            for item in data:
                if isinstance(item, dict):
                    returnable.append(await self.sanitize_data(item))
                else:
                    returnable.append(item)
            return returnable
        elif isinstance(data, dict):
            # logger.debug(data)
            if "id" in data:
                # logger.debug("replacing 'id' with 'api_id' in data found.")
                data["api_id"] = data.pop("id")
            if "object" in data:
                # logger.debug("replacing 'object' with 'obj' in data found.")
                data["obj"] = data.pop("object")
            returnable = dict()
            for k, v in data.items():
                # logger.debug(f"Processing data {k}: {v}")
                returnable[k] = await self.sanitize_data(v)
            # logger.debug(returnable)
            return returnable
        else:
            return data

    async def pagination_list(
        self, return_data: Optional[str], returnable: Dict[str, Any] | List[Dict[str, Any]]
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        if "has_more" in returnable:
            # logger.debug("found has_more")
            if returnable["has_more"] and "next_page" in returnable:
                # logger.debug("has_more true and has next_page")
                url = returnable["next_page"].replace(self.url, "")
                pagination = await self.get(url)
                if return_data:
                    returnable[return_data].append(pagination[return_data])
                else:
                    returnable.append(pagination)
            return returnable
        else:
            return returnable

    async def bulk_data(self):
        returnable_data = "data"
        bulk_data = await self.get("bulk-data", return_data=returnable_data)
        returnable = list()
        # logger.debug(bulk_data)
        for item in bulk_data[returnable_data]:
            returnable.append(BulkData(**item))
        return returnable

    async def card(self, api_id):
        returnable_data = None
        card_data = await self.get(f"cards/{api_id}", return_data=returnable_data)
        return Card(**card_data)
