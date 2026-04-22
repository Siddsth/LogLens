from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from loglens.models import Base, LogEntry
from loglens.api import app
from loglens.database import get_engine
from datetime import datetime
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(test_engine)

    monkeypatch.setattr("loglens.database.get_engine", lambda: test_engine)

    return TestClient(app)


@pytest.fixture
def client_with_data(client, tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(test_engine)

    monkeypatch.setattr("loglens.database.get_engine", lambda: test_engine)

    with Session(test_engine) as session:
        session.add_all([
            LogEntry(
                timestamp=datetime(2024, 1, 15, 10, 23, 45),
                level="ERROR",
                endpoint="/api/users",
                status_code=500,
                response_time_ms=234.0
            ),
            LogEntry(
                timestamp=datetime(2024, 1, 15, 10, 23, 46),
                level="INFO",
                endpoint="/api/health",
                status_code=200,
                response_time_ms=12.0
            ),
            LogEntry(
                timestamp=datetime(2024, 1, 15, 10, 23, 47),
                level="WARNING",
                endpoint="/api/orders",
                status_code=429,
                response_time_ms=5.0
            ),
        ])
        session.commit()

    return TestClient(app)


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to LogLens API"}


def test_get_logs_empty(client):
    response = client.get("/logs")
    assert response.status_code == 200
    assert response.json() == []


def test_get_logs_with_data(client_with_data):
    response = client_with_data.get("/logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["level"] == "ERROR"
    assert data[1]["level"] == "INFO"


def test_get_logs_by_valid_level(client_with_data):
    response = client_with_data.get("/logs/level/ERROR")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["endpoint"] == "/api/users"
    assert data[0]["status_code"] == 500


def test_get_logs_by_invalid_level(client):
    response = client.get("/logs/level/BANANA")
    assert response.status_code == 400
    assert "Invalid level" in response.json()["detail"]


def test_get_summary_empty(client):
    response = client.get("/logs/summary")
    assert response.status_code == 200
    assert response.json() == {"message": "No log entries found"}


def test_get_summary_with_data(client_with_data):
    response = client_with_data.get("/logs/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_entries"] == 3
    assert data["levels"]["ERROR"] == 1
    assert data["levels"]["INFO"] == 1
    assert data["levels"]["WARNING"] == 1
    assert "avg_response_time_ms" in data


def test_upload_log_file(client, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2024-01-15 10:23:45 INFO /api/health 200 12ms\n"
        "2024-01-15 10:23:46 ERROR /api/users 500 234ms\n"
    )

    with open(log_file, "rb") as f:
        response = client.post(
            "/logs/upload",
            files={"file": ("test.log", f, "text/plain")}
        )

    assert response.status_code == 200
    assert "2 log entries" in response.json()["message"]


def test_upload_invalid_file_type(client):
    response = client.post(
        "/logs/upload",
        files={"file": ("test.txt", b"some content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only .log files" in response.json()["detail"]