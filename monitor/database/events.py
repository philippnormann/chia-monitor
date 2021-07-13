from sqlalchemy import Boolean, Column, DateTime, Integer, String

from monitor.database import ChiaEvent


class HarvesterPlotsEvent(ChiaEvent):
    __tablename__ = "harvester_events"
    ts: float = Column(DateTime, primary_key=True)
    host = Column(String(255), primary_key=True)
    plot_count = Column(Integer)
    portable_plot_count = Column(Integer)
    plot_size = Column(Integer)
    portable_plot_size = Column(Integer)


class ConnectionsEvent(ChiaEvent):
    __tablename__ = "connection_events"
    ts: float = Column(DateTime, primary_key=True)
    full_node_count = Column(Integer)
    farmer_count = Column(Integer)
    wallet_count = Column(Integer)
    harvester_count = Column(Integer)


class BlockchainStateEvent(ChiaEvent):
    __tablename__ = "blockchain_state_events"
    ts: float = Column(DateTime, primary_key=True)
    space = Column(String(32))
    diffculty = Column(Integer)
    peak_height = Column(String(32))
    synced = Column(Boolean())


class WalletBalanceEvent(ChiaEvent):
    __tablename__ = "wallet_balance_events"
    ts: float = Column(DateTime, primary_key=True)
    confirmed = Column(String(32))
    farmed = Column(String(32))


class SignagePointEvent(ChiaEvent):
    __tablename__ = "signage_point_events"
    ts: float = Column(DateTime, primary_key=True)
    challenge_hash = Column(String(66), index=True)
    signage_point = Column(String(66), index=True)
    signage_point_index = Column(Integer)


class FarmingInfoEvent(ChiaEvent):
    __tablename__ = "farming_info_events"
    ts: float = Column(DateTime, primary_key=True)
    challenge_hash = Column(String(66), index=True)
    signage_point = Column(String(66), index=True)
    passed_filter = Column(Integer)
    proofs = Column(Integer)
    total_plots = Column(Integer)


class PoolStateEvent(ChiaEvent):
    __tablename__ = "pool_state_events"
    ts: float = Column(DateTime, primary_key=True)
    current_points = Column(Integer)
    current_difficulty = Column(Integer)
    points_found_since_start = Column(Integer)
    points_acknowledged_since_start = Column(Integer)
    num_pool_errors_24h = Column(Integer)
