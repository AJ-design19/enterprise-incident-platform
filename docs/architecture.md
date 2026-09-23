# Architecture

## Overview

The Enterprise Incident Intelligence Platform is a multi-agent system that takes a
free-text incident description and produces a classified, root-cause-analyzed,
actionable response — grounded in three local knowledge sources: historical incident
data and service topology (Neo4j), SOP documents (ChromaDB), and raw application logs.

## High-level flow

```
                        ┌─────────────────────┐
   User Query  ───────► │ Incident Classifier │
                        └──────────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
            ┌───────────────┐              ┌───────────────┐
            │  Log Agent     │              │  Graph Agent   │
            └───────┬────────┘              └───────┬────────┘
                    └──────────────┬──────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │ Knowledge Retrieval  │
                        └──────────┬───────────┘
                                   ▼
                        ┌─────────────────────┐
                        │   Root Cause Agent   │
                        └──────────┬───────────┘
                                   ▼
                        ┌─────────────────────┐
                        │ Recommendation Agent │
                        └──────────┬───────────┘
                                   ▼
                               Response
```

This is implemented as a `LangGraph` `StateGraph` in `workflows/incident_workflow.py`.
Classification runs first since its output (`affected_service`) seeds the graph query.
Log analysis and graph querying run as independent branches from the same state and
both feed into knowledge retrieval, which feeds the root cause synthesis, which feeds
the final recommendation node.

## Components

| Layer | Technology | Responsibility |
|---|---|---|
| Orchestration | LangGraph | Defines and executes the agent state machine |
| LLM inference | Ollama (Llama 3.2 / Qwen2.5) | Local, offline-capable model serving |
| Structured knowledge | Neo4j | Service topology, ownership, incident history graph |
| Semantic knowledge | ChromaDB | SOP document embeddings for retrieval |
| UI | Streamlit | Incident chat, search, knowledge base, graph viewer, analytics |
| Packaging | Docker / docker-compose | Reproducible local deployment |

## Agents

1. **Incident Classification Agent** (`agents/incident_classifier.py`) — category, priority, affected service.
2. **Knowledge Retrieval Agent** (`agents/retrieval_agent.py`) — semantic SOP search + grounded synthesis.
3. **Neo4j Query Agent** (`agents/graph_query_agent.py`) — natural language → read-only Cypher, with a
   keyword blocklist against write operations as a safety net on top of prompt instructions.
4. **Log Analysis Agent** (`agents/log_analyzer.py`) — structured log parsing + LLM-assisted signal extraction.
5. **Root Cause Agent** (`agents/rca_agent.py`) — synthesizes all upstream evidence into ranked hypotheses.
6. **Recommendation Agent** (`agents/recommendation_agent.py`) — immediate/verification/preventive actions.

Each agent inherits from `agents/base.py`, which wraps `ChatOllama`, retries transient
failures with exponential backoff, and parses structured JSON out of LLM responses.

## Graph schema

```
Nodes:          Service, API, Database, Team, Server, SOP, Incident
Relationships:  (Service)-[:CALLS]->(Service)
                (Service)-[:USES]->(API|Database)
                (Service)-[:HOSTED_ON]->(Server)
                (Service)-[:OWNED_BY]->(Team)
                (Service)-[:HAS_SOP]->(SOP)
                (Incident)-[:AFFECTS]->(Service)
                (Incident)-[:HANDLED_BY]->(Team)
```

## Error handling

Every workflow node is wrapped by `_safe(...)` in `incident_workflow.py`: if an agent
raises, the error is recorded in `state["errors"]` and the pipeline continues with
whatever evidence is available, rather than failing the whole run. The UI surfaces
these partial-failure states explicitly instead of hiding them.

## Data flow (ingestion)

`run_ingestion.py` is the single entrypoint for populating both stores:
1. Load and validate `incidents.csv` → merge into Neo4j as `(:Incident)` nodes.
2. Load `service_topology.csv` → merge `CALLS`/`USES`/`HOSTED_ON`/`OWNED_BY` relationships.
3. Chunk SOP files under `sample_data/sops/` → embed via Ollama → upsert into ChromaDB,
   and register one `(:SOP)` node per source file in Neo4j for graph-based lookup.
