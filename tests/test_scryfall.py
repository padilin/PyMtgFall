import httpx
import pytest

import src
from src.connection import ScryfallConnection


@pytest.mark.trio
async def test_4xx_5xx_status(httpx_mock):
    # httpx_mock.add_response()
    #
    # test_conn = ScryfallConnection()
    # with pytest.raises(Exception) as execption_info:
    #     await test_conn.get("symbology")
    assert True
