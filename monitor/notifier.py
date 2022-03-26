import logging
from dataclasses import dataclass
from threading import Thread
from time import sleep

from apprise import Apprise, AppriseAsset
from sqlalchemy.exc import OperationalError

from monitor.notifications import (FoundProofNotification, LostPlotsNotification, LostSyncNotification,
                                   PaymentNotification, SummaryNotification)


@dataclass(frozen=True)
class NotifierConfiguration:
    enable_notifications: bool
    refresh_interval_seconds: int
    status_interval_minutes: int
    lost_plots_alert_threshold: int
    disable_proof_found_alert: bool
    status_url: str
    alert_url: str


class Notifier:
    asset = AppriseAsset(async_mode=False)
    status_apobj = Apprise(asset=asset)
    alert_apobj = Apprise(asset=asset)
    refresh_interval: int
    stopped = False

    def __init__(self, config: NotifierConfiguration) -> None:
        self.log = logging.getLogger(__name__)
        self.status_apobj.add(config.status_url)
        self.alert_apobj.add(config.alert_url)
        self.refresh_interval = config.refresh_interval_seconds
        self.notifications = [
            LostSyncNotification(self.alert_apobj),
            LostPlotsNotification(self.alert_apobj, config.lost_plots_alert_threshold),
            PaymentNotification(self.alert_apobj),
            SummaryNotification(self.status_apobj, config.status_interval_minutes),
        ]
        if not config.disable_proof_found_alert:
            self.notifications.append(FoundProofNotification(self.status_apobj))

    def task(self) -> None:
        while True:
            try:
                for notification in self.notifications:
                    notification.run()
                sleep(self.refresh_interval)
            except OperationalError:
                logging.exception(
                    f"Failed to retrieve event from DB. Please initialize DB using: 'pipenv run alembic upgrade head'"
                )
                break
            if self.stopped:
                break

    def start(self) -> None:
        self.thread = Thread(target=self.task)
        self.thread.start()

    def stop(self) -> None:
        self.stopped = True
        self.thread.join()
