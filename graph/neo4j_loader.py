"""
Neo4j connection manager and graph-population routines.

Schema:
    Nodes: Service, API, Database, Team, Server, SOP, Incident
    Relationships: CALLS, USES, HOSTED_ON, OWNED_BY, HAS_SOP, CAUSED_BY
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable

from neo4j import GraphDatabase, Driver
from tenacity import retry, stop_after_attempt, wait_fixed

from config import neo4j_config
from logging_setup import logger


class Neo4jConnection:
    """Thin wrapper around the neo4j driver with retrying connect/close."""

    _driver: Driver | None = None

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self.uri = uri or neo4j_config.uri
        self.user = user or neo4j_config.user
        self.password = password or neo4j_config.password
        self.database = neo4j_config.database

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
    def connect(self) -> Driver:
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.uri}")
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self):
        driver = self.connect()
        session = driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()

    def run(self, query: str, parameters: dict | None = None) -> list[dict]:
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def run_many(self, query: str, rows: Iterable[dict]) -> None:
        """Run the same parameterized query once per row inside one transaction."""
        with self.session() as session:
            with session.begin_transaction() as tx:
                for row in rows:
                    tx.run(query, row)
                tx.commit()


CONSTRAINTS = [
    "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT team_name IF NOT EXISTS FOR (t:Team) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT api_name IF NOT EXISTS FOR (a:API) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT database_name IF NOT EXISTS FOR (d:Database) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT server_name IF NOT EXISTS FOR (sv:Server) REQUIRE sv.name IS UNIQUE",
    "CREATE CONSTRAINT sop_id IF NOT EXISTS FOR (sop:SOP) REQUIRE sop.id IS UNIQUE",
    "CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE",
]

MERGE_INCIDENT = """
MERGE (i:Incident {incident_id: $incident_id})
SET i.title = $title,
    i.description = $description,
    i.priority = $priority,
    i.category = $category,
    i.root_cause = $root_cause,
    i.resolution = $resolution,
    i.created_at = $created_at,
    i.resolved_at = $resolved_at
MERGE (svc:Service {name: $service})
MERGE (team:Team {name: $team})
MERGE (i)-[:AFFECTS]->(svc)
MERGE (i)-[:HANDLED_BY]->(team)
MERGE (svc)-[:OWNED_BY]->(team)
"""

MERGE_SOP = """
MERGE (sop:SOP {id: $id})
SET sop.title = $title, sop.source = $source, sop.doc_type = $doc_type
MERGE (svc:Service {name: $service})
MERGE (svc)-[:HAS_SOP]->(sop)
"""

MERGE_SERVICE_TOPOLOGY = """
MERGE (a:Service {name: $service})
FOREACH (_ IN CASE WHEN $calls IS NOT NULL THEN [1] ELSE [] END |
    MERGE (b:Service {name: $calls})
    MERGE (a)-[:CALLS]->(b)
)
FOREACH (_ IN CASE WHEN $uses_api IS NOT NULL THEN [1] ELSE [] END |
    MERGE (api:API {name: $uses_api})
    MERGE (a)-[:USES]->(api)
)
FOREACH (_ IN CASE WHEN $uses_db IS NOT NULL THEN [1] ELSE [] END |
    MERGE (db:Database {name: $uses_db})
    MERGE (a)-[:USES]->(db)
)
FOREACH (_ IN CASE WHEN $hosted_on IS NOT NULL THEN [1] ELSE [] END |
    MERGE (sv:Server {name: $hosted_on})
    MERGE (a)-[:HOSTED_ON]->(sv)
)
"""


def initialize_schema(conn: Neo4jConnection) -> None:
    logger.info("Applying Neo4j constraints")
    for stmt in CONSTRAINTS:
        conn.run(stmt)


def ingest_incidents(conn: Neo4jConnection, records: Iterable[dict]) -> int:
    rows = list(records)
    conn.run_many(MERGE_INCIDENT, rows)
    logger.info(f"Ingested {len(rows)} incidents into Neo4j")
    return len(rows)


def ingest_sops(conn: Neo4jConnection, sop_rows: Iterable[dict]) -> int:
    rows = list(sop_rows)
    conn.run_many(MERGE_SOP, rows)
    logger.info(f"Ingested {len(rows)} SOP nodes into Neo4j")
    return len(rows)


def ingest_topology(conn: Neo4jConnection, topology_rows: Iterable[dict]) -> int:
    rows = list(topology_rows)
    conn.run_many(MERGE_SERVICE_TOPOLOGY, rows)
    logger.info(f"Ingested topology for {len(rows)} services into Neo4j")
    return len(rows)


if __name__ == "__main__":
    conn = Neo4jConnection()
    initialize_schema(conn)
    print(conn.run("MATCH (n) RETURN labels(n) AS label, count(*) AS count"))
    conn.close()
