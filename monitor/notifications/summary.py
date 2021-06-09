from datetime import datetime, timedelta

from monitor.db import async_session
from monitor.events import (BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent,
                            HarvesterPlotsEvent, WalletBalanceEvent)
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

        if all(v is not None
               for v in [last_plots, last_balance, last_state, last_connections, proofs_found]):
            summary = "\n".join([
                format_plot_count(last_plots.plot_count),
                format_balance(int(last_balance.confirmed)),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
                format_full_node_count(last_connections.full_node_count),
                format_synced(last_state.synced),
                format_proofs(proofs_found),
            ])
            sent = self.apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            if sent:
                self.last_summary_ts = datetime.now()
                return True

        return False
