from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.covid import router as covid_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.db.session import init_db
from app.services.data_loader import data_loader_service

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.startup_error = None
    if settings.auto_load_on_startup:
        try:
            data_loader_service.load_data(force_reload=False)
        except Exception as exc:
            logger.exception("Data load failed on startup: %s", exc)
            app.state.startup_error = str(exc)
    yield

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    description="Scalable COVID-19 analytics API with hybrid forecasting and trend detection.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(covid_router, prefix=settings.api_prefix)
