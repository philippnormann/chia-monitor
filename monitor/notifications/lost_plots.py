from monitor.db import async_session
from monitor.events import HarvesterPlotsEvent
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select


class LostPlotsNotification(Notification):
    last_plot_count = None
    highest_plot_count = None

    async def condition(self) -> bool:
        async with async_session() as db_session:
            result = await db_session.execute(
                select(HarvesterPlotsEvent.plot_count).order_by(HarvesterPlotsEvent.ts.desc()).limit(1))
            self.last_plot_count = result.scalars().first()
        if self.last_plot_count is not None and self.highest_plot_count is not None and self.last_plot_count < self.highest_plot_count:
            return True
        else:
            self.highest_plot_count = self.last_plot_count
            return False

    async def trigger(self) -> None:
        self.apobj.notify(title='** 🚨 Farmer Lost Plots! 🚨 **',
                          body="It seems like your farmer lost some plots\n" +
                          f"Expected: {self.highest_plot_count}, Found: {self.last_plot_count}\n")
        self.last_sync_status = False

    async def recover(self) -> None:
        self.apobj.notify(title='** ✅ Farmer Plots recoverd! ✅ **',
                          body="Your farmer's plot count has recovered to its previous value")
        self.last_sync_status = True
