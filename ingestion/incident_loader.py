"""
Loads historical incident records from CSV into pandas, validates the schema,
and pushes them into Neo4j as (:Incident) nodes linked to (:Service)/(:Team).

Expected columns (case-insensitive, extra columns are kept but ignored):
    incident_id, title, description, service, team, priority, category,
    root_cause, resolution, created_at, resolved_at
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from logging_setup import logger

REQUIRED_COLUMNS = {
    "incident_id",
    "title",
    "description",
    "service",
    "team",
    "priority",
    "category",
    "root_cause",
}


class IncidentSchemaError(ValueError):
    """Raised when a CSV is missing required columns."""


def load_incidents_csv(path: str | Path) -> pd.DataFrame:
    """Load and normalize an incident history CSV file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Incident CSV not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise IncidentSchemaError(f"Incident CSV missing required columns: {sorted(missing)}")

    df = df.fillna("")
    df["incident_id"] = df["incident_id"].astype(str)

    for date_col in ("created_at", "resolved_at"):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    logger.info(f"Loaded {len(df)} incidents from {path.name}")
    return df


def iter_incident_records(df: pd.DataFrame) -> Iterable[dict]:
    """Yield incident rows as plain dicts, ready for Neo4j ingestion."""
    for _, row in df.iterrows():
        record = row.to_dict()
        for k, v in record.items():
            if pd.isna(v):
                record[k] = None
            elif hasattr(v, "isoformat"):
                record[k] = v.isoformat()
        yield record


if __name__ == "__main__":
    import sys

    sample = sys.argv[1] if len(sys.argv) > 1 else "sample_data/incidents.csv"
    frame = load_incidents_csv(sample)
    print(frame.head())
    print(f"\n{len(frame)} incidents loaded, columns: {list(frame.columns)}")
