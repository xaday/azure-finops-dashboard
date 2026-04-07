import pandas as pd
import pytest
from src.metrics import (
    cost_by_service,
    cost_by_tag,
    cost_over_time,
    detect_anomalies,
    tagging_compliance,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]),
        "cost": [10.5, 5.0, 12.0, 3.0],
        "service_name": ["Virtual Machines", "Storage", "Virtual Machines", "SQL Database"],
        "resource_group_name": ["rg-prod", "rg-dev", "rg-prod", "rg-prod"],
        "tags": [
            {"Team": "backend", "Environment": "prod"},
            {"Team": "frontend"},
            {},
            {"Environment": "prod"},
        ],
        "subscription_name": ["sub-main"] * 4,
    })


def test_cost_by_service_returns_dataframe(sample_df):
    result = cost_by_service(sample_df)
    assert isinstance(result, pd.DataFrame)


def test_cost_by_service_aggregates_correctly(sample_df):
    result = cost_by_service(sample_df)
    vm_cost = result.loc[result["service_name"] == "Virtual Machines", "cost"].iloc[0]
    assert vm_cost == pytest.approx(22.5)


def test_cost_by_service_sorted_descending(sample_df):
    result = cost_by_service(sample_df)
    assert result["cost"].is_monotonic_decreasing


def test_cost_by_tag_groups_by_tag_key(sample_df):
    result = cost_by_tag(sample_df, "Team")
    assert isinstance(result, pd.DataFrame)
    backend_cost = result.loc[result["tag_value"] == "backend", "cost"].iloc[0]
    assert backend_cost == pytest.approx(10.5)


def test_cost_by_tag_untagged_for_missing_key(sample_df):
    result = cost_by_tag(sample_df, "Team")
    untagged = result.loc[result["tag_value"] == "(untagged)", "cost"].iloc[0]
    assert untagged == pytest.approx(15.0)  # row 2 (12.0) + row 3 (3.0)


def test_cost_over_time_daily(sample_df):
    result = cost_over_time(sample_df, freq="D")
    assert isinstance(result, pd.DataFrame)
    assert "date" in result.columns
    assert "cost" in result.columns
    assert len(result) == 2


def test_cost_over_time_monthly(sample_df):
    result = cost_over_time(sample_df, freq="ME")
    assert len(result) == 1


def test_detect_anomalies_returns_dataframe(sample_df):
    result = detect_anomalies(sample_df, threshold=1.5)
    assert isinstance(result, pd.DataFrame)


def test_detect_anomalies_finds_spike():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03",
            "2024-01-04", "2024-01-05", "2024-01-06",
            "2024-01-07",
        ]),
        "cost": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 100.0],
    })
    result = detect_anomalies(df, threshold=2.0)
    assert len(result) == 1
    assert result.iloc[0]["cost"] == 100.0


def test_tagging_compliance_returns_dict(sample_df):
    result = tagging_compliance(sample_df, ["Team", "Environment"])
    assert isinstance(result, dict)


def test_tagging_compliance_calculates_percentage(sample_df):
    result = tagging_compliance(sample_df, ["Team"])
    # 2 out of 4 rows have Team tag
    assert result["Team"]["compliance_pct"] == pytest.approx(50.0)


def test_tagging_compliance_cost_at_risk(sample_df):
    result = tagging_compliance(sample_df, ["Team"])
    # rows without Team: row 2 (12.0) + row 3 (3.0) = 15.0
    assert result["Team"]["cost_at_risk"] == pytest.approx(15.0)
