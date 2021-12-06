from datetime import datetime, timedelta
from typing import Optional, Tuple

from monitor.database.events import (BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent,
                                     HarvesterPlotsEvent, SignagePointEvent, WalletBalanceEvent)
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.functions import func


def get_proofs_found(session: Session) -> Optional[int]:
    result = session.execute(select(func.sum(FarmingInfoEvent.proofs)))
    return result.scalars().first()


def get_harvester_count(session: Session) -> Optional[int]:
    result = session.execute(
        select(ConnectionsEvent.harvester_count).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


def get_sync_status(session: Session) -> Optional[bool]:
    result = session.execute(
        select(BlockchainStateEvent.synced).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


def get_blockchain_state(session: Session) -> Optional[BlockchainStateEvent]:
    result = session.execute(select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


def get_wallet_balance(session: Session) -> Optional[WalletBalanceEvent]:
    result = session.execute(select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


def get_connections(session: Session) -> Optional[ConnectionsEvent]:
    result = session.execute(select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


def get_farming_start(session: Session) -> Optional[datetime]:
    result = session.execute(select(func.min(FarmingInfoEvent.ts)))
    return result.scalars().first()


def get_previous_signage_point(session: Session) -> Optional[str]:
    result = session.execute(
        select(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc()).distinct(
            FarmingInfoEvent.signage_point).limit(2))
    return result.all()[-1][0]


def get_plot_delta(session: Session, period=timedelta(hours=24)) -> Tuple[int, int]:
    result = session.execute(select(func.min(HarvesterPlotsEvent.ts)))
    first_ts = result.scalars().first()
    if first_ts is None:
        return 0, 0
    initial_ts = max(first_ts, datetime.now() - period)
    sub_query = select([
        HarvesterPlotsEvent.plot_count, HarvesterPlotsEvent.portable_plot_count,
        HarvesterPlotsEvent.plot_size, HarvesterPlotsEvent.portable_plot_size
    ]).where(HarvesterPlotsEvent.ts > initial_ts).order_by(HarvesterPlotsEvent.ts).group_by(
        HarvesterPlotsEvent.host)
    result = session.execute(
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
    current_plot_count = get_plot_count(session)
    if current_plot_count is None:
        return 0, 0
    current_plot_size = get_plot_size(session)
    if current_plot_size is None:
        return 0, 0
    return current_plot_count - initial_plot_count, current_plot_size - initial_plot_size


def get_plot_count(session: Session) -> Optional[int]:
    og_plot_count = get_og_plot_count(session)
    portable_plot_count = get_portable_plot_count(session)
    if og_plot_count is not None and portable_plot_count is not None:
        return og_plot_count + portable_plot_count
    elif og_plot_count is not None and portable_plot_count is None:
        return og_plot_count
    elif og_plot_count is None and portable_plot_count is not None:
        return portable_plot_count
    else:
        return None


def get_plot_size(session: Session) -> Optional[int]:
    og_plot_size = get_og_plot_size(session)
    portable_plot_size = get_portable_plot_size(session)
    if og_plot_size is not None and portable_plot_size is not None:
        return og_plot_size + portable_plot_size
    elif og_plot_size is not None and portable_plot_size is None:
        return og_plot_size
    elif og_plot_size is None and portable_plot_size is not None:
        return portable_plot_size
    else:
        return None


def get_og_plot_size(session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_size).label("plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = session.execute(select(func.sum(sub_query.c.plot_size)))
    return result.scalars().first()


def get_og_plot_count(session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_count).label("plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = session.execute(select(func.sum(sub_query.c.plot_count)))
    return result.scalars().first()


def get_portable_plot_size(session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_size).label("portable_plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = session.execute(select(func.sum(sub_query.c.portable_plot_size)))
    return result.scalars().first()


def get_portable_plot_count(session: Session) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_count).label("portable_plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = session.execute(select(func.sum(sub_query.c.portable_plot_count)))
    return result.scalars().first()


def get_signage_points_per_minute(session: Session, interval: timedelta) -> Optional[float]:
    result = session.execute(
        select(func.count(
            SignagePointEvent.ts)).where(SignagePointEvent.ts >= datetime.now() - interval))
    num_signage_points = result.scalars().first()
    if num_signage_points is None:
        return None
    return num_signage_points / (interval.seconds / 60)


def get_passed_filters_per_minute(session: Session, interval: timedelta) -> Optional[float]:
    result = session.execute(
        select(func.sum(
            FarmingInfoEvent.passed_filter)).where(FarmingInfoEvent.ts >= datetime.now() - interval))
    passed_filters = result.scalars().first()
    if passed_filters is None:
        return None
    return passed_filters / (interval.seconds / 60)


def get_current_balance(session: Session) -> int:
    result = session.execute(select(WalletBalanceEvent.confirmed).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


def get_last_payment(session: Session) -> int:
    current_balance = get_current_balance(session)
    previous_balance_query = session.execute(
        select(WalletBalanceEvent.confirmed).where(
            WalletBalanceEvent.confirmed != current_balance).order_by(WalletBalanceEvent.ts.desc()))
    last_balance = previous_balance_query.scalars().first()
    return int(current_balance) - int(last_balance)
