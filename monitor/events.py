import orm

from monitor.db import database, metadata


class ChiaEvent(orm.Model):
    __tablename__ = "chia_events"
    __database__ = database
    __metadata__ = metadata
    ts: float = orm.DateTime(primary_key=True)


class HarvesterPlotsEvent(ChiaEvent):
    __tablename__ = "harvester_events"
    __database__ = database
    __metadata__ = metadata
    plot_count = orm.Integer()
    plot_size = orm.Integer()


class ConnectionsEvent(ChiaEvent):
    __tablename__ = "connection_events"
    __database__ = database
    __metadata__ = metadata
    full_node_count = orm.Integer()
    farmer_count = orm.Integer()
    wallet_count = orm.Integer()


class BlockchainStateEvent(ChiaEvent):
    __tablename__ = "blockchain_state_events"
    __database__ = database
    __metadata__ = metadata
    space = orm.String(max_length=32)
    diffculty = orm.Integer()
    peak_height = orm.String(max_length=32)
    synced = orm.Boolean()


class WalletBalanceEvent(ChiaEvent):
    __tablename__ = "wallet_balance_events"
    __database__ = database
    __metadata__ = metadata
    confirmed = orm.String(max_length=32)


class SignagePointEvent(ChiaEvent):
    __tablename__ = "signage_point_events"
    __database__ = database
    __metadata__ = metadata
    challenge_hash = orm.String(max_length=66, index=True)
    signage_point = orm.String(max_length=66, index=True)
    signage_point_index = orm.Integer()


class FarmingInfoEvent(ChiaEvent):
    __tablename__ = "farming_info_events"
    __database__ = database
    __metadata__ = metadata
    challenge_hash = orm.String(max_length=66, index=True)
    signage_point = orm.String(max_length=66, index=True)
    passed_filter = orm.Integer()
    proofs = orm.Integer()
