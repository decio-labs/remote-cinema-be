from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import update, select
from src.config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from .dependencies import AuthenticatedUser, GuestUser, get_websocket_user, get_websocket_room
from ..rooms.models import Room, RoomState
from .redis import get_redis_client
from .managers import manager
from .events import EventType

import logging, asyncio, time

logger = logging.getLogger("uvicorn.error")
HEARTBEAT_INTERVAL = 30
MAX_CHAT_MESSAGE = 200
redis = get_redis_client()

async def heartbeat(websocket: WebSocket):
    global HEARTBEAT_INTERVAL
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_json({'type': "PING"})
        except Exception:
            break

async def _broadcast_user_joined(room_code: str, user: AuthenticatedUser | GuestUser, is_host):
    await manager.publish(redis, room_code, {
        "type": EventType.USER_JOINED.value,
        "payload": {
            "user_name": user.user_name,
            "is_guest": user.is_guest,
            "is_host": is_host
        },
        "timestamp": time.time()
    })

async def _broadcast_sync_response(websocket: WebSocket, room: Room, is_host: bool):
    await manager.send_personal(websocket, {
        "type": EventType.SYNC_RESPONSE.value,
        "payload": {
            "room_state": room.room_state,
            "position": room.playback_position,
            "role": "host" if is_host else "guest"
        },
        "timestamp": time.time()
    })

async def _broadcast_chat_message(room_code: str, user: AuthenticatedUser | GuestUser, message):
    await manager.publish(redis, room_code, {
        "type": EventType.CHAT.value,
        "payload": {
            "message": message,
            "is_guest": user.is_guest, 
            "sender": user.user_name
        },
        "timestamp": time.time(),
    })

async def _broadcast_video_player(room_code: str, event: EventType, position: float, db: AsyncSession, user: AuthenticatedUser | GuestUser):
    if event == EventType.PLAY:
        new_state = RoomState.PLAYING
    elif event == EventType.PAUSE:
        new_state = RoomState.PAUSED
    else:
        room = await db.execute(select(Room).where(Room.room_code == room_code))
        new_state = room.scalar_one().room_state

    await db.execute(update(Room).where(Room.room_code == room_code).values(room_state=new_state, playback_position=position))
    await db.commit()

    await manager.publish(redis, room_code, {
        "type": event,
        "payload": {
            "position": position,
            "state": new_state.value,
            "server_time": time.time(),
        },
        "sender": user.user_name,
        "timestamp": time.time(),
    })

async def _broadcast_host_left(room_code: str, db: AsyncSession):
    await db.execute(
        update(Room)
        .where(Room.room_code == room_code)
        .values(is_active=False, room_state=RoomState.ENDED)
    )
    await db.commit()
    await manager.publish(redis, room_code, {
        "type": EventType.ROOM_CLOSED.value,
        "payload": {"detail": "Host has left. Room is closed."},
        "timestamp": time.time(),
    })
    

async def _broadcast_guest_left(room_code: str, user: AuthenticatedUser | GuestUser):
    await manager.publish(redis, room_code, {
        "type": EventType.USER_LEFT.value,
        "payload": {
            "username": user.user_name,
            "is_guest": user.is_guest,
        },
        "timestamp": time.time(),
    })

async def room_websocket(websocket: WebSocket, room_code: str, db: AsyncSession = Depends(get_db)):

    user: AuthenticatedUser | GuestUser = await get_websocket_user(websocket, db)
    room: Room = await get_websocket_room(room_code, db)
    is_host: bool = user.is_authenticated and str(room.host_id) == str(user.id)
    can_chat: bool = True
    can_control: bool = is_host

    # create connection
    await manager.connet(room_code=room_code, user=user, websocket=websocket)
    await _broadcast_user_joined(room_code, user, is_host)
    # send current playback
    await _broadcast_sync_response(websocket, room, is_host)
    
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    # main loop that keeps the connection alive
    try:
        while True:
            import json

            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                event_type: str = data.get("type")
                payload: dict = data.get("payload", {})
            except (json.JSONDecodeError, KeyError):
                await manager.send_personal(websocket, {
                    "type": EventType.ERROR.value,
                    "payload": {"detail": "Invalid message format."},
                })
                continue
            
            if event_type == "PONG":
                continue

            if event_type == EventType.SYNC_REQUEST:
                result = await db.execute(select(Room).where(Room.room_code == room_code, is_active=True))
                room = result.scalar_one()
                await _broadcast_sync_response(websocket, room, is_host)
                continue
            if event_type == EventType.CHAT:
                if not can_chat:
                    await manager.send_personal(websocket, {
                        "type": EventType.ERROR.value,
                        "payload": {"detail": "You cannot chat in this room."},
                    })
                    continue

                message = str(payload.get("message", None)).strip()[:MAX_CHAT_MESSAGE]
                if message:
                    await _broadcast_chat_message(room_code, user, message)
                continue


            if event_type == EventType.USER_LEFT:
                if is_host:
                    await _broadcast_host_left(room_code, db)
                    manager.disconnect(room_code, user)
                else:
                    await _broadcast_guest_left(room_code, user)
                    await manager.discard_user(room_code, user)
                continue

            if event_type in (EventType.PAUSE, EventType.PLAY, EventType.SEEK):
                if not can_control:
                    await manager.send_personal(websocket, {
                        "type": EventType.ERROR.value,
                        "payload": {
                            "detail": "Only the host can control playback."
                            if user.is_authenticated
                            else "Guests cannot control playback. Sign in to host a room."
                        },
                    })
                    continue
                position = float(payload.get("position", None))
                await _broadcast_video_player(room_code, event_type, position, db, user)
                continue

            await manager.send_personal(websocket, {
                "type": EventType.ERROR,
                "payload": {"detail": f"Unknown event type: {event_type}"},
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"Websocket error for user {user.user_name} in room {room_code}: {exc}")

    finally:
        heartbeat_task.cancel()
        manager.disconnect(room_code, user)

        if is_host:
            await _broadcast_host_left(room_code, db)
        else:
            await _broadcast_guest_left(room_code, user)