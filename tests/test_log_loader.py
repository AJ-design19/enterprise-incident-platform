import pytest

from ingestion.log_loader import filter_by_level, parse_log_file, summarize_entries


def test_parse_log_file_extracts_entries(sample_log_file):
    entries = parse_log_file(sample_log_file)
    assert len(entries) > 0
    assert any(e.level == "ERROR" for e in entries)


def test_parse_log_file_attaches_stack_traces(sample_log_file):
    entries = parse_log_file(sample_log_file)
    error_with_trace = next(e for e in entries if e.stack_trace)
    assert "ConnectionPool" in "\n".join(error_with_trace.stack_trace)


def test_parse_log_file_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_log_file(tmp_path / "missing.log")


def test_filter_by_level_default(sample_log_file):
    entries = parse_log_file(sample_log_file)
    filtered = filter_by_level(entries)
    assert all(e.level in ("ERROR", "CRITICAL", "WARNING") for e in filtered)
    assert len(filtered) > 0


def test_summarize_entries_counts_levels(sample_log_file):
    entries = parse_log_file(sample_log_file)
    counts = summarize_entries(entries)
    assert isinstance(counts, dict)
    assert sum(counts.values()) == len(entries)


def test_max_lines_truncates(sample_log_file):
    all_entries = parse_log_file(sample_log_file)
    limited = parse_log_file(sample_log_file, max_lines=3)
    assert len(limited) <= len(all_entries)
