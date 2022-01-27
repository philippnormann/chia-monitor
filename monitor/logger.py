import logging

from monitor.database.events import (BlockchainStateEvent, ChiaEvent, ConnectionsEvent, FarmingInfoEvent,
                                     HarvesterPlotsEvent, PoolStateEvent, PriceEvent, SignagePointEvent, WalletBalanceEvent)
from monitor.database.queries import get_signage_point_ts
from monitor.format import *


class ChiaLogger:
    last_signage_point: SignagePointEvent = None

    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)

    def process_event(self, event: ChiaEvent) -> None:
        if isinstance(event, HarvesterPlotsEvent):
            self.update_harvester_metrics(event)
        elif isinstance(event, FarmingInfoEvent):
            self.update_farmer_metrics(event)
        elif isinstance(event, ConnectionsEvent):
            self.update_connection_metrics(event)
        elif isinstance(event, BlockchainStateEvent):
            self.update_blockchain_state_metrics(event)
        elif isinstance(event, WalletBalanceEvent):
            self.update_wallet_balance_metrics(event)
        elif isinstance(event, SignagePointEvent):
            self.update_signage_point_metrics(event)
        elif isinstance(event, PoolStateEvent):
            self.update_pool_state_metrics(event)
        elif isinstance(event, PriceEvent):
            self.update_price_metrics(event)

    def update_harvester_metrics(self, event: HarvesterPlotsEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_og_plot_count(event.plot_count))
        self.log.info(format_portable_plot_count(event.portable_plot_count))
        self.log.info(format_og_plot_size(event.plot_size))
        self.log.info(format_portable_plot_size(event.portable_plot_size))
        self.log.info(format_hostname(event.host, fix_indent=True))

    def update_farmer_metrics(self, event: FarmingInfoEvent):
        self.log.info("-" * 64)
        self.log.info(format_challenge_hash(event.challenge_hash))
        self.log.info(format_signage_point(event.signage_point))
        self.log.info(format_plot_count(event.total_plots))
        self.log.info(format_passed_filter(event.passed_filter))
        self.log.info(format_proofs(event.proofs))
        self.log.info(format_proofs(event.proofs))
        if self.last_signage_point.signage_point == event.signage_point:
            signage_point_ts = self.last_signage_point.ts
        else:
            signage_point_ts = get_signage_point_ts(event.signage_point)
        lookup_time = event.ts - signage_point_ts
        self.log.info(format_lookup_time(lookup_time.total_seconds(), fix_indent=True))

    def update_connection_metrics(self, event: ConnectionsEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_full_node_count(event.full_node_count))
        self.log.info(format_full_node_count(event.farmer_count, "Farmer"))
        self.log.info(format_full_node_count(event.harvester_count, "Harvester"))

    def update_blockchain_state_metrics(self, event: BlockchainStateEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_space(int(event.space)))
        self.log.info(format_diffculty(event.diffculty))
        self.log.info(format_peak_height(int(event.peak_height), fix_indent=True))
        self.log.info(format_synced(event.synced))
        self.log.info(format_mempool_size(event.mempool_size))

    def update_wallet_balance_metrics(self, event: WalletBalanceEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_balance(int(event.confirmed)))
        self.log.info(format_farmed(int(event.farmed)))

    def update_signage_point_metrics(self, event: SignagePointEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_signage_point_index(event.signage_point_index))
        self.log.info(format_challenge_hash(event.challenge_hash))
        self.log.info(format_signage_point(event.signage_point))
        self.last_signage_point = event

    def update_pool_state_metrics(self, event: PoolStateEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_current_points(event.current_points))
        self.log.info(format_pool_difficulty(event.current_difficulty))
        self.log.info(format_points_found(event.points_found_since_start))
        self.log.info(format_points_acknowledged(event.points_acknowledged_since_start))
        self.log.info(format_points_found_24h(event.points_found_24h))
        self.log.info(format_points_acknowledged_24h(event.points_acknowledged_24h))
        self.log.info(format_pool_errors_24h(event.num_pool_errors_24h))

    def update_price_metrics(self, event: PriceEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_price(event.usd_cents / 100, "USD", fix_indent=True))
        self.log.info(format_price(event.eur_cents / 100, "EUR", fix_indent=True))
        self.log.info(format_price(event.btc_satoshi / 10e7, "BTC", fix_indent=True))
        self.log.info(format_price(event.eth_gwei / 10e8, "ETH", fix_indent=True))
