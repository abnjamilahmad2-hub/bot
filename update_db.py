import asyncio
from shared.database import AsyncSessionLocal
from shared.models import Guild
from sqlalchemy import update

async def f():
    async with AsyncSessionLocal() as session:
        await session.execute(update(Guild).values(active_systems='guard_ai,level_ai,economy_ai,onboard_ai,event_ai,support_ai'))
        await session.commit()

asyncio.run(f())
