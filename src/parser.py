import json
import re
import warnings
from typing import Union
import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = {"date", "cost", "service_name"}
OPTIONAL_DEFAULTS = {"resource_group_name": "(unknown)", "tags": None}

_COLUMN_MAP = {
    # Date variants
    "date": "date",
    "month": "date",
    "usagedatetime": "date",
    "billingperiodstartdate": "date",
    # Cost variants
    "cost": "cost",
    "pretaxcost": "cost",
    "costinbillingcurrency": "cost",
    "totalusd": "cost",
    "total": "cost",
    "subtotalusd": "cost",
    # Currency variants
    "billingcurrency": "billing_currency",
    "currency": "billing_currency",
    # Service name variants
    "servicename": "service_name",
    "service": "service_name",
    "metercategory": "service_name",
    "consumedservice": "service_name",
    # Resource group variants
    "resourcegroupname": "resource_group_name",
    "resourcegroup": "resource_group_name",
    "region": "resource_group_name",
    "location": "resource_group_name",
    # Other
    "resourceid": "resource_id",
    "tags": "tags",
    "subscriptionname": "subscription_name",
    "team": "team",
    "environment": "environment",
}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen_targets = set()
    renamed = {}
    for col in df.columns:
        key = col.lower().replace(" ", "").replace("_", "").replace("(", "").replace(")", "")
        target = _COLUMN_MAP.get(key, col.lower().replace(" ", "_"))
        if target in seen_targets:
            target = col.lower().replace(" ", "_")
        seen_targets.add(target)
        renamed[col] = target
    return df.rename(columns=renamed)


def _parse_tags(raw) -> dict:
    if not raw or (isinstance(raw, float)):
        return {}
    raw = str(raw).strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', raw)
        return dict(pairs)


def load_csv(source) -> pd.DataFrame:
    is_path = isinstance(source, (str, Path))
    name = str(source) if is_path else getattr(source, "name", "upload")
    try:
        read_target = Path(source) if is_path else source
        df = pd.read_csv(read_target, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise ValueError(f"File is empty: {name}")

    if df.empty:
        raise ValueError(f"File is empty: {name}")

    df = _normalise_columns(df)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Columns found: {list(df.columns)}"
        )

    for col, default in OPTIONAL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").astype(float)
    nan_cost = df["cost"].isna().sum()
    if nan_cost > 0:
        warnings.warn(f"{nan_cost} row(s) have invalid cost values and were set to NaN.")

    df["date"] = pd.to_datetime(df["date"], format="%b", errors="coerce").map(
        lambda d: d.replace(year=2024) if pd.notna(d) else d
    )
    if df["date"].isna().all():
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    nan_date = df["date"].isna().sum()
    if nan_date > 0:
        warnings.warn(f"{nan_date} row(s) have invalid date values and were set to NaT.")

    df["tags"] = df["tags"].apply(_parse_tags)

    return df.reset_index(drop=True)
