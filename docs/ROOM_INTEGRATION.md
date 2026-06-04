# Room Integration Guide

This document explains how the `src/rooms` backend integration works and how frontend developers can consume it.

## Overview

The room module exposes the following FastAPI endpoints under `/rooms`:

- `POST /rooms/`
- `POST /rooms/join`
- `POST /rooms/leave`
- `GET /rooms/{room_id}`

It supports two room content types:

- `upload`: room uses uploaded content via `upload_content_id`
- `youtube`: room uses a YouTube video URL via `link`

Rooms are identified by both:

- `room_id` (UUID)
- `room_code` (unique 8-character code used by viewers to join)

Frontend integration should support both authenticated users and guest users by sending one or both of these headers:

- `Authorization: Bearer <token>`
- `Session-Key: <session_key>`

---

## Key Concepts

### Room creation

`POST /rooms/` creates a room and registers the requestor as the host.

Request payload fields:

- `max_guest`: integer, between 2 and 50
- `room_code`: string, unique room code
- `provider`: `"upload"` or `"youtube"`
- `link`: required for `youtube`
- `upload_content_id`: required for `upload`

Important details:

- `provider = upload` uses `upload_content_id`
- `provider = youtube` uses `link`
- YouTube URLs are validated and the video ID is extracted on the backend
- Duplicate `room_code` values are rejected

### Join room

`POST /rooms/join` lets a user join an existing room by `room_code`.

Payload:

- `room_code`: string, 8 characters

Headers supported:

- `Authorization: Bearer <token>` for authenticated users
- `Session-Key: <session_key>` for guest users

### Leave room

`POST /rooms/{room_id}/leave` removes a user from a room.

path parameter:

- `room_id`: UUID

Headers:

- `Authorization: Bearer <token>`
- `Session-Key: <session_key>`

If the host leaves, the room can be marked as ended and inactive.

### Room detail

`GET /rooms/{room_id}/detail` returns room metadata and membership details.

Headers:

- `Authorization: Bearer <token>`
- `Session-Key: <session_key>`

The endpoint checks if the requester is a room member before returning the room.

---

## Request / Response Contract

### Create Room

Endpoint:

- `POST /rooms/`

Example request for YouTube:

```json
{
  "max_guest": 12,
  "room_code": "ABCD1234",
  "provider": "youtube",
  "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

Example request for uploaded content:

```json
{
  "max_guest": 10,
  "room_code": "ABCD1234",
  "provider": "upload",
  "upload_content_id": "uuid-of-uploaded-content"
}
```

Response type: `RoomResponse`

Important response fields:

- `room_id`
- `room_code`
- `host`
- `room_state`
- `movie_id`
- `movie_link`
- `provider`
- `playback_position`
- `is_active`
- `max_guests`
- `no_guest`
- `member_count`
- `content`
- `members`
- `chats`
- `created_at`

### Join Room

Endpoint:

- `POST /rooms/join`

Request body:

```json
{
  "room_code": "ABCD1234"
}
```

Return:

- full `RoomResponse` payload

### Leave Room

Endpoint:

- `POST /rooms/{room_id}/leave`

Headers:

- `Session-Key` or `Authorization`

Return example:

```json
{ "status": true, "details": "user left this room" }
```

### Get Room Detail

Endpoint:

- `GET /rooms/{room_id}/detail`

Return:

- full `RoomResponse` payload

---

## Authentication and Guest Handling

- Authenticated users must send `Authorization: Bearer <token>`.
- Guests should send `Session-Key: <session_key>`.
- The backend resolves membership using either the authenticated user ID or the guest session key.
- For guest users, the frontend should persist a stable `Session-Key` during the browser session.

> Note: room details are only returned if the requester is a registered room member.

---

## Room Data Shape

### Provider values

`RoomProvider` values:

- `upload`
- `youtube`

### Member shape

`RoomMemberResponse` includes:

- `member_id`
- `email`
- `role` (`host` or `viewer`)
- `joined_at`

### Content field

When the room uses uploaded content, `content` includes:

- `content_id`
- `title`
- `description`
- `url`
- `r2_key`
- `thumbnail_url`
- `file_size`
- `duration`
- `content_type`
- `created_at`

---

## Frontend Integration Flow

1. Generate or ask the user for a unique `room_code`.
2. Call `POST /rooms/` to create the room.
   - For YouTube, submit `link`.
   - For upload content, submit `upload_content_id`.
3. Store the returned `room_id` and `room_code`.
4. Call `POST /rooms/join` with `room_code` to enter a room.
5. Send `Session-Key` for guest users.
6. Send `Authorization: Bearer <token>` for authenticated users.
7. Load room state with `GET /rooms/{room_id}`.
8. Call `POST /rooms/leave` when the user exits.

---

## Integration Recommendations

- Persist `Session-Key` in local storage or cookie for guest users.
- Validate YouTube URLs on the client before calling `/rooms/`.
- Always send the exact `room_code` created by the host.
- Render `members`, `chats`, and `content` metadata in the room UI.
- Use the `provider` field to decide between a YouTube player or uploaded content playback.

---

## Important Notes

- `room_code` must be unique.
- `max_guest` is limited to 50.
- The backend extracts YouTube video IDs from valid URLs.
- Room detail access is restricted to room members.
- If the host leaves, the room may become ended/inactive.
