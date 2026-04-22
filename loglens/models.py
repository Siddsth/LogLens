from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel
from datetime import datetime


class Base(DeclarativeBase):
    pass


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    level = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)

    def __repr__(self):
        return (
            f"<LogEntry id={self.id} level={self.level} "
            f"endpoint={self.endpoint} status={self.status_code}>"
        )

class LogEntrySchema(BaseModel):
    id: int
    timestamp: datetime
    level: str
    endpoint: str
    status_code: int
    response_time_ms: float

    model_config = {"from_attributes": True}