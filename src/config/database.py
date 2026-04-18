from .settings import setting
from sqlalchemy.ext.asyncio import (create_async_engine, 
                                    async_sessionmaker, AsyncSession)
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = setting.DATABASE_URL

create_engine = create_async_engine(
    DATABASE_URL, echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=create_engine, expire_on_commit=False,
    autoflush=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            await session.rollback()
            raise exc
        finally: 
            await session.close()

