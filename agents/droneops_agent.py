"""LangChain-backed engineering copilot for grounded flight-log questions."""

from __future__ import annotations

import os
from typing import Any

try:
    from pydantic import BaseModel, Field
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except ImportError:  # The demo API remains runnable without optional AI dependencies.
    BaseModel = None  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    ChatPromptTemplate = None  # type: ignore[assignment]
    ChatOpenAI = None  # type: ignore[assignment]


if BaseModel is not None:

    class FlightAnswer(BaseModel):
        """Structured response returned by the analysis copilot."""

        answer: str = Field(description="A concise direct answer to the engineer's question.")
        observations: list[str] = Field(default_factory=list)
        inferences: list[str] = Field(default_factory=list)
        recommendations: list[str] = Field(default_factory=list)
        sources: list[str] = Field(default_factory=list)
        confidence: str = Field(description="One of high, medium, or low, with a brief reason.")
        insufficient_evidence: list[str] = Field(default_factory=list)

else:

    class FlightAnswer:  # type: ignore[no-redef]
        """Fallback marker used when optional dependencies are unavailable."""


SYSTEM_PROMPT = """You are DroneOps AI, an AI Engineering Copilot for Drone Flight Analysis.
Your job is to answer what happened in a flight using only the supplied evidence.
Never invent telemetry, timestamps, aircraft details, or maintenance history.
Separate direct observations from hypotheses and recommendations. Cite the supplied
source labels. If evidence is missing, list the concrete gaps and lower confidence.
Recommendations are for qualified human review; never issue flight-control commands,
change parameters, or claim a certified safety decision.
Return the requested structured response.
"""


def _fallback_answer(question: str, analysis: dict[str, Any]) -> dict[str, Any]:
    anomalies = analysis.get("anomalies", [])
    sources = analysis.get("sources", [])
    first_anomaly = anomalies[0] if anomalies else {}
    evidence = first_anomaly.get("evidence", "No anomaly evidence is available.")
    recommendation = first_anomaly.get("recommendation", "Review the flight with a qualified engineer.")
    flight_id = analysis.get("flight_id", "the selected flight")
    return {
        "answer": (
            f'For "{question.strip()}", {flight_id} shows {evidence} '
            "This is an engineering finding, not a certified flight-safety decision."
        ),
        "observations": [evidence] if evidence else [],
        "inferences": ["The available fixture does not contain enough correlated telemetry to establish a root cause."],
        "recommendations": [recommendation],
        "sources": sources,
        "confidence": "low: the demo fixture contains summarized findings rather than raw timestamped channels",
        "insufficient_evidence": ["Raw telemetry channels, timestamps, and aircraft baseline are not available in the demo fixture."],
    }


def _build_chain() -> Any:
    if ChatPromptTemplate is None or ChatOpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "Question: {question}\nFlight evidence:\n{evidence}")]
    )
    model = ChatOpenAI(model=os.getenv("DRONEOPS_MODEL", "gpt-4o-mini"), temperature=0)
    return prompt | model.with_structured_output(FlightAnswer)


def answer_flight_question(question: str, analysis: dict[str, Any]) -> dict[str, Any]:
    """Answer against one supplied analysis, using LangChain when configured."""
    fallback = _fallback_answer(question, analysis)
    chain = _build_chain()
    if chain is None:
        return fallback

    evidence = {
        "flight_id": analysis.get("flight_id"),
        "filename": analysis.get("filename"),
        "telemetry_points": analysis.get("telemetry_points"),
        "anomalies": analysis.get("anomalies", []),
        "sources": analysis.get("sources", []),
    }
    try:
        result = chain.invoke({"question": question.strip(), "evidence": evidence})
        return result.model_dump()
    except Exception:
        # A provider outage must not turn a grounded API into an unavailable API.
        return fallback
