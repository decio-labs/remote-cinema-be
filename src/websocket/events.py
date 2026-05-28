
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class EventType(str, Enum):
    PLAY         = "PLAY"
    PAUSE        = "PAUSE"
    SEEK         = "SEEK"

    SYNC_REQUEST  = "SYNC_REQUEST"
    SYNC_RESPONSE = "SYNC_RESPONSE"

    USER_JOINED  = "USER_JOINED"
    USER_LEFT    = "USER_LEFT"

    CHAT         = "CHAT"

    ERROR        = "ERROR"
    ROOM_CLOSED  = "ROOM_CLOSED"


class WebSocketEvent(BaseModel):
    type: EventType
    payload: dict = {}
    sender: Optional[str] = None    
    timestamp: Optional[float] = None