import pandas as pd
from typing import IO, Union
from pathlib import Path

WASTE_COLUMN_MAP = {
    "rowid": "row_id",
    "issuetype": "issue_type",
    "severity": "severity",
    "billingmonth": "date",
    "billingperiodstart": "date",
    "subscriptionid": "subscription_id",
    "resourcegroup": "resource_group_name",
    "resourcename": "resource_name",
    "resourceid": "resource_id",
    "servicename": "service_name",
    "sku": "sku",
    "region": "region",
    "unitofmeasure": "unit_of_measure",
    "quantity": "quantity",
    "unitpriceusd": "unit_price",
    "subtotalusd": "subtotal",
    "taxusd": "tax",
    "totalcostusd": "cost",
    "idle/unuseddays": "idle_days",
    "lastactivitydate": "last_activity_date",
    "avgcpuutilization(%)": "avg_cpu_pct",
    "avgmemoryutilization(%)": "avg_memory_pct",
    "networkin(mb)": "network_in_mb",
    "issuedetail": "issue_detail",
    "recommendedaction": "recommended_action",
    "estmonthlysavingsusd": "monthly_savings",
    "estannualsavingsusd": "annual_savings",
    "finopscategory": "finops_category",
    "automationavailable": "automation_available",
    "notes": "notes",
    # Untagged resources CSV variants
    "missingtags": "missing_tags",
    "policyviolated": "policy_violated",
    "daysdesdeúltimoaudit": "days_since_audit",
    "acãorecomendada": "recommended_action",
}

REQUIRED_WASTE_COLUMNS = {"issue_type", "cost", "service_name"}
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _normalise_waste_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    seen = set()
    for col in df.columns:
        key = col.lower().replace(" ", "").replace("_", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "").replace("%", "")
        target = WASTE_COLUMN_MAP.get(key, col.lower().replace(" ", "_"))
        if target in seen:
            target = col.lower().replace(" ", "_")
        seen.add(target)
        renamed[col] = target
    return df.rename(columns=renamed)


def load_waste_csv(source: Union[Path, str, IO]) -> pd.DataFrame:
    is_path = isinstance(source, (str, Path))
    name = str(source) if is_path else getattr(source, "name", "upload")
    try:
        read_target = Path(source) if is_path else source
        df = pd.read_csv(read_target, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise ValueError(f"File is empty: {name}")

    if df.empty:
        raise ValueError(f"File is empty: {name}")

    df = _normalise_waste_columns(df)

    missing = REQUIRED_WASTE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Columns found: {list(df.columns)}"
        )

    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0.0)

    for col in ["monthly_savings", "annual_savings", "avg_cpu_pct", "avg_memory_pct",
                "idle_days", "network_in_mb", "quantity", "unit_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "severity" not in df.columns:
        df["severity"] = "Medium"

    if "finops_category" not in df.columns:
        df["finops_category"] = "Unknown"

    if "automation_available" not in df.columns:
        df["automation_available"] = "Manual Review Required"

    return df.reset_index(drop=True)


def waste_summary(df: pd.DataFrame) -> dict:
    total_cost = df["cost"].sum()
    monthly_savings = df["monthly_savings"].sum() if "monthly_savings" in df.columns else 0.0
    annual_savings = df["annual_savings"].sum() if "annual_savings" in df.columns else 0.0
    automatable = df[
        df["automation_available"].str.startswith("Yes", na=False)
    ]["monthly_savings"].sum() if "monthly_savings" in df.columns else 0.0

    return {
        "total_resources": len(df),
        "total_cost": round(total_cost, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "automatable_savings": round(automatable, 2),
        "critical_count": int((df["severity"] == "Critical").sum()),
        "high_count": int((df["severity"] == "High").sum()),
    }
