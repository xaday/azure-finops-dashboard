import pandas as pd


def cost_by_service(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby("service_name", as_index=False)["cost"]
        .sum()
        .sort_values("cost", ascending=False)
        .reset_index(drop=True)
    )
    return result


def cost_by_tag(df: pd.DataFrame, tag_key: str) -> pd.DataFrame:
    def extract_tag(tags: dict) -> str:
        return tags.get(tag_key, "(untagged)") or "(untagged)"

    copy = df.copy()
    copy["tag_value"] = copy["tags"].apply(extract_tag)
    result = (
        copy.groupby("tag_value", as_index=False)["cost"]
        .sum()
        .sort_values("cost", ascending=False)
        .reset_index(drop=True)
    )
    return result


def cost_over_time(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    result = (
        df.groupby(pd.Grouper(key="date", freq=freq))["cost"]
        .sum()
        .reset_index()
    )
    return result


def detect_anomalies(df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    daily = cost_over_time(df, freq="D")
    rolling_mean = daily["cost"].rolling(window=7, min_periods=1).mean()
    anomalies = daily[daily["cost"] > threshold * rolling_mean].copy()
    anomalies["rolling_mean"] = rolling_mean[anomalies.index]
    anomalies["delta"] = anomalies["cost"] - anomalies["rolling_mean"]
    return anomalies.reset_index(drop=True)


def tagging_compliance(df: pd.DataFrame, mandatory_tags: list) -> dict:
    result = {}
    total = len(df)
    for tag in mandatory_tags:
        has_tag = df["tags"].apply(lambda t: bool(t.get(tag)))
        compliant = has_tag.sum()
        cost_at_risk = df.loc[~has_tag, "cost"].sum()
        result[tag] = {
            "compliance_pct": round(100.0 * compliant / total, 1) if total > 0 else 0.0,
            "compliant_count": int(compliant),
            "total_count": total,
            "cost_at_risk": float(cost_at_risk),
        }
    return result
