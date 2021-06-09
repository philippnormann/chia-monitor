from datetime import datetime, timedelta

from monitor.db import async_session
from monitor.events import (BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent,
                            HarvesterPlotsEvent, SignagePointEvent, WalletBalanceEvent)
from monitor.format import *
from monitor.notifications.notification import Notification
from sqlalchemy import select
from sqlalchemy.sql import func


class SummaryNotification(Notification):
    summary_interval = timedelta(hours=1)
    startup_delay = timedelta(seconds=30)
    last_summary_ts: datetime = datetime.now() - summary_interval + startup_delay

    async def condition(self) -> bool:
        if datetime.now() - self.last_summary_ts > self.summary_interval:
            return True
        else:
            return False

    async def trigger(self) -> None:
        async with async_session() as db_session:
            result = await db_session.execute(
                select(HarvesterPlotsEvent).order_by(HarvesterPlotsEvent.ts.desc()).limit(1))
            last_plots: HarvesterPlotsEvent = result.scalars().first()

            result = await db_session.execute(
                select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()).limit(1))
            last_state: BlockchainStateEvent = result.scalars().first()

            result = await db_session.execute(
                select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()).limit(1))
            last_balance: WalletBalanceEvent = result.scalars().first()

            result = await db_session.execute(
                select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()).limit(1))
            last_connections: ConnectionsEvent = result.scalars().first()

            result = await db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
            proofs_found: int = result.scalars().first()

            result = await db_session.execute(
                select(func.avg(FarmingInfoEvent.passed_filter)).where(
                    FarmingInfoEvent.ts >= datetime.now() - self.summary_interval))
            avg_passed_filters: float = result.scalars().first()

            result = await db_session.execute(select(func.min(FarmingInfoEvent.ts)))
            farming_start: datetime = result.scalars().first()

            avg_challenges_per_min = None
            if farming_start is not None:
                farming_since: timedelta = datetime.now() - farming_start
                interval_secs = min(farming_since.seconds, self.summary_interval.seconds)
                if interval_secs > 0:
                    result = await db_session.execute(
                        select(func.count(SignagePointEvent.ts)).where(
                            SignagePointEvent.ts >= datetime.now() - self.summary_interval))
                    num_signage_points = result.scalars().first()
                    avg_challenges_per_min: float = num_signage_points / (interval_secs / 60)

        if all(v is not None for v in [
                last_plots, last_balance, last_state, last_connections, proofs_found, avg_passed_filters,
                avg_challenges_per_min
        ]):
            summary = "\n".join([
                format_plot_count(last_plots.plot_count),
                format_balance(int(last_balance.confirmed)),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
                format_full_node_count(last_connections.full_node_count),
                format_synced(last_state.synced),
                format_proofs(proofs_found),
                format_avg_passed_filter(avg_passed_filters),
                format_challenges_per_min(avg_challenges_per_min)
            ])
            sent = self.apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            if sent:
                self.last_summary_ts = datetime.now()
                return True

        return False
