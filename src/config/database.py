from .settings import setting
from sqlalchemy.ext.asyncio import (create_async_engine, 
                                    async_sessionmaker, AsyncSession)

DATABASE_URL = setting.DATABASE_URL

create_engine = create_async_engine(
    DATABASE_URL, echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=create_engine, expire_on_commit=False,
    auto_flush=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

