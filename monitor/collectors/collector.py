from __future__ import annotations

import logging
from asyncio import Queue
from pathlib import Path
from typing import Dict

from monitor.events import ChiaEvent


class Collector:
    log: logging.Logger
    event_queue: Queue[ChiaEvent]

    @staticmethod
    async def create(root_path: Path, net_config: Dict, event_queue: Queue[ChiaEvent]) -> Collector:
        raise NotImplementedError

    async def publish_event(self, event: ChiaEvent) -> None:
        await self.event_queue.put(event)

    async def task(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
