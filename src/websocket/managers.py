from redis.asyncio import Redis
from fastapi import WebSocket
from .redis import get_redis_client 

import logging, asyncio, json, time

logger = logging.getLogger('uvicorn.error')
redis: Redis = get_redis_client()

class ConnectionManager:
    def  __init__(self):
        self._connection: dict[str, dict[str, WebSocket]] = {}
        self.subscriber_tasks: dict[str, asyncio.Task] = {} # tracks one subscriber per room

    def _session_key(self, user) -> str:
        return str(user.id)

    async def connet(self, room_code: str, user, websocket: WebSocket):
        await websocket.accept()
        if  room_code not in self._connection:
            # create an empty object to hold users in room
            self._connection[room_code] = {}
        self._connection[room_code][self._session_key(user)] = websocket
        logger.info(f"Websocket conneted successfully for user: {self._session_key(user)}")
        
        if room_code not in self.subscriber_tasks or self.subscriber_tasks[room_code].done():
            task = asyncio.create_task(self.subscribe_to_room(redis, room_code))
            self.subscriber_tasks[room_code] = task
            logger.info(f"Started Redis subscription task for room: {room_code}")
        else:
            logger.info(f"Already subscribed to Redis channel for room: {room_code}")

    async def discard_user(self, room_code: str, user):
        del self._connection[room_code][self._session_key(user)]

    async def disconnect(self, room_code: str, user):
        if room_code in self._connection:
            self._connection[room_code].pop(self._session_key(user), None)
            if not self._connection:
                del self._connection[room_code]
            
            if room_code in self.subscriber_tasks:
                task = self.subscriber_tasks[room_code]
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled Redis subscription task for room: {room_code}")
                del self.subscriber_tasks[room_code]
        logger.info(f"{user.user_name} disconnected from room {room_code}")

    async def send_personal(self, websocket: WebSocket, event: dict):
        try:
            await websocket.send_json(event)
        except Exception:
            pass
    
    async def broadcast_local(self, room_code: str, event: dict):
        if room_code not in self._connection:
            return
        dead = []
        for session_key, websocket in self._connection[room_code].items():
            try:
                await websocket.send_json(event)
            except Exception:
                dead.append(session_key)
        
        for key in dead:
            self._connection[room_code].pop(key, None)

    async def publish(self, redis: Redis, room_code: str, event: dict):
        logger.info("publishing event to Redis channel for room %s: %s", room_code, event)
        await redis.publish(f"room:{room_code.strip()}", json.dumps(event))

    async def subscribe_to_room(self, redis: Redis, room_code: str):
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"room:{room_code.strip()}")
        logger.info(f"Subscribed to Redis channel for room: {room_code}")
        try:
            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                event = json.loads(message['data'])
                await self.broadcast_local(room_code, event)
                if room_code not in self._connection:
                    break
        except Exception as e:
            logger.error(f"Error in Redis subscription for room {room_code}: {e}")
        except asyncio.CancelledError:
            logger.info(f"Redis subscription for room {room_code} cancelled")
        finally:
            await pubsub.unsubscribe(f"room:{room_code}")
            await pubsub.aclose()
            logger.info(f"Unsubscribed from Redis channel for room: {room_code}")


manager = ConnectionManager()