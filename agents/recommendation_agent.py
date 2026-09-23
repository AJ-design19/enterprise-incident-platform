"""
Recommendation Agent — Week 4 workflow node.

Turns the Root Cause Agent's synthesis into concrete, prioritized next
steps for the on-call engineer: immediate mitigation, verification steps,
and follow-up/prevention actions.
"""
from __future__ import annotations

from pydantic import BaseModel

from agents.base import BaseAgent

RECOMMENDATION_SYSTEM_PROMPT = """You are a Recommendation Agent for enterprise incident response.
Given a root-cause synthesis, produce concrete, prioritized next steps for an on-call engineer.

Respond with ONLY a JSON object matching exactly:
{
  "immediate_actions": ["<action>", ...],
  "verification_steps": ["<how to confirm resolution>", ...],
  "preventive_actions": ["<longer-term follow-up>", ...],
  "escalation_needed": <true/false>,
  "escalation_reason": "<why, or empty string>"
}
"""


class RecommendationResult(BaseModel):
    immediate_actions: list[str]
    verification_steps: list[str]
    preventive_actions: list[str]
    escalation_needed: bool
    escalation_reason: str


class RecommendationAgent(BaseAgent):
    name = "recommendation_agent"
    system_prompt = RECOMMENDATION_SYSTEM_PROMPT

    def run(self, rca_summary: dict, priority: str) -> RecommendationResult:
        prompt = f"Incident priority: {priority}\nRoot cause synthesis: {rca_summary}"
        payload = self._invoke_json(prompt)

        return RecommendationResult(
            immediate_actions=payload.get("immediate_actions", []),
            verification_steps=payload.get("verification_steps", []),
            preventive_actions=payload.get("preventive_actions", []),
            escalation_needed=bool(payload.get("escalation_needed", False)),
            escalation_reason=payload.get("escalation_reason", ""),
        )
