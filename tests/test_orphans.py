import pandas as pd
import pytest
from src.orphans import detect_orphans, ORPHAN_PRONE_SERVICES


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-01", "2024-02-01", "2024-03-01",
            "2024-01-01", "2024-01-01", "2024-01-01",
        ]),
        "cost": [5.0, 5.0, 5.0, 200.0, 0.01, 50.0],
        "service_name": [
            "Azure Managed Disks",
            "Azure Managed Disks",
            "Azure Managed Disks",
            "Azure Kubernetes Service",
            "Azure Public IP Addresses",
            "Azure Load Balancer",
        ],
        "resource_group_name": ["rg-old", "rg-old", "rg-old", "rg-prod", "rg-dev", "rg-dev"],
        "resource_id": [
            "/subscriptions/x/disks/disk1",
            "/subscriptions/x/disks/disk1",
            "/subscriptions/x/disks/disk1",
            "/subscriptions/x/aks/cluster1",
            "/subscriptions/x/publicips/ip1",
            "/subscriptions/x/loadbalancers/lb1",
        ],
        "tags": [
            {},
            {},
            {},
            {"Team": "backend", "Environment": "prod"},
            {},
            {"Team": "devops"},
        ],
        "status": ["Active", "Active", "Active", "Active", "Active", "Active"],
    })


def test_detect_orphans_returns_dataframe(sample_df):
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    assert isinstance(result, pd.DataFrame)


def test_detect_orphans_has_required_columns(sample_df):
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    for col in ["service_name", "resource_group_name", "cost", "reason", "confidence"]:
        assert col in result.columns


def test_detect_orphans_flags_orphan_prone_service_without_tags(sample_df):
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    # disk1 is orphan-prone (Managed Disks) and has no Team tag
    assert any("Managed Disks" in str(r) or "orphan-prone" in str(r).lower()
               for r in result["reason"].tolist())


def test_detect_orphans_confidence_values_are_valid(sample_df):
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    assert set(result["confidence"].unique()).issubset({"Alto", "Médio", "Baixo"})


def test_detect_orphans_status_column_detection():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]),
        "cost": [10.0],
        "service_name": ["Azure Managed Disks"],
        "resource_group_name": ["rg-old"],
        "resource_id": ["/subscriptions/x/disks/disk1"],
        "tags": [{}],
        "status": ["Orphaned"],
    })
    result = detect_orphans(df, mandatory_tags=["Team"])
    assert len(result) == 1
    assert "status" in result.iloc[0]["reason"].lower() or "orphan" in result.iloc[0]["reason"].lower()


def test_detect_orphans_near_zero_cost_flagged():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01"]),
        "cost": [0.01],
        "service_name": ["Azure Public IP Addresses"],
        "resource_group_name": ["rg-dev"],
        "resource_id": ["/subscriptions/x/publicips/ip1"],
        "tags": [{}],
        "status": ["Active"],
    })
    result = detect_orphans(df, mandatory_tags=["Team"])
    assert len(result) >= 1


def test_detect_orphans_healthy_resource_not_flagged(sample_df):
    # AKS with proper tags should not be flagged
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    aks_flagged = result[result["service_name"] == "Azure Kubernetes Service"]
    assert len(aks_flagged) == 0


def test_detect_orphans_deduplicates_same_resource(sample_df):
    # disk1 appears 3 times (3 months) but should appear once in results
    result = detect_orphans(sample_df, mandatory_tags=["Team"])
    disk_results = result[result["service_name"] == "Azure Managed Disks"]
    assert len(disk_results) <= 1


def test_orphan_prone_services_is_nonempty():
    assert len(ORPHAN_PRONE_SERVICES) > 0
