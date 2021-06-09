from monitor.db import async_session
from monitor.events import BlockchainStateEvent
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select


class LostSyncNotification(Notification):
    async def condition(self) -> bool:
        async with async_session() as db_session:
            result = await db_session.execute(
                select(BlockchainStateEvent.synced).order_by(BlockchainStateEvent.ts.desc()).limit(1))
            sync_status: BlockchainStateEvent = result.scalars().first()
        return sync_status is not None and not sync_status

    async def trigger(self) -> None:
        return self.apobj.notify(
            title='** 🚨 Farmer Lost Sync! 🚨 **',
            body="It seems like your farmer lost its connection to the Chia Network")

    async def recover(self) -> None:
        return self.apobj.notify(title='** ✅ Farmer Synced! ✅ **',
                                 body="Your farmer is successfully synced to the Chia Network again")
