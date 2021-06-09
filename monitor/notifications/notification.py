import logging

from apprise import Apprise


class Notification:
    apobj: Apprise
    firing: bool = False

    def __init__(self, apobj: Apprise) -> None:
        self.apobj = apobj
        self.log = logging.getLogger(__name__)

    async def condition(self) -> bool:
        raise NotImplementedError

    async def trigger(self) -> bool:
        raise NotImplementedError

    async def recover(self) -> bool:
        pass

    async def run(self) -> None:
        if await self.condition():
            if not self.firing:
                sent = await self.trigger()
                if sent:
                    self.firing = True
        elif self.firing:
            sent = await self.recover()
            if sent:
                self.firing = False
