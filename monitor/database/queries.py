from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, Tuple

from monitor.database import session
from monitor.database.events import (BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent, HarvesterPlotsEvent,
                                     SignagePointEvent, WalletBalanceEvent)
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.functions import func


def get_proofs_found(db_session: Session) -> Optional[int]:
    result = db_session.execute(select(func.sum(FarmingInfoEvent.proofs)))
    return result.scalars().first()


def get_harvester_count(db_session: Session) -> Optional[int]:
    result = db_session.execute(select(ConnectionsEvent.harvester_count).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


def get_sync_status(db_session: Session) -> Optional[bool]:
    result = db_session.execute(select(BlockchainStateEvent.synced).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


def get_blockchain_state(db_session: Session) -> Optional[BlockchainStateEvent]:
    result = db_session.execute(select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


def get_wallet_balance(db_session: Session) -> Optional[WalletBalanceEvent]:
    result = db_session.execute(select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


def get_connections(db_session: Session) -> Optional[ConnectionsEvent]:
    result = db_session.execute(select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


def get_farming_start(db_session: Session) -> Optional[datetime]:
    result = db_session.execute(select(func.min(FarmingInfoEvent.ts)))
    return result.scalars().first()


def get_previous_signage_point(db_session: Session) -> Optional[str]:
    result = db_session.execute(
        select(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc()).distinct(
            FarmingInfoEvent.signage_point).limit(2))
    return result.all()[-1][0]


def get_plot_delta(db_session: Session, period=timedelta(hours=24)) -> Tuple[int, int]:
    result = db_session.execute(select(func.min(HarvesterPlotsEvent.ts)))
    first_ts = result.scalars().first()
    if first_ts is None:
        return 0, 0
    initial_ts = max(first_ts, datetime.now() - period)
    sub_query = select([
        HarvesterPlotsEvent.plot_count, HarvesterPlotsEvent.portable_plot_count, HarvesterPlotsEvent.plot_size,
        HarvesterPlotsEvent.portable_plot_size
    ]).where(HarvesterPlotsEvent.ts > initial_ts).order_by(HarvesterPlotsEvent.ts).group_by(HarvesterPlotsEvent.host)
    result = db_session.execute(
        select([
            func.sum(sub_query.c.plot_count),
            func.sum(sub_query.c.portable_plot_count),
            func.sum(sub_query.c.plot_size),
            func.sum(sub_query.c.portable_plot_size)
        ]))
    initial_plots = result.one()
    if initial_plots is None:
        return 0, 0
    initial_og_plot_count, initial_portable_plot_count, initial_og_plot_size, initial_portable_plot_size = initial_plots
    initial_plot_count = initial_og_plot_count + initial_portable_plot_count
    initial_plot_size = initial_og_plot_size + initial_portable_plot_size
    current_plot_count = get_plot_count(db_session)
    if current_plot_count is None:
        return 0, 0
    current_plot_size = get_plot_size(db_session)
    if current_plot_size is None:
        return 0, 0
    return current_plot_count - initial_plot_count, current_plot_size - initial_plot_size


def get_plot_count(db_session: Session) -> Optional[int]:
    og_plot_count = get_og_plot_count(db_session)
    portable_plot_count = get_portable_plot_count(db_session)
    if og_plot_count is not None and portable_plot_count is not None:
        return og_plot_count + portable_plot_count
    elif og_plot_count is not None and portable_plot_count is None:
        return og_plot_count
    elif og_plot_count is None and portable_plot_count is not None:
        return portable_plot_count
    else:
        return None


def get_plot_size(db_session: Session) -> Optional[int]:
    og_plot_size = get_og_plot_size(db_session)
    portable_plot_size = get_portable_plot_size(db_session)
    if og_plot_size is not None and portable_plot_size is not None:
        return og_plot_size + portable_plot_size
    elif og_plot_size is not None and portable_plot_size is None:
        return og_plot_size
    elif og_plot_size is None and portable_plot_size is not None:
        return portable_plot_size
    else:
        return None


def get_og_plot_size(db_session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_size).label("plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(HarvesterPlotsEvent.host)
    result = db_session.execute(select(func.sum(sub_query.c.plot_size)))
    return result.scalars().first()


def get_og_plot_count(db_session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_count).label("plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(HarvesterPlotsEvent.host)
    result = db_session.execute(select(func.sum(sub_query.c.plot_count)))
    return result.scalars().first()


def get_portable_plot_size(db_session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_size).label("portable_plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(HarvesterPlotsEvent.host)
    result = db_session.execute(select(func.sum(sub_query.c.portable_plot_size)))
    return result.scalars().first()


def get_portable_plot_count(db_session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_count).label("portable_plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(HarvesterPlotsEvent.host)
    result = db_session.execute(select(func.sum(sub_query.c.portable_plot_count)))
    return result.scalars().first()


def get_signage_points_per_minute(db_session: Session, interval: timedelta) -> Optional[float]:
    result = db_session.execute(
        select(func.count(SignagePointEvent.ts)).where(SignagePointEvent.ts >= datetime.now() - interval))
    num_signage_points = result.scalars().first()
    if num_signage_points is None:
        return None
    return num_signage_points / (interval.seconds / 60)


def get_passed_filters_per_minute(db_session: Session, interval: timedelta) -> Optional[float]:
    result = db_session.execute(
        select(func.sum(FarmingInfoEvent.passed_filter)).where(FarmingInfoEvent.ts >= datetime.now() - interval))
    passed_filters = result.scalars().first()
    if passed_filters is None:
        return None
    return passed_filters / (interval.seconds / 60)


def get_current_balance(db_session: Session) -> int:
    result = db_session.execute(select(WalletBalanceEvent.confirmed).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


def get_last_payment(db_session: Session) -> int:
    current_balance = get_current_balance(db_session)
    previous_balance_query = db_session.execute(
        select(WalletBalanceEvent.confirmed).where(WalletBalanceEvent.confirmed != current_balance).order_by(
            WalletBalanceEvent.ts.desc()))
    last_balance = previous_balance_query.scalars().first()
    return int(current_balance) - int(last_balance)


@lru_cache(maxsize=16)
def get_signage_point_ts(signage_point: str, db_session: Session = None) -> datetime:
    query = select(SignagePointEvent.ts).where(SignagePointEvent.signage_point == signage_point)
    if db_session is not None:
        result = db_session.execute(query)
        return result.scalars().first()
    with session() as db_session:
        result = db_session.execute(query)
        return result.scalars().first()
