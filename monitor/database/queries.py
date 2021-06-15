from datetime import datetime, timedelta
from typing import Optional

from monitor.database.events import BlockchainStateEvent, ConnectionsEvent, FarmingInfoEvent, HarvesterPlotsEvent, SignagePointEvent, WalletBalanceEvent
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


async def get_last_plot_count(session: AsyncSession, harvester_count: int) -> Optional[int]:
    sub_query = select([
        func.sum(FarmingInfoEvent.total_plots).label("plot_count"),
        func.count(FarmingInfoEvent.ts).label("harvester_count")
    ]).group_by(FarmingInfoEvent.signage_point).order_by(FarmingInfoEvent.ts.desc())
    result = await session.execute(
        select(sub_query.c.plot_count).where(sub_query.c.harvester_count == harvester_count))
    return result.scalars().first()


async def get_plot_size(session: AsyncSession) -> Optional[int]:
    sub_query = select([
        func.max(HarvesterPlotsEvent.plot_size).label("plot_size")
    ]).where(HarvesterPlotsEvent.ts > datetime.now() - timedelta(seconds=60)).group_by(
        HarvesterPlotsEvent.host)
    result = await session.execute(select(func.sum(sub_query.c.plot_size)))
    return result.scalars().first()


async def get_plot_count(session: AsyncSession, signage_point: str) -> Optional[int]:
    result = await session.execute(
        select(func.sum(
            FarmingInfoEvent.total_plots)).where(FarmingInfoEvent.signage_point == signage_point))
    return result.scalars().first()


async def get_signage_points_per_minute(session: AsyncSession, interval: timedelta) -> Optional[float]:
    result = await session.execute(
        select(func.count(SignagePointEvent.ts)).where(SignagePointEvent.ts >= datetime.now() - interval)
    )
    num_signage_points = result.scalars().first()
    return num_signage_points / (interval.seconds / 60)


async def get_passed_filters_per_minute(session: AsyncSession, interval: timedelta) -> Optional[float]:
    result = await session.execute(
        select(func.sum(
            FarmingInfoEvent.passed_filter)).where(FarmingInfoEvent.ts >= datetime.now() - interval))
    passed_filters = result.scalars().first()
    return passed_filters / (interval.seconds / 60)