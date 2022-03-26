import json
from dataclasses import dataclass

from monitor.collectors.rpc_collector import RpcCollectorConfiguration
from monitor.collectors.price_collector import PriceCollectorConfiguration
from monitor.notifier import NotifierConfiguration


@dataclass(frozen=True)
class Configuration:
    exporter_port: int
    rpc_collector: RpcCollectorConfiguration
    price_collector: PriceCollectorConfiguration
    notifier: NotifierConfiguration


def read_config() -> Configuration:
    try:
        with open("config.json") as f:
            config_json = json.load(f)
    except Exception:
        raise RuntimeError("Failed to read config.json. "
                           "Please copy the config-example.json to config.json and configure it to your preferences.")

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
        raise RuntimeError(f"Failed to validate config. Missing required key {ex}. Please compare the fields of your "
                           f"config.json with the config-example.json and fix all inconsistencies. ")

    return config
