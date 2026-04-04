import re
from datetime import datetime
from pathlib import Path


LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>\w+)\s+"
    r"(?P<endpoint>\S+)\s+"
    r"(?P<status_code>\d{3})\s+"
    r"(?P<response_time>\d+)ms"
)


def parse_line(line: str) -> dict | None:
    """
    Parse a single log line into a dictionary.
    Returns None if the line doesn't match the expected format.
    """
    line = line.strip()

    if not line or line.startswith("#"):
        return None

    match = LOG_PATTERN.match(line)
    if not match:
        return None

    data = match.groupdict()

    return {
        "timestamp": datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S"),
        "level": data["level"].upper(),
        "endpoint": data["endpoint"],
        "status_code": int(data["status_code"]),
        "response_time_ms": int(data["response_time"]),
    }


def parse_file(filepath: str | Path) -> list[dict]:
    """
    Parse an entire log file and return a list of structured log entries.
    Malformed lines are skipped with a warning printed to the console.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Log file not found: {filepath}")

    entries = []
    skipped = 0

    with open(filepath, "r") as f:
        for line_number, line in enumerate(f, start=1):
            result = parse_line(line)
            if result:
                entries.append(result)
            elif line.strip() and not line.strip().startswith("#"):
                print(f"  [skip] line {line_number}: {line.strip()}")
                skipped += 1

    print(f"Parsed {len(entries)} entries, skipped {skipped} malformed lines.")
    return entries