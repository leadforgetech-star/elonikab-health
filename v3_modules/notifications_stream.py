"""Notifications temps reel via Server-Sent Events (SSE) - V2 optimisee."""
import asyncio
import json
from datetime import datetime

from fastapi import Cookie, Request
from fastapi.responses import StreamingResponse


SESSION_COOKIE = "elonikab_session"


def install_notifications_stream(app, get_db):
    """Enregistre GET /api/notifications/stream (SSE)."""

    @app.get("/api/notifications/stream")
    async def stream(request: Request, session_token: str = Cookie(None, alias=SESSION_COOKIE)):
        # Auth manuelle
        if not session_token:
            return StreamingResponse(
                iter(["event: error\ndata: unauthorized\n\n"]),
                media_type="text/event-stream",
                status_code=401,
            )

        conn = get_db()
        try:
            user = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token = ? AND s.expires_at > ?",
                (session_token, datetime.now().isoformat(timespec="seconds")),
            ).fetchone()
        finally:
            conn.close()

        if user is None:
            return StreamingResponse(
                iter(["event: error\ndata: unauthorized\n\n"]),
                media_type="text/event-stream",
                status_code=401,
            )

        user_id = user["id"]

        # Capturer le MAX(id) courant pour ne livrer QUE les nouvelles notifs
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(id), 0) AS mx FROM notifications WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            baseline_id = row["mx"] if row else 0
        finally:
            conn.close()

        async def event_generator():
            import time
            last_id = baseline_id
            started = time.time()
            # Limiter la duree de connexion pour permettre le reload uvicorn
            MAX_LIFETIME = 25.0
            # Ping initial pour amorcer les buffers proxy
            yield ": connected\n\n"
            idle = 0
            while True:
                if await request.is_disconnected():
                    break
                if time.time() - started > MAX_LIFETIME:
                    yield ": reload-window\n\n"
                    break
                try:
                    conn = get_db()
                    rows = conn.execute(
                        "SELECT id, title, body, order_id, is_read, created_at"
                        " FROM notifications WHERE user_id = ? AND id > ?"
                        " ORDER BY id LIMIT 50",
                        (user_id, last_id),
                    ).fetchall()
                    conn.close()
                    if rows:
                        for r in rows:
                            last_id = r["id"]
                            payload = {
                                "id": r["id"],
                                "title": r["title"],
                                "body": r["body"],
                                "order_id": r["order_id"],
                                "created_at": r["created_at"],
                            }
                            yield "data: " + json.dumps(payload) + "\n\n"
                        idle = 0
                    else:
                        idle += 1
                        if idle % 10 == 0:
                            yield ": keep-alive\n\n"
                except Exception:
                    yield ": error\n\n"

                await asyncio.sleep(1.0)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "Content-Encoding": "identity",
            },
        )
