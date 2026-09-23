"""Shared pytest fixtures. Tests that need Ollama/Neo4j/Chroma live are
marked and skipped by default in CI — see pytest.ini `-m "not integration"`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_incidents_csv() -> Path:
    return ROOT / "sample_data" / "incidents.csv"


@pytest.fixture
def sample_sops_dir() -> Path:
    return ROOT / "sample_data" / "sops"


@pytest.fixture
def sample_log_file() -> Path:
    return ROOT / "sample_data" / "logs" / "app.log"
