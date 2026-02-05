"""Database connections"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import clickhouse_connect
from config import settings


# PostgreSQL
pg_engine = create_async_engine(settings.postgres_dsn, echo=False)
async_session = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


# ClickHouse
def get_clickhouse():
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_db,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )
