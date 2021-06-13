from datetime import datetime, timedelta

from apprise import Apprise
from monitor.db import async_session
from monitor.events import (BlockchainStateEvent, ConnectionsEvent,
                            FarmingInfoEvent, HarvesterPlotsEvent,
                            SignagePointEvent, WalletBalanceEvent)
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select
from sqlalchemy.sql import func


class SummaryNotification(Notification):
    summary_interval: timedelta
    startup_delay: timedelta
    last_summary_ts: datetime

    def __init__(self, apobj: Apprise, summary_interval_minutes: int) -> None:
        super().__init__(apobj)
        self.startup_delay = timedelta(seconds=30)
        self.summary_interval = timedelta(minutes=summary_interval_minutes)
        self.last_summary_ts: datetime = datetime.now() - self.summary_interval + self.startup_delay

    async def condition(self) -> bool:
        if datetime.now() - self.last_summary_ts > self.summary_interval:
            return True
        else:
            return False

    async def trigger(self) -> None:
        async with async_session() as db_session:
            result = await db_session.execute(
                select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()))
            last_state: BlockchainStateEvent = result.scalars().first()

            result = await db_session.execute(
                select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()))
            last_balance: WalletBalanceEvent = result.scalars().first()

            result = await db_session.execute(
                select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()))
            last_connections: ConnectionsEvent = result.scalars().first()

            result = await db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
            proofs_found: int = result.scalars().first()

            result = await db_session.execute(
                select(func.min(FarmingInfoEvent.ts)).where(
                    FarmingInfoEvent.ts >= datetime.now() - self.summary_interval))
            farming_start: datetime = result.scalars().first()

            result = await db_session.execute(
                select(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc()).distinct(
                    FarmingInfoEvent.signage_point).limit(2))
            previous_sp: str = result.all()[-1][0]

            last_plots = None
            avg_challenges_per_min = None
            avg_passed_filters_per_min = None
            if farming_start is not None:
                farming_since: timedelta = datetime.now() - farming_start
                interval_secs = min(farming_since.seconds, self.summary_interval.seconds)
                if interval_secs > 0:
                    result = await db_session.execute(
                        select(func.sum(FarmingInfoEvent.total_plots)).where(
                            FarmingInfoEvent.signage_point == previous_sp))
                    last_plots: int = result.scalars().first()

                    result = await db_session.execute(
                        select(func.count(SignagePointEvent.ts)).where(
                            SignagePointEvent.ts >= datetime.now() - self.summary_interval))
                    num_signage_points = result.scalars().first()
                    avg_challenges_per_min: float = num_signage_points / (interval_secs / 60)

                    result = await db_session.execute(
                        select(func.sum(FarmingInfoEvent.passed_filter)).where(
                            FarmingInfoEvent.ts >= datetime.now() - self.summary_interval))
                    passed_filters = result.scalars().first()
                    avg_passed_filters_per_min: float = passed_filters / (interval_secs / 60)

        if all(v is not None for v in [
                last_plots, last_balance, last_state, last_connections, proofs_found,
                avg_challenges_per_min, avg_passed_filters_per_min
        ]):
            summary = "\n".join([
                format_plot_count(last_plots),
                format_balance(int(last_balance.confirmed)),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
                format_full_node_count(last_connections.full_node_count),
                format_synced(last_state.synced),
                format_proofs(proofs_found),
                format_challenges_per_min(avg_challenges_per_min),
                format_passed_filter_per_min(avg_passed_filters_per_min)
            ])
            sent = self.apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            if sent:
                self.last_summary_ts = datetime.now()
                return True

        return False
