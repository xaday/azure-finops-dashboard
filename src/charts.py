import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def bar_cost_by_service(df: pd.DataFrame) -> go.Figure:
    return px.bar(
        df,
        x="cost",
        y="service_name",
        orientation="h",
        title="Custo por Serviço",
        labels={"cost": "Custo (EUR)", "service_name": "Serviço"},
        color="cost",
        color_continuous_scale="Blues",
    )


def treemap_cost_by_service(df: pd.DataFrame) -> go.Figure:
    return px.treemap(
        df,
        path=["service_name"],
        values="cost",
        title="Distribuição por Serviço",
        color="cost",
        color_continuous_scale="Blues",
    )


def bar_cost_by_tag(df: pd.DataFrame, tag_key: str) -> go.Figure:
    return px.bar(
        df,
        x="cost",
        y="tag_value",
        orientation="h",
        title=f"Custo por {tag_key}",
        labels={"cost": "Custo (EUR)", "tag_value": tag_key},
        color="cost",
        color_continuous_scale="Greens",
    )


def line_cost_over_time(df: pd.DataFrame) -> go.Figure:
    return px.line(
        df,
        x="date",
        y="cost",
        title="Tendência de Custos",
        labels={"cost": "Custo (EUR)", "date": "Data"},
        markers=True,
    )


def scatter_anomalies(anomalies_df: pd.DataFrame, baseline_df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        baseline_df,
        x="date",
        y="cost",
        title="Anomalias de Custo",
        labels={"cost": "Custo (EUR)", "date": "Data"},
    )
    if not anomalies_df.empty:
        fig.add_scatter(
            x=anomalies_df["date"],
            y=anomalies_df["cost"],
            mode="markers",
            marker=dict(color="red", size=10),
            name="Anomalia",
        )
    return fig


def bar_tagging_compliance(compliance: dict) -> go.Figure:
    tags = list(compliance.keys())
    pcts = [compliance[t]["compliance_pct"] for t in tags]
    fig = px.bar(
        x=tags,
        y=pcts,
        title="Compliance de Tagging (%)",
        labels={"x": "Tag", "y": "Compliance (%)"},
        color=pcts,
        color_continuous_scale=["red", "yellow", "green"],
        range_color=[0, 100],
    )
    fig.update_layout(yaxis_range=[0, 100])
    return fig
