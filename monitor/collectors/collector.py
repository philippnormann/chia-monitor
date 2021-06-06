from __future__ import annotations

import logging
from monitor.events import ChiaEvent
from pathlib import Path
from typing import Coroutine, Dict
from asyncio import Queue


class Collector:
    log: logging.Logger
    event_queue: Queue[ChiaEvent]

    @staticmethod
    async def create(root_path: Path, net_config: Dict,
                     event_queue: Queue[ChiaEvent]) -> Collector:
        raise NotImplementedError

    async def task(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
