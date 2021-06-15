from monitor.database import async_session
from monitor.database.queries import get_harvester_count, get_last_plot_count
from monitor.format import *
from monitor.notifications.notification import Notification


class LostPlotsNotification(Notification):
    last_plot_count: int = None
    highest_plot_count: int = None

    async def condition(self) -> bool:

        async with async_session() as db_session:
            harvester_count = await get_harvester_count(db_session)

            if harvester_count is not None:
                self.last_plot_count = await get_last_plot_count(db_session, harvester_count)

        if harvester_count is not None and self.last_plot_count is not None and self.highest_plot_count is not None and self.last_plot_count < self.highest_plot_count:
            return True
        else:
            self.highest_plot_count = self.last_plot_count
            return False

    async def trigger(self) -> None:
        return self.apobj.notify(title='** 🚨 Farmer Lost Plots! 🚨 **',
                                 body="It seems like your farmer lost some plots\n" +
                                 f"Expected: {self.highest_plot_count}, Found: {self.last_plot_count}\n")

    async def recover(self) -> None:
        return self.apobj.notify(title='** ✅ Farmer Plots recoverd! ✅ **',
                                 body="Your farmer's plot count has recovered to its previous value")
