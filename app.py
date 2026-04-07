import streamlit as st
import pandas as pd
from src.parser import load_csv
from src.orphans import detect_orphans
from src.waste_parser import load_waste_csv, waste_summary
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

    all_files = st.file_uploader(
        "Upload CSV(s) Azure",
        type=["csv"],
        accept_multiple_files=True,
        help="Aceita ficheiros de custos, waste, orfãos ou recursos sem tags. O tipo é detectado automaticamente.",
    )

    st.divider()
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
if not all_files:
    st.info("Faz upload de um ou mais ficheiros CSV do Azure para começar.")
    st.stop()


def _is_waste_file(file) -> bool:
    peek = pd.read_csv(file, nrows=0, encoding="utf-8-sig")
    file.seek(0)
    cols = {c.lower().replace(" ", "").replace("_", "") for c in peek.columns}
    return "issuetype" in cols or "recommendedaction" in cols


dfs = []
waste_files = []
for f in all_files:
    try:
        if _is_waste_file(f):
            waste_files.append(f)
        else:
            dfs.append(load_csv(f))
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview", "Por Serviço", "Por Equipa", "Tendências", "Anomalias", "Tagging", "Orfãos"
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

        preferred_cols = ["resource_id", "resource_group_name", "service_name", "cost", "tags"]
        display_cols = [c for c in preferred_cols if c in df.columns]
        incomplete = df[df.apply(is_incomplete, axis=1)][display_cols].sort_values("cost", ascending=False)

        st.dataframe(incomplete, use_container_width=True)

        csv_export = incomplete.copy()
        csv_export["tags"] = csv_export["tags"].astype(str)
        st.download_button(
            "Exportar para CSV",
            data=csv_export.to_csv(index=False),
            file_name="tagging_incompleto.csv",
            mime="text/csv",
        )

# Tab 7: Orfãos
with tab7:
    # ── Waste files (dedicated reports) ──────────────────────────────────────
    waste_dfs = []
    if waste_files:
        for wf in waste_files:
            try:
                wdf = load_waste_csv(wf)
                waste_dfs.append(wdf)
            except ValueError as e:
                st.error(f"Erro ao processar {wf.name}: {e}")

    if waste_dfs:
        import plotly.express as px

        wdf = pd.concat(waste_dfs, ignore_index=True)
        summary = waste_summary(wdf)

        st.subheader("Resumo de Waste")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Recursos", summary["total_resources"])
        c2.metric("Custo Total (USD)", f"{summary['total_cost']:,.0f}")
        c3.metric("Poupança Mensal (USD)", f"{summary['monthly_savings']:,.0f}")
        c4.metric("Poupança Anual (USD)", f"{summary['annual_savings']:,.0f}")
        c5.metric("Automatizável (USD/mês)", f"{summary['automatable_savings']:,.0f}")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            sev_counts = wdf["severity"].value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            sev_order = ["Critical", "High", "Medium", "Low"]
            sev_counts["severity"] = pd.Categorical(sev_counts["severity"], categories=sev_order, ordered=True)
            sev_counts = sev_counts.sort_values("severity")
            fig_sev = px.bar(
                sev_counts, x="severity", y="count",
                title="Recursos por Severidade",
                color="severity",
                color_discrete_map={"Critical": "#d62728", "High": "#ff7f0e", "Medium": "#ffbb78", "Low": "#2ca02c"},
            )
            st.plotly_chart(fig_sev, use_container_width=True)

        with col_b:
            if "finops_category" in wdf.columns:
                cat_savings = wdf.groupby("finops_category", as_index=False)["monthly_savings"].sum()
                fig_cat = px.pie(cat_savings, names="finops_category", values="monthly_savings",
                                 title="Poupança por Categoria FinOps")
                st.plotly_chart(fig_cat, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            if "issue_type" in wdf.columns:
                top_issues = (
                    wdf.groupby("issue_type", as_index=False)["monthly_savings"]
                    .sum()
                    .sort_values("monthly_savings", ascending=False)
                    .head(10)
                )
                fig_issues = px.bar(
                    top_issues, x="monthly_savings", y="issue_type",
                    orientation="h", title="Top 10 Issue Types por Poupança (USD/mês)",
                    labels={"monthly_savings": "Poupança Mensal (USD)", "issue_type": "Tipo"},
                    color="monthly_savings", color_continuous_scale="Reds",
                )
                st.plotly_chart(fig_issues, use_container_width=True)

        with col_d:
            if "automation_available" in wdf.columns:
                auto_savings = wdf.groupby("automation_available", as_index=False)["monthly_savings"].sum()
                fig_auto = px.bar(
                    auto_savings, x="monthly_savings", y="automation_available",
                    orientation="h", title="Poupança por Tipo de Automação",
                    labels={"monthly_savings": "Poupança Mensal (USD)", "automation_available": "Automação"},
                    color="monthly_savings", color_continuous_scale="Greens",
                )
                st.plotly_chart(fig_auto, use_container_width=True)

        st.subheader("Detalhes dos Recursos")
        sev_filter = st.multiselect(
            "Filtrar por severidade",
            options=["Critical", "High", "Medium", "Low"],
            default=["Critical", "High"],
        )
        display_cols = [c for c in [
            "severity", "issue_type", "service_name", "resource_group_name",
            "resource_name", "cost", "monthly_savings", "recommended_action",
            "automation_available", "issue_detail",
        ] if c in wdf.columns]

        filtered_waste = wdf[wdf["severity"].isin(sev_filter)][display_cols].sort_values(
            "monthly_savings", ascending=False
        ) if "monthly_savings" in wdf.columns else wdf[wdf["severity"].isin(sev_filter)][display_cols]

        st.dataframe(filtered_waste, use_container_width=True)
        st.download_button(
            "Exportar para CSV",
            data=filtered_waste.to_csv(index=False),
            file_name="waste_report.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("Detecção heurística (CSV de custos)")

    # ── Heuristic detection from cost CSV ────────────────────────────────────
    orphans = detect_orphans(df, mandatory_tags)
    total_orphan_cost = orphans["cost"].sum() if not orphans.empty else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Suspeitos (heurística)", len(orphans))
    col2.metric("Custo em risco", f"{total_orphan_cost:,.2f}")
    col3.metric("Confiança Alta", len(orphans[orphans["confidence"] == "Alto"]) if not orphans.empty else 0)

    if orphans.empty:
        st.success("Nenhum recurso orfão detectado com os critérios actuais.")
    else:
        confidence_filter = st.multiselect(
            "Filtrar por confiança",
            options=["Alto", "Médio", "Baixo"],
            default=["Alto", "Médio"],
            key="orphan_confidence",
        )
        filtered_orphans = orphans[orphans["confidence"].isin(confidence_filter)]
        st.dataframe(filtered_orphans, use_container_width=True)

        orphan_export = filtered_orphans.copy()
        if "tags" in orphan_export.columns:
            orphan_export["tags"] = orphan_export["tags"].astype(str)
        st.download_button(
            "Exportar heurística CSV",
            data=orphan_export.to_csv(index=False),
            file_name="orfaos_heuristico.csv",
            mime="text/csv",
            key="orphan_download",
        )

    with st.expander("Como são detectados os orfãos?"):
        st.markdown("""
**Ficheiros de waste dedicados (sidebar):** Carrega CSVs do Azure Advisor ou Cost Management
com campos como `Issue Type`, `Severity`, `Est. Monthly Savings` para análise completa.

**Detecção heurística (CSV de custos):**

| Critério | Confiança |
|----------|-----------|
| Coluna `status` com valor `Orphaned`, `Unattached`, `Idle` | Alto |
| Tipo orphan-prone + sem tags obrigatórias | Alto |
| Custo residual (≤ 0.10) em recurso orphan-prone | Médio |
| Tipo orphan-prone sem tags | Baixo |

**Tipos orphan-prone:** Managed Disks, Public IPs, NICs, Snapshots, Load Balancers,
App Gateways, App Service Plans, VNets, NAT Gateways, Route Tables, NSGs.
        """)
