
## 1. What this connection does
A WebSocket connection keeps all participants in a room synchronized (play, pause, seek), allows text chat, and broadcasts join/leave and room state updates in real time.

---

## 2. Connection endpoint
- Path: `/ws/api/room/{room_code}`
- The server accepts a JWT token via the `token` query parameter for authenticated users. If absent or invalid, a guest identity is generated.

---

## 3. Authentication (simple description)
- If a valid JWT is present in the `token` query parameter, the server loads the authenticated user and marks `is_authenticated = True` for that connection.
- If no valid token is provided, the server generates a temporary `GuestUser` (unique id and a guest display name). Guests have limited permissions.
- The server determines if a connection is the room host by comparing the authenticated user's id with the room's `host_id`.

---

## 4. Core event types (what they mean)
The server and clients exchange JSON messages with a `type` field and an optional `payload` object. Key event types used by the backend:

- `PLAY` — host triggered: instructs clients to play at a specified position.
- `PAUSE` — host triggered: instructs clients to pause at a specified position.
- `SEEK` — host triggered: instructs clients to seek to a specified position.
- `SYNC_REQUEST` — client -> server: asks for current room state.
- `SYNC_RESPONSE` — server -> client: returns current `room_state`, `position`, and `role` for the requesting client.
- `USER_JOINED` — server -> room: announced when a new user connects.
- `USER_LEFT` — two-way -> user state broadcast to the room.
- `CHAT` — two-way: chat messages broadcast to the room.
- `ERROR` — server -> client: returned for malformed messages or unauthorized actions.
- `ROOM_CLOSED` — server -> room: broadcast when the host disconnects and room is closed.
- `PING` / `PONG` — heartbeat: server sends `PING`; client replies with `PONG` to stay connected.

---

## 5. Server-side behavior (brief)
- The server resolves the connecting user and the `Room` record from the database.
- It tracks active WebSocket connections in an in-memory connection manager for each room.
- The server uses Redis pub/sub to publish room events and to deliver them to all connected instances/processes.
- On connection, the server publishes `USER_JOINED` and immediately sends a `SYNC_RESPONSE` back to the new client with the current playback `position` and `room_state`.
- Playback control (`PLAY`, `PAUSE`, `SEEK`) updates the database room record (state and playback position) and is broadcast to the room.
- If the host disconnects, the server marks the room inactive, sets the state to `ENDED`, and broadcasts `ROOM_CLOSED`.

---

## 6. Room model (state fields)
Important fields the server uses and communicates:
- `room_code` — human-facing room identifier.
- `room_state` — one of `waiting`, `playing`, `paused`, `ended`.
- `host_id` — the user id of the host.
- `playback_position` — float seconds representing the current position.
- `is_active` — whether the room is active.

These fields are included or used when forming `SYNC_RESPONSE` and playback events.

---

## 7. Heartbeat (what happens)
- The server sends a `PING` message periodically (about every 30 seconds).
- The server expects clients to respond with a `PONG`. If a client does not respond, the server may consider the connection dead.

---

## 8. Error cases (what to expect)
- Malformed JSON or missing fields: server sends an `ERROR` with `payload.detail = "Invalid message format."`.
- Unauthorized actions (e.g., guest or non-host trying to control playback): server sends `ERROR` with a descriptive `detail` (e.g., "Only the host can control playback.").
- Chat disabled: server may send `ERROR` like "You cannot chat in this room." if rules disallow the action.
- Room not found on connect: server raises a policy violation and the connection will not be established.

---

## 9. Typical lifecycle (step-by-step)
1. Client connects to `/ws/api/room/{room_code}` (optionally with `?token=...`).
2. Server validates token (if present) and identifies user or generates a guest.
3. Server accepts WebSocket and registers the connection in the connection manager.
4. Server subscribes to Redis channel for the room and publishes `USER_JOINED` to the channel.
5. Server sends `SYNC_RESPONSE` to the connecting client with current `room_state` and `playback_position`.
6. Server periodically sends `PING`; client should send `PONG` to remain active.
7. Playback events by host update DB and are published to all clients via Redis -> connection manager -> client sockets.
8. On disconnect: if host, room is closed and `ROOM_CLOSED` is published; otherwise `USER_LEFT` is published.



End of document.
