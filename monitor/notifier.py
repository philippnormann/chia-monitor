import asyncio
import logging
from typing import Coroutine, List
from apprise import Apprise, AppriseAsset
from monitor.notifications import FoundProofNotification, LostSyncNotification, SummaryNotification


class Notifier:
    asset = AppriseAsset(async_mode=False)
    status_apobj = Apprise(asset=asset)
    alert_apobj = Apprise(asset=asset)
    notifications = [
        FoundProofNotification(alert_apobj),
        LostSyncNotification(alert_apobj),
        SummaryNotification(status_apobj)
    ]

    def __init__(self, status_url: str, alert_url: str) -> None:
        self.log = logging.getLogger(__name__)
        self.status_apobj.add(status_url)
        self.alert_apobj.add(alert_url)

    async def task(self) -> None:
        while True:
            try:
                tasks = [n.run() for n in self.notifications]
                await asyncio.gather(*tasks)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
