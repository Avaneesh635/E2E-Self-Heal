"""FastAPI application for the product layer.

The product never runs Playwright or repair logic; it only consumes structured output that
the user's CI sends after running the core (see discussion #332).
"""

from typing import Annotated, Literal

from app.logging import configure_logging
from fastapi import Depends, FastAPI, Response, status
from pydantic import BaseModel
from sqlalchemy import Engine

from product_api.config import get_settings
from product_api.db import database_reachable, get_engine


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool


def create_app() -> FastAPI:
    api = FastAPI(title="E2E Self-Heal API")

    @api.get("/healthz")
    def healthz(response: Response, engine: Annotated[Engine, Depends(get_engine)]) -> Health:
        if not database_reachable(engine):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return Health(status="degraded", database=False)
        return Health(status="ok", database=True)

    return api


def run() -> FastAPI:
    """Uvicorn factory: configure logging from settings, then build the app."""
    configure_logging(get_settings().log_level)
    return create_app()
