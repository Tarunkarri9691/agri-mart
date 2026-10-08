"""Rate limiting (per client IP) and audit logging of state-changing requests."""
import time
from collections import defaultdict, deque

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from . import config
from .database import SessionLocal
from .models import AuditLog


class RateLimiter:
    """Sliding-window limiter, in memory (use Redis when running multiple workers)."""
    def __init__(self):
        self.hits: dict[tuple, deque] = defaultdict(deque)

    def allow(self, key: tuple, limit: int, window: float = 60.0, now: float | None = None) -> bool:
        if limit <= 0:
            return True
        now = time.time() if now is None else now
        q = self.hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


limiter = RateLimiter()


def _ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        auth = path.startswith("/auth/")
        limit = config.AUTH_RATE_LIMIT_PER_MIN if auth else config.RATE_LIMIT_PER_MIN
        if request.method != "OPTIONS" and not limiter.allow((_ip(request), auth), limit):
            return JSONResponse({"detail": "Too many requests. Please slow down."}, status_code=429,
                                headers={"Retry-After": "60"})
        return await call_next(request)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if config.AUDIT_LOG and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            uid = None
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                try:
                    uid = int(jwt.decode(auth[7:], config.SECRET_KEY, algorithms=[config.ALGORITHM])["sub"])
                except Exception:
                    pass
            try:
                with SessionLocal() as db:   # no request bodies are stored (privacy)
                    db.add(AuditLog(user_id=uid, method=request.method, path=request.url.path[:200],
                                    status_code=response.status_code, ip=_ip(request)[:45]))
                    db.commit()
            except Exception:
                pass
        return response
