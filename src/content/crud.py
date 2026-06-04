from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db
from src.content.models import Content
from sqlalchemy import select

import uuid
class ContentCRUDService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_content(self, title: str, description: str, content_type: str, r2_key: str, url: str, thumbnail_url: str, duration: float, file_size: int, uploaded_by_id: uuid.UUID):
        content = Content(
            title=title,
            description=description,
            content_type=content_type,
            r2_key=r2_key,
            url=url,
            thumbnail_url=thumbnail_url,
            duration=duration,
            file_size=file_size,
            uploaded_by_id=uploaded_by_id
        )
        self.db.add(content)
        await self.db.commit()
        await self.db.refresh(content)
        return content
    
    async def get_content(self, user_id: uuid.UUID, content_id: uuid.UUID):
        stmt = select(Content).where(Content.content_id == content_id, Content.uploaded_by_id == user_id)
        content = await self.db.execute(stmt)
        return content.scalar_one_or_none()


def content_service(db: AsyncSession):
    return ContentCRUDService(db=db)
