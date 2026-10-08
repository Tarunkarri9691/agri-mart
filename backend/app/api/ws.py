import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import config
from ..ws import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    try:
        user_id = int(jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])["sub"])
    except Exception:
        await ws.close(code=4401)
        return
    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()   # keep-alive pings from the client
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
