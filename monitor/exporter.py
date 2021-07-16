import logging

from prometheus_client import Counter, Gauge, start_http_server

from monitor.database.events import (BlockchainStateEvent, ChiaEvent, ConnectionsEvent, FarmingInfoEvent,
                                     HarvesterPlotsEvent, PoolStateEvent, PriceEvent, SignagePointEvent,
                                     WalletBalanceEvent)
from monitor.format import *


class ChiaExporter:
    # Wallet metrics
    total_balance_gauge = Gauge('chia_confirmed_total_mojos', 'Sum of confirmed wallet balances')
    total_farmed_gauge = Gauge('chia_farmed_total_mojos', 'Total chia farmed')

    # Full node metrics
    network_space_gauge = Gauge('chia_network_space', 'Approximation of current netspace')
    diffculty_gauge = Gauge('chia_diffculty', 'Current networks farming difficulty')
    height_gauge = Gauge('chia_peak_height', 'Block height of the current peak')
    sync_gauge = Gauge('chia_sync_status', 'Sync status of the connected full node')
    connections_gauge = Gauge('chia_connections_count',
                              'Count of peers that the node is currently connected to', ["type"])

    # Harvester metrics
    plot_count_gauge = Gauge('chia_plot_count', 'OG plot count being farmed by harvester', ["host"])
    plot_size_gauge = Gauge('chia_plot_size', 'Size of OG plots being farmed by harvester', ["host"])
    portable_plot_count_gauge = Gauge('chia_portable_plot_count',
                                      'Portable plot count being farmed by harvester', ["host"])
    portable_plot_size_gauge = Gauge('chia_portable_plot_size',
                                     'Size of portable plots being farmed by harvester', ["host"])

    # Farmer metrics
    signage_point_counter = Counter('chia_signage_points', 'Received signage points')
    signage_point_index_gauge = Gauge('chia_signage_point_index', 'Received signage point index')
    challenges_counter = Counter('chia_block_challenges', 'Attempted block challenges')
    passed_filter_counter = Counter('chia_plots_passed_filter', 'Plots passed filter')
    proofs_found_counter = Counter('chia_proofs_found', 'Proofs found')

    # Pool metrics
    current_pool_points_gauge = Gauge('chia_current_pool_points',
                                      'Number of pooling points you have collected during this round',
                                      ['p2', 'url'])
    current_pool_difficulty_gauge = Gauge('chia_current_pool_difficulty',
                                          'Difficulty of partials you are submitting', ['p2', 'url'])
    pool_points_found_since_start_gauge = Gauge('chia_pool_points_found_since_start',
                                                'Total number of pooling points found', ['p2', 'url'])
    pool_points_acknowledged_since_start_gauge = Gauge('chia_pool_points_acknowledged_since_start',
                                                       'Total number of pooling points acknowledged',
                                                       ['p2', 'url'])
    num_pool_errors_24h_gauge = Gauge('chia_num_pool_errors_24h',
                                      'Number of pool errors during the last 24 hours', ['p2', 'url'])

    # Price metrics
    price_usd_cents_gauge = Gauge('chia_price_usd_cent', 'Current Chia price in USD cent')
    price_eur_cents_gauge = Gauge('chia_price_eur_cent', 'Current Chia price in EUR cent')
    price_btc_satoshi_gauge = Gauge('chia_price_btc_satoshi', 'Current Chia price in BTC satoshi')
    price_eth_gwei_gauge = Gauge('chia_price_eth_gwei', 'Current Chia price in ETH gwei')

    def __init__(self, port: int) -> None:
        self.log = logging.getLogger(__name__)
        start_http_server(port)

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
        self.plot_count_gauge.labels(event.host).set(event.plot_count)
        self.log.info(format_og_plot_count(event.plot_count))
        self.portable_plot_count_gauge.labels(event.host).set(event.portable_plot_count)
        self.log.info(format_portable_plot_count(event.portable_plot_count))
        self.plot_size_gauge.labels(event.host).set(event.plot_size)
        self.log.info(format_og_plot_size(event.plot_size))
        self.portable_plot_size_gauge.labels(event.host).set(event.portable_plot_size)
        self.log.info(format_portable_plot_size(event.portable_plot_size))
        self.log.info(format_hostname(event.host, fix_indent=True))

    def update_farmer_metrics(self, event: FarmingInfoEvent):
        self.log.info("-" * 64)
        self.challenges_counter.inc()
        self.log.info(format_challenge_hash(event.challenge_hash))
        self.log.info(format_signage_point(event.signage_point))
        self.log.info(format_plot_count(event.total_plots))
        self.passed_filter_counter.inc(event.passed_filter)
        self.log.info(format_passed_filter(event.passed_filter))
        self.proofs_found_counter.inc(event.proofs)
        self.log.info(format_proofs(event.proofs))

    def update_connection_metrics(self, event: ConnectionsEvent) -> None:
        self.log.info("-" * 64)
        self.connections_gauge.labels("Full Node").set(event.full_node_count)
        self.log.info(format_full_node_count(event.full_node_count))
        self.connections_gauge.labels("Farmer").set(event.farmer_count)
        self.log.info(format_full_node_count(event.farmer_count, "Farmer"))
        self.connections_gauge.labels("Harvester").set(event.harvester_count)
        self.log.info(format_full_node_count(event.harvester_count, "Harvester"))

    def update_blockchain_state_metrics(self, event: BlockchainStateEvent) -> None:
        self.log.info("-" * 64)
        self.network_space_gauge.set(int(event.space))
        self.log.info(format_space(int(event.space)))
        self.diffculty_gauge.set(event.diffculty)
        self.log.info(format_diffculty(event.diffculty))
        self.height_gauge.set(int(event.peak_height))
        self.log.info(format_peak_height(int(event.peak_height), fix_indent=True))
        self.sync_gauge.set(event.synced)
        self.log.info(format_synced(event.synced))

    def update_wallet_balance_metrics(self, event: WalletBalanceEvent) -> None:
        self.log.info("-" * 64)
        self.total_balance_gauge.set(int(event.confirmed))
        self.log.info(format_balance(int(event.confirmed)))
        self.total_farmed_gauge.set(int(event.farmed))
        self.log.info(format_farmed(int(event.farmed)))

    def update_signage_point_metrics(self, event: SignagePointEvent) -> None:
        self.log.info("-" * 64)
        self.signage_point_counter.inc()
        self.signage_point_index_gauge.set(event.signage_point_index)
        self.log.info(format_signage_point_index(event.signage_point_index))
        self.log.info(format_challenge_hash(event.challenge_hash))
        self.log.info(format_signage_point(event.signage_point))

    def update_pool_state_metrics(self, event: PoolStateEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_current_points(event.current_points))
        self.current_pool_points_gauge.labels(event.p2_singleton_puzzle_hash,
                                              event.pool_url).set(event.current_points)
        self.log.info(format_pool_difficulty(event.current_difficulty))
        self.current_pool_difficulty_gauge.labels(event.p2_singleton_puzzle_hash,
                                                  event.pool_url).set(event.current_difficulty)
        self.log.info(format_points_found(event.points_found_since_start))
        self.pool_points_found_since_start_gauge.labels(
            event.p2_singleton_puzzle_hash, event.pool_url).set(event.points_found_since_start)
        self.log.info(format_points_acknowledged(event.points_acknowledged_since_start))
        self.pool_points_acknowledged_since_start_gauge.labels(
            event.p2_singleton_puzzle_hash, event.pool_url).set(event.points_acknowledged_since_start)
        self.log.info(format_pool_errors_24h(event.num_pool_errors_24h))
        self.num_pool_errors_24h_gauge.labels(event.p2_singleton_puzzle_hash,
                                              event.pool_url).set(event.num_pool_errors_24h)

    def update_price_metrics(self, event: PriceEvent) -> None:
        self.log.info("-" * 64)
        self.log.info(format_price(event.usd_cents / 100, "USD", fix_indent=True))
        self.price_usd_cents_gauge.set(event.usd_cents)
        self.log.info(format_price(event.eur_cents / 100, "EUR", fix_indent=True))
        self.price_eur_cents_gauge.set(event.eur_cents)
        self.log.info(format_price(event.btc_satoshi / 10e7, "BTC", fix_indent=True))
        self.price_btc_satoshi_gauge.set(event.btc_satoshi)
        self.log.info(format_price(event.eth_gwei / 10e8, "ETH", fix_indent=True))
        self.price_eth_gwei_gauge.set(event.eth_gwei)
