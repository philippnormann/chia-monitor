from dataclasses import dataclass

from monitor.collectors.price_collector import PriceCollectorConfiguration
from monitor.collectors.rpc_collector import RpcCollectorConfiguration
from monitor.notifier import NotifierConfiguration


@dataclass(frozen=True)
class Configuration:
    exporter_port: int
    rpc_collector: RpcCollectorConfiguration
    price_collector: PriceCollectorConfiguration
    notifier: NotifierConfiguration
