from __future__ import annotations

import asyncio
from secrets import token_bytes
import logging
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from typing import Dict

import aiohttp
from chia.server.server import ssl_context_for_client
from chia.util.ws_message import WsRpcMessage
from monitor.exporters.exporter import Exporter
from prometheus_client import Counter


class WsExporter(Exporter):
    session: aiohttp.ClientSession
    ws: aiohttp.ClientWebSocketResponse
    farming_info_queue: Queue

    challenges_counter = Counter('chia_block_challanges',
                                 'Attempted block challanges')
    passed_filter_counter = Counter('chia_plots_passed_filter',
                                    'Plots passed filter')
    proofs_found_counter = Counter('chia_proofs_found', 'Proofs found')

    async def subscribe(self):
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

    async def get_farmer_info(self):
        while True:
            msg = await self.ws.receive_json()
            cmd = msg["command"]
            if cmd == "new_farming_info":
                self.farming_info_queue.put(msg["data"]["farming_info"])

    @staticmethod
    async def create(root_path: Path, net_config: Dict) -> WsExporter:
        self = WsExporter()
        self.log = logging.getLogger(__name__)
        self.farming_info_queue = Queue()

        ca_crt_path = root_path / net_config["private_ssl_ca"]["crt"]
        ca_key_path = root_path / net_config["private_ssl_ca"]["key"]
        crt_path = root_path / net_config["daemon_ssl"]["private_crt"]
        key_path = root_path / net_config["daemon_ssl"]["private_key"]
        self.ssl_context = ssl_context_for_client(ca_crt_path, ca_key_path,
                                                  crt_path, key_path)
        self.session = aiohttp.ClientSession()
        self_hostname = net_config["self_hostname"]
        daemon_port = net_config["daemon_port"]
        self.ws = await self.session.ws_connect(
            f"wss://{self_hostname}:{daemon_port}",
            ssl_context=self.ssl_context)
        await self.subscribe()
        asyncio.create_task(self.get_farmer_info())
        return self

    @property
    def coros(self):
        return [self.update_farmer_metrics]

    async def update_farmer_metrics(self):
        farming_infos = []
        try:
            while True:
                farming_info = self.farming_info_queue.get_nowait()
                farming_infos.append(farming_info)
        except Empty:
            challenges = len(farming_infos)
            self.challenges_counter.inc(challenges)
            self.log.info(f"🎰 Challenges:         {challenges}")

            passed_filter = sum(info["passed_filter"]
                                for info in farming_infos)
            self.passed_filter_counter.inc(passed_filter)
            self.log.info(f"🔎 Passed Filter:      {passed_filter}")

            proofs_found = sum(info["proofs"] for info in farming_infos)
            self.proofs_found_counter.inc(proofs_found)
            self.log.info(f"✅ Proofs found:       {proofs_found}")

    async def close(self):
        await self.ws.close()
        await self.session.close()
