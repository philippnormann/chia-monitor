import asyncio
import logging
import sys
from asyncio.queues import Queue
from typing import Optional

import colorlog
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
from sqlalchemy.exc import OperationalError

from monitor.configuration import Configuration, read_config
from monitor.collectors.ws_collector import WsCollector
from monitor.collectors.rpc_collector import RpcCollector
from monitor.collectors.price_collector import PriceCollector
from monitor.database import ChiaEvent, session
from monitor.exporter import ChiaExporter
from monitor.logger import ChiaLogger
from monitor.notifier import Notifier

chia_config = load_config(DEFAULT_ROOT_PATH, "config.yaml")


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


def persist_event(event: ChiaEvent):
    with session.begin() as db_session:
        db_session.add(event)
        db_session.commit()


async def aggregator(exporter: ChiaExporter, notifier: Optional[Notifier], config: Configuration) -> None:
    rpc_collector = None
    ws_collector = None
    price_collector = None
    event_queue = Queue()
    logger = ChiaLogger()

    try:
        logging.info("🔌 Creating RPC Collector...")
        rpc_collector = await RpcCollector.create(DEFAULT_ROOT_PATH, chia_config, event_queue, config.rpc_collector)
    except Exception as e:
        logging.warning(f"Failed to create RPC collector. Continuing without it. {type(e).__name__}: {e}")

    try:
        logging.info("🔌 Creating WebSocket Collector...")
        ws_collector = await WsCollector.create(DEFAULT_ROOT_PATH, chia_config, event_queue)
    except Exception as e:
        logging.warning(f"Failed to create WebSocket collector. Continuing without it. {type(e).__name__}: {e}")

    try:
        logging.info("🔌 Creating Price Collector...")
        price_collector = await PriceCollector.create(DEFAULT_ROOT_PATH, chia_config, event_queue,
                                                      config.price_collector)
    except Exception as e:
        logging.warning(f"Failed to create Price collector. Continuing without it. {type(e).__name__}: {e}")

    if rpc_collector and ws_collector:
        logging.info("🚀 Starting monitoring loop!")
        rpc_task = asyncio.create_task(rpc_collector.task())
        ws_task = asyncio.create_task(ws_collector.task())
        if notifier is not None:
            notifier.start()
        if price_collector is not None:
            asyncio.create_task(price_collector.task())
        while True:
            try:
                event = await event_queue.get()
                exporter.process_event(event)
                logger.process_event(event)
                persist_event(event)

            except OperationalError:
                logging.exception(
                    f"Failed to persist event to DB. Please initialize DB using: 'pipenv run alembic upgrade head'")
                break

            except asyncio.CancelledError:
                break

    else:
        logging.error("Failed to create any collector.")

    logging.info("🛑 Shutting down!")
    if rpc_collector:
        rpc_task.cancel()
        await rpc_collector.close()
    if ws_collector:
        ws_task.cancel()
        await ws_collector.close()
    if notifier:
        notifier.stop()


if __name__ == "__main__":
    initilize_logging()
    try:
        config = read_config()
    except RuntimeError as ex:
        logging.error(ex)
        sys.exit(1)

    exporter = ChiaExporter(config.exporter_port)
    if config.notifier.enable_notifications:
        notifier = Notifier(config.notifier)
    else:
        notifier = None

    try:
        asyncio.run(aggregator(exporter, notifier, config))
    except KeyboardInterrupt:
        logging.info("👋 Bye!")
