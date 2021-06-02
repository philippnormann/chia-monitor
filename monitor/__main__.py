import asyncio
import logging

import colorlog
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
from prometheus_client import start_http_server

from monitor.exporters.rpc_exporter import RpcExporter

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


async def main():
    rpc_exporter = await RpcExporter.create(DEFAULT_ROOT_PATH, config)

    logging.info("🚀 Starting monitor loop!")
    while True:
        try:
            tasks = [coro() for coro in rpc_exporter.coros]
            await asyncio.gather(*tasks)
            logging.info("-" * 42)
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logging.info("🛑 Shutting down!")
            break

    await rpc_exporter.close()


if __name__ == "__main__":
    initilize_logging()
    start_http_server(8000)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Bye!")
