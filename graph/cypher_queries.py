"""
A small library of named, parameterized Cypher queries used by the
Neo4j Query Agent and the dashboard's graph viewer. Keeping these
centralized makes it easy to unit test them and avoids agents
hand-building injectable query strings.
"""
from __future__ import annotations

QUERIES: dict[str, str] = {
    "services_using_dependency": """
        MATCH (s:Service)-[:USES]->(d {name: $dependency_name})
        RETURN s.name AS service
        ORDER BY s.name
    """,
    "service_dependencies": """
        MATCH (s:Service {name: $service_name})-[r:USES|CALLS|HOSTED_ON]->(dep)
        RETURN type(r) AS relationship, labels(dep)[0] AS dependency_type, dep.name AS dependency
        ORDER BY relationship
    """,
    "downstream_impact": """
        MATCH (s:Service {name: $service_name})<-[:CALLS*1..3]-(caller:Service)
        RETURN DISTINCT caller.name AS impacted_service
    """,
    "team_owned_services": """
        MATCH (svc:Service)-[:OWNED_BY]->(t:Team {name: $team_name})
        RETURN svc.name AS service
        ORDER BY svc.name
    """,
    "service_incident_history": """
        MATCH (i:Incident)-[:AFFECTS]->(s:Service {name: $service_name})
        RETURN i.incident_id AS incident_id, i.title AS title, i.priority AS priority,
               i.category AS category, i.created_at AS created_at
        ORDER BY i.created_at DESC
        LIMIT $limit
    """,
    "service_sops": """
        MATCH (s:Service {name: $service_name})-[:HAS_SOP]->(sop:SOP)
        RETURN sop.id AS sop_id, sop.title AS title, sop.source AS source
    """,
    "top_failing_services": """
        MATCH (i:Incident)-[:AFFECTS]->(s:Service)
        RETURN s.name AS service, count(i) AS incident_count
        ORDER BY incident_count DESC
        LIMIT $limit
    """,
    "single_points_of_failure": """
        MATCH (dep)<-[:USES|CALLS]-(dependent:Service)
        WITH dep, count(DISTINCT dependent) AS dependents
        WHERE dependents >= $min_dependents
        RETURN labels(dep)[0] AS type, dep.name AS name, dependents
        ORDER BY dependents DESC
    """,
    "graph_overview": """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT $limit
    """,
}


def get_query(name: str) -> str:
    if name not in QUERIES:
        raise KeyError(f"Unknown query '{name}'. Available: {sorted(QUERIES)}")
    return QUERIES[name]
