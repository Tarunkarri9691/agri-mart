"""WebSocket push so recommendations/notifications update live (patent: 'recommendations can be updated when new data becomes available')."""
import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.conns: dict[int, set[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.loop = asyncio.get_running_loop()
        self.conns.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        self.conns.get(user_id, set()).discard(ws)

    async def _send(self, user_id: int, ws: WebSocket, msg: dict):
        try:
            await ws.send_json(msg)
        except Exception:
            self.disconnect(user_id, ws)

    def push(self, user_id: int, msg: dict):
        """Thread-safe: callable from request handlers and scheduler threads."""
        if not self.loop or not self.conns.get(user_id):
            return
        for ws in list(self.conns[user_id]):
            asyncio.run_coroutine_threadsafe(self._send(user_id, ws, msg), self.loop)


manager = ConnectionManager()
