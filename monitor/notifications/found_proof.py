from monitor.database.queries import get_proofs_found
from monitor.database import async_session
from monitor.database.events import FarmingInfoEvent
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select
from sqlalchemy.sql import func


class FoundProofNotification(Notification):
    last_proofs_found: int = None

    async def condition(self) -> bool:
        async with async_session() as db_session:
            proofs_found = await get_proofs_found(db_session)
        if proofs_found is not None and self.last_proofs_found is not None and proofs_found > self.last_proofs_found:
            self.last_proofs_found = proofs_found
            return True
        else:            
            self.last_proofs_found = proofs_found
            return False

    async def trigger(self) -> None:
        return self.apobj.notify(title='** 🤑 Proof found! 🤑 **',
                                       body="Your farm found a new proof")
