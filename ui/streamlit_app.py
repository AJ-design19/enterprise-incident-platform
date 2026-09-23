"""
Enterprise Incident Intelligence Platform — Streamlit Dashboard.

Run with:  streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run ui/streamlit_app.py` to resolve project-root imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ui.pages import analytics, graph_viewer, incident_chat, incident_search, knowledge_base

st.set_page_config(
    page_title="Incident Intelligence Platform",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "💬 Incident Chat": incident_chat.render,
    "🔎 Incident Search": incident_search.render,
    "📚 Knowledge Base": knowledge_base.render,
    "🕸️ Neo4j Graph Viewer": graph_viewer.render,
    "📊 Analytics": analytics.render,
}


def main() -> None:
    st.sidebar.title("🛠️ Incident Intelligence")
    st.sidebar.caption("Agentic AI for Enterprise Incident Management")
    choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Stack: LangGraph · Ollama · Neo4j · ChromaDB · Streamlit")

    PAGES[choice]()


if __name__ == "__main__":
    main()
