from fastapi import FastAPI, HTTPException, UploadFile, File
from loglens.database import get_all_entries, get_entries_by_level, save_entries
from loglens.models import LogEntrySchema
from loglens.parser import parse_file
import tempfile
import os
from loglens.detector import run_all_detectors


app = FastAPI(
    title="LogLens API",
    description="Analyze and query log files",
    version="1.0.0"
)


@app.get("/")
def root():
    return {"message": "Welcome to LogLens API"}


@app.get("/logs", response_model=list[LogEntrySchema])
def get_logs():
    entries = get_all_entries()
    return entries


@app.get("/logs/level/{level}", response_model=list[LogEntrySchema])
def get_logs_by_level(level: str):
    valid_levels = ["INFO", "ERROR", "WARNING"]
    if level.upper() not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level. Choose from {valid_levels}"
        )
    entries = get_entries_by_level(level)
    return entries


@app.post("/logs/upload")
async def upload_log_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".log"):
        raise HTTPException(
            status_code=400,
            detail="Only .log files are accepted"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        entries = parse_file(tmp_path)
        saved = save_entries(entries)
        return {"message": f"Successfully uploaded and saved {saved} log entries"}
    finally:
        os.unlink(tmp_path)


@app.get("/logs/summary")
def get_summary():
    entries = get_all_entries()

    if not entries:
        return {"message": "No log entries found"}

    levels = {}
    endpoints = {}
    total_response_time = 0

    for entry in entries:
        levels[entry.level] = levels.get(entry.level, 0) + 1
        endpoints[entry.endpoint] = endpoints.get(entry.endpoint, 0) + 1
        total_response_time += entry.response_time_ms

    return {
        "total_entries": len(entries),
        "levels": levels,
        "endpoints": endpoints,
        "avg_response_time_ms": round(total_response_time / len(entries), 2)
    }

@app.get("/anomalies")
def get_anomalies():
    results = run_all_detectors()
    return results


@app.get("/anomalies/statistical")
def get_statistical_anomalies():
    from loglens.detector import detect_statistical_anomalies
    entries = get_all_entries()
    anomalies = detect_statistical_anomalies(entries)
    return {
        "count": len(anomalies),
        "anomalies": anomalies
    }