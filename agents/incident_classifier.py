"""
Agent 1 — Incident Classification Agent

Input:  free-text incident description (e.g. "Payment API timeout")
Output: {category, priority, affected_service, confidence, reasoning}
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agents.base import BaseAgent

VALID_CATEGORIES = [
    "Network",
    "Database",
    "Application",
    "Infrastructure",
    "Security",
    "Performance",
    "Authentication",
    "Third-Party Integration",
    "Deployment",
    "Unknown",
]
VALID_PRIORITIES = ["P1-Critical", "P2-High", "P3-Medium", "P4-Low"]

CLASSIFIER_SYSTEM_PROMPT = f"""You are an enterprise IT Incident Classification Agent.
Given a free-text incident report, classify it precisely.

Valid categories: {", ".join(VALID_CATEGORIES)}
Valid priorities: {", ".join(VALID_PRIORITIES)}
Priority guidance:
- P1-Critical: full outage, revenue-impacting, no workaround
- P2-High: major degradation, partial outage, workaround exists
- P3-Medium: minor functionality impacted, limited users
- P4-Low: cosmetic or negligible user impact

Respond with ONLY a JSON object, no prose, no markdown fences, matching exactly:
{{
  "category": "<one of the valid categories>",
  "priority": "<one of the valid priorities>",
  "affected_service": "<best-guess service/component name, or 'Unknown'>",
  "confidence": <float between 0 and 1>,
  "reasoning": "<one sentence explanation>"
}}
"""


class ClassificationResult(BaseModel):
    category: str
    priority: str
    affected_service: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    raw_input: Optional[str] = None


class IncidentClassifierAgent(BaseAgent):
    name = "incident_classifier"
    system_prompt = CLASSIFIER_SYSTEM_PROMPT

    def run(self, incident_text: str) -> ClassificationResult:
        payload = self._invoke_json(f"Incident report:\n{incident_text}")

        category = payload.get("category", "Unknown")
        if category not in VALID_CATEGORIES:
            category = "Unknown"

        priority = payload.get("priority", "P3-Medium")
        if priority not in VALID_PRIORITIES:
            priority = "P3-Medium"

        return ClassificationResult(
            category=category,
            priority=priority,
            affected_service=payload.get("affected_service", "Unknown"),
            confidence=float(payload.get("confidence", 0.5)),
            reasoning=payload.get("reasoning", ""),
            raw_input=incident_text,
        )


if __name__ == "__main__":
    agent = IncidentClassifierAgent()
    result = agent.run("Payment API is timing out for ~15% of checkout requests since 10:42 UTC.")
    print(result.model_dump_json(indent=2))
