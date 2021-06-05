from __future__ import annotations

import asyncio
import logging
from asyncio import Queue
from pathlib import Path
from typing import Dict

from chia.rpc.farmer_rpc_client import FarmerRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.rpc_client import RpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.server.outbound_message import NodeType
from chia.util.ints import uint16
from monitor.collectors.collector import Collector
from monitor.events import (BlockchainStateEvent, ChiaEvent, ConnectionsEvent,
                            HarvesterPlotsEvent, WalletBalanceEvent)


class RpcCollector(Collector):
    full_node_client: FullNodeRpcClient
    wallet_client: WalletRpcClient
    harvester_client: HarvesterRpcClient
    farmer_client: FarmerRpcClient

    @staticmethod
    async def create(root_path: Path, net_config: Dict,
                     event_queue: Queue[ChiaEvent]) -> RpcCollector:
        self = RpcCollector()
        self.log = logging.getLogger(__name__)
        self.event_queue = event_queue

        self_hostname = net_config["self_hostname"]
        full_node_rpc_port = net_config["full_node"]["rpc_port"]
        wallet_rpc_port = net_config["wallet"]["rpc_port"]
        harvester_rpc_port = net_config["harvester"]["rpc_port"]
        farmer_rpc_port = net_config["farmer"]["rpc_port"]

        self.full_node_client = await FullNodeRpcClient.create(self_hostname,
                                                               uint16(full_node_rpc_port),
                                                               root_path, net_config)
        self.wallet_client = await WalletRpcClient.create(self_hostname,
                                                          uint16(wallet_rpc_port),
                                                          root_path, net_config)
        self.harvester_client = await HarvesterRpcClient.create(
            self_hostname, uint16(harvester_rpc_port), root_path, net_config)
        self.farmer_client = await FarmerRpcClient.create(self_hostname,
                                                          uint16(farmer_rpc_port),
                                                          root_path, net_config)
        return self

    async def get_wallet_balance(self) -> None:
        try:
            wallets = await self.wallet_client.get_wallets()
            confirmed_balances = []
            for wallet in wallets:
                balance = await self.wallet_client.get_wallet_balance(wallet["id"])
                confirmed_balances.append(balance["confirmed_wallet_balance"])
        except:
            raise ConnectionError(
                "Failed to get wallet balance via RPC. Is your wallet running?")
        await self.event_queue.put(WalletBalanceEvent(confirmed=sum(confirmed_balances)))

    async def update_harvester_metrics(self) -> None:
        plots = await self.harvester_client.get_plots()
        await self.event_queue.put(
            HarvesterPlotsEvent(plot_count=len(plots["plots"]),
                                plot_size=sum(plot["file_size"]
                                              for plot in plots["plots"])))

    async def get_blockchain_state(self) -> None:
        state = await self.full_node_client.get_blockchain_state()
        await self.event_queue.put(
            BlockchainStateEvent(space=state["space"],
                                 diffculty=state["difficulty"],
                                 peak_height=state["peak"].height,
                                 synced=state["sync"]["synced"]))

    async def get_connections(self) -> None:
        peers = await self.full_node_client.get_connections()
        full_node_connections = [
            peer for peer in peers if NodeType(peer["type"]) == NodeType.FULL_NODE
        ]
        farmer_connections = [
            peer for peer in peers if NodeType(peer["type"]) == NodeType.FARMER
        ]
        wallet_connections = [
            peer for peer in peers if NodeType(peer["type"]) == NodeType.WALLET
        ]
        await self.event_queue.put(
            ConnectionsEvent(full_node_count=len(full_node_connections),
                             farmer_count=len(farmer_connections),
                             wallet_count=len(wallet_connections)))

    async def task(self):
        while True:
            await asyncio.gather(self.get_wallet_balance(),
                                 self.update_harvester_metrics(),
                                 self.get_blockchain_state(), self.get_connections())
            await asyncio.sleep(10)

    @staticmethod
    async def close_rpc_client(rpc_client: RpcClient):
        rpc_client.close()
        await rpc_client.await_closed()

    async def close(self):
        await RpcCollector.close_rpc_client(self.full_node_client)
        await RpcCollector.close_rpc_client(self.wallet_client)
        await RpcCollector.close_rpc_client(self.harvester_client)
        await RpcCollector.close_rpc_client(self.farmer_client)
