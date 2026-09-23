"""Analytics page — top incident categories, trends over time, resolution
time distribution, and frequently failing services, all sourced live
from Neo4j."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from graph.cypher_queries import get_query
from graph.neo4j_loader import Neo4jConnection

TREND_QUERY = """
MATCH (i:Incident)
WHERE i.created_at IS NOT NULL
RETURN date(datetime(i.created_at)) AS day, count(*) AS incidents
ORDER BY day
"""

CATEGORY_QUERY = """
MATCH (i:Incident)
RETURN i.category AS category, count(*) AS count
ORDER BY count DESC
"""

RESOLUTION_TIME_QUERY = """
MATCH (i:Incident)
WHERE i.created_at IS NOT NULL AND i.resolved_at IS NOT NULL
RETURN i.incident_id AS incident_id, i.priority AS priority,
       duration.inSeconds(datetime(i.created_at), datetime(i.resolved_at)).seconds / 3600.0 AS resolution_hours
"""


@st.cache_resource(show_spinner=False)
def _conn() -> Neo4jConnection:
    return Neo4jConnection()


def render() -> None:
    st.title("📊 Analytics")
    st.caption("Trends and patterns across all ingested incident history.")

    conn = _conn()
    try:
        top_failing = conn.run(get_query("top_failing_services"), {"limit": 10})
        categories = conn.run(CATEGORY_QUERY)
        trend = conn.run(TREND_QUERY)
        resolution = conn.run(RESOLUTION_TIME_QUERY)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not query Neo4j: {exc}")
        st.info("Start Neo4j via `docker compose up neo4j` and run the ingestion pipeline first.")
        return

    if not categories:
        st.info("No incident data yet. Run the ingestion pipeline (Week 2) to populate Neo4j first.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top incident categories")
        st.plotly_chart(
            px.bar(pd.DataFrame(categories), x="category", y="count", color="category"),
            use_container_width=True,
        )
    with col2:
        st.subheader("Most frequently failing services")
        st.plotly_chart(
            px.bar(pd.DataFrame(top_failing), x="service", y="incident_count", color="service"),
            use_container_width=True,
        )

    st.subheader("Incident trend over time")
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend["day"] = df_trend["day"].astype(str)
        st.plotly_chart(px.line(df_trend, x="day", y="incidents", markers=True), use_container_width=True)
    else:
        st.caption("No dated incidents available for a trend line.")

    st.subheader("Resolution time distribution")
    if resolution:
        df_res = pd.DataFrame(resolution)
        st.plotly_chart(
            px.box(df_res, x="priority", y="resolution_hours", points="all", color="priority"),
            use_container_width=True,
        )
    else:
        st.caption("No resolved-incident timestamps available yet.")
