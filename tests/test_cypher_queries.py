import pytest

from graph.cypher_queries import QUERIES, get_query


def test_get_query_returns_known_query():
    query = get_query("services_using_dependency")
    assert "MATCH" in query
    assert "$dependency_name" in query


def test_get_query_unknown_raises():
    with pytest.raises(KeyError):
        get_query("not_a_real_query")


@pytest.mark.parametrize("name", list(QUERIES.keys()))
def test_all_queries_are_read_only(name):
    query = QUERIES[name].upper()
    for forbidden in ("CREATE ", "MERGE ", "DELETE ", "SET ", "DROP ", "DETACH "):
        assert forbidden not in query, f"{name} contains a write keyword: {forbidden}"
