# Module / API Reference

This project doesn't expose a REST API by default (the Streamlit UI calls Python
modules directly), but every module is designed to be imported and used
programmatically — e.g. from a notebook, a future FastAPI wrapper, or a CLI.

## `workflows.incident_workflow.IncidentWorkflow`

```python
from workflows.incident_workflow import IncidentWorkflow

workflow = IncidentWorkflow()
result = workflow.run(
    incident_text="Payment API is timing out for checkout requests.",
    log_path="sample_data/logs/app.log",       # optional
    graph_question="Which services use Redis?", # optional override
)
# result: dict with keys classification, log_findings, graph_findings,
#         sop_findings, rca, recommendation, errors
```

## `agents.incident_classifier.IncidentClassifierAgent`

```python
from agents.incident_classifier import IncidentClassifierAgent

agent = IncidentClassifierAgent()
result = agent.run("Payment API is timing out")
# result: ClassificationResult(category, priority, affected_service, confidence, reasoning)
```

## `agents.graph_query_agent.GraphQueryAgent`

```python
from agents.graph_query_agent import GraphQueryAgent

agent = GraphQueryAgent()
result = agent.run("Which services use Redis?")
# result.cypher      -> generated (read-only) Cypher
# result.rows        -> query results
# result.error       -> set if generation/execution failed or a write was blocked
```

## `graph.neo4j_loader.Neo4jConnection`

```python
from graph.neo4j_loader import Neo4jConnection

conn = Neo4jConnection()
rows = conn.run("MATCH (s:Service) RETURN s.name AS name LIMIT 5")
conn.close()
```

## `vector_db.chroma_store.SopVectorStore`

```python
from vector_db.chroma_store import SopVectorStore

store = SopVectorStore()
hits = store.search("database connection timeout", k=4)
# hits: [{content, metadata, score}, ...]
```

## `ingestion.log_loader`

```python
from ingestion.log_loader import parse_log_file, filter_by_level, summarize_entries

entries = parse_log_file("sample_data/logs/app.log")
errors = filter_by_level(entries)          # ERROR/CRITICAL/WARNING only
counts = summarize_entries(entries)        # {"ERROR": 5, "INFO": 12, ...}
```

## Cypher query library

`graph.cypher_queries.QUERIES` holds named, parameterized, read-only queries
(`services_using_dependency`, `service_dependencies`, `downstream_impact`,
`team_owned_services`, `service_incident_history`, `service_sops`,
`top_failing_services`, `single_points_of_failure`, `graph_overview`).
Use `get_query(name)` to fetch one by name — this is what powers both the
Graph Query Agent's fallback and the dashboard's Analytics/Graph Viewer pages.
