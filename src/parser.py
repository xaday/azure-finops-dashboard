import json
import re
from typing import Union
import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = {"date", "cost", "service_name", "resource_group_name", "tags"}

_COLUMN_MAP = {
    "date": "date",
    "cost": "cost",
    "pretaxcost": "cost",
    "billingcurrency": "billing_currency",
    "currency": "billing_currency",
    "servicename": "service_name",
    "metercategory": "service_name",
    "resourcegroupname": "resource_group_name",
    "resourcegroup": "resource_group_name",
    "resourceid": "resource_id",
    "tags": "tags",
    "subscriptionname": "subscription_name",
}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {
        col: _COLUMN_MAP.get(col.lower().replace(" ", "").replace("_", ""), col.lower().replace(" ", "_"))
        for col in df.columns
    }
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


def load_csv(path: Union[Path, str]) -> pd.DataFrame:
    path = Path(path)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise ValueError(f"File is empty: {path}")

    if df.empty:
        raise ValueError(f"File is empty: {path}")

    df = _normalise_columns(df)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").astype(float)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["tags"] = df["tags"].apply(_parse_tags)

    return df.reset_index(drop=True)
