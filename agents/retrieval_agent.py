"""
Agent 2 — Knowledge Retrieval Agent

Searches the ChromaDB SOP knowledge base for procedures relevant to an
incident, then asks the LLM to synthesize a short, grounded answer that
cites which SOP each recommendation came from.
"""
from __future__ import annotations

from pydantic import BaseModel

from agents.base import BaseAgent
from vector_db.chroma_store import SopVectorStore

RETRIEVAL_SYSTEM_PROMPT = """You are a Knowledge Retrieval Agent for enterprise IT operations.
You will be given an incident description and a set of SOP excerpts retrieved from the
knowledge base. Using ONLY the provided excerpts (do not invent procedures), produce a
concise, actionable summary of relevant guidance. If no excerpt is relevant, say so plainly.

Respond with ONLY a JSON object matching exactly:
{
  "relevant": <true/false>,
  "summary": "<concise actionable guidance, or empty string if none>",
  "cited_sources": ["<source filename>", ...]
}
"""


class RetrievalResult(BaseModel):
    relevant: bool
    summary: str
    cited_sources: list[str]
    raw_hits: list[dict]


class KnowledgeRetrievalAgent(BaseAgent):
    name = "knowledge_retrieval"
    system_prompt = RETRIEVAL_SYSTEM_PROMPT

    def __init__(self, store: SopVectorStore | None = None, **kwargs):
        super().__init__(**kwargs)
        self.store = store or SopVectorStore()

    def run(self, incident_text: str, k: int = 4) -> RetrievalResult:
        hits = self.store.search(incident_text, k=k)

        if not hits:
            return RetrievalResult(relevant=False, summary="", cited_sources=[], raw_hits=[])

        excerpt_block = "\n\n".join(
            f"[Source: {h['metadata'].get('source', 'unknown')}]\n{h['content']}" for h in hits
        )
        prompt = f"Incident:\n{incident_text}\n\nSOP excerpts:\n{excerpt_block}"
        payload = self._invoke_json(prompt)

        return RetrievalResult(
            relevant=bool(payload.get("relevant", False)),
            summary=payload.get("summary", ""),
            cited_sources=payload.get("cited_sources", []),
            raw_hits=hits,
        )


if __name__ == "__main__":
    agent = KnowledgeRetrievalAgent()
    result = agent.run("Database connection pool exhausted, app throwing timeout errors")
    print(result.model_dump_json(indent=2))
