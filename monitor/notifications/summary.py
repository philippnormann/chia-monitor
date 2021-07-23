from datetime import datetime, timedelta

from apprise import Apprise
from monitor.database import async_session
from monitor.database.queries import (get_blockchain_state, get_connections,
                                      get_farming_start, get_og_plot_count,
                                      get_og_plot_size,
                                      get_passed_filters_per_minute,
                                      get_plot_delta, get_portable_plot_count,
                                      get_portable_plot_size, get_proofs_found,
                                      get_signage_points_per_minute,
                                      get_wallet_balance)
from monitor.format import *
from monitor.notifications.notification import Notification

SECONDS_PER_BLOCK = (24 * 3600) / 4608


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
            last_og_plot_count = await get_og_plot_count(db_session)
            last_portable_plot_count = await get_portable_plot_count(db_session)
            last_og_plot_size = await get_og_plot_size(db_session)
            last_portable_plot_size = await get_portable_plot_size(db_session)
            plot_count_delta, plot_size_delta = await get_plot_delta(db_session)

            signage_points_per_min = None
            passed_filters_per_min = None
            if farming_start is not None:
                farming_since: timedelta = datetime.now() - farming_start
                interval = min(farming_since, self.summary_interval)
                if interval.seconds > 0:
                    signage_points_per_min = await get_signage_points_per_minute(db_session, interval)
                    passed_filters_per_min = await get_passed_filters_per_minute(db_session, interval)

        if all(v is not None for v in [
                last_og_plot_count, last_portable_plot_count, last_og_plot_size, last_portable_plot_size,
                last_balance, last_state, last_connections, proofs_found, signage_points_per_min,
                passed_filters_per_min
        ]):
            proportion = (last_og_plot_size + last_portable_plot_size) / int(last_state.space)
            expected_minutes_to_win = int((SECONDS_PER_BLOCK / 60) / proportion)
            summary = "\n".join([
                format_og_plot_count(last_og_plot_count),
                format_portable_plot_count(last_portable_plot_count),
                format_og_plot_size(last_og_plot_size),
                format_portable_plot_size(last_portable_plot_size),
                format_plot_delta_24h(plot_count_delta, plot_size_delta),
                format_signage_points_per_min(signage_points_per_min),
                format_passed_filter_per_min(passed_filters_per_min),
                format_proofs(proofs_found),
                format_balance(int(last_balance.confirmed)),
                format_expected_time_to_win(expected_minutes_to_win),
                format_space(int(last_state.space)),
                format_peak_height(last_state.peak_height),
                format_full_node_count(last_connections.full_node_count),
                format_synced(last_state.synced, last_state.peak_height, last_state.max_height),
            ])
            sent = self.apobj.notify(title='** 👨‍🌾 Farm Status 👩‍🌾 **', body=summary)
            if sent:
                self.last_summary_ts = datetime.now()
                return True

        return False
