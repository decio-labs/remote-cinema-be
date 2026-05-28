
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from src.content.models import ContentType

import uuid

class ContentResponse(BaseModel):
    content_id: uuid.UUID
    title: str
    description: Optional[str]
    url: str
    r2_key: str
    thumbnail_url: Optional[str]
    file_size: Optional[int]
    duration: Optional[float]
    content_type: ContentType
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class UserLibraryResponse(BaseModel):
    total_storage: Optional[float]
    used_storage: Optional[float]
    current_plan: Optional[str]
    your_movies: Optional[list]
