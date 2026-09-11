from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import get_config

config = get_config()
engine = create_async_engine(config.postgres.dsn, echo=False)
SessionFactory = async_sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)
