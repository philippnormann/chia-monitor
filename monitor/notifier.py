import asyncio
import logging
from threading import Thread
from typing import Coroutine, List
from datetime import datetime, timedelta
import apprise
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from monitor.events import BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent, WalletBalanceEvent
from monitor.db import async_session
from monitor.format import *


class Notifier:
    asset = apprise.AppriseAsset(async_mode=False)
    status_apobj = apprise.Apprise(asset=asset)
    alert_apobj = apprise.Apprise(asset=asset)
    db_session: AsyncSession
    worker_thread: Thread

    summary_interval = timedelta(hours=1)
    last_summary_ts: datetime = datetime.now() - summary_interval

    last_proofs_found = None
    last_synced = True

    stop = False

    def __init__(self, status_url: str, alert_url: str) -> None:
        self.log = logging.getLogger(__name__)
        self.db_session = async_session()
        self.status_apobj.add(status_url)
        self.alert_apobj.add(alert_url)
        self.worker_thread = Thread(target=asyncio.run, args=(self.worker(), ))
        self.worker_thread.start()

    async def send_summary(self) -> None:
        result = await self.db_session.execute(
            select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()).limit(1))
        last_state: BlockchainStateEvent = result.scalars().first()

        result = await self.db_session.execute(
            select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()).limit(1))
        last_balance: WalletBalanceEvent = result.scalars().first()

        result = await self.db_session.execute(
            select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()).limit(1))
        last_connections: ConnectionsEvent = result.scalars().first()

        result = await self.db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
        proofs_found: int = result.scalars().first()

        if last_state and last_balance:
            summary = "\n".join([
                format_balance(int(last_balance.confirmed)),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
                format_full_node_count(last_connections.full_node_count),
                format_synced(last_state.synced),
                format_proofs(proofs_found)
            ])
            self.status_apobj.notify(title='** Farm Status **', body=summary)
            self.last_summary_ts = datetime.now()

    async def lost_sync(self) -> None:
        result = await self.db_session.execute(
            select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()).limit(1))
        new_state: BlockchainStateEvent = result.scalars().first()
        if new_state:
            if self.last_synced and not new_state.synced:
                self.alert_apobj.notify(
                    title='** 🚨 Farmer Lost Sync! 🚨 **',
                    body="It seems like your farmer lost it's connection to the Chia Network")
                self.last_synced = False
            if not self.last_synced and new_state.synced:
                self.alert_apobj.notify(title='** ✅ Farmer Successfully Synced! ✅ **',
                                        body="Your farmer is successfully synced to the Chia Network")
                self.last_synced = True

    @property
    def alerts(self) -> List[Coroutine]:
        return [self.lost_sync()]

    async def worker(self) -> None:
        while not self.stop:
            await asyncio.gather(*self.alerts)
            if datetime.now() - self.last_summary_ts > self.summary_interval:
                await self.send_summary()
            for _ in range(10):
                if not self.stop:
                    await asyncio.sleep(1)
                else:
                    break

    async def close(self) -> None:
        self.stop = True
        self.worker_thread.join()
        await self.db_session.close()
