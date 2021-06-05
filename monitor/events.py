import time
from dataclasses import dataclass


@dataclass
class ChiaEvent:
    ts: float = time.time()


@dataclass
class HarvesterPlotsEvent(ChiaEvent):
    plot_count: int = 0
    plot_size: int = 0


@dataclass
class ConnectionsEvent(ChiaEvent):
    full_node_count: int = 0
    farmer_count: int = 0
    wallet_count: int = 0


@dataclass
class BlockchainStateEvent(ChiaEvent):
    space: int = 0
    diffculty: int = 0
    peak_height: int = 0
    synced: bool = False


@dataclass
class WalletBalanceEvent(ChiaEvent):
    confirmed: int = 0


@dataclass
class SignagePointEvent(ChiaEvent):
    challenge_hash: str = None
    challenge_chain_sp: str = None
    reward_chain_sp: str = None
    signage_point_index: int = 0


@dataclass
class FarmingInfoEvent(ChiaEvent):
    challenge_hash: str = None
    signage_point: str = None
    passed_filter: str = None
    proofs: int = 0