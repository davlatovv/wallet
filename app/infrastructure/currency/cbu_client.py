import aiohttp
from decimal import Decimal

_CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"


async def get_usd_rate() -> Decimal:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(_CBU_URL) as resp:
            data = await resp.json(content_type=None)
    for item in data:
        if item.get("Ccy") == "USD":
            return Decimal(item["Rate"])
    raise ValueError("USD rate not found in CBU response")
