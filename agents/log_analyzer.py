"""
Agent 4 — Log Analysis Agent

Extracts ERROR/WARNING entries and stack traces from raw logs, then asks
the LLM to summarize likely root-cause signals from the extracted evidence.
"""
from __future__ import annotations

from pydantic import BaseModel

from agents.base import BaseAgent
from ingestion.log_loader import LogEntry, filter_by_level, parse_log_file, summarize_entries

LOG_ANALYSIS_SYSTEM_PROMPT = """You are a Log Analysis Agent for enterprise IT operations.
You will be given a set of extracted ERROR/WARNING log lines (with stack traces where present).
Identify the most likely root-cause signal(s) and any recurring error patterns.

Respond with ONLY a JSON object matching exactly:
{
  "likely_root_cause_signals": ["<short signal>", ...],
  "recurring_patterns": ["<short pattern description>", ...],
  "summary": "<2-3 sentence plain-English summary>"
}
"""


class LogAnalysisResult(BaseModel):
    level_counts: dict[str, int]
    error_count: int
    sample_errors: list[str]
    likely_root_cause_signals: list[str]
    recurring_patterns: list[str]
    summary: str


class LogAnalysisAgent(BaseAgent):
    name = "log_analyzer"
    system_prompt = LOG_ANALYSIS_SYSTEM_PROMPT

    def run(self, log_path: str, max_lines: int = 2000, sample_size: int = 25) -> LogAnalysisResult:
        entries: list[LogEntry] = parse_log_file(log_path, max_lines=max_lines)
        counts = summarize_entries(entries)
        problem_entries = filter_by_level(entries)

        if not problem_entries:
            return LogAnalysisResult(
                level_counts=counts,
                error_count=0,
                sample_errors=[],
                likely_root_cause_signals=[],
                recurring_patterns=[],
                summary="No ERROR/WARNING/CRITICAL entries found in the analyzed window.",
            )

        sample = problem_entries[:sample_size]
        evidence_block = "\n".join(
            f"[{e.timestamp or 'no-ts'}] {e.level}: {e.message}"
            + ("\n    " + "\n    ".join(e.stack_trace[:5]) if e.stack_trace else "")
            for e in sample
        )
        payload = self._invoke_json(f"Extracted log evidence:\n{evidence_block}")

        return LogAnalysisResult(
            level_counts=counts,
            error_count=len(problem_entries),
            sample_errors=[e.message for e in sample],
            likely_root_cause_signals=payload.get("likely_root_cause_signals", []),
            recurring_patterns=payload.get("recurring_patterns", []),
            summary=payload.get("summary", ""),
        )


if __name__ == "__main__":
    agent = LogAnalysisAgent()
    result = agent.run("sample_data/logs/app.log")
    print(result.model_dump_json(indent=2))
