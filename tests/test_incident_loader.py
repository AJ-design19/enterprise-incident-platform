import pandas as pd
import pytest

from ingestion.incident_loader import IncidentSchemaError, iter_incident_records, load_incidents_csv


def test_load_incidents_csv_returns_expected_row_count(sample_incidents_csv):
    df = load_incidents_csv(sample_incidents_csv)
    assert len(df) == 12
    assert "incident_id" in df.columns


def test_load_incidents_csv_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_incidents_csv(tmp_path / "does_not_exist.csv")


def test_load_incidents_csv_missing_columns_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("incident_id,title\n1,Something broke\n")
    with pytest.raises(IncidentSchemaError):
        load_incidents_csv(bad_csv)


def test_iter_incident_records_yields_dicts(sample_incidents_csv):
    df = load_incidents_csv(sample_incidents_csv)
    records = list(iter_incident_records(df))
    assert len(records) == len(df)
    assert isinstance(records[0], dict)
    assert records[0]["incident_id"] == "INC-1001"


def test_columns_are_normalized(tmp_path):
    csv_path = tmp_path / "messy.csv"
    csv_path.write_text(
        "Incident ID,Title,Description,Service,Team,Priority,Category,Root Cause\n"
        "1,T,D,svc,team,P1-Critical,Network,cause\n"
    )
    df = load_incidents_csv(csv_path)
    assert "incident_id" in df.columns
    assert "root_cause" in df.columns
