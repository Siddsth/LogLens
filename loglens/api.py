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

# ─── SHARED COMPONENTS ────────────────────────────────────────────────────────

def navbar(active: str) -> str:
    """
    Returns the HTML for the shared navbar.
    active = the name of the current page, used to highlight the active link.
    """
    pages = [
        ("Dashboard", "/dashboard"),
        ("Logs",      "/view/logs"),
        ("Anomalies", "/view/anomalies"),
        ("Summary",   "/view/summary"),
        ("Upload",    "/view/upload"),
        ("API Docs",  "/docs"),
    ]
    links = ""
    for name, href in pages:
        is_active = name == active
        links += f"""
        <a href="{href}" class="nav-link {'active' if is_active else ''}">
            {name}
        </a>"""

    return f"""
    <header>
        <div class="nav-brand"><span>Log</span>Lens</div>
        <nav class="nav-links">{links}</nav>
    </header>"""


BASE_CSS = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
  a { color: #00b4d8; text-decoration: none; }

  header { background: #161b22; border-bottom: 1px solid #30363d; padding: 0 28px; display: flex; align-items: center; justify-content: space-between; height: 56px; }
  .nav-brand { font-size: 20px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
  .nav-brand span { color: #00b4d8; }
  .nav-links { display: flex; gap: 4px; }
  .nav-link { padding: 6px 14px; border-radius: 6px; font-size: 13px; color: #8b949e; transition: background 0.15s, color 0.15s; }
  .nav-link:hover { background: #21262d; color: #c9d1d9; }
  .nav-link.active { background: #00b4d820; color: #00b4d8; font-weight: 600; }

  .main { padding: 28px; max-width: 1400px; margin: 0 auto; }
  .page-title { font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 24px; }
  .page-title span { color: #8b949e; font-size: 14px; font-weight: 400; margin-left: 10px; }

  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
  .stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
  .stat-card .label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .stat-card .value { font-size: 32px; font-weight: 700; font-family: 'Consolas', monospace; }
  .stat-card.blue .value { color: #00b4d8; }
  .stat-card.green .value { color: #3fb950; }
  .stat-card.amber .value { color: #e3b341; }
  .stat-card.red .value { color: #f85149; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
  .card h2 { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 16px; }

  .bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .bar-label { font-size: 12px; color: #8b949e; width: 80px; font-family: 'Consolas', monospace; }
  .bar-label.ep { width: 140px; font-size: 11px; }
  .bar-track { flex: 1; background: #21262d; border-radius: 4px; height: 8px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; }
  .bar-count { font-size: 12px; color: #8b949e; width: 30px; text-align: right; }

  .table-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; margin-bottom: 24px; }
  .table-header { padding: 16px 20px; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; }
  .table-header h2 { font-size: 14px; font-weight: 600; color: #fff; }
  table { width: 100%; border-collapse: collapse; }
  thead tr { background: #0d1117; }
  th { padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #30363d; }
  td { padding: 10px 16px; border-bottom: 1px solid #21262d; font-size: 13px; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: #1c2128; }
  .anomaly-row { background: #f8514910 !important; }
  .anomaly-row:hover { background: #f8514918 !important; }

  .badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: 'Consolas', monospace; }
  .status-ok { color: #3fb950; font-family: 'Consolas', monospace; }
  .status-err { color: #f85149; font-family: 'Consolas', monospace; }
  .rt-slow { color: #f85149; font-family: 'Consolas', monospace; }
  .ok { color: #3fb950; }

  .anomaly-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .anomaly-card.flagged { border-color: #f8514940; background: #f8514908; }
  .anomaly-card h3 { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 8px; }
  .anomaly-reason { font-size: 12px; color: #8b949e; font-family: 'Consolas', monospace; background: #0d1117; padding: 8px 12px; border-radius: 4px; margin-top: 8px; }

  .upload-box { background: #161b22; border: 2px dashed #30363d; border-radius: 8px; padding: 48px; text-align: center; transition: border-color 0.2s; }
  .upload-box:hover { border-color: #00b4d8; }
  .upload-box input[type=file] { display: none; }
  .upload-label { display: inline-block; padding: 10px 24px; background: #00b4d8; color: #0d1117; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 16px; }
  .upload-label:hover { background: #0096b4; }
  .upload-submit { display: inline-block; padding: 10px 24px; background: #3fb950; color: #0d1117; border-radius: 6px; font-weight: 600; cursor: pointer; border: none; font-size: 14px; margin-top: 12px; }
  .upload-submit:hover { background: #2ea043; }
  .upload-hint { font-size: 12px; color: #8b949e; margin-top: 8px; }
  .filename { font-size: 13px; color: #00b4d8; margin-top: 10px; font-family: 'Consolas', monospace; }

  .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
  .empty { padding: 48px; text-align: center; color: #8b949e; }

  .filter-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
  .filter-btn { padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid #30363d; background: #161b22; color: #8b949e; cursor: pointer; transition: all 0.15s; }
  .filter-btn:hover { border-color: #00b4d8; color: #00b4d8; }
  .filter-btn.active { background: #00b4d820; border-color: #00b4d8; color: #00b4d8; }
  .filter-btn.error.active { background: #f8514920; border-color: #f85149; color: #f85149; }
  .filter-btn.warning.active { background: #e3b34120; border-color: #e3b341; color: #e3b341; }
  .filter-btn.info.active { background: #3fb95020; border-color: #3fb950; color: #3fb950; }

  @media (max-width: 900px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .grid-2 { grid-template-columns: 1fr; }
    .summary-grid { grid-template-columns: 1fr; }
    .nav-links { gap: 2px; }
    .nav-link { padding: 6px 8px; font-size: 12px; }
  }
</style>
"""

def base_page(title: str, active: str, content: str) -> str:
    """Wraps any page content with the shared navbar, CSS, and structure."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LogLens — {title}</title>
{BASE_CSS}
</head>
<body>
{navbar(active)}
<div class="main">
{content}
</div>
<script>
// File upload label update
const fileInput = document.getElementById('logfile');
const fileLabel = document.getElementById('file-chosen');
if (fileInput) {{
    fileInput.addEventListener('change', () => {{
        fileLabel.textContent = fileInput.files[0]?.name || 'No file chosen';
    }});
}}
</script>
</body>
</html>"""


# ─── JSON API ENDPOINTS (unchanged) ──────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Welcome to LogLens API — visit /dashboard for the UI"}


@app.get("/logs", response_model=list[LogEntrySchema])
def get_logs():
    return get_all_entries()


@app.get("/logs/level/{level}", response_model=list[LogEntrySchema])
def get_logs_by_level(level: str):
    valid_levels = ["INFO", "ERROR", "WARNING"]
    if level.upper() not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid level. Choose from {valid_levels}")
    return get_entries_by_level(level)


@app.post("/logs/upload")
async def upload_log_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".log"):
        raise HTTPException(status_code=400, detail="Only .log files are accepted")
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
    levels, endpoints, total_rt = {}, {}, 0
    for entry in entries:
        levels[entry.level] = levels.get(entry.level, 0) + 1
        endpoints[entry.endpoint] = endpoints.get(entry.endpoint, 0) + 1
        total_rt += entry.response_time_ms
    return {
        "total_entries": len(entries),
        "levels": levels,
        "endpoints": endpoints,
        "avg_response_time_ms": round(total_rt / len(entries), 2)
    }


@app.get("/anomalies")
def get_anomalies():
    return run_all_detectors()


@app.get("/anomalies/statistical")
def get_statistical_anomalies():
    from loglens.detector import detect_statistical_anomalies
    entries = get_all_entries()
    anomalies = detect_statistical_anomalies(entries)
    return {"count": len(anomalies), "anomalies": anomalies}


# ─── HTML PAGES ───────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    entries = get_all_entries()
    from loglens.detector import detect_statistical_anomalies, detect_isolation_forest_anomalies

    anomaly_ids = set()
    if entries:
        stat = detect_statistical_anomalies(entries)
        iso = detect_isolation_forest_anomalies(entries)
        anomaly_ids = {a["id"] for a in stat + iso}

    levels, endpoints, total_rt = {}, {}, 0
    for e in entries:
        levels[e.level] = levels.get(e.level, 0) + 1
        endpoints[e.endpoint] = endpoints.get(e.endpoint, 0) + 1
        total_rt += e.response_time_ms

    avg_rt = round(total_rt / len(entries), 1) if entries else 0
    level_colors = {"ERROR": "#f85149", "WARNING": "#e3b341", "INFO": "#3fb950"}

    rows = ""
    for e in entries:
        color = level_colors.get(e.level, "#8b949e")
        flag = "🚨" if e.id in anomaly_ids else '<span class="ok">✓</span>'
        rows += f"""
        <tr class="{'anomaly-row' if e.id in anomaly_ids else ''}">
            <td>{e.id}</td>
            <td>{e.timestamp}</td>
            <td><span class="badge" style="background:{color}20;color:{color};border:1px solid {color}40">{e.level}</span></td>
            <td>{e.endpoint}</td>
            <td><span class="{'status-err' if e.status_code >= 400 else 'status-ok'}">{e.status_code}</span></td>
            <td><span class="{'rt-slow' if e.response_time_ms > 500 else ''}">{e.response_time_ms}ms</span></td>
            <td>{flag}</td>
        </tr>"""

    total = len(entries) or 1
    level_bars = ""
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

    content = f"""
    <div class="page-title">Dashboard <span>{len(entries)} entries · {len(anomaly_ids)} anomalies</span></div>

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
            {level_bars or '<p style="color:#8b949e;font-size:13px">No data yet</p>'}
        </div>
        <div class="card">
            <h2>Endpoints</h2>
            {endpoint_rows or '<p style="color:#8b949e;font-size:13px">No data yet</p>'}
        </div>
    </div>

    <div class="table-card">
        <div class="table-header">
            <h2>Recent log entries</h2>
            <a href="/view/logs" style="font-size:12px;color:#8b949e">View all →</a>
        </div>
        {'<table><thead><tr><th>ID</th><th>Timestamp</th><th>Level</th><th>Endpoint</th><th>Status</th><th>Response time</th><th>Anomaly</th></tr></thead><tbody>' + rows + '</tbody></table>' if entries else '<div class="empty">No log entries yet. <a href="/view/upload">Upload a log file →</a></div>'}
    </div>"""

    return base_page("Dashboard", "Dashboard", content)


@app.get("/view/logs", response_class=HTMLResponse)
def view_logs():
    entries = get_all_entries()
    from loglens.detector import detect_statistical_anomalies, detect_isolation_forest_anomalies

    anomaly_ids = set()
    if entries:
        stat = detect_statistical_anomalies(entries)
        iso = detect_isolation_forest_anomalies(entries)
        anomaly_ids = {a["id"] for a in stat + iso}

    level_colors = {"ERROR": "#f85149", "WARNING": "#e3b341", "INFO": "#3fb950"}

    rows = ""
    for e in entries:
        color = level_colors.get(e.level, "#8b949e")
        flag = "🚨" if e.id in anomaly_ids else '<span class="ok">✓</span>'
        rows += f"""
        <tr class="{'anomaly-row' if e.id in anomaly_ids else ''}" data-level="{e.level}">
            <td>{e.id}</td>
            <td>{e.timestamp}</td>
            <td><span class="badge" style="background:{color}20;color:{color};border:1px solid {color}40">{e.level}</span></td>
            <td>{e.endpoint}</td>
            <td><span class="{'status-err' if e.status_code >= 400 else 'status-ok'}">{e.status_code}</span></td>
            <td><span class="{'rt-slow' if e.response_time_ms > 500 else ''}">{e.response_time_ms}ms</span></td>
            <td>{flag}</td>
        </tr>"""

    content = f"""
    <div class="page-title">Logs <span>{len(entries)} entries</span></div>

    <div class="filter-bar">
        <button class="filter-btn active" onclick="filterLogs('ALL', this)">All</button>
        <button class="filter-btn error" onclick="filterLogs('ERROR', this)">ERROR</button>
        <button class="filter-btn warning" onclick="filterLogs('WARNING', this)">WARNING</button>
        <button class="filter-btn info" onclick="filterLogs('INFO', this)">INFO</button>
    </div>

    <div class="table-card">
        <div class="table-header">
            <h2>All log entries</h2>
            <a href="/view/upload" style="font-size:12px;color:#8b949e">Upload more →</a>
        </div>
        {'<table id="logs-table"><thead><tr><th>ID</th><th>Timestamp</th><th>Level</th><th>Endpoint</th><th>Status</th><th>Response time</th><th>Anomaly</th></tr></thead><tbody>' + rows + '</tbody></table>' if entries else '<div class="empty">No log entries yet. <a href="/view/upload">Upload a log file →</a></div>'}
    </div>

    <script>
    function filterLogs(level, btn) {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('#logs-table tbody tr').forEach(row => {{
            row.style.display = (level === 'ALL' || row.dataset.level === level) ? '' : 'none';
        }});
    }}
    </script>"""

    return base_page("Logs", "Logs", content)


@app.get("/view/anomalies", response_class=HTMLResponse)
def view_anomalies():
    from loglens.detector import detect_statistical_anomalies, detect_isolation_forest_anomalies
    entries = get_all_entries()

    stat_anomalies = detect_statistical_anomalies(entries) if entries else []
    iso_anomalies = detect_isolation_forest_anomalies(entries) if entries else []
    level_colors = {"ERROR": "#f85149", "WARNING": "#e3b341", "INFO": "#3fb950"}

    def anomaly_cards(anomalies):
        if not anomalies:
            return '<div class="empty" style="padding:24px">None detected ✓</div>'
        cards = ""
        for a in anomalies:
            color = level_colors.get(a["level"], "#8b949e")
            cards += f"""
            <div class="anomaly-card flagged">
                <h3>
                    <span class="badge" style="background:{color}20;color:{color};border:1px solid {color}40;margin-right:8px">{a["level"]}</span>
                    {a["endpoint"]}
                    <span style="color:#8b949e;font-size:12px;margin-left:8px">ID #{a["id"]}</span>
                </h3>
                <div style="display:flex;gap:20px;margin-top:8px;font-size:12px;color:#8b949e">
                    <span>Status: <span style="color:#c9d1d9">{a["status_code"]}</span></span>
                    <span>Response time: <span style="color:#f85149">{a["response_time_ms"]}ms</span></span>
                </div>
                <div class="anomaly-reason">{a["reason"]}</div>
            </div>"""
        return cards

    content = f"""
    <div class="page-title">Anomalies
        <span>{len(stat_anomalies)} statistical · {len(iso_anomalies)} ML flagged</span>
    </div>

    <div class="grid-2">
        <div>
            <div class="card" style="margin-bottom:16px">
                <h2 style="color:#e3b341">📊 Statistical Detection (Z-Score)</h2>
                <p style="font-size:12px;color:#8b949e;margin-top:4px;margin-bottom:16px">
                    Flags entries more than 2.0 standard deviations above mean response time
                </p>
            </div>
            {anomaly_cards(stat_anomalies)}
        </div>
        <div>
            <div class="card" style="margin-bottom:16px">
                <h2 style="color:#f85149">🤖 Isolation Forest (ML)</h2>
                <p style="font-size:12px;color:#8b949e;margin-top:4px;margin-bottom:16px">
                    Unsupervised ML model that detects outliers across all features simultaneously
                </p>
            </div>
            {anomaly_cards(iso_anomalies)}
        </div>
    </div>

    {'<div class="empty" style="margin-top:24px">No entries to analyze yet. <a href="/view/upload">Upload a log file →</a></div>' if not entries else ''}"""

    return base_page("Anomalies", "Anomalies", content)


@app.get("/view/summary", response_class=HTMLResponse)
def view_summary():
    entries = get_all_entries()

    if not entries:
        content = """
        <div class="page-title">Summary</div>
        <div class="empty">No log entries yet. <a href="/view/upload">Upload a log file →</a></div>"""
        return base_page("Summary", "Summary", content)

    levels, endpoints, total_rt = {}, {}, 0
    slowest = max(entries, key=lambda e: e.response_time_ms)
    most_errors_ep = {}

    for e in entries:
        levels[e.level] = levels.get(e.level, 0) + 1
        endpoints[e.endpoint] = endpoints.get(e.endpoint, 0) + 1
        total_rt += e.response_time_ms
        if e.status_code >= 400:
            most_errors_ep[e.endpoint] = most_errors_ep.get(e.endpoint, 0) + 1

    avg_rt = round(total_rt / len(entries), 1)
    level_colors = {"ERROR": "#f85149", "WARNING": "#e3b341", "INFO": "#3fb950"}
    total = len(entries)

    level_rows = ""
    for level, count in sorted(levels.items()):
        color = level_colors.get(level, "#8b949e")
        pct = round(count / total * 100)
        level_rows += f"""
        <tr>
            <td><span class="badge" style="background:{color}20;color:{color};border:1px solid {color}40">{level}</span></td>
            <td style="font-family:Consolas;color:#c9d1d9">{count}</td>
            <td style="color:#8b949e">{pct}%</td>
        </tr>"""

    endpoint_rows = ""
    for ep, count in sorted(endpoints.items(), key=lambda x: -x[1]):
        errors = most_errors_ep.get(ep, 0)
        endpoint_rows += f"""
        <tr>
            <td style="font-family:Consolas;color:#c9d1d9">{ep}</td>
            <td>{count}</td>
            <td style="color:{'#f85149' if errors else '#3fb950'}">{errors}</td>
        </tr>"""

    content = f"""
    <div class="page-title">Summary <span>{total} total entries</span></div>

    <div class="summary-grid">
        <div class="stat-card blue">
            <div class="label">Total entries</div>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card {'amber' if avg_rt > 200 else 'green'}">
            <div class="label">Avg response time</div>
            <div class="value">{avg_rt}<span style="font-size:14px;font-weight:400;color:#8b949e">ms</span></div>
        </div>
        <div class="stat-card red">
            <div class="label">Slowest entry</div>
            <div class="value" style="font-size:20px">{slowest.response_time_ms}<span style="font-size:14px;font-weight:400;color:#8b949e">ms</span></div>
        </div>
    </div>

    <div class="grid-2">
        <div class="table-card">
            <div class="table-header"><h2>By log level</h2></div>
            <table>
                <thead><tr><th>Level</th><th>Count</th><th>Share</th></tr></thead>
                <tbody>{level_rows}</tbody>
            </table>
        </div>
        <div class="table-card">
            <div class="table-header"><h2>By endpoint</h2></div>
            <table>
                <thead><tr><th>Endpoint</th><th>Requests</th><th>Errors</th></tr></thead>
                <tbody>{endpoint_rows}</tbody>
            </table>
        </div>
    </div>"""

    return base_page("Summary", "Summary", content)


@app.get("/view/upload", response_class=HTMLResponse)
def view_upload():
    content = """
    <div class="page-title">Upload Log File</div>

    <form id="upload-form" enctype="multipart/form-data">
        <div class="upload-box" id="drop-zone">
            <div style="font-size:36px">📂</div>
            <p style="color:#c9d1d9;margin-top:12px;font-size:15px">Drop your <code style="color:#00b4d8">.log</code> file here</p>
            <p style="color:#8b949e;font-size:12px;margin-top:6px">or click to browse</p>
            <label class="upload-label" for="logfile">Choose file</label>
            <input type="file" id="logfile" name="file" accept=".log">
            <p class="filename" id="file-chosen">No file chosen</p>
        </div>
        <div style="text-align:center;margin-top:16px">
            <button class="upload-submit" type="submit">Upload & Parse</button>
        </div>
    </form>

    <div id="result" style="margin-top:24px"></div>

    <div class="card" style="margin-top:24px">
        <h2>Expected log format</h2>
        <div style="background:#0d1117;border-radius:6px;padding:16px;margin-top:12px;font-family:Consolas;font-size:12px;color:#8b949e;line-height:1.8">
            2024-01-15 10:23:45 ERROR /api/users 500 234ms<br>
            2024-01-15 10:23:46 INFO /api/health 200 12ms<br>
            2024-01-15 10:23:47 WARNING /api/orders 429 5ms
        </div>
        <p style="font-size:12px;color:#8b949e;margin-top:12px">
            Format: <code style="color:#00b4d8">YYYY-MM-DD HH:MM:SS LEVEL /endpoint STATUS_CODE RESPONSEms</code>
        </p>
    </div>

    <script>
    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = document.getElementById('logfile').files[0];
        if (!file) { alert('Please choose a file first'); return; }

        const formData = new FormData();
        formData.append('file', file);

        const result = document.getElementById('result');
        result.innerHTML = '<div class="card" style="color:#8b949e">Uploading...</div>';

        try {
            const res = await fetch('/logs/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                result.innerHTML = `<div class="card" style="border-color:#3fb95040;background:#3fb95008">
                    <span style="color:#3fb950;font-size:18px">✓</span>
                    <span style="color:#3fb950;font-weight:600;margin-left:8px">${data.message}</span>
                    <div style="margin-top:12px">
                        <a href="/dashboard" style="color:#00b4d8">Go to Dashboard →</a>
                        &nbsp;&nbsp;
                        <a href="/view/logs" style="color:#00b4d8">View Logs →</a>
                    </div>
                </div>`;
            } else {
                result.innerHTML = `<div class="card" style="border-color:#f8514940;background:#f8514908">
                    <span style="color:#f85149">✗ ${data.detail}</span>
                </div>`;
            }
        } catch (err) {
            result.innerHTML = '<div class="card" style="color:#f85149">Upload failed. Is the server running?</div>';
        }
    });
    </script>"""

    return base_page("Upload", "Upload", content)