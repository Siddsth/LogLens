from loglens.detector import (
    detect_statistical_anomalies,
    detect_isolation_forest_anomalies,
    get_features,
)
from loglens.models import LogEntry
from datetime import datetime
import numpy as np


def make_entry(id, response_time_ms, level="INFO",
               endpoint="/api/health", status_code=200):
    """
    Helper function to create a LogEntry object without
    needing a real database. We can just construct one directly.
    """
    entry = LogEntry(
        id=id,
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        level=level,
        endpoint=endpoint,
        status_code=status_code,
        response_time_ms=response_time_ms,
    )
    return entry


NORMAL_ENTRIES = [make_entry(i, 50.0) for i in range(1, 10)]
ANOMALOUS_ENTRY = make_entry(
    id=10,
    response_time_ms=1200.0,
    level="ERROR",
    endpoint="/api/products",
    status_code=503
)
ALL_ENTRIES = NORMAL_ENTRIES + [ANOMALOUS_ENTRY]


def test_statistical_detects_slow_entry():
    anomalies = detect_statistical_anomalies(ALL_ENTRIES)
    assert len(anomalies) == 1
    assert anomalies[0]["id"] == 9
    assert anomalies[0]["response_time_ms"] == 1200.0


def test_statistical_detects_slow_entry():
    anomalies = detect_statistical_anomalies(ALL_ENTRIES)
    assert len(anomalies) == 1
    assert anomalies[0]["id"] == 10
    assert anomalies[0]["response_time_ms"] == 1200.0


def test_isolation_forest_detects_anomaly():
    anomalies = detect_isolation_forest_anomalies(ALL_ENTRIES)
    flagged_ids = [a["id"] for a in anomalies]
    assert 10 in flagged_ids

def test_statistical_reason_message():
    anomalies = detect_statistical_anomalies(ALL_ENTRIES)
    assert "standard deviations above mean" in anomalies[0]["reason"]


def test_isolation_forest_needs_minimum_entries():
    few_entries = [make_entry(i, 50.0) for i in range(1, 5)]
    anomalies = detect_isolation_forest_anomalies(few_entries)
    assert anomalies == []



def test_get_features_shape():
    features = get_features(ALL_ENTRIES)
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(ALL_ENTRIES)
    assert features.shape[1] == 4

def test_statistical_no_anomalies_in_uniform_data():
    uniform_entries = [make_entry(i, 50.0) for i in range(1, 11)]
    anomalies = detect_statistical_anomalies(uniform_entries)
    assert len(anomalies) == 0


def test_statistical_empty_entries():
    anomalies = detect_statistical_anomalies([])
    assert anomalies == []