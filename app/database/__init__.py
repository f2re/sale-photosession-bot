from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from .models import Base


class Database:
    def __init__(self, db_url: str):
        # Use proper connection pooling for production
        self.engine = create_async_engine(
            db_url,
            poolclass=AsyncAdaptedQueuePool,  # Use connection pool instead of NullPool
            pool_size=10,  # Core pool size - connections kept alive
            max_overflow=20,  # Additional connections under load
            pool_timeout=30,  # Wait time for connection (seconds)
            pool_recycle=3600,  # Recycle connections every hour (prevents stale connections)
            pool_pre_ping=True,  # Check connection health before use
            echo=False
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.session_maker()


# Global database instance
db: Database = None


def get_db() -> Database:
    """Get global database instance"""
    return db


def init_db(db_url: str) -> Database:
    """Initialize database"""
    global db
    db = Database(db_url)
    return db
