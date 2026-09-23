"""
Central configuration for the Enterprise Incident Intelligence Platform.
All modules import settings from here instead of reading os.environ directly,
so behavior stays consistent across the CLI, Streamlit UI, and tests.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root regardless of current working directory
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class OllamaConfig:
    host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3.2"))
    embed_model: str = field(default_factory=lambda: _env("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    temperature: float = 0.1
    request_timeout: int = 120


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str = field(default_factory=lambda: _env("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: _env("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: _env("NEO4J_PASSWORD", "neo4j"))
    database: str = field(default_factory=lambda: _env("NEO4J_DATABASE", "neo4j"))


@dataclass(frozen=True)
class ChromaConfig:
    persist_dir: str = field(
        default_factory=lambda: _env("CHROMA_PERSIST_DIR", str(ROOT_DIR / "vector_db" / "chroma_store"))
    )
    collection: str = field(default_factory=lambda: _env("CHROMA_COLLECTION", "sop_knowledge_base"))


@dataclass(frozen=True)
class AppConfig:
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    env: str = field(default_factory=lambda: _env("APP_ENV", "development"))
    max_log_lines: int = field(default_factory=lambda: int(_env("MAX_LOG_LINES_PER_ANALYSIS", "2000")))
    sample_data_dir: Path = ROOT_DIR / "sample_data"
    reports_dir: Path = ROOT_DIR / "sample_data" / "reports"


ollama_config = OllamaConfig()
neo4j_config = Neo4jConfig()
chroma_config = ChromaConfig()
app_config = AppConfig()

app_config.reports_dir.mkdir(parents=True, exist_ok=True)
