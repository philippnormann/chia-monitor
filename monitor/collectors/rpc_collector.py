from __future__ import annotations

import asyncio
import json
import logging
from asyncio import Queue
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List

from chia.rpc.farmer_rpc_client import FarmerRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.rpc_client import RpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.server.outbound_message import NodeType
from chia.util.ints import uint16
from monitor.collectors.collector import Collector
from monitor.database.events import (BlockchainStateEvent, ChiaEvent, ConnectionsEvent,
                                     HarvesterPlotsEvent, WalletBalanceEvent)


class RpcCollector(Collector):
    full_node_client: FullNodeRpcClient
    wallet_client: WalletRpcClient
    harvester_clients: List[HarvesterRpcClient]
    farmer_client: FarmerRpcClient
    root_path: Path
    net_config: Dict
    hostname: str
    tasks: List[Callable]

    @staticmethod
    async def create(root_path: Path, net_config: Dict, event_queue: Queue[ChiaEvent]) -> RpcCollector:
        self = RpcCollector()
        self.log = logging.getLogger(__name__)
        self.event_queue = event_queue

        self.root_path = root_path
        self.net_config = net_config
        self.hostname = net_config["self_hostname"]
        self.tasks = []
        self.harvester_clients = []

        try:
            full_node_rpc_port = net_config["full_node"]["rpc_port"]
            self.full_node_client = await FullNodeRpcClient.create(self.hostname,
                                                                   uint16(full_node_rpc_port),
                                                                   self.root_path, self.net_config)
            await self.full_node_client.get_connections()
            self.tasks.append(self.get_blockchain_state)
            self.tasks.append(self.get_connections)
        except Exception as e:
            if self.full_node_client is not None:
                await RpcCollector.close_rpc_client(self.full_node_client)
                self.full_node_client = None
            self.log.warning(f"Failed to connect to full node RPC endpoint. Continuing without it. {e}")

        try:
            wallet_rpc_port = net_config["wallet"]["rpc_port"]
            self.wallet_client = await WalletRpcClient.create(self.hostname, uint16(wallet_rpc_port),
                                                              self.root_path, self.net_config)
            await self.wallet_client.get_connections()
            self.tasks.append(self.get_wallet_balance)
        except Exception as e:
            if self.wallet_client is not None:
                await RpcCollector.close_rpc_client(self.wallet_client)
                self.wallet_client = None
            self.log.warning(f"Failed to connect to wallet RPC endpoint. Continuing without it. {e}")

        try:
            farming_rpc_port = net_config["farmer"]["rpc_port"]
            self.farmer_client = await FarmerRpcClient.create(self.hostname, uint16(farming_rpc_port),
                                                              self.root_path, self.net_config)
            await self.farmer_client.get_connections()
            self.tasks.append(self.get_harvester_plots)
        except Exception as e:
            if self.farmer_client is not None:
                await RpcCollector.close_rpc_client(self.farmer_client)
                self.farmer_client = None
            self.log.warning(f"Failed to connect to farmer RPC endpoint. Continuing without it. {e}")

        if len(self.tasks) < 1:
            raise ConnectionError(
                "Failed to connect to any RPC endpoints, Check if your Chia services are running")

        return self

    async def get_wallet_balance(self) -> None:
        try:
            wallets = await self.wallet_client.get_wallets()
            confirmed_balances = []
            for wallet in wallets:
                balance = await self.wallet_client.get_wallet_balance(wallet["id"])
                confirmed_balances.append(balance["confirmed_wallet_balance"])
        except Exception as e:
            raise ConnectionError(f"Failed to get wallet balance via RPC. Is your wallet running? {e}")
        event = WalletBalanceEvent(ts=datetime.now(), confirmed=str(sum(confirmed_balances)))
        await self.publish_event(event)

    async def get_harvester_plots(self) -> None:
        try:
            harvesters = await self.farmer_client.get_harvesters()
            for harvester in harvesters["harvesters"]:
                host = harvester["connection"]["host"]
                plots = harvester["plots"]
                og_plots = [plot for plot in plots if plot["pool_contract_puzzle_hash"] is None]
                portable_plots = [
                    plot for plot in plots if plot["pool_contract_puzzle_hash"] is not None
                ]
                event = HarvesterPlotsEvent(ts=datetime.now(),
                                            plot_count=len(og_plots),
                                            plot_size=sum(og_plot["file_size"] for og_plot in og_plots),
                                            portable_plot_count=len(portable_plots),
                                            portable_plot_size=sum(portable_plot["file_size"]
                                                                   for portable_plot in portable_plots),
                                            host=host)
                await self.publish_event(event)
        except:
            raise ConnectionError("Failed to get harvesters via RPC. Is your farmer running?")

    async def get_blockchain_state(self) -> None:
        try:
            state = await self.full_node_client.get_blockchain_state()
        except:
            raise ConnectionError("Failed to get blockchain state via RPC. Is your full node running?")
        peak_height = state["peak"].height if state["peak"] is not None else 0
        event = BlockchainStateEvent(ts=datetime.now(),
                                     space=str(state["space"]),
                                     diffculty=state["difficulty"],
                                     peak_height=str(peak_height),
                                     synced=state["sync"]["synced"])
        await self.publish_event(event)

    async def get_connections(self) -> None:
        full_node_connections = []
        farmer_connections = []
        wallet_connections = []
        harvester_connections = []
        if self.full_node_client is not None:
            peers = await self.full_node_client.get_connections()
            full_node_connections = [
                peer for peer in peers if NodeType(peer["type"]) == NodeType.FULL_NODE
            ]
            farmer_connections = [peer for peer in peers if NodeType(peer["type"]) == NodeType.FARMER]
            wallet_connections = [peer for peer in peers if NodeType(peer["type"]) == NodeType.WALLET]
        if self.farmer_client is not None:
            peers = await self.farmer_client.get_connections()
            harvester_connections = [
                peer for peer in peers if NodeType(peer["type"]) == NodeType.HARVESTER
            ]
        event = ConnectionsEvent(ts=datetime.now(),
                                 full_node_count=len(full_node_connections),
                                 farmer_count=len(farmer_connections),
                                 wallet_count=len(wallet_connections),
                                 harvester_count=len(harvester_connections))
        await self.publish_event(event)

    async def task(self) -> None:
        while True:
            try:
                await asyncio.gather(*[task() for task in self.tasks])
            except Exception as e:
                self.log.warning(f"Error while collecting events. Trying again... {e}")
            await asyncio.sleep(10)

    @staticmethod
    async def close_rpc_client(rpc_client: RpcClient) -> None:
        rpc_client.close()
        await rpc_client.await_closed()

    async def close(self) -> None:
        await RpcCollector.close_rpc_client(self.full_node_client)
        await RpcCollector.close_rpc_client(self.wallet_client)
        await RpcCollector.close_rpc_client(self.farmer_client)
        for harvester_client in self.harvester_clients:
            await RpcCollector.close_rpc_client(harvester_client)
