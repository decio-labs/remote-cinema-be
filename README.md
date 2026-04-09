# 🎬 Joint Streaming App

A real-time streaming platform that lets users watch videos together in sync while communicating through voice chat. Built for seamless shared experiences, no matter the distance.

---

## 🚀 Overview

This application enables multiple users to join a shared session where video playback is synchronized across all participants. Actions like play, pause, and seek are reflected instantly for everyone in the room.

It combines real-time communication with a scalable backend to simulate a “watch together” experience online.

---

## ✨ Features

- 🔄 **Synchronized Video Playback**  
  Real-time syncing of play, pause, and seek across all users

- 🎧 **Voice Chat Integration**  
  Communicate live while watching

- 👥 **Room-Based Sessions**  
  Create or join private streaming rooms via unique IDs

- ⚡ **Low Latency Updates**  
  WebSocket-based communication ensures near-instant updates

- 🔐 **User Authentication (Optional / Planned)**  
  Secure access and session control

---

## 🏗️ Tech Stack

### Backend
- **FastAPI** – High-performance Python web framework  
- **PostgreSQL** – Relational database for persistent storage  
- **WebSockets** – Real-time communication and synchronization  
- **Redis (Optional but Recommended)** – Pub/Sub and caching for scaling  

### Frontend
- **SQLAlchemy / ORM** – Database interaction  

### Backend

- **FastAPI** – High-performance Python web framework
- **PostgreSQL** – Recommended relational database for persistent storage (development defaults to SQLite)
- **WebSockets** – Real-time communication and synchronization
- **Redis (Optional but Recommended)** – Pub/Sub and caching for scaling
---
### Tooling

- **SQLAlchemy / ORM** – Database interaction
- **Alembic** – Database migrations
- **Docker** – Containerization (optional)
- **Swagger (OpenAPI)** – API documentation (auto-generated via FastAPI)

### Database & Migrations (Postgres recommended)

This project prefers PostgreSQL in production. For local development you can use SQLite (default in `app/core/config.py`).

Set your `DATABASE_URL` in a local `.env` file (not committed) or in your shell. Example Postgres URL:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/remote_cinema
```

Run migrations with Alembic after installing requirements and setting `DATABASE_URL`:

```bash
source env/bin/activate
pip install -r requirements.txt
alembic revision --autogenerate -m "init"
alembic upgrade head
```

If you prefer SQLite for quick local testing, use the `.env.example` which defaults to `sqlite:///./dev.db`.
2. Another user joins using a room ID  
3. When a user interacts with playback:
   - The action is sent to the backend via WebSocket
   - FastAPI processes and broadcasts the event  
4. All connected clients update their playback state instantly  
5. Voice chat runs in parallel using WebRTC  

---

## 📁 Project Structure
- /backend
- /app
- /api # API routes
- /core # Config, settings
- /models # Database models
- /schemas # Pydantic schemas
- /services # Business logic
- /websocket # WebSocket handlers
- /db # Database connection
- main.py # Entry point