from __future__ import annotations

import logging
from pathlib import Path
from typing import Coroutine, Dict, List


class Exporter:
    log: logging.Logger

    @staticmethod
    async def create(root_path: Path, net_config: Dict) -> Exporter:
        raise NotImplementedError

    @property
    def coros(self) -> List[Coroutine]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
