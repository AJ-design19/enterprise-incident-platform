"""
End-to-end data ingestion pipeline (Week 2 deliverable).

Usage:
    python run_ingestion.py                 # ingest everything under sample_data/
    python run_ingestion.py --reset         # wipe Chroma + Neo4j graph data first
    python run_ingestion.py --incidents path/to/incidents.csv
    python run_ingestion.py --sops path/to/sops_dir
    python run_ingestion.py --topology path/to/topology.csv
"""
from __future__ import annotations

import argparse

import pandas as pd

from graph.neo4j_loader import Neo4jConnection, ingest_incidents, ingest_sops, ingest_topology, initialize_schema
from ingestion.incident_loader import iter_incident_records, load_incidents_csv
from ingestion.pdf_loader import load_sop_directory
from logging_setup import logger
from vector_db.chroma_store import SopVectorStore


def _sop_graph_rows(sop_documents, service_hint: str | None = None) -> list[dict]:
    """Build one (service -> SOP) graph row per source SOP file (not per chunk),
    guessing the service from the filename when no explicit hint is given."""
    seen_sources = {}
    rows = []
    for doc in sop_documents:
        if doc.source in seen_sources:
            continue
        seen_sources[doc.source] = True
        guessed_service = service_hint or doc.source.rsplit(".", 1)[0].replace("-errors", "").replace("-timeout", "")
        rows.append(
            {
                "id": doc.source,
                "title": doc.source.replace("-", " ").rsplit(".", 1)[0].title(),
                "source": doc.source,
                "doc_type": doc.doc_type,
                "service": guessed_service,
            }
        )
    return rows


def _topology_rows(path: str) -> list[dict]:
    df = pd.read_csv(path).fillna("")
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "service": row["service"],
                "calls": row.get("calls") or None,
                "uses_api": row.get("uses_api") or None,
                "uses_db": row.get("uses_db") or None,
                "hosted_on": row.get("hosted_on") or None,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest incidents, SOPs, and topology into Neo4j + ChromaDB")
    parser.add_argument("--incidents", default="sample_data/incidents.csv")
    parser.add_argument("--sops", default="sample_data/sops")
    parser.add_argument("--topology", default="sample_data/service_topology.csv")
    parser.add_argument("--reset", action="store_true", help="Reset ChromaDB collection before ingesting")
    args = parser.parse_args()

    conn = Neo4jConnection()
    initialize_schema(conn)

    logger.info("== Step 1/3: Ingesting incident history into Neo4j ==")
    incidents_df = load_incidents_csv(args.incidents)
    ingest_incidents(conn, iter_incident_records(incidents_df))

    logger.info("== Step 2/3: Ingesting service topology into Neo4j ==")
    ingest_topology(conn, _topology_rows(args.topology))

    logger.info("== Step 3/3: Ingesting SOPs into ChromaDB + Neo4j ==")
    store = SopVectorStore()
    if args.reset:
        store.reset()
    sop_documents = load_sop_directory(args.sops)
    store.add_documents(sop_documents)
    ingest_sops(conn, _sop_graph_rows(sop_documents))

    conn.close()
    logger.info("Ingestion pipeline complete.")
    print(f"\n✅ Ingested {len(incidents_df)} incidents, "
          f"{len(sop_documents)} SOP chunks ({store.count()} total in Chroma).")


if __name__ == "__main__":
    main()
