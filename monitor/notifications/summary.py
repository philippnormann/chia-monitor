from datetime import datetime, timedelta

from apprise import Apprise
from monitor.database import async_session
from monitor.database.queries import (get_blockchain_state, get_connections, get_farming_start,
                                      get_passed_filters_per_minute, get_plot_count, get_plot_size,
                                      get_previous_signage_point, get_proofs_found,
                                      get_signage_points_per_minute, get_wallet_balance)
from monitor.format import *
from monitor.notifications.notification import Notification


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
            last_state = await get_blockchain_state(db_session)
            last_balance = await get_wallet_balance(db_session)
            last_connections = await get_connections(db_session)
            proofs_found = await get_proofs_found(db_session)
            farming_start = await get_farming_start(db_session)
            previous_sp = await get_previous_signage_point(db_session)

            last_plot_count = None
            last_plot_size = None
            avg_signage_points_per_min = None
            avg_passed_filters_per_min = None
            if farming_start is not None:
                farming_since: timedelta = datetime.now() - farming_start
                interval = min(farming_since, self.summary_interval)
                if interval.seconds > 0:
                    last_plot_count = await get_plot_count(db_session, previous_sp)
                    last_plot_size = await get_plot_size(db_session)
                    avg_signage_points_per_min = await get_signage_points_per_minute(
                        db_session, interval)
                    avg_passed_filters_per_min = await get_passed_filters_per_minute(
                        db_session, interval)

        if all(v is not None for v in [
                last_plot_count, last_plot_size, last_balance, last_state, last_connections,
                proofs_found, avg_signage_points_per_min, avg_passed_filters_per_min
        ]):
            summary = "\n".join([
                format_plot_count(last_plot_count),
                format_plot_size(last_plot_size),
                format_synced(last_state.synced),
                format_full_node_count(last_connections.full_node_count),
                format_signage_points_per_min(avg_signage_points_per_min),
                format_passed_filter_per_min(avg_passed_filters_per_min),
                format_proofs(proofs_found),
                format_balance(int(last_balance.confirmed)),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
            ])
            sent = self.apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            if sent:
                self.last_summary_ts = datetime.now()
                return True

        return False
