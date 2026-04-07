import pandas as pd

ORPHAN_PRONE_SERVICES = [
    "managed disks",
    "public ip addresses",
    "network interfaces",
    "snapshots",
    "load balancer",
    "application gateway",
    "app service plan",
    "virtual network",
    "nat gateway",
    "route table",
    "network security group",
]

ORPHANED_STATUSES = {"orphaned", "unattached", "idle", "unused", "detached"}

NEAR_ZERO_COST_THRESHOLD = 0.10


def _is_orphan_prone(service_name: str) -> bool:
    name = service_name.lower()
    return any(s in name for s in ORPHAN_PRONE_SERVICES)


def _detect_reasons(row: pd.Series, mandatory_tags: list) -> list:
    reasons = []

    status = str(row.get("status", "")).lower().strip()
    if status in ORPHANED_STATUSES:
        reasons.append(f"Status: {row['status']}")

    if _is_orphan_prone(row["service_name"]):
        missing_tags = [t for t in mandatory_tags if not row["tags"].get(t)]
        if missing_tags:
            reasons.append(f"Tipo orphan-prone sem tags: {', '.join(missing_tags)}")

    if row["cost"] <= NEAR_ZERO_COST_THRESHOLD and _is_orphan_prone(row["service_name"]):
        reasons.append(f"Custo residual ({row['cost']:.4f}) em recurso orphan-prone")

    return reasons


def _confidence(reasons: list, row: pd.Series) -> str:
    status = str(row.get("status", "")).lower().strip()
    if status in ORPHANED_STATUSES:
        return "Alto"
    if len(reasons) >= 2:
        return "Alto"
    if row["cost"] <= NEAR_ZERO_COST_THRESHOLD:
        return "Médio"
    return "Baixo"


def detect_orphans(df: pd.DataFrame, mandatory_tags: list) -> pd.DataFrame:
    id_col = "resource_id" if "resource_id" in df.columns else None

    # Aggregate to one row per resource (sum cost across periods)
    group_cols = ["service_name", "resource_group_name"]
    if id_col:
        group_cols = [id_col] + group_cols

    agg = df.groupby(group_cols, as_index=False).agg(
        cost=("cost", "sum"),
        tags=("tags", "first"),
        status=("status", "first") if "status" in df.columns else ("cost", "count"),
    )

    if "status" not in df.columns:
        agg["status"] = ""

    suspects = []
    for _, row in agg.iterrows():
        reasons = _detect_reasons(row, mandatory_tags)
        if reasons:
            suspects.append({
                **({"resource_id": row[id_col]} if id_col else {}),
                "service_name": row["service_name"],
                "resource_group_name": row["resource_group_name"],
                "cost": round(row["cost"], 2),
                "reason": "; ".join(reasons),
                "confidence": _confidence(reasons, row),
            })

    if not suspects:
        return pd.DataFrame(columns=[
            *(["resource_id"] if id_col else []),
            "service_name", "resource_group_name", "cost", "reason", "confidence",
        ])

    return (
        pd.DataFrame(suspects)
        .sort_values("cost", ascending=False)
        .reset_index(drop=True)
    )
