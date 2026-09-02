from backend.db import save_user
from backend.ingest import analyze_uploaded_log


def test_save_user_persists_user_record():
    user = {
        "name": "Test Operator",
        "email": "operator@example.com",
        "role": "Pilot",
        "status": "Pending",
    }

    saved_user = save_user(user)

    assert saved_user["name"] == "Test Operator"
    assert saved_user["email"] == "operator@example.com"
    assert saved_user["role"] == "Pilot"
    assert saved_user["status"] == "Pending"


def test_sample_csv_produces_real_flight_analysis():
    analysis = analyze_uploaded_log("sample_flight_log.csv")

    assert analysis["flight_id"] == "FL-SAMPLE-001"
    assert analysis["telemetry_points"] >= 10
    assert "motor_temperature_spike" in {item["type"] for item in analysis["anomalies"]}
    assert analysis["channels"]


def test_sample_log_detects_failsafe_event():
    analysis = analyze_uploaded_log("sample_flight_events.log")

    assert analysis["flight_id"] == "FL-SAMPLE-001"
    assert any(item["type"] == "failsafe_triggered" for item in analysis["anomalies"])


def test_anomaly_questions_are_routed_to_anomaly_agent():
    from backend.server import should_use_anomaly_agent

    assert should_use_anomaly_agent("Explain the motor_temperature_spike anomaly in detail.") is True
    assert should_use_anomaly_agent("Summarize the entire flight and maintenance plan.") is False
