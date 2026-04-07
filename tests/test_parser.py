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


def test_load_csv_warns_on_invalid_cost(tmp_path):
    bad_cost_csv = tmp_path / "bad_cost.csv"
    bad_cost_csv.write_text(
        "Date,Cost,BillingCurrency,ServiceName,ResourceGroupName,ResourceId,Tags,SubscriptionName\n"
        "2024-01-01,not_a_number,EUR,Storage,rg-dev,/sub/res,,sub\n"
    )
    with pytest.warns(UserWarning, match="invalid cost"):
        df = load_csv(bad_cost_csv)
    assert df["cost"].isna().sum() == 1


def test_load_csv_warns_on_invalid_date(tmp_path):
    bad_date_csv = tmp_path / "bad_date.csv"
    bad_date_csv.write_text(
        "Date,Cost,BillingCurrency,ServiceName,ResourceGroupName,ResourceId,Tags,SubscriptionName\n"
        "not_a_date,10.0,EUR,Storage,rg-dev,/sub/res,,sub\n"
    )
    with pytest.warns(UserWarning, match="invalid date"):
        df = load_csv(bad_date_csv)
    assert df["date"].isna().sum() == 1


def test_load_csv_tags_regex_fallback(tmp_path):
    # Tags in non-JSON format that falls back to regex parsing
    regex_csv = tmp_path / "regex_tags.csv"
    regex_csv.write_text(
        'Date,Cost,BillingCurrency,ServiceName,ResourceGroupName,ResourceId,Tags,SubscriptionName\n'
        '2024-01-01,10.0,EUR,Storage,rg-dev,/sub/res,"Team: backend",sub\n'
    )
    df = load_csv(regex_csv)
    # non-JSON tags without braces won't match regex pattern either, just return {}
    assert isinstance(df.loc[0, "tags"], dict)
