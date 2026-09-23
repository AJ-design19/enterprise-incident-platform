"""Neo4j Graph Viewer page — renders the service topology as an
interactive network graph and exposes a free-form Cypher console for
power users (read-only queries encouraged)."""
from __future__ import annotations

import streamlit as st
from pyvis.network import Network

from graph.cypher_queries import get_query
from graph.neo4j_loader import Neo4jConnection

LABEL_COLORS = {
    "Service": "#4C9AFF",
    "API": "#79E2A5",
    "Database": "#F5A623",
    "Team": "#B892F5",
    "Server": "#FF8A80",
    "SOP": "#FFD166",
    "Incident": "#EF476F",
}


@st.cache_resource(show_spinner=False)
def _conn() -> Neo4jConnection:
    return Neo4jConnection()


def _build_network(rows: list[dict]) -> str:
    net = Network(height="600px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    seen_nodes = set()

    for row in rows:
        n, r, m = row.get("n"), row.get("r"), row.get("m")
        for node in (n, m):
            if node is None:
                continue
            node_id = node.element_id
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            label = list(node.labels)[0] if node.labels else "Node"
            name = node.get("name") or node.get("title") or node.get("incident_id") or label
            net.add_node(node_id, label=str(name), color=LABEL_COLORS.get(label, "#CCCCCC"), title=label)
        if r is not None and n is not None and m is not None:
            net.add_edge(n.element_id, m.element_id, label=r.type, color="#888888")

    net.set_options('{"physics": {"stabilization": true, "barnesHut": {"springLength": 120}}}')
    return net.generate_html()


def render() -> None:
    st.title("🕸️ Neo4j Graph Viewer")
    st.caption("Visualize the live service topology, ownership, and incident relationships.")

    conn = _conn()
    limit = st.slider("Max nodes/relationships to render", 25, 500, 150, step=25)

    try:
        rows = conn.run(get_query("graph_overview"), {"limit": limit})
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not query Neo4j: {exc}")
        st.info("Start Neo4j via `docker compose up neo4j` and run the ingestion pipeline first.")
        return

    if not rows:
        st.info("Graph is empty. Run the ingestion pipeline (Week 2) to populate Neo4j first.")
        return

    html = _build_network(rows)
    st.components.v1.html(html, height=620, scrolling=True)

    with st.expander("🔧 Cypher console (read-only queries recommended)"):
        query = st.text_area("Cypher query", "MATCH (s:Service) RETURN s.name AS service LIMIT 25")
        if st.button("Run query"):
            try:
                st.dataframe(conn.run(query), use_container_width=True)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
