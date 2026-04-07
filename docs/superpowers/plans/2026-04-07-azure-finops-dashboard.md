# Azure FinOps Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit dashboard that ingests Azure Cost Management CSV exports and presents interactive FinOps metrics (costs by service/team, trends, anomalies, tagging compliance).

**Architecture:** CSV upload → pandas parse/clean → metrics calculation → Plotly charts rendered in Streamlit tabs. Stateless: data lives only in the session.

**Tech Stack:** Python 3.11+, Streamlit, Pandas, Plotly Express, pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Python dependencies |
| `src/__init__.py` | Makes src a package |
| `src/parser.py` | CSV ingestion, column normalisation, tags parsing |
| `src/metrics.py` | Pure functions: aggregations, anomaly detection, tagging compliance |
| `src/charts.py` | Plotly figure builders (no business logic) |
| `app.py` | Streamlit entry point, sidebar, tabs, pipeline orchestration |
| `tests/test_parser.py` | Unit tests for parser |
| `tests/test_metrics.py` | Unit tests for metrics |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.33.0
pandas>=2.2.0
plotly>=5.20.0
openpyxl>=3.1.0
pytest>=8.0.0
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 3: Create src/__init__.py and tests/__init__.py**

Both files are empty. Run:

```bash
mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages installed without errors.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pytest.ini src/__init__.py tests/__init__.py
git commit -m "chore: project setup with dependencies and pytest config"
```

---

## Task 2: CSV Parser

**Files:**
- Create: `src/parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/sample.csv` (test fixture)

- [ ] **Step 1: Create test fixture**

Create `tests/fixtures/sample.csv`:

```csv
Date,Cost,BillingCurrency,ServiceName,ResourceGroupName,ResourceId,Tags,SubscriptionName
2024-01-01,10.5,EUR,Virtual Machines,rg-prod,/subscriptions/abc/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm1,"{""Team"": ""backend"", ""Environment"": ""prod""}",sub-main
2024-01-01,5.0,EUR,Storage,rg-dev,/subscriptions/abc/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/sa1,"{""Team"": ""frontend""}",sub-main
2024-01-02,12.0,EUR,Virtual Machines,rg-prod,/subscriptions/abc/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm1,,sub-main
2024-01-02,3.0,EUR,SQL Database,rg-prod,/subscriptions/abc/resourceGroups/rg-prod/providers/Microsoft.Sql/servers/sql1,"{""Environment"": ""prod""}",sub-main
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_parser.py`:

```python
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
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_parser.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `src.parser` does not exist yet.

- [ ] **Step 4: Implement src/parser.py**

```python
import json
import re
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


def load_csv(path: Path | str) -> pd.DataFrame:
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
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_parser.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/parser.py tests/test_parser.py tests/fixtures/sample.csv tests/__init__.py
git commit -m "feat: CSV parser with column normalisation and tag parsing"
```

---

## Task 3: Metrics

**Files:**
- Create: `src/metrics.py`
- Create: `tests/test_metrics.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_metrics.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_metrics.py -v
```

Expected: `ImportError` — `src.metrics` does not exist yet.

- [ ] **Step 3: Implement src/metrics.py**

```python
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


def tagging_compliance(df: pd.DataFrame, mandatory_tags: list[str]) -> dict:
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_metrics.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/metrics.py tests/test_metrics.py
git commit -m "feat: metrics module with aggregations, anomaly detection and tagging compliance"
```

---

## Task 4: Charts

**Files:**
- Create: `src/charts.py`

No unit tests for charts (Plotly figures are visual; test via app rendering). Verify by running the app in Task 5.

- [ ] **Step 1: Implement src/charts.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/charts.py
git commit -m "feat: Plotly chart builders for all dashboard sections"
```

---

## Task 5: Streamlit App

**Files:**
- Create: `app.py`

- [ ] **Step 1: Implement app.py**

```python
import streamlit as st
import pandas as pd
from pathlib import Path
from src.parser import load_csv
from src.metrics import (
    cost_by_service,
    cost_by_tag,
    cost_over_time,
    detect_anomalies,
    tagging_compliance,
)
from src.charts import (
    bar_cost_by_service,
    treemap_cost_by_service,
    bar_cost_by_tag,
    line_cost_over_time,
    scatter_anomalies,
    bar_tagging_compliance,
)

st.set_page_config(page_title="Azure FinOps Dashboard", layout="wide")
st.title("Azure FinOps Dashboard")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuração")

    uploaded_files = st.file_uploader(
        "Upload CSV(s) do Azure Cost Management",
        type=["csv"],
        accept_multiple_files=True,
    )

    anomaly_threshold = st.slider(
        "Limiar de anomalia (× média móvel)",
        min_value=1.1,
        max_value=5.0,
        value=2.0,
        step=0.1,
    )

    mandatory_tags_input = st.text_input(
        "Tags obrigatórias (separadas por vírgula)",
        value="Team,Environment,CostCenter",
    )
    mandatory_tags = [t.strip() for t in mandatory_tags_input.split(",") if t.strip()]

# ── Load data ─────────────────────────────────────────────────────────────────
if not uploaded_files:
    st.info("Faz upload de um ou mais ficheiros CSV do Azure Cost Management para começar.")
    st.stop()

dfs = []
for f in uploaded_files:
    try:
        df = load_csv(f)
        dfs.append(df)
    except ValueError as e:
        st.error(f"Erro ao processar {f.name}: {e}")

if not dfs:
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# ── Date filter ───────────────────────────────────────────────────────────────
with st.sidebar:
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    date_range = st.date_input(
        "Intervalo de datas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if len(date_range) == 2:
    start, end = date_range
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

if df.empty:
    st.warning("Sem dados para o intervalo seleccionado.")
    st.stop()

# ── Tag key selector ──────────────────────────────────────────────────────────
available_tag_keys = sorted({k for tags in df["tags"] for k in tags.keys()})
with st.sidebar:
    selected_tag_key = st.selectbox(
        "Tag para análise por equipa",
        options=available_tag_keys if available_tag_keys else ["(sem tags)"],
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview", "Por Serviço", "Por Equipa", "Tendências", "Anomalias", "Tagging"
])

# Tab 1: Overview
with tab1:
    total_cost = df["cost"].sum()
    currency = df["billing_currency"].iloc[0] if "billing_currency" in df.columns else "EUR"

    col1, col2, col3 = st.columns(3)
    col1.metric("Custo Total", f"{total_cost:,.2f} {currency}")
    col2.metric("Nº de Serviços", df["service_name"].nunique())
    col3.metric("Nº de Resource Groups", df["resource_group_name"].nunique())

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Top 5 Serviços")
        top_services = cost_by_service(df).head(5)
        st.dataframe(top_services, use_container_width=True)
    with col_b:
        st.subheader("Top 5 Resource Groups")
        top_rgs = (
            df.groupby("resource_group_name", as_index=False)["cost"]
            .sum()
            .sort_values("cost", ascending=False)
            .head(5)
        )
        st.dataframe(top_rgs, use_container_width=True)

    if "subscription_name" in df.columns:
        st.subheader("Custo por Subscrição")
        sub_cost = (
            df.groupby("subscription_name", as_index=False)["cost"]
            .sum()
            .sort_values("cost", ascending=False)
        )
        st.dataframe(sub_cost, use_container_width=True)

# Tab 2: Por Serviço
with tab2:
    service_df = cost_by_service(df)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(bar_cost_by_service(service_df), use_container_width=True)
    with col2:
        st.plotly_chart(treemap_cost_by_service(service_df), use_container_width=True)

# Tab 3: Por Equipa
with tab3:
    if available_tag_keys:
        tag_df = cost_by_tag(df, selected_tag_key)
        st.plotly_chart(bar_cost_by_tag(tag_df, selected_tag_key), use_container_width=True)
        st.dataframe(tag_df, use_container_width=True)
    else:
        st.warning("Nenhuma tag encontrada nos dados.")

# Tab 4: Tendências
with tab4:
    freq = st.radio("Granularidade", ["Diário", "Mensal"], horizontal=True)
    freq_code = "D" if freq == "Diário" else "ME"

    filter_col = st.selectbox("Filtrar por", ["(todos)", "Serviço", "Resource Group"])
    if filter_col == "Serviço":
        services = df["service_name"].unique().tolist()
        selected = st.multiselect("Serviços", services, default=services)
        filtered = df[df["service_name"].isin(selected)]
    elif filter_col == "Resource Group":
        rgs = df["resource_group_name"].unique().tolist()
        selected = st.multiselect("Resource Groups", rgs, default=rgs)
        filtered = df[df["resource_group_name"].isin(selected)]
    else:
        filtered = df

    time_df = cost_over_time(filtered, freq=freq_code)
    st.plotly_chart(line_cost_over_time(time_df), use_container_width=True)

# Tab 5: Anomalias
with tab5:
    baseline = cost_over_time(df, freq="D")
    anomalies = detect_anomalies(df, threshold=anomaly_threshold)
    st.plotly_chart(scatter_anomalies(anomalies, baseline), use_container_width=True)

    if anomalies.empty:
        st.success("Nenhuma anomalia detectada com o limiar actual.")
    else:
        st.warning(f"{len(anomalies)} anomalia(s) detectada(s).")
        st.dataframe(anomalies, use_container_width=True)

# Tab 6: Tagging
with tab6:
    if not mandatory_tags:
        st.info("Define tags obrigatórias na sidebar.")
    else:
        compliance = tagging_compliance(df, mandatory_tags)
        st.plotly_chart(bar_tagging_compliance(compliance), use_container_width=True)

        st.subheader("Detalhe por Tag")
        summary_rows = [
            {
                "Tag": tag,
                "Compliance (%)": data["compliance_pct"],
                "Recursos conformes": data["compliant_count"],
                "Total recursos": data["total_count"],
                "Custo em risco (EUR)": round(data["cost_at_risk"], 2),
            }
            for tag, data in compliance.items()
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        st.subheader("Recursos com Tagging Incompleto")
        def is_incomplete(row):
            return any(not row["tags"].get(t) for t in mandatory_tags)

        incomplete = df[df.apply(is_incomplete, axis=1)][
            ["resource_id", "resource_group_name", "service_name", "cost", "tags"]
        ].sort_values("cost", ascending=False)

        st.dataframe(incomplete, use_container_width=True)

        csv_export = incomplete.copy()
        csv_export["tags"] = csv_export["tags"].astype(str)
        st.download_button(
            "Exportar para CSV",
            data=csv_export.to_csv(index=False),
            file_name="tagging_incompleto.csv",
            mime="text/csv",
        )
```

- [ ] **Step 2: Run the app locally to verify it works**

```bash
streamlit run app.py
```

Expected: browser opens at `http://localhost:8501`. Upload `tests/fixtures/sample.csv` and verify all 6 tabs render correctly.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit dashboard with 6 FinOps analysis tabs"
```

---

## Task 6: Final Check

- [ ] **Step 1: Run all tests**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Verify coverage (informational)**

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

Expected: `src/parser.py` and `src/metrics.py` above 80%. `src/charts.py` is excluded (visual).

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final test run and coverage check"
```

---

## Usage

```bash
# Install
pip install -r requirements.txt

# Run tests
pytest -v

# Start dashboard
streamlit run app.py
```

Upload one or more Azure Cost Management CSV exports and explore the 6 tabs.
