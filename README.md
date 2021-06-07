# chia-monitor

A monitoring tool to collect all important metrics from your Chia farming node and notify you with regular status updates or in case something goes wrong.

![grafana](.readme/grafana.png)

This [Grafana](https://grafana.com/) dashboard displays all collected metrics and can be imported from [grafana.com](https://grafana.com/grafana/dashboards/14544) using the ID `14544`.

## Metrics
The following statistics are collected from your local [Chia](https://chia.net) node using the [RPC](https://github.com/Chia-Network/chia-blockchain/wiki/RPC-Interfaces) and WebSocket APIs. All of these metrics are then exported via a [Prometheus](https://prometheus.io) compatible `/metrics` HTTP endpoint on port `8000`.

### Supported wallet metrics
- Total balance (`chia_confirmed_total_mojos`)

### Supported full node metrics
- Sync status (`chia_sync_status`)
- Peak height (`chia_peak_height`)
- Difficulty (`chia_diffculty`)
- Total netspace (`chia_network_space`)
- Connection count (`chia_connections_count`)

### Supported harvester metrics
- Plot count (`chia_plot_count`)
- Plot size (`chia_plot_size`)

### Supported farmer metrics
- Attempted challenges (`chia_block_challenges`)
- Plots passed filter (`chia_plots_passed_filter`)
- Proofs found (`chia_proofs_found`)

## Notifications
To use notifications, please configure a `status_service_url` and `alert_service_url` for your desired notification service in the `config.json`. 

You can use most popular notifications services by creating a service specific webhook URL, following the instructions from [this](https://github.com/caronc/apprise/wiki) wiki.

Following notifications are currently sent to the `status_service_url`:
### Farm summary (once every hour)
```
** 👨‍🌾 Farm Status 👩‍🌾 **
🌾 Plot Count: 64
💰 Total Balance: 43.00003 XCH
💾 Current Netspace: 0.056 PiB
🏔️ Peak Height: 166193
📶 Peer Count: 8
🔄 Synced: True
✅ Proofs found: 0
```
Following notifications are currently sent to the `alert_service_url`:
### Sync lost alert
```
** 🚨 Farmer Lost Sync! 🚨 **
It seems like your farmer lost it's connection to the Chia Network
```
### Sync recovery alert
```
** ✅ Farmer Successfully Synced! ✅ **
Your farmer is successfully synced to the Chia Network
```
### Proof found alert
```
** 🤑 Proof found! 🤑 **
Your farm found a new proof
```

## Installation
To run this tool, we need the following things:
- Python 3
- Pipenv

### Linux (Ubuntu)
```bash
sudo apt install python3 pipenv
cd chia-monitor
pipenv install 
```
## Usage
To use the tool run the module as a service or screen in the background.
```bash
cd chia-monitor
pipenv run python -m monitor
```

### Basic Prometheus Configuration
Add a block to the `scrape_configs` of your `prometheus.yml` config file:
```yaml
scrape_configs:
  - job_name: chia_monitor
    static_configs:
    - targets: ['<<CHIA-MONITOR-HOSTNAME>>:8000']
```
and adjust the host name accordingly.

## Architecture
![architecture](.readme/architecture.svg)