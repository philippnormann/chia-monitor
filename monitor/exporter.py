import logging

from prometheus_client import Counter, Gauge, start_http_server

from monitor.events import (BlockchainStateEvent, ChiaEvent, ConnectionsEvent,
                            FarmingInfoEvent, HarvesterPlotsEvent, SignagePointEvent,
                            WalletBalanceEvent)


class ChiaExporter:
    # Wallet metrics
    total_balance_gauge = Gauge('chia_confirmed_total_mojos',
                                'Sum of confirmed wallet balances')

    # Full node metrics
    network_space_gauge = Gauge('chia_network_space', 'Approximation of current netspace')
    diffculty_gauge = Gauge('chia_diffculty', 'Current networks farming difficulty')
    height_gauge = Gauge('chia_peak_height', 'Block height of the current peak')
    sync_gauge = Gauge('chia_sync_status', 'Sync status of the connected full node')
    connections_gauge = Gauge('chia_connections_count',
                              'Count of peers that the node is currently connected to')

    # Harvester metrics
    plot_count_gauge = Gauge('chia_plot_count', 'Plot count being farmed by harvester')
    plot_size_gauge = Gauge('chia_plot_size', 'Size of plots being farmed by harvester')

    # Farmer metrics
    signage_point_counter = Counter('chia_signage_points', 'Received signage points')
    signage_point_index_gauge = Gauge('chia_signage_point_index',
                                      'Received signage point index')
    challenges_counter = Counter('chia_block_challanges', 'Attempted block challanges')
    passed_filter_counter = Counter('chia_plots_passed_filter', 'Plots passed filter')
    proofs_found_counter = Counter('chia_proofs_found', 'Proofs found')

    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        start_http_server(8000)

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

    def update_harvester_metrics(self, event: HarvesterPlotsEvent) -> None:
        self.log.info("-" * 64)
        self.plot_count_gauge.set(event.plot_size)
        self.log.info(f"🌾 Plot Count:          {event.plot_count}")
        self.plot_size_gauge.set(event.plot_size)
        self.log.info(f"🧺 Plot Size:           {event.plot_size/(1024 ** 4):.3f} TiB")

    def update_farmer_metrics(self, event: FarmingInfoEvent):
        self.log.info("-" * 64)
        self.challenges_counter.inc()
        self.log.info(f"🎰 Challenge Hash:      {event.challenge_hash}")
        self.log.info(f"⌛ Signage Point:       {event.signage_point}")
        self.passed_filter_counter.inc(event.passed_filter)
        self.log.info(f"🔎 Passed Filter:       {event.passed_filter}")
        self.proofs_found_counter.inc(event.proofs)
        self.log.info(f"✅ Proofs found:        {event.proofs}")

    def update_connection_metrics(self, event: ConnectionsEvent) -> None:
        self.log.info("-" * 64)
        self.connections_gauge.set(event.full_node_count)
        self.log.info(f"📶 Peer Count:          {event.full_node_count}")

    def update_blockchain_state_metrics(self, event: BlockchainStateEvent) -> None:
        self.log.info("-" * 64)
        self.network_space_gauge.set(event.space)
        self.log.info(f"💾 Current Netspace:    {event.space/(1024 ** 5):.3f} PiB")
        self.diffculty_gauge.set(event.diffculty)
        self.log.info(f"📈 Farming Difficulty:  {event.diffculty}")
        self.height_gauge.set(event.peak_height)
        self.log.info(f"🏔️  Peak Height:         {event.peak_height}")
        self.sync_gauge.set(event.synced)
        self.log.info(f"🔄 Synced:              {event.synced}")

    def update_wallet_balance_metrics(self, event: WalletBalanceEvent) -> None:
        self.log.info("-" * 64)
        self.total_balance_gauge.set(event.confirmed)
        self.log.info(f"💰 Total Balance:       {event.confirmed/1e12:.5f} XCH")

    def update_signage_point_metrics(self, event: SignagePointEvent) -> None:
        self.log.info("-" * 64)
        self.signage_point_counter.inc()
        self.signage_point_index_gauge.set(event.signage_point_index)
        self.log.info(f"🔏 Signage Point Index: {event.signage_point_index}")
        self.log.info(f"🎰 Challange Hash:      {event.challenge_hash}")
        self.log.info(f"⌛ Signage Point:       {event.challenge_chain_sp}")
