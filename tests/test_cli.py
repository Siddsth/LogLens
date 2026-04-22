from click.testing import CliRunner
from loglens.cli import cli
from loglens.models import Base
from sqlalchemy import create_engine
import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Every test gets a fresh empty database automatically.
    autouse=True means this fixture runs for every test in
    this file without needing to be listed as an argument.
    """
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr("loglens.database.get_engine", lambda: test_engine)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_log(tmp_path):
    log_file = tmp_path / "sample.log"
    log_file.write_text(
        "2024-01-15 10:23:45 INFO /api/health 200 12ms\n"
        "2024-01-15 10:23:46 ERROR /api/users 500 234ms\n"
        "2024-01-15 10:23:47 WARNING /api/orders 429 5ms\n"
        "2024-01-15 10:23:48 INFO /api/users 200 45ms\n"
        "2024-01-15 10:23:49 ERROR /api/products 503 1200ms\n"
    )
    return str(log_file)


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "LogLens" in result.output


def test_parse_valid_file(runner, sample_log):
    result = runner.invoke(cli, ["parse", sample_log])
    assert result.exit_code == 0
    assert "Successfully saved 5 entries" in result.output


def test_parse_missing_file(runner):
    result = runner.invoke(cli, ["parse", "nonexistent.log"])
    assert result.exit_code == 0
    assert "not found" in result.output


def test_logs_empty(runner):
    result = runner.invoke(cli, ["logs"])
    assert result.exit_code == 0
    assert "No entries found" in result.output


def test_logs_with_data(runner, sample_log):
    runner.invoke(cli, ["parse", sample_log])
    result = runner.invoke(cli, ["logs"])
    assert result.exit_code == 0
    assert "ERROR" in result.output
    assert "/api/users" in result.output


def test_logs_filter_by_level(runner, sample_log):
    runner.invoke(cli, ["parse", sample_log])
    result = runner.invoke(cli, ["logs", "--level", "ERROR"])
    assert result.exit_code == 0
    assert "ERROR" in result.output
    assert "INFO" not in result.output


def test_summary_empty(runner):
    result = runner.invoke(cli, ["summary"])
    assert result.exit_code == 0
    assert "No entries in database" in result.output


def test_summary_with_data(runner, sample_log):
    runner.invoke(cli, ["parse", sample_log])
    result = runner.invoke(cli, ["summary"])
    assert result.exit_code == 0
    assert "LogLens Summary" in result.output
    assert "Total entries:      5" in result.output
    assert "ERROR" in result.output


def test_anomalies_empty(runner):
    result = runner.invoke(cli, ["anomalies"])
    assert result.exit_code == 0
    assert "No entries to analyze" in result.output


def test_anomalies_with_data(runner, sample_log):
    runner.invoke(cli, ["parse", sample_log])
    result = runner.invoke(cli, ["anomalies"])
    assert result.exit_code == 0
    assert "Statistical Anomalies" in result.output
    assert "Isolation Forest Anomalies" in result.output
    