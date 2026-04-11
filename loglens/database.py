from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path
from loglens.models import Base, LogEntry


DB_PATH = Path(__file__).parent.parent / "loglens.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


def get_engine():
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine


def save_entries(entries: list[dict]) -> int:
    engine = get_engine()
    saved = 0

    with Session(engine) as session:
        for entry in entries:
            log = LogEntry(
                timestamp=entry["timestamp"],
                level=entry["level"],
                endpoint=entry["endpoint"],
                status_code=entry["status_code"],
                response_time_ms=entry["response_time_ms"],
            )
            session.add(log)
            saved += 1

        session.commit()

    print(f"Saved {saved} entries to database.")
    return saved


def get_all_entries() -> list[LogEntry]:
    engine = get_engine()

    with Session(engine) as session:
        entries = session.query(LogEntry).all()
        return entries


def get_entries_by_level(level: str) -> list[LogEntry]:
    engine = get_engine()

    with Session(engine) as session:
        entries = (
            session.query(LogEntry)
            .filter(LogEntry.level == level.upper())
            .all()
        )
        return entries