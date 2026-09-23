"""
ChromaDB-backed SOP knowledge base. Uses Ollama for embeddings so the whole
pipeline stays local/offline-capable (no external embedding API required).
"""
from __future__ import annotations

import hashlib
from typing import List, Sequence

import chromadb
from chromadb.config import Settings
from langchain_ollama import OllamaEmbeddings

from config import chroma_config, ollama_config
from ingestion.pdf_loader import SopDocument
from logging_setup import logger


def _doc_id(doc: SopDocument) -> str:
    key = f"{doc.source}:{doc.metadata.get('chunk_index', 0)}:{doc.content[:50]}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


class SopVectorStore:
    """Wraps a persistent Chroma collection with Ollama embeddings."""

    def __init__(self, persist_dir: str | None = None, collection_name: str | None = None):
        self.persist_dir = persist_dir or chroma_config.persist_dir
        self.collection_name = collection_name or chroma_config.collection
        self.client = chromadb.PersistentClient(path=self.persist_dir, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )
        self.embeddings = OllamaEmbeddings(base_url=ollama_config.host, model=ollama_config.embed_model)

    def add_documents(self, documents: Sequence[SopDocument], batch_size: int = 32) -> int:
        if not documents:
            logger.warning("No SOP documents provided to add_documents")
            return 0

        added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            ids = [_doc_id(d) for d in batch]
            texts = [d.content for d in batch]
            metadatas = [{"source": d.source, "doc_type": d.doc_type, **d.metadata} for d in batch]
            vectors = self.embeddings.embed_documents(texts)

            self.collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
            added += len(batch)
            logger.debug(f"Upserted batch {i // batch_size + 1}: {len(batch)} chunks")

        logger.info(f"Added/updated {added} SOP chunks in Chroma collection '{self.collection_name}'")
        return added

    def search(self, query: str, k: int = 4, where: dict | None = None) -> List[dict]:
        query_vector = self.embeddings.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where=where,
        )

        hits: List[dict] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            hits.append({"content": doc, "metadata": meta, "score": 1 - dist})
        return hits

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )
        logger.warning(f"Reset Chroma collection '{self.collection_name}'")


if __name__ == "__main__":
    from ingestion.pdf_loader import load_sop_directory

    store = SopVectorStore()
    chunks = load_sop_directory("sample_data/sops")
    store.add_documents(chunks)
    print(f"Collection now has {store.count()} chunks")
    for hit in store.search("database connection timeout", k=3):
        print(f"[{hit['score']:.3f}] {hit['metadata']['source']} :: {hit['content'][:120]}")
