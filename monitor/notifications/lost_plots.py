from apprise.Apprise import Apprise
from monitor.database import async_session
from monitor.database.queries import get_plot_count
from monitor.format import *
from monitor.notifications.notification import Notification


class LostPlotsNotification(Notification):
    last_plot_count: int
    highest_plot_count: int
    alert_threshold: int

    def __init__(self, apobj: Apprise, alert_threshold: int) -> None:
        super().__init__(apobj)
        self.last_plot_count = None
        self.highest_plot_count = None
        self.alert_threshold = alert_threshold

    async def condition(self) -> bool:

        async with async_session() as db_session:
            self.last_plot_count = await get_plot_count(db_session)

        if self.last_plot_count is not None and self.highest_plot_count is not None and self.last_plot_count < self.highest_plot_count - self.alert_threshold:
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
