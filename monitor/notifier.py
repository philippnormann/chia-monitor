import asyncio
import logging
from asyncio.exceptions import CancelledError
from datetime import datetime, timedelta
from typing import Coroutine, List

import apprise
from sqlalchemy import select
from sqlalchemy.sql import func

from monitor.db import async_session
from monitor.events import (BlockchainStateEvent, ConnectionsEvent,
                            FarmingInfoEvent, HarvesterPlotsEvent,
                            WalletBalanceEvent)
from monitor.format import *


class Notifier:
    asset = apprise.AppriseAsset(async_mode=False)
    status_apobj = apprise.Apprise(asset=asset)
    alert_apobj = apprise.Apprise(asset=asset)

    summary_interval = timedelta(hours=1)
    last_summary_ts: datetime = datetime.now() - summary_interval

    last_proofs_found = None
    last_sync_status = True

    def __init__(self, status_url: str, alert_url: str) -> None:
        self.log = logging.getLogger(__name__)
        self.status_apobj.add(status_url)
        self.alert_apobj.add(alert_url)

    @property
    def alerts(self) -> List[Coroutine]:
        return [self.lost_sync(), self.found_proof()]

    async def lost_sync(self) -> None:
        async with async_session() as db_session:
            result = await db_session.execute(
                select(BlockchainStateEvent.synced).order_by(BlockchainStateEvent.ts.desc()).limit(1))
            new_sync_status: BlockchainStateEvent = result.scalars().first()

        if new_sync_status is not None:
            if self.last_sync_status and not new_sync_status:
                self.alert_apobj.notify(
                    title='** 🚨 Farmer Lost Sync! 🚨 **',
                    body="It seems like your farmer lost it's connection to the Chia Network")
                self.last_sync_status = False

            if not self.last_sync_status and new_sync_status:
                self.alert_apobj.notify(title='** ✅ Farmer Successfully Synced! ✅ **',
                                        body="Your farmer is successfully synced to the Chia Network")
                self.last_sync_status = True

    async def found_proof(self) -> None:
        async with async_session() as db_session:
            result = await db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
            proofs_found: int = result.scalars().first()

        if proofs_found is not None and self.last_proofs_found is not None and proofs_found > self.last_proofs_found:
            self.alert_apobj.notify(title='** 🤑 Proof found! 🤑 **', body="Your farm found a new proof")

        self.last_proofs_found = proofs_found

    async def send_summary(self) -> None:
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
            self.status_apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            self.last_summary_ts = datetime.now()

    async def task(self) -> None:
        while True:
            try:
                await asyncio.gather(*self.alerts)
                if datetime.now() - self.last_summary_ts > self.summary_interval:
                    await self.send_summary()
                await asyncio.sleep(1)
            except CancelledError:
                break
