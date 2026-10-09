from app.schemas import SCHEMA_VERSION, RepairSummary
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from product_api.db import get_engine
from product_api.main import create_app


def _client(database_url: str) -> TestClient:
    api = create_app()
    api.dependency_overrides[get_engine] = lambda: create_engine(database_url)
    return TestClient(api)


def test_healthz_is_ok_when_the_database_answers() -> None:
    response = _client("sqlite://").get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


def test_healthz_is_degraded_when_the_database_is_unreachable() -> None:
    # Port 1 refuses the connection immediately, so this does not wait on a timeout.
    response = _client("postgresql+psycopg://u:p@127.0.0.1:1/db").get("/healthz")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": False}


def test_core_ci_contract_is_importable() -> None:
    # The API ingests the core's --json output; this proves the path dependency resolves.
    assert RepairSummary.model_fields["schema_version"].default == SCHEMA_VERSION
