from fastapi.responses import JSONResponse
from fastapi import WebSocket, Depends, status
from src.config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.websocket.redis import close_redis
from src.websocket.consumers import room_websocket
import src.manage

app = src.manage.app

@app.get("/read_root")
def read_root():
    return JSONResponse(content={"status": True, 'details': "Backend is running"}, status_code=200)

@app.websocket("/ws/api/room/{room_code}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    db: AsyncSession = Depends(get_db)

):
    await room_websocket(websocket, room_code, db)
    

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis()