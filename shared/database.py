from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import insert, select, text
from shared.config import settings
import logging

logger = logging.getLogger("TS_BOT")

# تحديد رابط قاعدة البيانات مع الرجوع التلقائي لـ SQLite
_db_url = settings.database_url

# إذا كان الرابط PostgreSQL لكن asyncpg غير مثبت، نتحول تلقائياً لـ SQLite
if "postgresql" in _db_url or "asyncpg" in _db_url:
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        logger.warning("DATABASE_URL points to PostgreSQL but asyncpg is not installed. Falling back to SQLite.")
        _db_url = "sqlite+aiosqlite:///./bot.db"

engine = create_async_engine(
    _db_url,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

Base = declarative_base()

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    import shared.models  # تسجيل الجداول في Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

_ensured_cache = set()

async def ensure_user_and_guild(session: AsyncSession, user_id: int, guild_id: int, guild_name: str = "Unknown"):
    cache_key = f"{user_id}:{guild_id}"
    if cache_key in _ensured_cache:
        return

    from shared.models import User, Guild
    
    # استخدام INSERT OR IGNORE لمنع تضارب البيانات في حالات الضغط
    user_stmt = insert(User).values(id=user_id).prefix_with("OR IGNORE")
    await session.execute(user_stmt)
    
    guild_stmt = insert(Guild).values(id=guild_id, name=guild_name).prefix_with("OR IGNORE")
    await session.execute(guild_stmt)
    
    await session.commit()
    _ensured_cache.add(cache_key)
