"""
Unit tests for FastAPI Health and Readiness Probes.
Covers liveness, root discovery, and all 5 readiness dependency permutation scenarios
using controlled mocks to isolate unit testing from external infrastructure.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify application metadata and demo fiscal year configuration."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["demo_company"] == "Acme Corporation"
    assert data["demo_fiscal_year"] == 2026


def test_liveness_check_independent_of_dependencies():
    """
    Scenario 5: Liveness must succeed (HTTP 200) regardless of downstream dependencies.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Acme HR & IT Assistant API"
    assert data["demo_fiscal_year"] == 2026


@patch("app.routers.health.check_chromadb")
@patch("app.routers.health.check_postgres")
def test_readiness_both_dependencies_available(mock_pg, mock_chroma):
    """
    Scenario 1: Both PostgreSQL and ChromaDB are available -> HTTP 200.
    """
    mock_pg.return_value = (True, "connected")
    mock_chroma.return_value = (True, "connected")

    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"] == "connected"
    assert data["dependencies"]["chromadb"] == "connected"


@patch("app.routers.health.check_chromadb")
@patch("app.routers.health.check_postgres")
def test_readiness_postgres_unavailable(mock_pg, mock_chroma):
    """
    Scenario 2: PostgreSQL unavailable, ChromaDB available -> HTTP 503.
    """
    mock_pg.return_value = (False, "disconnected (OperationalError)")
    mock_chroma.return_value = (True, "connected")

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert "disconnected" in data["dependencies"]["database"]
    assert data["dependencies"]["chromadb"] == "connected"


@patch("app.routers.health.check_chromadb")
@patch("app.routers.health.check_postgres")
def test_readiness_chromadb_unavailable(mock_pg, mock_chroma):
    """
    Scenario 3: PostgreSQL available, ChromaDB unavailable -> HTTP 503.
    """
    mock_pg.return_value = (True, "connected")
    mock_chroma.return_value = (False, "disconnected (ConnectError)")

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["database"] == "connected"
    assert "disconnected" in data["dependencies"]["chromadb"]


@patch("app.routers.health.check_chromadb")
@patch("app.routers.health.check_postgres")
def test_readiness_both_unavailable(mock_pg, mock_chroma):
    """
    Scenario 4: Both PostgreSQL and ChromaDB unavailable -> HTTP 503.
    """
    mock_pg.return_value = (False, "disconnected (OperationalError)")
    mock_chroma.return_value = (False, "disconnected (ConnectError)")

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert "disconnected" in data["dependencies"]["database"]
    assert "disconnected" in data["dependencies"]["chromadb"]


@patch("app.routers.health.check_chromadb")
@patch("app.routers.health.check_postgres")
def test_liveness_remains_operational_when_dependencies_fail(mock_pg, mock_chroma):
    """
    Scenario 5 (explicit): Verify liveness probe stays 200 OK even while readiness is failing.
    """
    mock_pg.return_value = (False, "disconnected")
    mock_chroma.return_value = (False, "disconnected")

    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 503

    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "ok"
