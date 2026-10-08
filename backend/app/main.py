import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, models  # noqa: F401  (register tables)
from .api import admin, alerts, auth, buyer, farmer, groups, offers, prices, recommendations, ws as ws_api
from .database import Base, engine
from .middleware import AuditMiddleware, RateLimitMiddleware
from .ws import manager

if config.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.loop = asyncio.get_running_loop()
    scheduler = None
    if config.ENABLE_SCHEDULER:
        from .jobs import start_scheduler
        scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="AI Agricultural Marketplace", version="2.0.0", lifespan=lifespan,
              description="Farmer-buyer matching, net realization optimization, offers, alerts and admin tools")
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, farmer.router, buyer.router, recommendations.router, prices.router, offers.router,
          groups.router, alerts.router, admin.router, ws_api.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
