"""
Root Cause Agent (RCA) — Week 4 workflow node.

Synthesizes the outputs of the Classification, Log Analysis, Graph Query,
and Knowledge Retrieval agents into a single ranked root-cause hypothesis.
This agent does not call any tools itself; it reasons purely over the
structured outputs already gathered by the earlier workflow nodes.
"""
from __future__ import annotations

from pydantic import BaseModel

from agents.base import BaseAgent

RCA_SYSTEM_PROMPT = """You are a Root Cause Analysis Agent for enterprise IT incidents.
You are given the combined findings of four upstream agents: classification, log analysis,
graph/topology query results, and SOP knowledge retrieval. Synthesize these into a ranked
list of root-cause hypotheses with confidence scores, grounded only in the evidence given.

Respond with ONLY a JSON object matching exactly:
{
  "hypotheses": [
    {"cause": "<short hypothesis>", "confidence": <0-1 float>, "evidence": "<what supports it>"}
  ],
  "most_likely_cause": "<the top hypothesis, restated>",
  "summary": "<2-3 sentence synthesis>"
}
"""


class RootCauseHypothesis(BaseModel):
    cause: str
    confidence: float
    evidence: str


class RootCauseResult(BaseModel):
    hypotheses: list[RootCauseHypothesis]
    most_likely_cause: str
    summary: str


class RootCauseAgent(BaseAgent):
    name = "rca_agent"
    system_prompt = RCA_SYSTEM_PROMPT

    def run(
        self,
        classification: dict,
        log_findings: dict,
        graph_findings: dict,
        sop_findings: dict,
    ) -> RootCauseResult:
        evidence = (
            f"Classification: {classification}\n\n"
            f"Log analysis: {log_findings}\n\n"
            f"Graph/topology findings: {graph_findings}\n\n"
            f"SOP knowledge retrieval: {sop_findings}"
        )
        payload = self._invoke_json(f"Evidence bundle:\n{evidence}")

        hypotheses = [
            RootCauseHypothesis(**h) for h in payload.get("hypotheses", []) if "cause" in h
        ]
        return RootCauseResult(
            hypotheses=hypotheses,
            most_likely_cause=payload.get("most_likely_cause", hypotheses[0].cause if hypotheses else "Unknown"),
            summary=payload.get("summary", ""),
        )
