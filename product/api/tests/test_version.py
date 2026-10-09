from importlib.metadata import version

import pytest
from app.schemas import SCHEMA_VERSION
from fastapi.testclient import TestClient

from product_api import main
from product_api.db import get_engine


def test_version_reports_installed_package_and_core_schema_without_database() -> None:
    def database_must_not_be_used() -> None:
        raise AssertionError("The version endpoint must not access the database")

    api = main.create_app()
    api.dependency_overrides[get_engine] = database_must_not_be_used
    client = TestClient(api)

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "api_version": version("product-api"),
        "schema_version": SCHEMA_VERSION,
    }
    assert client.get("/openapi.json").json()["info"]["version"] == version("product-api")


def test_version_updates_with_package_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def installed_version(package: str) -> str:
        assert package == "product-api"
        return "1.2.3"

    monkeypatch.setattr(main, "version", installed_version, raising=False)
    api = main.create_app()

    assert TestClient(api).get("/version").json() == {
        "api_version": "1.2.3",
        "schema_version": SCHEMA_VERSION,
    }
    assert api.version == "1.2.3"
