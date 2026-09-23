"""
Unit tests for agent logic using mocked LLM calls, so the suite runs
without a live Ollama instance. Integration tests that hit real Ollama
live in test_integration.py and are skipped by default.
"""
from unittest.mock import patch

from agents.graph_query_agent import GraphQueryAgent
from agents.incident_classifier import IncidentClassifierAgent


def test_incident_classifier_valid_response():
    fake_payload = {
        "category": "Database",
        "priority": "P1-Critical",
        "affected_service": "payment-db",
        "confidence": 0.9,
        "reasoning": "Timeouts point to DB connection exhaustion.",
    }
    with patch("agents.base.BaseAgent._invoke_json", return_value=fake_payload):
        agent = IncidentClassifierAgent.__new__(IncidentClassifierAgent)
        result = agent.run("Payment API timing out")

    assert result.category == "Database"
    assert result.priority == "P1-Critical"
    assert 0.0 <= result.confidence <= 1.0


def test_incident_classifier_invalid_category_falls_back_to_unknown():
    fake_payload = {
        "category": "Not A Real Category",
        "priority": "Not A Real Priority",
        "affected_service": "svc",
        "confidence": 0.5,
        "reasoning": "test",
    }
    with patch("agents.base.BaseAgent._invoke_json", return_value=fake_payload):
        agent = IncidentClassifierAgent.__new__(IncidentClassifierAgent)
        result = agent.run("some incident")

    assert result.category == "Unknown"
    assert result.priority == "P3-Medium"


def test_graph_query_agent_blocks_write_queries():
    fake_payload = {"cypher": "MATCH (s:Service) DETACH DELETE s", "explanation": "malicious"}
    with patch("agents.base.BaseAgent._invoke_json", return_value=fake_payload):
        agent = GraphQueryAgent.__new__(GraphQueryAgent)
        agent.conn = None  # should never be reached
        result = agent.run("delete everything")

    assert result.error is not None
    assert "blocked" in result.error.lower()


def test_graph_query_agent_adds_limit_when_missing():
    fake_payload = {"cypher": "MATCH (s:Service) RETURN s.name AS name", "explanation": "list services"}

    class FakeConn:
        def run(self, cypher, params=None):
            assert "LIMIT" in cypher
            return [{"name": "payment-api"}]

    with patch("agents.base.BaseAgent._invoke_json", return_value=fake_payload):
        agent = GraphQueryAgent.__new__(GraphQueryAgent)
        agent.conn = FakeConn()
        result = agent.run("list services", row_limit=10)

    assert result.error is None
    assert result.rows == [{"name": "payment-api"}]
