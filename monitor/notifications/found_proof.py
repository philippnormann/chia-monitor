from monitor.db import async_session
from monitor.events import FarmingInfoEvent
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select
from sqlalchemy.sql import func


class FoundProofNotification(Notification):
    last_proofs_found: int = None

    async def condition(self) -> bool:
        async with async_session() as db_session:
            result = await db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
            proofs_found: int = result.scalars().first()
        if proofs_found is not None and self.last_proofs_found is not None and proofs_found > self.last_proofs_found:
            self.last_proofs_found = proofs_found
            return True
        else:
            return False

    async def trigger(self) -> None:
        return self.apobj.notify(title='** 🤑 Proof found! 🤑 **',
                                       body="Your farm found a new proof")
