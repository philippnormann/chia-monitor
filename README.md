# chia-monitor

A monitoring tool to help us keep track of important farmer statistics and get notified in case something goes wrong.

## Metrics
The following statistics are collected from your local [Chia](https://chia.net) node using the [RPC
API](https://github.com/Chia-Network/chia-blockchain/wiki/RPC-Interfaces) and are exposed via a [Prometheus](https://prometheus.io) compatible `/metrics` HTTP endpoint.

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

## Installation
To run this tool, we need the following things:
- Python 3.9
- Pipenv

### Linux (Ubuntu)
```bash
sudo apt install python3 pipenv
cd chia-monitor
pipenv install 
```
## Notifications
`# TODO`

## Usage
To use the tool run the module as a service or screen in the background.
```bash
cd nvidia-sniper
pipenv run python -m monitor
```

### Basic Prometheus Configuration
Add a block to the scrape_configs of your prometheus.yml config file:
```yaml
scrape_configs:
  - job_name: chia_monitor
    static_configs:
    - targets: ['<<CHIA-MONITOR-HOSTNAME>>:8000']
```
and adjust the host name accordingly.