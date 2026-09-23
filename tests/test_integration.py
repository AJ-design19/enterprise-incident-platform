"""
End-to-end integration tests against live services. Run explicitly with:
    pytest -m integration
Requires Ollama, Neo4j, and a populated ChromaDB (run `python run_ingestion.py` first).
"""
import pytest

from workflows.incident_workflow import IncidentWorkflow


@pytest.mark.integration
def test_full_workflow_runs_end_to_end(sample_log_file):
    workflow = IncidentWorkflow()
    result = workflow.run(
        incident_text="Payment API is timing out for checkout requests.",
        log_path=str(sample_log_file),
    )

    assert "classification" in result
    assert "rca" in result
    assert "recommendation" in result
    assert result["classification"].get("category")


@pytest.mark.integration
def test_graph_query_agent_live():
    from agents.graph_query_agent import GraphQueryAgent

    agent = GraphQueryAgent()
    result = agent.run("Which services use Redis?")
    assert result.error is None
