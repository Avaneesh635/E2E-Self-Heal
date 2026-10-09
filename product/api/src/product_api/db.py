"""Database engine for the product API."""

from functools import lru_cache

import structlog
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from product_api.config import get_settings

logger = structlog.get_logger(__name__)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def database_reachable(engine: Engine) -> bool:
    """Return whether a trivial query succeeds against ``engine``."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("database_unreachable")
        return False
    return True
