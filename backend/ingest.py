from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalise_severity(value: Any) -> str:
    if value is None:
        return "Medium"
    text = str(value).strip().lower()
    if text in {"critical", "high", "warn", "warning"}:
        return "High"
    if text in {"medium", "moderate"}:
        return "Medium"
    return "Low"


def _flatten_record(record: Any, prefix: str = "") -> list[str]:
    if isinstance(record, dict):
        channels: list[str] = []
        for key, value in record.items():
            key_name = f"{prefix}{key}"
            if isinstance(value, dict):
                channels.extend(_flatten_record(value, f"{key_name}_"))
            elif isinstance(value, (int, float, bool, str)) and key_name not in {"mode", "flight_mode"}:
                channels.append(key_name)
        return channels
    return []


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _build_anomaly(anomaly_type: str, evidence: str, severity: Any = "Medium", recommendation: str = "Inspect the flight condition and compare with recent maintenance activity.") -> dict[str, Any]:
    return {
        "type": anomaly_type,
        "severity": _normalise_severity(severity),
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _detect_csv_anomalies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for row in rows:
        temp = _to_float(row.get("motor1_temp_c"))
        if temp is not None and temp >= 70:
            anomalies.append(
                _build_anomaly(
                    "motor_temperature_spike",
                    f"Motor temperature reached {temp:.1f}°C while the motor output was {row.get('motor1_output_pct', 'unknown')}%.",
                    "High",
                    "Inspect the motor assembly before the next high-load flight.",
                )
            )
        hdop = _to_float(row.get("gps_hdop"))
        if hdop is not None and hdop >= 1.5:
            anomalies.append(
                _build_anomaly(
                    "gps_accuracy_degradation",
                    f"GPS accuracy degraded to HDOP {hdop:.2f} during the flight.",
                    "Medium",
                    "Review antenna placement and revalidate the GPS solution before the next route.",
                )
            )
        if str(row.get("failsafe", "")).lower() == "true":
            anomalies.append(
                _build_anomaly(
                    "failsafe_triggered",
                    "Failsafe logic engaged during the return phase.",
                    "High",
                    "Review the RC link and flight controller event sequence before the next mission.",
                )
            )
        if row.get("motor1_temp_c") and _to_float(row.get("motor1_temp_c")) >= 75:
            anomalies.append(
                _build_anomaly(
                    "thermal_overload",
                    "Temperature remained elevated for the final descent window.",
                    "Medium",
                    "Check thermal performance and validate cooling behavior after maintenance.",
                )
            )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in anomalies:
        key = item["type"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _detect_json_anomalies(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for record in records:
        propulsion = record.get("propulsion") or {}
        temperature = _to_float(propulsion.get("motor1_temp_c"))
        if temperature is not None and temperature >= 70:
            anomalies.append(
                _build_anomaly(
                    "motor_temperature_spike",
                    f"Motor temperature reached {temperature:.1f}°C while load was {propulsion.get('motor1_output_pct', 'unknown')}%.",
                    "High",
                    "Inspect the motor assembly before the next high-load flight.",
                )
            )
        navigation = record.get("navigation") or {}
        hdop = _to_float(navigation.get("gps_hdop"))
        if hdop is not None and hdop >= 1.5:
            anomalies.append(
                _build_anomaly(
                    "gps_accuracy_degradation",
                    f"GPS accuracy degraded to HDOP {hdop:.2f} during the mission.",
                    "Medium",
                    "Review antenna placement and perform a controlled GPS validation.",
                )
            )
        estimator = record.get("estimator") or {}
        innovation = _to_float(estimator.get("ekf_pos_innovation_m"))
        if innovation is not None and innovation >= 0.5:
            anomalies.append(
                _build_anomaly(
                    "ekf_innovation_high",
                    f"EKF position innovation reached {innovation:.2f} m.",
                    "Medium",
                    "Check inertial alignment and compare the navigation solution against baseline conditions.",
                )
            )
        motion = record.get("motion") or {}
        accel = _to_float(motion.get("imu_accel_rms_g"))
        if accel is not None and accel >= 0.25:
            anomalies.append(
                _build_anomaly(
                    "vibration_high",
                    f"IMU acceleration RMS reached {accel:.2f} g.",
                    "Medium",
                    "Inspect frame integrity and confirm vibration levels are within normal bounds.",
                )
            )
        link = record.get("link") or {}
        quality = _to_float(link.get("rc_link_quality_pct"))
        if quality is not None and quality <= 80:
            anomalies.append(
                _build_anomaly(
                    "rc_link_degraded",
                    f"RC link quality dropped to {quality:.0f}%.",
                    "Medium",
                    "Check link integrity and verify the control path before the next mission.",
                )
            )
        if (record.get("flight") or {}).get("failsafe") is True:
            anomalies.append(
                _build_anomaly(
                    "failsafe_triggered",
                    "Failsafe logic engaged during a critical phase of flight.",
                    "High",
                    "Review the failsafe event sequence and confirm whether link degradation or navigation loss caused the trigger.",
                )
            )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in anomalies:
        key = item["type"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _detect_log_anomalies(lines: list[str]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for line in lines:
        if "event=" not in line:
            continue
        event_match = re.search(r"event=([A-Za-z0-9_]+)", line)
        if not event_match:
            continue
        event_name = event_match.group(1)
        if event_name == "motor_temperature_spike":
            anomalies.append(
                _build_anomaly(
                    "motor_temperature_spike",
                    "Motor temperature spike event was logged during the cruise phase.",
                    "High",
                    "Inspect the motor assembly before the next high-load flight.",
                )
            )
        elif event_name == "gps_accuracy_degradation":
            anomalies.append(
                _build_anomaly(
                    "gps_accuracy_degradation",
                    "GPS accuracy degradation event was logged during flight.",
                    "Medium",
                    "Review antenna placement and validate the GPS solution before the next route.",
                )
            )
        elif event_name == "failsafe_triggered":
            anomalies.append(
                _build_anomaly(
                    "failsafe_triggered",
                    "Failsafe trigger event indicates a critical control or link issue.",
                    "High",
                    "Review the failsafe path and verify the associated RC or navigation conditions.",
                )
            )
        elif event_name == "rc_link_degraded":
            anomalies.append(
                _build_anomaly(
                    "rc_link_degraded",
                    "RC link quality degraded below the acceptable threshold.",
                    "Medium",
                    "Verify RF integrity and the radio configuration before the next mission.",
                )
            )
        elif event_name == "ekf_innovation_high":
            anomalies.append(
                _build_anomaly(
                    "ekf_innovation_high",
                    "EKF innovation was elevated during the flight.",
                    "Medium",
                    "Check inertial alignment and compare the navigation solution against the expected baseline.",
                )
            )
        elif event_name == "vibration_high":
            anomalies.append(
                _build_anomaly(
                    "vibration_high",
                    "Vibration levels rose above the normal operating threshold.",
                    "Medium",
                    "Inspect the propulsion system and frame for looseness or imbalance.",
                )
            )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in anomalies:
        key = item["type"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _parse_csv_file(content: str) -> dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(content)))
    if not rows:
        raise ValueError("No rows found in CSV file.")
    channels = _dedupe_preserve_order([key for key in rows[0].keys() if key not in {"timestamp", "flight_id"}])
    flight_id = rows[0].get("flight_id") or "FL-UNKNOWN"
    return {
        "flight_id": flight_id,
        "status": "complete",
        "telemetry_points": len(rows),
        "channels": channels,
        "anomalies": _detect_csv_anomalies(rows),
        "sources": ["CSV telemetry fixture", "flight log parser"],
    }


def _parse_json_file(content: str) -> dict[str, Any]:
    payload = json.loads(content)
    records = payload.get("telemetry") or []
    if not records:
        raise ValueError("JSON telemetry payload did not contain any records.")
    channels = _dedupe_preserve_order(
        [channel for record in records for channel in _flatten_record(record)]
    )
    anomalies = _detect_json_anomalies(records)
    mission_name = payload.get("mission") or payload.get("mission_name") or "Survey mission"
    return {
        "flight_id": payload.get("flight_id") or "FL-UNKNOWN",
        "mission_name": mission_name,
        "status": "complete",
        "telemetry_points": len(records),
        "channels": channels,
        "anomalies": anomalies,
        "sources": ["JSON telemetry fixture", "flight log parser"],
    }


def _parse_log_file(content: str) -> dict[str, Any]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("No lines found in log file.")
    flight_id = "FL-UNKNOWN"
    for line in lines:
        match = re.search(r"flight=([A-Za-z0-9\-]+)", line)
        if match:
            flight_id = match.group(1)
            break
    anomalies = _detect_log_anomalies(lines)
    return {
        "flight_id": flight_id,
        "status": "complete",
        "telemetry_points": len(lines),
        "channels": ["flight_id", "event_type", "motor_temp_c", "gps_hdop", "rc_link_quality_pct"],
        "anomalies": anomalies,
        "sources": ["Event log parser", "flight telemetry events"],
    }


def analyze_uploaded_log(filename: str, content: str | None = None) -> dict[str, Any]:
    normalized_name = (filename or "").strip()
    if not normalized_name:
        raise ValueError("A filename is required for analysis.")

    if content is None:
        path = DATA_DIR / normalized_name
        if not path.exists():
            raise FileNotFoundError(f"No fixture found for {normalized_name!r} in {DATA_DIR}")
        content = path.read_text(encoding="utf-8")

    lower_name = normalized_name.lower()
    if lower_name.endswith(".csv"):
        analysis = _parse_csv_file(content)
    elif lower_name.endswith(".json"):
        analysis = _parse_json_file(content)
    elif lower_name.endswith(".log"):
        analysis = _parse_log_file(content)
    else:
        raise ValueError(f"Unsupported file format for {normalized_name!r}")

    analysis["filename"] = normalized_name
    return analysis
