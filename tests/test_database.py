from loglens.database import save_entries, get_all_entries, get_entries_by_level
from loglens.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest


@pytest.fixture
def test_engine(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    return engine


SAMPLE_ENTRIES = [
    {
        "timestamp": "2024-01-15 10:23:45",
        "level": "ERROR",
        "endpoint": "/api/users",
        "status_code": 500,
        "response_time_ms": 234,
    },
    {
        "timestamp": "2024-01-15 10:23:46",
        "level": "INFO",
        "endpoint": "/api/health",
        "status_code": 200,
        "response_time_ms": 12,
    },
]


def test_save_and_retrieve(test_engine):
    with Session(test_engine) as session:
        from loglens.models import LogEntry
        from datetime import datetime
        for entry in SAMPLE_ENTRIES:
            log = LogEntry(
                timestamp=datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S"),
                level=entry["level"],
                endpoint=entry["endpoint"],
                status_code=entry["status_code"],
                response_time_ms=entry["response_time_ms"],
            )
            session.add(log)
        session.commit()

        results = session.query(LogEntry).all()
        assert len(results) == 2


def test_filter_by_level(test_engine):
    with Session(test_engine) as session:
        from loglens.models import LogEntry
        from datetime import datetime
        for entry in SAMPLE_ENTRIES:
            log = LogEntry(
                timestamp=datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S"),
                level=entry["level"],
                endpoint=entry["endpoint"],
                status_code=entry["status_code"],
                response_time_ms=entry["response_time_ms"],
            )
            session.add(log)
        session.commit()

        errors = session.query(LogEntry).filter(LogEntry.level == "ERROR").all()
        assert len(errors) == 1
        assert errors[0].endpoint == "/api/users"