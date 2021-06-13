from monitor.db import async_session
from monitor.events import FarmingInfoEvent
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select
from sqlalchemy.sql import func


class LostPlotsNotification(Notification):
    last_plot_count = None
    highest_plot_count = None

    async def condition(self) -> bool:

        async with async_session() as db_session:
            result = await db_session.execute(
                select(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc()).distinct(
                    FarmingInfoEvent.signage_point).limit(2))
            previous_sp: str = result.all()[-1][0]

            if previous_sp is not None:
                result = await db_session.execute(
                    select(func.sum(FarmingInfoEvent.total_plots)).where(
                        FarmingInfoEvent.signage_point == previous_sp))
                self.last_plot_count: int = result.scalars().first()

        if previous_sp is not None and self.last_plot_count is not None and self.highest_plot_count is not None and self.last_plot_count < self.highest_plot_count:
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
