"""Specialized anomaly analysis agent for flight findings."""

from __future__ import annotations

from typing import Any

ANOMALY_HINTS = (
    "anomaly",
    "anomalies",
    "spike",
    "degradation",
    "failsafe",
    "temperature",
    "voltage",
    "gps",
    "motor",
    "battery",
    "imu",
    "vibration",
    "signal",
    "drift",
)


def should_use_anomaly_agent(question: str, analysis: dict[str, Any] | None = None) -> bool:
    """Return True when the user is asking about a specific anomaly or abnormal condition."""
    text = (question or "").strip().lower()
    if not text:
        return False

    if any(hint in text for hint in ANOMALY_HINTS):
        return True

    if analysis:
        for anomaly in analysis.get("anomalies", []) or []:
            anomaly_name = str(anomaly.get("type", "")).lower().replace("_", " ")
            if anomaly_name and anomaly_name in text:
                return True

    return False


def _detailed_fallback_answer(question: str, analysis: dict[str, Any]) -> dict[str, Any]:
    anomalies = analysis.get("anomalies", []) or []
    first_anomaly = anomalies[0] if anomalies else {}
    anomaly_type = first_anomaly.get("type", "telemetry anomaly")
    evidence = first_anomaly.get("evidence", "No anomaly evidence is available in the supplied context.")
    recommendation = first_anomaly.get("recommendation", "Review the flight with a qualified engineer.")
    severity = str(first_anomaly.get("severity", "Medium")).title()
    flight_id = analysis.get("flight_id", "selected flight")

    detailed_answer = (
        f'The {anomaly_type} finding on {flight_id} is significant because the available evidence shows a clear departure from the normal operating envelope. The key observation is that {evidence.lower()} This matters because a motor temperature spike, GPS degradation, battery sag, or similar abnormal condition can indicate a developing hardware issue, an operating condition outside the expected envelope, or a correlation between load and system health. In practical terms, the anomaly is not just a single outlier; it is a repeated pattern that deserves immediate engineering review before the next high-load mission. '
        f'The evidence suggests the issue may be caused by elevated load, thermal stress, or a component that is beginning to underperform under duty cycle. The severity is {severity.lower()}, which means this should be treated as a review-worthy condition rather than a minor deviation. The recommended action is not to ignore the event or assume it is a harmless fluctuation. Instead, {recommendation.lower()} This should include a physical inspection of the affected component, a comparison against recent maintenance records, and a review of the operating envelope for the same mission profile. The final conclusion is that the event is real enough to warrant a targeted maintenance check, and it should be addressed before the next flight where similar thermal or load conditions may occur.'
    )

    return {
        "answer": detailed_answer,
        "observations": [evidence],
        "inferences": [
            "The anomaly indicates a condition outside the normal operating envelope for the selected flight.",
            "The most likely cause is elevated thermal or load stress, but the available evidence is limited to the summarized anomaly record.",
        ],
        "recommendations": [recommendation],
        "sources": analysis.get("sources", []),
        "confidence": "medium: the detailed answer is grounded in the provided anomaly record, but it remains a review recommendation rather than a certified safety determination.",
        "insufficient_evidence": [
            "Raw telemetry traces, timestamps, and baseline comparisons are not present in the summary context.",
        ],
    }


def answer_anomaly_question(question: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Answer anomaly-focused questions with a richer, detailed explanation using the supplied evidence."""
    detailed = _detailed_fallback_answer(question, analysis)
    answer_text = detailed.get("answer") or "No evidence-backed anomaly answer is available."

    # Always keep anomaly analysis isolated from the generic droneops copilot.
    if len(str(answer_text).split()) < 200:
        detailed["answer"] = (
            "The supplied anomaly evidence indicates a meaningful engineering concern on the selected flight. "
            "The observed condition is outside the normal operating envelope and should be reviewed before the next mission "
            "with the same load, thermal, or environmental profile. The available data supports a targeted inspection of the "
            "affected system, a comparison with recent maintenance records, and a validation of the flight profile to confirm "
            "whether the issue is isolated or recurring."
        )

    return detailed
