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
    
    async def trigger(self) -> None:
        raise NotImplementedError
    
    async def recover(self) -> None:
        pass
        
    async def run(self) -> None:
        if await self.condition():
            if not self.firing:
                await self.trigger()
                self.firing = True
        elif self.firing:
            await self.recover()
            self.firing = False
        
