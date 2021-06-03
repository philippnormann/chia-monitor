from __future__ import annotations

import logging
from pathlib import Path
from typing import Coroutine, Dict, List

from chia.rpc.farmer_rpc_client import FarmerRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.rpc_client import RpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.util.ints import uint16
from monitor.exporters.exporter import Exporter
from prometheus_client import Gauge


class RpcExporter(Exporter):
    full_node_client: FullNodeRpcClient
    wallet_client: WalletRpcClient
    harvester_client: HarvesterRpcClient
    farmer_client: FarmerRpcClient

    # Wallet metrics
    total_balance_gauge = Gauge('chia_confirmed_total_mojos',
                                'Sum of confirmed wallet balances')

    # Full node metrics
    network_space_gauge = Gauge('chia_network_space',
                                'Approximation of current netspace')
    diffculty_gauge = Gauge('chia_diffculty',
                            'Current networks farming difficulty')
    height_gauge = Gauge('chia_peak_height',
                         'Block height of the current peak')
    sync_gauge = Gauge('chia_sync_status',
                       'Sync status of the connected full node')
    connections_gauge = Gauge(
        'chia_connections_count',
        'Count of peers that the node is currently connected to')

    # Harvester metrics
    plot_count_gauge = Gauge('chia_plot_count',
                             'Plot count being farmed by harvester')
    plot_size_gauge = Gauge('chia_plot_size',
                            'Size of plots being farmed by harvester')

    @staticmethod
    async def create(root_path: Path, net_config: Dict) -> RpcExporter:
        self = RpcExporter()
        self.log = logging.getLogger(__name__)

        self_hostname = net_config["self_hostname"]
        full_node_rpc_port = net_config["full_node"]["rpc_port"]
        wallet_rpc_port = net_config["wallet"]["rpc_port"]
        harvester_rpc_port = net_config["harvester"]["rpc_port"]
        farmer_rpc_port = net_config["farmer"]["rpc_port"]

        self.full_node_client = await FullNodeRpcClient.create(
            self_hostname, uint16(full_node_rpc_port), root_path, net_config)

        self.wallet_client = await WalletRpcClient.create(
            self_hostname, uint16(wallet_rpc_port), root_path, net_config)

        self.harvester_client = await HarvesterRpcClient.create(
            self_hostname, uint16(harvester_rpc_port), root_path, net_config)

        self.farmer_client = await FarmerRpcClient.create(
            self_hostname, uint16(farmer_rpc_port), root_path, net_config)

        return self

    @property
    def coros(self) -> List[Coroutine]:
        return [
            self.update_wallet_metrics, self.update_node_metrics,
            self.update_harvester_metrics
        ]

    async def update_wallet_metrics(self) -> None:
        wallets = await self.wallet_client.get_wallets()
        balances = []

        for wallet in wallets:
            balance = await self.wallet_client.get_wallet_balance(wallet["id"])
            balances.append(balance["confirmed_wallet_balance"])

        total = sum(balances)
        self.total_balance_gauge.set(total)
        self.log.info(f"💰 Total Balance:      {total/1e12:.5f} XCH")

    async def update_node_metrics(self) -> None:
        state = await self.full_node_client.get_blockchain_state()
        peers = await self.full_node_client.get_connections()

        space = state["space"]
        self.network_space_gauge.set(space)
        self.log.info(f"💾 Current Netspace:   {space/(1024 ** 5):.3f} PiB")

        diffculty = state["difficulty"]
        self.diffculty_gauge.set(diffculty)
        self.log.info(f"📈 Farming Difficulty: {diffculty}")

        height = state["peak"].height
        self.height_gauge.set(height)
        self.log.info(f"🏔️  Peak Height:        {height}")

        synced = state["sync"]["synced"]
        self.sync_gauge.set(synced)
        self.log.info(f"🔄 Synced:             {synced}")

        full_node_peers = [peer for peer in peers if peer["type"] == 1]
        peer_count = len(full_node_peers)
        self.connections_gauge.set(peer_count)
        self.log.info(f"📶 Peer Count:         {peer_count}")

    async def update_harvester_metrics(self) -> None:
        plots = await self.harvester_client.get_plots()
        plots = plots["plots"]

        plot_count = len(plots)
        plot_size = sum(plot["file_size"] for plot in plots)
        self.plot_count_gauge.set(plot_count)
        self.log.info(f"🌾 Plot Count:         {plot_count}")
        self.plot_size_gauge.set(plot_size)
        self.log.info(f"🧺 Plot Size:          {plot_size/(1024 ** 4):.3f} TiB")

    @staticmethod
    async def close_rpc_client(rpc_client: RpcClient):
        rpc_client.close()
        await rpc_client.await_closed()

    async def close(self):
        await RpcExporter.close_rpc_client(self.full_node_client)
        await RpcExporter.close_rpc_client(self.wallet_client)
        await RpcExporter.close_rpc_client(self.harvester_client)
        await RpcExporter.close_rpc_client(self.farmer_client)
