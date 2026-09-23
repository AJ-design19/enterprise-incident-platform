# 🛠️ Enterprise Incident Intelligence Platform

A local, agentic AI system that turns a plain-English incident report into a
classified, root-cause-analyzed, actionable response — grounded in your service
topology, SOPs, and logs. Built as a 6-week internship project.

**Stack:** Python · LangGraph · Ollama · Neo4j · ChromaDB · Streamlit · Docker

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://github.com/<your-username>/enterprise-incident-platform/actions/workflows/ci.yml/badge.svg)

## What it does

Describe an incident like *"Payment API is timing out for ~15% of checkout requests"*
and the platform:

1. **Classifies** it (category, priority, affected service) — `Incident Classification Agent`
2. **Analyzes logs** for the affected window — `Log Analysis Agent`
3. **Queries the service graph** for topology, ownership, and incident history — `Neo4j Query Agent`
4. **Retrieves relevant SOPs** via semantic search — `Knowledge Retrieval Agent`
5. **Synthesizes root-cause hypotheses** from all of the above — `Root Cause Agent`
6. **Recommends next steps** — immediate actions, verification, prevention — `Recommendation Agent`

All six agents run inside a single `LangGraph` workflow with parallel execution and
graceful partial-failure handling, orchestrated end-to-end from a Streamlit dashboard.

## Screens

| Page | What it's for |
|---|---|
| 💬 Incident Chat | Run the full agent pipeline on a new incident |
| 🔎 Incident Search | Filter/search historical incidents from Neo4j |
| 📚 Knowledge Base | Upload SOPs, browse what's indexed, semantic search |
| 🕸️ Neo4j Graph Viewer | Interactive service topology graph + Cypher console |
| 📊 Analytics | Top categories, failing services, trends, resolution times |

## Quick start (Docker)

```bash
git clone https://github.com/<your-username>/enterprise-incident-platform.git
cd enterprise-incident-platform
cp .env.example .env
docker compose up -d --build

docker exec -it incident-platform-ollama ollama pull llama3.2
docker exec -it incident-platform-ollama ollama pull nomic-embed-text
docker exec -it incident-platform-app python run_ingestion.py
```

Open **http://localhost:8501**.

Full setup instructions (Docker and local/no-Docker): [`docs/installation.md`](docs/installation.md).

## Project structure

```
enterprise-incident-platform/
├── agents/                  # 6 agents: classifier, retrieval, graph query, log analysis, RCA, recommendation
├── ingestion/                # CSV / SOP (PDF/DOCX/MD) / log file loaders
├── graph/                    # Neo4j connection, schema, curated read-only Cypher library
├── vector_db/                 # ChromaDB wrapper (Ollama embeddings)
├── workflows/                # LangGraph multi-agent orchestration
├── ui/                        # Streamlit app + 5 pages
├── sample_data/               # Sample incidents, service topology, SOPs, logs
├── docs/                      # Architecture, installation, API reference
├── tests/                     # Unit tests (mocked LLM) + integration tests (live services)
├── Dockerfile / docker-compose.yml
├── run_ingestion.py            # One-command data pipeline (CSV/SOPs → Neo4j + ChromaDB)
└── config.py / logging_setup.py
```

## Running tests

```bash
pip install -r requirements.txt
pytest                       # unit tests only (mocked LLM, no live services needed)
pytest -m integration        # full pipeline against live Ollama/Neo4j/Chroma
```

## Documentation

- [Architecture](docs/architecture.md) — system design, agent flow, graph schema
- [Installation](docs/installation.md) — Docker and local setup, troubleshooting
- [API / Module Reference](docs/api_documentation.md) — how to use each module programmatically

## Roadmap (from the 6-week plan)

- [x] Week 1 — Environment setup, dataset preparation
- [x] Week 2 — Data ingestion & knowledge graph
- [x] Week 3 — Four individual agents
- [x] Week 4 — Multi-agent LangGraph workflow
- [x] Week 5 — Streamlit dashboard
- [x] Week 6 — Testing, Docker packaging, documentation

## License

MIT — see [LICENSE](LICENSE).
