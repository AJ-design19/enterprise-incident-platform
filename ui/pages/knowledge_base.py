"""Knowledge Base page — upload new SOP files, view what's indexed, and
run ad-hoc semantic searches against the ChromaDB collection."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from ingestion.pdf_loader import load_sop_directory
from vector_db.chroma_store import SopVectorStore


@st.cache_resource(show_spinner=False)
def _store() -> SopVectorStore:
    return SopVectorStore()


def render() -> None:
    st.title("📚 Knowledge Base")
    st.caption("SOP documents indexed in ChromaDB for semantic retrieval.")

    store = _store()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Chunks indexed", store.count())

    st.subheader("Upload a new SOP")
    uploaded = st.file_uploader("PDF, DOCX, or Markdown", type=["pdf", "docx", "md", "txt"])
    if uploaded is not None and st.button("Index this document", type="primary"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / uploaded.name
            tmp_path.write_bytes(uploaded.getbuffer())
            with st.spinner("Chunking and embedding..."):
                docs = load_sop_directory(tmp)
                added = store.add_documents(docs)
            st.success(f"Indexed {added} chunks from {uploaded.name}")
            st.rerun()

    st.divider()
    st.subheader("Semantic search")
    query = st.text_input("Ask a question against the SOP knowledge base")
    if query:
        hits = store.search(query, k=5)
        for hit in hits:
            with st.expander(f"📄 {hit['metadata'].get('source', 'unknown')}  ·  score {hit['score']:.2f}"):
                st.write(hit["content"])
