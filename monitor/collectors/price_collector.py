from __future__ import annotations

import asyncio
import logging
from asyncio.queues import Queue
from datetime import datetime
from pathlib import Path
from typing import Dict

import aiohttp
from monitor.collectors.collector import Collector
from monitor.database import ChiaEvent
from monitor.database.events import PriceEvent

VS_CURRENCIES = ["USD", "EUR", "BTC", "ETH"]
PRICE_API = f"https://api.coingecko.com/api/v3/simple/price?ids=chia&vs_currencies={','.join(VS_CURRENCIES)}"


class PriceCollector(Collector):
    session: aiohttp.ClientSession

    @staticmethod
    async def create(_root_path: Path, _net_config: Dict, event_queue: Queue[ChiaEvent]) -> Collector:
        self = PriceCollector()
        self.log = logging.getLogger(__name__)
        self.event_queue = event_queue
        self.session = aiohttp.ClientSession()
        return self

    async def get_current_prices(self) -> None:
        async with self.session.get(PRICE_API) as resp:
            result = await resp.json()
            event = PriceEvent(
                ts=datetime.now(),
                usd_cents=int(result["chia"]["usd"] * 100),
                eur_cents=int(result["chia"]["eur"] * 100),
                btc_satoshi=int(result["chia"]["btc"] * 10e7),
                eth_gwei=int(result["chia"]["eth"] * 10e8),
            )
            await self.publish_event(event)

    async def task(self) -> None:
        while True:
            try:
                await self.get_current_prices()
            except Exception as e:
                self.log.warning(f"Error while collecting prices. Trying again... {type(e).__name__}: {e}")
            await asyncio.sleep(10)

    async def close(self) -> None:
        await self.session.close()
