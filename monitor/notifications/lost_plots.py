from monitor.db import async_session
from monitor.events import ConnectionsEvent, FarmingInfoEvent
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
                select(ConnectionsEvent.harvester_count).order_by(ConnectionsEvent.ts.desc()))
            harvester_count: str = result.scalars().first()

            if harvester_count is not None:
                sub_query = select([
                    func.sum(FarmingInfoEvent.total_plots).label("plot_count"),
                    func.count(FarmingInfoEvent.ts).label("harvester_count")
                ]).group_by(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc())
                result = await db_session.execute(
                    select(sub_query.c.plot_count).where(sub_query.c.harvester_count == harvester_count))
                self.last_plot_count: int = result.scalars().first()
        
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
