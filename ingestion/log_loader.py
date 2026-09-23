"""
Parses raw application/server log files into structured entries:
timestamp, level (ERROR/WARNING/INFO/DEBUG), message, and stack trace
continuation lines. Built to be resilient to heterogeneous formats
(e.g. LogHub-style datasets) rather than assuming one fixed layout.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from logging_setup import logger

LEVEL_PATTERN = re.compile(r"\b(ERROR|WARN(?:ING)?|INFO|DEBUG|CRITICAL|FATAL)\b", re.IGNORECASE)
TIMESTAMP_PATTERNS = [
    re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"),  # 2024-01-02 03:04:05
    re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}"),  # 01/02/2024 03:04:05
    re.compile(r"[A-Z][a-z]{2} \d{1,2} \d{2}:\d{2}:\d{2}"),  # Jan  2 03:04:05 (syslog)
]

_LEVEL_NORMALIZE = {"WARN": "WARNING", "FATAL": "CRITICAL"}


@dataclass
class LogEntry:
    raw: str
    timestamp: Optional[str]
    level: str
    message: str
    stack_trace: List[str] = field(default_factory=list)


def _extract_timestamp(line: str) -> Optional[str]:
    for pattern in TIMESTAMP_PATTERNS:
        match = pattern.search(line)
        if match:
            return match.group(0)
    return None


def _extract_level(line: str) -> str:
    match = LEVEL_PATTERN.search(line)
    if not match:
        return "UNKNOWN"
    level = match.group(1).upper()
    return _LEVEL_NORMALIZE.get(level, level)


def _looks_like_new_entry(line: str) -> bool:
    return _extract_timestamp(line) is not None or bool(LEVEL_PATTERN.search(line))


def parse_log_file(path: str | Path, max_lines: Optional[int] = None) -> List[LogEntry]:
    """Parse a log file into structured LogEntry objects, attaching stack
    trace / continuation lines to the entry they follow."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if max_lines:
        lines = lines[:max_lines]

    entries: List[LogEntry] = []
    current: Optional[LogEntry] = None

    for line in lines:
        if not line.strip():
            continue
        if _looks_like_new_entry(line):
            current = LogEntry(
                raw=line,
                timestamp=_extract_timestamp(line),
                level=_extract_level(line),
                message=line.strip(),
            )
            entries.append(current)
        elif current is not None:
            current.stack_trace.append(line.strip())
        else:
            # First line(s) of the file with no discernible header — keep as INFO
            current = LogEntry(raw=line, timestamp=None, level="INFO", message=line.strip())
            entries.append(current)

    logger.info(f"Parsed {len(entries)} log entries from {path.name}")
    return entries


def filter_by_level(entries: List[LogEntry], levels: tuple[str, ...] = ("ERROR", "CRITICAL", "WARNING")) -> List[LogEntry]:
    return [e for e in entries if e.level in levels]


def summarize_entries(entries: List[LogEntry]) -> dict:
    """Quick counts used by both the Log Analysis agent and the dashboard."""
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.level] = counts.get(e.level, 0) + 1
    return counts


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "sample_data/logs/app.log"
    parsed = parse_log_file(target)
    print(summarize_entries(parsed))
    for entry in filter_by_level(parsed)[:5]:
        print(entry.timestamp, entry.level, entry.message[:100])
