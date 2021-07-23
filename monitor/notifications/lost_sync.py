from monitor.database.queries import get_sync_status
from monitor.database import async_session
from monitor.format import *
from monitor.notifications.notification import Notification


class LostSyncNotification(Notification):
    async def condition(self) -> bool:
        async with async_session() as db_session:
            sync_status = await get_sync_status(db_session)
        return sync_status is not None and sync_status == "0"

    async def trigger(self) -> None:
        return self.apobj.notify(
            title='** 🚨 Farmer Lost Sync! 🚨 **',
            body="It seems like your farmer lost its connection to the Chia Network")

    async def recover(self) -> None:
        return self.apobj.notify(title='** ✅ Farmer Synced! ✅ **',
                                 body="Your farmer is successfully synced to the Chia Network again")
