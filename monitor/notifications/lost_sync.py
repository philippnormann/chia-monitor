from monitor.database import session
from monitor.database.queries import get_sync_status
from monitor.format import *
from monitor.notifications.notification import Notification


class LostSyncNotification(Notification):
    def condition(self) -> bool:
        with session() as db_session:
            sync_status = get_sync_status(db_session)
        return sync_status is not None and not sync_status

    def trigger(self) -> None:
        return self.apobj.notify(
            title='** 🚨 Farmer Lost Sync! 🚨 **',
            body="It seems like your farmer lost its connection to the Chia Network")

    def recover(self) -> None:
        return self.apobj.notify(title='** ✅ Farmer Synced! ✅ **',
                                 body="Your farmer is successfully synced to the Chia Network again")
