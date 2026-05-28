from pydantic import BaseModel

import uuid
from datetime import datetime
from typing import Optional

class MessageReqeust(BaseModel):
    message: str

class MessageResponse(BaseModel):
    chat_id: uuid.UUID
    session_key: Optional[str]
    user_id: Optional[uuid.UUID]
    created_at: datetime
    message: str

class MessageListResponse(BaseModel):
    status: bool
    result: list
