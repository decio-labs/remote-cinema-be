from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db
from src.content.models import Content

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

def content_service(db: AsyncSession):
    return ContentCRUDService(db=db)
