from fastapi.responses import HTMLResponse
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

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    entries = get_all_entries()
    from loglens.detector import detect_statistical_anomalies, detect_isolation_forest_anomalies
 
    anomaly_ids = set()
    if entries:
        stat = detect_statistical_anomalies(entries)
        iso = detect_isolation_forest_anomalies(entries)
        anomaly_ids = {a["id"] for a in stat + iso}
 
    levels = {}
    endpoints = {}
    total_rt = 0
    for e in entries:
        levels[e.level] = levels.get(e.level, 0) + 1
        endpoints[e.endpoint] = endpoints.get(e.endpoint, 0) + 1
        total_rt += e.response_time_ms
 
    avg_rt = round(total_rt / len(entries), 1) if entries else 0
 
    level_colors = {"ERROR": "#f85149", "WARNING": "#e3b341", "INFO": "#3fb950"}
 
    rows = ""
    for e in entries:
        color = level_colors.get(e.level, "#8b949e")
        flag = " 🚨" if e.id in anomaly_ids else ""
        rows += f"""
        <tr class="{'anomaly-row' if e.id in anomaly_ids else ''}">
            <td>{e.id}</td>
            <td>{e.timestamp}</td>
            <td><span class="badge" style="background:{color}20;color:{color};border:1px solid {color}40">{e.level}</span></td>
            <td>{e.endpoint}</td>
            <td><span class="{'status-err' if e.status_code >= 400 else 'status-ok'}">{e.status_code}</span></td>
            <td><span class="{'rt-slow' if e.response_time_ms > 500 else ''}">{e.response_time_ms}ms</span></td>
            <td>{flag if flag else '<span class="ok">✓</span>'}</td>
        </tr>"""
 
    level_bars = ""
    total = len(entries) or 1
    for level, count in sorted(levels.items()):
        pct = round(count / total * 100)
        color = level_colors.get(level, "#8b949e")
        level_bars += f"""
        <div class="bar-row">
            <span class="bar-label">{level}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
            <span class="bar-count">{count}</span>
        </div>"""
 
    endpoint_rows = ""
    for ep, count in sorted(endpoints.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100)
        endpoint_rows += f"""
        <div class="bar-row">
            <span class="bar-label ep">{ep}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:#00b4d8"></div></div>
            <span class="bar-count">{count}</span>
        </div>"""
 
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LogLens Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }}
  a {{ color: #00b4d8; text-decoration: none; }}
 
  header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 20px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }}
  header h1 span {{ color: #00b4d8; }}
  .header-links {{ display: flex; gap: 16px; font-size: 13px; }}
 
  .main {{ padding: 24px 28px; max-width: 1400px; margin: 0 auto; }}
 
  .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }}
  .stat-card .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
  .stat-card .value {{ font-size: 32px; font-weight: 700; font-family: 'Consolas', monospace; }}
  .stat-card.blue .value {{ color: #00b4d8; }}
  .stat-card.green .value {{ color: #3fb950; }}
  .stat-card.amber .value {{ color: #e3b341; }}
  .stat-card.red .value {{ color: #f85149; }}
 
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }}
  .card h2 {{ font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 16px; }}
 
  .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .bar-label {{ font-size: 12px; color: #8b949e; width: 80px; font-family: 'Consolas', monospace; }}
  .bar-label.ep {{ width: 140px; font-size: 11px; }}
  .bar-track {{ flex: 1; background: #21262d; border-radius: 4px; height: 8px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.4s ease; }}
  .bar-count {{ font-size: 12px; color: #8b949e; width: 30px; text-align: right; }}
 
  .table-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
  .table-header {{ padding: 16px 20px; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; }}
  .table-header h2 {{ font-size: 14px; font-weight: 600; color: #fff; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ background: #0d1117; }}
  th {{ padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #30363d; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #21262d; font-size: 13px; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: #1c2128; }}
  .anomaly-row {{ background: #f8514910 !important; }}
  .anomaly-row:hover {{ background: #f8514918 !important; }}
 
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: 'Consolas', monospace; }}
  .status-ok {{ color: #3fb950; font-family: 'Consolas', monospace; }}
  .status-err {{ color: #f85149; font-family: 'Consolas', monospace; }}
  .rt-slow {{ color: #f85149; font-family: 'Consolas', monospace; }}
  .ok {{ color: #3fb950; }}
 
  .empty {{ padding: 48px; text-align: center; color: #8b949e; }}
  .upload-hint {{ font-size: 12px; color: #8b949e; margin-top: 6px; }}
 
  @media (max-width: 900px) {{
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<header>
  <h1><span>Log</span>Lens</h1>
  <div class="header-links">
    <a href="/logs">JSON</a>
    <a href="/anomalies">Anomalies API</a>
    <a href="/docs">Swagger Docs</a>
    <a href="/logs/summary">Summary API</a>
  </div>
</header>
 
<div class="main">
  <div class="stats-grid">
    <div class="stat-card blue">
      <div class="label">Total entries</div>
      <div class="value">{len(entries)}</div>
    </div>
    <div class="stat-card {'amber' if avg_rt > 200 else 'green'}">
      <div class="label">Avg response time</div>
      <div class="value">{avg_rt}<span style="font-size:14px;font-weight:400;color:#8b949e">ms</span></div>
    </div>
    <div class="stat-card red">
      <div class="label">Errors</div>
      <div class="value">{levels.get('ERROR', 0)}</div>
    </div>
    <div class="stat-card {'red' if anomaly_ids else 'green'}">
      <div class="label">Anomalies flagged</div>
      <div class="value">{len(anomaly_ids)}</div>
    </div>
  </div>
 
  <div class="grid-2">
    <div class="card">
      <h2>Log levels</h2>
      {level_bars if level_bars else '<p style="color:#8b949e;font-size:13px">No data yet</p>'}
    </div>
    <div class="card">
      <h2>Endpoints</h2>
      {endpoint_rows if endpoint_rows else '<p style="color:#8b949e;font-size:13px">No data yet</p>'}
    </div>
  </div>
 
  <div class="table-card">
    <div class="table-header">
      <h2>Log entries</h2>
      <span class="upload-hint">Upload logs at <a href="/docs#/default/upload_log_file_logs_upload_post">/docs → /logs/upload</a></span>
    </div>
    {'<table><thead><tr><th>ID</th><th>Timestamp</th><th>Level</th><th>Endpoint</th><th>Status</th><th>Response time</th><th>Anomaly</th></tr></thead><tbody>' + rows + '</tbody></table>' if entries else '<div class="empty">No log entries yet.<br><span class="upload-hint">Run <code>loglens parse logs/sample.log</code> or upload via /docs</span></div>'}
  </div>
</div>
</body>
</html>"""
    return html
 