import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from loglens.database import get_all_entries


def get_features(entries):
    """
    Convert log entries into a numeric feature matrix for ML.
    ML models only understand numbers, so we need to convert
    everything into numeric form first.
    """
    level_encoder = LabelEncoder()
    endpoint_encoder = LabelEncoder()

    levels = level_encoder.fit_transform([e.level for e in entries])
    endpoints = endpoint_encoder.fit_transform([e.endpoint for e in entries])

    features = np.column_stack([
        [e.response_time_ms for e in entries],
        [e.status_code for e in entries],
        levels,
        endpoints,
    ])

    return features


def detect_statistical_anomalies(entries, threshold=2.0):
    """
    Flag entries whose response time is more than `threshold`
    standard deviations above the mean.
    Z-score = (value - mean) / standard_deviation
    """
    if not entries:
        return []

    response_times = np.array([e.response_time_ms for e in entries])
    mean = np.mean(response_times)
    std = np.std(response_times)

    if std == 0:
        return []

    anomalies = []
    for entry in entries:
        z_score = (entry.response_time_ms - mean) / std
        if z_score > threshold:
            anomalies.append({
                "id": entry.id,
                "level": entry.level,
                "endpoint": entry.endpoint,
                "status_code": entry.status_code,
                "response_time_ms": entry.response_time_ms,
                "reason": f"Response time {entry.response_time_ms}ms is {z_score:.1f} standard deviations above mean ({mean:.1f}ms)",
            })

    return anomalies


def detect_isolation_forest_anomalies(entries, contamination=0.1):
    """
    Use Isolation Forest to detect anomalies across all features.
    contamination=0.1 means we expect roughly 10% of entries to be anomalies.
    Returns -1 for anomalies, 1 for normal entries.
    """
    if len(entries) < 10:
        return []

    features = get_features(entries)

    model = IsolationForest(
        contamination=contamination,
        random_state=42
    )
    predictions = model.fit_predict(features)

    anomalies = []
    for entry, prediction in zip(entries, predictions):
        if prediction == -1:
            anomalies.append({
                "id": entry.id,
                "level": entry.level,
                "endpoint": entry.endpoint,
                "status_code": entry.status_code,
                "response_time_ms": entry.response_time_ms,
                "reason": "Flagged as anomaly by Isolation Forest model",
            })

    return anomalies


def run_all_detectors():
    """
    Run both detection methods and combine the results.
    """
    entries = get_all_entries()

    if not entries:
        return {
            "message": "No entries to analyze",
            "statistical_anomalies": [],
            "isolation_forest_anomalies": [],
        }

    statistical = detect_statistical_anomalies(entries)
    isolation = detect_isolation_forest_anomalies(entries)

    return {
        "total_entries_analyzed": len(entries),
        "statistical_anomalies": statistical,
        "statistical_anomaly_count": len(statistical),
        "isolation_forest_anomalies": isolation,
        "isolation_forest_anomaly_count": len(isolation),
    }