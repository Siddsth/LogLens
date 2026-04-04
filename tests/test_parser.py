from loglens.parser import parse_line, parse_file
from datetime import datetime


def test_parse_valid_line():
    line = "2024-01-15 10:23:45 ERROR /api/users 500 234ms"
    result = parse_line(line)

    assert result is not None
    assert result["level"] == "ERROR"
    assert result["status_code"] == 500
    assert result["response_time_ms"] == 234
    assert result["endpoint"] == "/api/users"
    assert isinstance(result["timestamp"], datetime)


def test_parse_invalid_line():
    assert parse_line("this is garbage") is None
    assert parse_line("") is None
    assert parse_line("# a comment") is None


def test_parse_file(tmp_path):
    # tmp_path is a pytest built-in that gives you a temporary directory
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2024-01-15 10:23:45 INFO /api/health 200 12ms\n"
        "2024-01-15 10:23:46 ERROR /api/users 500 234ms\n"
        "this line is malformed\n"
    )

    results = parse_file(log_file)
    assert len(results) == 2
    assert results[0]["level"] == "INFO"
    assert results[1]["level"] == "ERROR"