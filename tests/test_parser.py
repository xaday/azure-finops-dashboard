import pandas as pd
import pytest
from pathlib import Path
from src.parser import load_csv, REQUIRED_COLUMNS

FIXTURE = Path("tests/fixtures/sample.csv")


def test_load_csv_returns_dataframe():
    df = load_csv(FIXTURE)
    assert isinstance(df, pd.DataFrame)


def test_load_csv_normalises_column_names():
    df = load_csv(FIXTURE)
    assert "date" in df.columns
    assert "cost" in df.columns
    assert "service_name" in df.columns
    assert "resource_group_name" in df.columns
    assert "tags" in df.columns


def test_load_csv_cost_is_float():
    df = load_csv(FIXTURE)
    assert df["cost"].dtype == float


def test_load_csv_date_is_datetime():
    df = load_csv(FIXTURE)
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_load_csv_tags_parsed_to_dict():
    df = load_csv(FIXTURE)
    # Row 0 has tags, row 2 has empty tags
    assert isinstance(df.loc[0, "tags"], dict)
    assert df.loc[0, "tags"].get("Team") == "backend"


def test_load_csv_empty_tags_become_empty_dict():
    df = load_csv(FIXTURE)
    # Row 2 has no tags
    assert df.loc[2, "tags"] == {}


def test_load_csv_raises_on_missing_required_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="Missing required columns"):
        load_csv(bad_csv)


def test_load_csv_raises_on_empty_file(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_csv(empty_csv)
