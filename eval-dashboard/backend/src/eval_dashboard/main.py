from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eval_dashboard import eval_runner
from eval_dashboard.api import eval as eval_api
from eval_dashboard.api import nav, scoreboard
from eval_dashboard.config import get_settings
from eval_dashboard.db import close_pool, init_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    eval_runner.set_event_loop(asyncio.get_running_loop())
    yield
    close_pool()


app = FastAPI(title="eval-dashboard", version="0.1.0", lifespan=lifespan)

cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cfg.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nav.router, prefix="/api", tags=["nav"])
app.include_router(scoreboard.router, prefix="/api", tags=["scoreboard"])
app.include_router(eval_api.router, prefix="/api", tags=["eval"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
