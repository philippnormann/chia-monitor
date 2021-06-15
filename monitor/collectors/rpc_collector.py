from __future__ import annotations

import asyncio
import logging
from asyncio import Queue
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Tuple
from urllib.parse import urlparse

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
            farmer_peers = await self.farmer_client.get_connections()
        except Exception as e:
            if self.farmer_client is not None:
                await RpcCollector.close_rpc_client(self.farmer_client)
                self.farmer_client = None
            self.log.warning(f"Failed to connect to farmer RPC endpoint. Continuing without it. {e}")
            farmer_peers = [{"peer_host": self.hostname, "type": NodeType.HARVESTER}]

        if farmer_peers is not None:
            connected_harvester = [
                peer["peer_host"] for peer in farmer_peers
                if NodeType(peer["type"]) == NodeType.HARVESTER
            ]
            if len(connected_harvester) > 0:
                self.harvester_clients = await self.create_harvester_clients(connected_harvester)
                if len(self.harvester_clients) > 0:
                    self.tasks.append(self.get_harvester_plots)
            else:
                self.log.warning(f"No harvester is connected to your farmer. Continuing without it.")

        if len(self.tasks) < 1:
            raise ConnectionError(
                "Failed to connect to any RPC endpoints, Check if your Chia services are running")

        return self

    async def create_harvester_clients(
            self, harvester_peers: List[Tuple[str, uint16]]) -> List[HarvesterRpcClient]:
        harvester_clients = []
        harvester_rpc_port = self.net_config["harvester"]["rpc_port"]
        for harvester_host in harvester_peers:
            try:
                harvester_client = await HarvesterRpcClient.create(harvester_host,
                                                                   uint16(harvester_rpc_port),
                                                                   self.root_path, self.net_config)
                await harvester_client.get_connections()
                harvester_clients.append(harvester_client)
            except Exception as e:
                if harvester_client is not None:
                    await RpcCollector.close_rpc_client(harvester_client)
                self.log.warning(
                    f"Failed to connect to harvester RPC endpoint on {harvester_host}:{harvester_rpc_port}. Continuing without it. {e}"
                )
        return harvester_clients

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
        for harvester_client in self.harvester_clients:
            harvester_host = urlparse(harvester_client.url).netloc
            try:
                plots = await harvester_client.get_plots()
            except:
                raise ConnectionError(
                    f"Failed to get harvester plots via RPC from {harvester_host}. Is your harvester running?"
                )
            event = HarvesterPlotsEvent(ts=datetime.now(),
                                        plot_count=len(plots["plots"]),
                                        plot_size=sum(plot["file_size"] for plot in plots["plots"]),
                                        host=harvester_host)
            await self.publish_event(event)

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
