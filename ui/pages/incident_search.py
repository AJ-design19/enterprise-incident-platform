"""Incident Search page — browse and filter historical incidents pulled
straight from Neo4j, with a downloadable CSV report."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from graph.neo4j_loader import Neo4jConnection

SEARCH_QUERY = """
MATCH (i:Incident)-[:AFFECTS]->(s:Service)
OPTIONAL MATCH (i)-[:HANDLED_BY]->(t:Team)
WHERE ($category = '' OR i.category = $category)
  AND ($priority = '' OR i.priority = $priority)
  AND ($service = '' OR s.name = $service)
  AND (i.title CONTAINS $keyword OR i.description CONTAINS $keyword)
RETURN i.incident_id AS incident_id, i.title AS title, i.category AS category,
       i.priority AS priority, s.name AS service, t.name AS team,
       i.root_cause AS root_cause, i.created_at AS created_at
ORDER BY i.created_at DESC
LIMIT 200
"""

FACETS_QUERY = """
MATCH (i:Incident)-[:AFFECTS]->(s:Service)
RETURN collect(DISTINCT i.category) AS categories,
       collect(DISTINCT i.priority) AS priorities,
       collect(DISTINCT s.name) AS services
"""


@st.cache_resource(show_spinner=False)
def _conn() -> Neo4jConnection:
    return Neo4jConnection()


def render() -> None:
    st.title("🔎 Incident Search")
    st.caption("Search historical incidents stored in the knowledge graph.")

    conn = _conn()
    try:
        facets = conn.run(FACETS_QUERY)[0]
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not connect to Neo4j: {exc}")
        st.info("Start Neo4j via `docker compose up neo4j` and run the ingestion pipeline first.")
        return

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        keyword = st.text_input("Keyword", "")
    with col2:
        category = st.selectbox("Category", [""] + sorted(facets.get("categories") or []))
    with col3:
        priority = st.selectbox("Priority", [""] + sorted(facets.get("priorities") or []))
    with col4:
        service = st.selectbox("Service", [""] + sorted(facets.get("services") or []))

    rows = conn.run(
        SEARCH_QUERY,
        {"category": category, "priority": priority, "service": service, "keyword": keyword},
    )
    df = pd.DataFrame(rows)

    st.write(f"**{len(df)}** incidents found")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, file_name="incident_report.csv", mime="text/csv")
