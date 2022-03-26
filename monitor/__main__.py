import asyncio
import json
import logging
import sys
from asyncio.queues import Queue
from typing import Optional

import colorlog
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
from sqlalchemy.exc import OperationalError

from monitor.configuration import Configuration
from monitor.collectors.ws_collector import WsCollector
from monitor.collectors.rpc_collector import RpcCollector, RpcCollectorConfiguration
from monitor.collectors.price_collector import PriceCollector, PriceCollectorConfiguration
from monitor.database import ChiaEvent, session
from monitor.exporter import ChiaExporter
from monitor.logger import ChiaLogger
from monitor.notifier import Notifier, NotifierConfiguration

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


def read_config():
    with open("config.json") as f:
        config = json.load(f)
    return config


if __name__ == "__main__":
    initilize_logging()
    try:
        config_json = read_config()
    except:
        logging.error(
            "Failed to read config.json. Please copy the config-example.json to config.json and configure it to your preferences."
        )
        sys.exit(1)

    try:
        config = Configuration(
            config_json["exporter_port"],
            RpcCollectorConfiguration(
                config_json["rpc_collector"]["refresh_interval_seconds"]
            ),
            PriceCollectorConfiguration(
                config_json["price_collector"]["refresh_interval_seconds"]
            ),
            NotifierConfiguration(
                config_json["notifications"]["enable"],
                config_json["notifications"]["refresh_interval_seconds"],
                config_json["notifications"]["status_interval_minutes"],
                config_json["notifications"]["lost_plots_alert_threshold"],
                config_json["notifications"]["disable_proof_found_alert"],
                config_json["notifications"]["status_service_url"],
                config_json["notifications"]["alert_service_url"]
            )
        )
    except KeyError as ex:
        logging.error(
            f"Failed to validate config. Missing required key {ex}. Please compare the fields of your config.json with the config-example.json and fix all inconsistencies."
        )
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
