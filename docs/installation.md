# Installation Guide

## Option A — Docker (recommended)

Requires Docker + Docker Compose only.

```bash
git clone <your-repo-url>.git
cd enterprise-incident-platform
cp .env.example .env          # edit NEO4J_PASSWORD at minimum
docker compose up -d --build
```

Pull the models into the Ollama container once it's up:

```bash
docker exec -it incident-platform-ollama ollama pull llama3.2
docker exec -it incident-platform-ollama ollama pull nomic-embed-text
```

Then run the ingestion pipeline (populates Neo4j + ChromaDB from `sample_data/`):

```bash
docker exec -it incident-platform-app python run_ingestion.py
```

Open the dashboard: http://localhost:8501
Neo4j Browser: http://localhost:7474 (user: `neo4j`, password: from your `.env`)

## Option B — Local (no Docker)

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed locally
- Neo4j Community Edition (or Neo4j Desktop)

### Steps

```bash
git clone <your-repo-url>.git
cd enterprise-incident-platform

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # edit as needed

# Pull models
ollama pull llama3.2
ollama pull nomic-embed-text

# Start Neo4j (adjust to your install method), then:
python run_ingestion.py

streamlit run ui/streamlit_app.py
```

## Verifying the setup

```bash
python -m ingestion.incident_loader sample_data/incidents.csv
python -m ingestion.log_loader sample_data/logs/app.log
python -m agents.incident_classifier
python -m workflows.incident_workflow
pytest
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ConnectionRefusedError` on Neo4j | Neo4j not running / wrong port | Check `docker compose ps`, confirm `NEO4J_URI` |
| Agent returns `non-JSON output` error | Model too small / prompt drift | Try a larger model (e.g. `qwen2.5:7b`) or lower temperature |
| ChromaDB empty on Knowledge Base page | Ingestion not run yet | `python run_ingestion.py` |
| Streamlit graph viewer blank | No data in Neo4j | Run ingestion, then refresh |
