https://balanced-forgiveness-production-ba0e.up.railway.app/dashboard

# LogLens

A CLI log analyzer and anomaly detector built with Python. Parses raw log files, stores structured data in SQLite, exposes a REST API, and uses machine learning to automatically flag anomalies.

**31 tests · 5 phases · 6 API endpoints · 2 ML detectors**

---

## Tech Stack

| Tool | Role |
|------|------|
| Python 3.14 | Core language |
| FastAPI | REST API framework |
| SQLAlchemy | ORM and SQLite storage |
| Pydantic | Data validation and serialization |
| scikit-learn | Isolation Forest anomaly detection |
| Click | CLI interface |
| pytest | Testing (31 tests) |
| uvicorn | ASGI server |

---

## Project Structure

```
LogLens/
├── loglens/
│   ├── __init__.py
│   ├── parser.py       ← Phase 1: Parses raw .log files into structured dicts
│   ├── models.py       ← Phase 2: SQLAlchemy table + Pydantic API schema
│   ├── database.py     ← Phase 2: SQLite connection, save/query functions
│   ├── api.py          ← Phase 3: FastAPI REST endpoints
│   ├── detector.py     ← Phase 4: Z-score + Isolation Forest anomaly detection
│   └── cli.py          ← Phase 5: Click CLI interface
├── logs/
│   └── sample.log      ← Sample log file for testing
├── tests/
│   ├── test_parser.py      ← 3 tests: parsing, edge cases, file I/O
│   ├── test_database.py    ← 2 tests: save, retrieve, filter
│   ├── test_api.py         ← 9 tests: all endpoints, upload, validation
│   ├── test_detector.py    ← 7 tests: statistical + ML detection
│   └── test_cli.py         ← 10 tests: all CLI commands and flags
├── setup.py
└── requirements.txt
```

---

## File Descriptions

### `loglens/parser.py`
Reads a `.log` file line by line and converts each line into a structured Python dictionary using regex named capture groups. Handles blank lines, comments, and malformed lines gracefully.

- `parse_line(line)` — parses a single log line, returns a dict or None
- `parse_file(filepath)` — parses an entire file, returns a list of dicts

**Log format expected:**
```
2024-01-15 10:23:45 ERROR /api/users 500 234ms
```

**Output:**
```python
{
    "timestamp": datetime(2024, 1, 15, 10, 23, 45),
    "level": "ERROR",
    "endpoint": "/api/users",
    "status_code": 500,
    "response_time_ms": 234
}
```

---

### `loglens/models.py`
Two separate model definitions:

**`LogEntry` (SQLAlchemy)** — defines the `log_entries` database table with columns for id, timestamp, level, endpoint, status_code, and response_time_ms.

**`LogEntrySchema` (Pydantic)** — defines the shape of data going in and out of the API. Ensures FastAPI validates and serializes responses correctly.

---

### `loglens/database.py`
Manages the SQLite database connection and provides functions to save and query log entries.

- `get_engine()` — creates the database connection and creates tables if they don't exist
- `save_entries(entries)` — takes a list of dicts from the parser and saves them to the database
- `get_all_entries()` — retrieves all log entries
- `get_entries_by_level(level)` — retrieves entries filtered by log level

The database file (`loglens.db`) is automatically created in the project root on first run.

---

### `loglens/api.py`
FastAPI application with 6 REST endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/logs` | All log entries |
| GET | `/logs/level/{level}` | Filter by INFO / ERROR / WARNING |
| GET | `/logs/summary` | Counts, averages, breakdown by level and endpoint |
| GET | `/anomalies` | Run both anomaly detectors |
| GET | `/anomalies/statistical` | Z-score anomalies only |
| POST | `/logs/upload` | Upload a `.log` file |

Interactive documentation auto-generated at `/docs`.

---

### `loglens/detector.py`
Two independent anomaly detection methods:

**Statistical (Z-score)**
Calculates the mean and standard deviation of all response times. Flags any entry more than 2 standard deviations above the mean. Returns a human-readable reason string with the exact deviation.

**Isolation Forest (scikit-learn)**
Encodes all features (response time, status code, level, endpoint) as numeric values using `LabelEncoder`, then trains an `IsolationForest` model. Anomalies are entries that get isolated in fewer random splits — they are furthest from the normal cluster. Uses `contamination=0.1` (expects ~10% anomalies) and `random_state=42` for reproducibility.

- `detect_statistical_anomalies(entries)` — Z-score detection
- `detect_isolation_forest_anomalies(entries)` — ML detection
- `run_all_detectors()` — runs both and combines results

---

### `loglens/cli.py`
Click-powered CLI with 4 commands:

| Command | Description |
|---------|-------------|
| `loglens parse <filepath>` | Parse a log file and save to database |
| `loglens logs [--level LEVEL]` | Display log entries, optionally filtered |
| `loglens summary` | Show statistics and breakdown |
| `loglens anomalies` | Run anomaly detection |

---

## Setup

```bash
git clone https://github.com/Siddsth/LogLens.git
cd LogLens

python3 -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

pip install -r requirements.txt
pip install -e .
```

---

## CLI Usage

```bash
# Parse a log file into the database
loglens parse logs/sample.log

# View all logs (color coded by level)
loglens logs

# Filter by log level
loglens logs --level ERROR

# Summary statistics
loglens summary

# Run anomaly detection
loglens anomalies
```

---

## API Usage

Start the server:
```bash
uvicorn loglens.api:app --reload
```

Then visit:
- `http://127.0.0.1:8000/docs` — interactive Swagger UI
- `http://127.0.0.1:8000/logs` — all log entries as JSON
- `http://127.0.0.1:8000/logs/level/ERROR` — filter by level
- `http://127.0.0.1:8000/logs/summary` — summary statistics
- `http://127.0.0.1:8000/anomalies` — anomaly detection results

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: **31 passed**

---

## Sample Log Format

```
2024-01-15 10:23:45 ERROR /api/users 500 234ms
2024-01-15 10:23:46 INFO /api/health 200 12ms
2024-01-15 10:23:47 WARNING /api/orders 429 5ms
```

Each line must follow: `YYYY-MM-DD HH:MM:SS LEVEL /endpoint STATUS_CODE RESPONSEms`
