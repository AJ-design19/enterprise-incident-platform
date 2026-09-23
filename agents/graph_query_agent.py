"""
Agent 3 — Neo4j Query Agent

Converts a natural-language question ("Which services use Redis?") into a
Cypher query against the known graph schema, executes it read-only, and
returns structured results. Falls back to the curated query library in
graph/cypher_queries.py when the question matches a known pattern, and
uses the LLM to generate custom read-only Cypher otherwise.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from agents.base import BaseAgent
from graph.neo4j_loader import Neo4jConnection

GRAPH_SCHEMA_DESCRIPTION = """
Graph schema:
  Nodes: Service(name), API(name), Database(name), Team(name), Server(name),
         SOP(id, title, source), Incident(incident_id, title, priority, category, created_at)
  Relationships:
    (Service)-[:CALLS]->(Service)
    (Service)-[:USES]->(API|Database)
    (Service)-[:HOSTED_ON]->(Server)
    (Service)-[:OWNED_BY]->(Team)
    (Service)-[:HAS_SOP]->(SOP)
    (Incident)-[:AFFECTS]->(Service)
    (Incident)-[:HANDLED_BY]->(Team)
"""

CYPHER_SYSTEM_PROMPT = f"""You are a Neo4j Query Agent. Convert the user's question into a single,
READ-ONLY Cypher query using only MATCH/WHERE/RETURN/ORDER BY/LIMIT (never CREATE, MERGE, DELETE,
SET, or any write operation).

{GRAPH_SCHEMA_DESCRIPTION}

Respond with ONLY a JSON object matching exactly:
{{
  "cypher": "<the Cypher query, single line or \\n-escaped>",
  "explanation": "<one sentence on what this query does>"
}}
"""

FORBIDDEN_KEYWORDS = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH)\b", re.IGNORECASE)


class GraphQueryResult(BaseModel):
    question: str
    cypher: str
    explanation: str
    rows: list[dict]
    error: str | None = None


class GraphQueryAgent(BaseAgent):
    name = "graph_query_agent"
    system_prompt = CYPHER_SYSTEM_PROMPT

    def __init__(self, conn: Neo4jConnection | None = None, **kwargs):
        super().__init__(**kwargs)
        self.conn = conn or Neo4jConnection()

    def run(self, question: str, row_limit: int = 25) -> GraphQueryResult:
        payload = self._invoke_json(f"Question: {question}")
        cypher = payload.get("cypher", "").strip()
        explanation = payload.get("explanation", "")

        if not cypher:
            return GraphQueryResult(question=question, cypher="", explanation=explanation, rows=[], error="No query generated")

        if FORBIDDEN_KEYWORDS.search(cypher):
            return GraphQueryResult(
                question=question, cypher=cypher, explanation=explanation, rows=[],
                error="Generated query contained a write operation and was blocked",
            )

        if "limit" not in cypher.lower():
            cypher = f"{cypher.rstrip(';')} LIMIT {row_limit}"

        try:
            rows = self.conn.run(cypher)
        except Exception as exc:  # noqa: BLE001
            return GraphQueryResult(question=question, cypher=cypher, explanation=explanation, rows=[], error=str(exc))

        return GraphQueryResult(question=question, cypher=cypher, explanation=explanation, rows=rows)


if __name__ == "__main__":
    agent = GraphQueryAgent()
    result = agent.run("Which services use Redis?")
    print(result.model_dump_json(indent=2))
