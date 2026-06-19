"""FastAPI application entrypoint.

Each module exposes an ``APIRouter`` named ``router`` in ``app/api/<name>.py``
(BACKEND agent), ``app/interpretation/api.py`` (DATA-SCIENCE agent), and
``app/evidence/api.py`` (RESEARCH agent). They are included here defensively so a
not-yet-implemented module never breaks startup.
"""
from __future__ import annotations

import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS

app = FastAPI(title="Health Intelligence", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Routers contributed by the specialist agents. Add module paths here.
_ROUTER_MODULES = [
    "app.api.profile",
    "app.api.domains",
    "app.api.metrics",
    "app.api.genome",
    "app.api.ingest",
    "app.interpretation.api",
    "app.evidence.api",
]

for _mod in _ROUTER_MODULES:
    try:
        module = importlib.import_module(_mod)
        app.include_router(module.router)
    except ModuleNotFoundError:
        # Module not implemented yet — skip silently during incremental build.
        pass
