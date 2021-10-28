from datetime import datetime, timedelta
from typing import Optional, Tuple

from monitor.database.events import (BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent,
                                     HarvesterPlotsEvent, SignagePointEvent, WalletBalanceEvent)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.functions import func


async def get_proofs_found(session: AsyncSession) -> Optional[int]:
    result = await session.execute(select(func.sum(FarmingInfoEvent.proofs)))
    return result.scalars().first()


async def get_harvester_count(session: AsyncSession) -> Optional[int]:
    result = await session.execute(
        select(ConnectionsEvent.harvester_count).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


async def get_sync_status(session: AsyncSession) -> Optional[bool]:
    result = await session.execute(
        select(BlockchainStateEvent.synced).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


async def get_blockchain_state(session: AsyncSession) -> Optional[BlockchainStateEvent]:
    result = await session.execute(select(BlockchainStateEvent).order_by(BlockchainStateEvent.ts.desc()))
    return result.scalars().first()


async def get_wallet_balance(session: AsyncSession) -> Optional[WalletBalanceEvent]:
    result = await session.execute(select(WalletBalanceEvent).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


async def get_connections(session: AsyncSession) -> Optional[ConnectionsEvent]:
    result = await session.execute(select(ConnectionsEvent).order_by(ConnectionsEvent.ts.desc()))
    return result.scalars().first()


async def get_farming_start(session: AsyncSession) -> Optional[datetime]:
    result = await session.execute(select(func.min(FarmingInfoEvent.ts)))
    return result.scalars().first()


async def get_previous_signage_point(session: AsyncSession) -> Optional[str]:
    result = await session.execute(
        select(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc()).distinct(
            FarmingInfoEvent.signage_point).limit(2))
    return result.all()[-1][0]


async def get_plot_delta(session: AsyncSession, period=timedelta(hours=24)) -> Tuple[int, int]:
    result = await session.execute(select(func.min(HarvesterPlotsEvent.ts)))
    first_ts = result.scalars().first()
    if first_ts is None:
        return 0, 0
    initial_ts = max(first_ts, datetime.now() - period)
    sub_query = select([
        HarvesterPlotsEvent.plot_count, HarvesterPlotsEvent.portable_plot_count,
        HarvesterPlotsEvent.plot_size, HarvesterPlotsEvent.portable_plot_size
    ]).where(HarvesterPlotsEvent.ts > initial_ts).order_by(HarvesterPlotsEvent.ts).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(
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
    current_plot_count = await get_plot_count(session)
    if current_plot_count is None:
        return 0, 0
    current_plot_size = await get_plot_size(session)
    if current_plot_size is None:
        return 0, 0
    return current_plot_count - initial_plot_count, current_plot_size - initial_plot_size


async def get_plot_count(session: AsyncSession) -> Optional[int]:
    og_plot_count = await get_og_plot_count(session)
    portable_plot_count = await get_portable_plot_count(session)
    if og_plot_count is not None and portable_plot_count is not None:
        return og_plot_count + portable_plot_count
    elif og_plot_count is not None and portable_plot_count is None:
        return og_plot_count
    elif og_plot_count is None and portable_plot_count is not None:
        return portable_plot_count
    else:
        return None


async def get_plot_size(session: AsyncSession) -> Optional[int]:
    og_plot_size = await get_og_plot_size(session)
    portable_plot_size = await get_portable_plot_size(session)
    if og_plot_size is not None and portable_plot_size is not None:
        return og_plot_size + portable_plot_size
    elif og_plot_size is not None and portable_plot_size is None:
        return og_plot_size
    elif og_plot_size is None and portable_plot_size is not None:
        return portable_plot_size
    else:
        return None


async def get_og_plot_size(session: AsyncSession) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_size).label("plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(select(func.sum(sub_query.c.plot_size)))
    return result.scalars().first()


async def get_og_plot_count(session: AsyncSession) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_count).label("plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(select(func.sum(sub_query.c.plot_count)))
    return result.scalars().first()


async def get_portable_plot_size(session: AsyncSession) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_size).label("portable_plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(select(func.sum(sub_query.c.portable_plot_size)))
    return result.scalars().first()


async def get_portable_plot_count(session: AsyncSession) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.portable_plot_count).label("portable_plot_count")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=30)).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(select(func.sum(sub_query.c.portable_plot_count)))
    return result.scalars().first()


async def get_signage_points_per_minute(session: AsyncSession, interval: timedelta) -> Optional[float]:
    result = await session.execute(
        select(func.count(SignagePointEvent.ts)).where(SignagePointEvent.ts >= datetime.now() - interval)
    )
    num_signage_points = result.scalars().first()
    if num_signage_points is None:
        return None
    return num_signage_points / (interval.seconds / 60)


async def get_passed_filters_per_minute(session: AsyncSession, interval: timedelta) -> Optional[float]:
    result = await session.execute(
        select(func.sum(
            FarmingInfoEvent.passed_filter)).where(FarmingInfoEvent.ts >= datetime.now() - interval))
    passed_filters = result.scalars().first()
    if passed_filters is None:
        return None
    return passed_filters / (interval.seconds / 60)


async def get_current_balance(session: AsyncSession) -> int:
    result = await session.execute(
        select(WalletBalanceEvent.confirmed).order_by(WalletBalanceEvent.ts.desc()))
    return result.scalars().first()


async def get_last_payment(session: AsyncSession) -> int:
    current_balance = await get_current_balance(session)
    previous_balance_query = await session.execute(
        select(WalletBalanceEvent.confirmed).where(
            WalletBalanceEvent.confirmed != current_balance).order_by(WalletBalanceEvent.ts.desc()))
    last_balance = previous_balance_query.scalars().first()
    return int(current_balance) - int(last_balance)
