from __future__ import annotations

import logging
from asyncio import Queue
from datetime import datetime
from pathlib import Path
from secrets import token_bytes
from typing import Dict

import aiohttp
from chia.server.server import ssl_context_for_client
from chia.util.ws_message import WsRpcMessage
from monitor.collectors.collector import Collector
from monitor.database.events import ChiaEvent, FarmingInfoEvent, SignagePointEvent


class WsCollector(Collector):
    session: aiohttp.ClientSession
    ws: aiohttp.ClientWebSocketResponse
    closed = False

    @staticmethod
    async def create(root_path: Path, net_config: Dict, event_queue: Queue[ChiaEvent]) -> WsCollector:
        self = WsCollector()
        self.log = logging.getLogger(__name__)
        self.event_queue = event_queue

        ca_crt_path = root_path / net_config["private_ssl_ca"]["crt"]
        ca_key_path = root_path / net_config["private_ssl_ca"]["key"]
        crt_path = root_path / net_config["daemon_ssl"]["private_crt"]
        key_path = root_path / net_config["daemon_ssl"]["private_key"]
        self.ssl_context = ssl_context_for_client(ca_crt_path, ca_key_path, crt_path, key_path)
        try:
            self.session = aiohttp.ClientSession()
            self_hostname = net_config["self_hostname"]
            daemon_port = net_config["daemon_port"]
            self.ws = await self.session.ws_connect(f"wss://{self_hostname}:{daemon_port}",
                                                    ssl_context=self.ssl_context)
            await self.subscribe()
        except:
            await self.session.close()
            raise ConnectionError("Failed to connect to WebSocket API")
        return self

    async def subscribe(self) -> None:
        msg = WsRpcMessage(
            command="register_service",
            ack=False,
            data={"service": "wallet_ui"},
            request_id=token_bytes().hex(),
            destination="daemon",
            origin="client",
        )
        await self.ws.send_json(msg)
        try:
            msg = await self.ws.receive_json()
            assert (msg["data"]["success"])
        except:
            await self.close()
            raise ConnectionError("Failed to subscribe to daemon WebSocket")

    async def process_farming_info(self, farming_info: Dict) -> None:
        event = FarmingInfoEvent(ts=datetime.now(),
                                 challenge_hash=farming_info["challenge_hash"],
                                 signage_point=farming_info["signage_point"],
                                 passed_filter=farming_info["passed_filter"],
                                 proofs=farming_info["proofs"],
                                 total_plots=farming_info["total_plots"])
        await self.publish_event(event)

    async def process_signage_point(self, signage_point: Dict) -> None:
        event = SignagePointEvent(ts=datetime.now(),
                                  challenge_hash=signage_point["challenge_hash"],
                                  signage_point_index=signage_point["signage_point_index"],
                                  signage_point=signage_point["challenge_chain_sp"])
        await self.publish_event(event)

    async def task(self) -> None:
        while not self.closed:
            try:
                msg = await self.ws.receive_json()
                cmd = msg["command"]
                if cmd == "new_farming_info":
                    await self.process_farming_info(msg["data"]["farming_info"])
                elif cmd == "new_signage_point":
                    await self.process_signage_point(msg["data"]["signage_point"])
            except Exception as e:
                if self.closed:
                    break
                else:
                    self.log.warning(f"Error while collecting events. Trying again... {e}")

    async def close(self) -> None:
        self.closed = True
        await self.ws.close()
        await self.session.close()
