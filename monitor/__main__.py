import asyncio
import logging
from asyncio.exceptions import CancelledError
from asyncio.queues import Queue

from sqlalchemy.ext.asyncio.session import AsyncSession

import colorlog
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH

from monitor.collectors.rpc_collector import RpcCollector
from monitor.collectors.ws_collector import WsCollector
from monitor.db import ChiaEvent, init_models, async_session
from monitor.exporter import ChiaExporter

config = load_config(DEFAULT_ROOT_PATH, "config.yaml")


def initilize_logging():
    handler = colorlog.StreamHandler()
    log_date_format = "%Y-%m-%dT%H:%M:%S"
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(asctime)s.%(msecs)03d %(log_color)s%(levelname)-6s%(reset)s %(message)s",
            datefmt=log_date_format,
            reset=True,
        ))
    logger = colorlog.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


async def persist_event(db_session: AsyncSession, event: ChiaEvent):
    async with db_session.begin():
        db_session.add(event)
        await db_session.commit()

async def main(exporter: ChiaExporter) -> None:
    rpc_collector = None
    ws_collector = None
    event_queue = Queue()
    
    db_session = async_session()
    await init_models()

    try:
        rpc_collector = await RpcCollector.create(DEFAULT_ROOT_PATH, config, event_queue)
    except:
        logging.error("Failed to create RPC collector")
    try:
        ws_collector = await WsCollector.create(DEFAULT_ROOT_PATH, config, event_queue)
    except:
        logging.error("Failed to create WebSocket collector")

    if rpc_collector and ws_collector:
        logging.info("🚀 Starting monitoring loop!")
        asyncio.create_task(rpc_collector.task())
        asyncio.create_task(ws_collector.task())
        while True:
            try:
                event = await event_queue.get()
                exporter.process_event(event)
                await persist_event(db_session, event)

            except CancelledError:
                break

    logging.info("🛑 Shutting down!")
    if rpc_collector:
        await rpc_collector.close()
    if ws_collector:
        await ws_collector.close()



if __name__ == "__main__":
    initilize_logging()
    exporter = ChiaExporter()
    try:
        asyncio.run(main(exporter))
    except KeyboardInterrupt:
        logging.info("👋 Bye!")
