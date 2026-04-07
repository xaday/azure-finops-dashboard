# Azure FinOps Dashboard — Design Spec

**Date:** 2026-04-07
**Status:** Approved

---

## Overview

A local Streamlit dashboard for analysing Azure Cost Management CSV exports. Processes files uploaded at runtime (no persistence between sessions) and presents interactive FinOps metrics via Plotly charts.

---

## Architecture

```
CSV Upload → Pandas (parse/clean) → Streamlit UI → Plotly (charts)
```

- Single-command startup: `streamlit run app.py`
- No database, no server, no external dependencies beyond Python packages
- Stateless: each upload reloads the data in session

---

## Project Structure

```
azure-finops-dashboard/
├── app.py                  # Streamlit entry point
├── src/
│   ├── parser.py           # CSV ingestion and cleaning
│   ├── metrics.py          # Cost calculations and anomaly detection
│   └── charts.py           # Plotly chart builders
├── requirements.txt
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-07-azure-finops-dashboard-design.md
```

---

## Data Source

- **Format:** Azure Cost Management standard CSV export
- **Key columns:** `Date`, `Cost`, `Currency`, `ServiceName`, `ResourceGroup`, `ResourceId`, `Tags`
- **Upload:** Via Streamlit file uploader (supports single or multiple files for period comparison)

---

## Dashboard Sections

### 1. Overview
- Total cost for the period
- Top 5 services by cost
- Top 5 resource groups by cost
- Cost by subscription (if multiple)

### 2. Por Serviço
- Bar/treemap chart of cost broken down by `ServiceName`
- Filterable by date range

### 3. Por Equipa
- Cost breakdown by tag values (e.g. `Team`, `CostCenter`)
- Tag key selector in sidebar

### 4. Tendências
- Line chart of daily/monthly cost over time
- Filterable by service or resource group

### 5. Anomalias
- Automatic detection of cost spikes above a configurable threshold (default: 2× rolling average)
- Table of anomalous days with cost delta
- Threshold configurable in sidebar

### 6. Análise de Tagging
- User-configurable list of mandatory tags in sidebar (e.g. `Team`, `Environment`, `CostCenter`)
- Compliance % per mandatory tag
- Cost at risk: total cost of resources missing one or more mandatory tags
- Exportable table of resources with incomplete tagging

---

## Components

### `parser.py`
- Reads CSV (handles encoding, BOM, Azure date formats)
- Normalises column names to lowercase snake_case
- Parses `Tags` column (Azure exports tags as a JSON-like string)
- Returns a clean `pd.DataFrame`

### `metrics.py`
- `cost_by_service(df)` → aggregated costs per service
- `cost_by_tag(df, tag_key)` → aggregated costs per tag value
- `cost_over_time(df, freq)` → time series (daily or monthly)
- `detect_anomalies(df, threshold)` → rows where cost exceeds threshold × rolling mean
- `tagging_compliance(df, mandatory_tags)` → compliance stats per tag

### `charts.py`
- Thin wrappers around Plotly Express / Graph Objects
- Each function receives a DataFrame and returns a `fig` object
- No business logic — only presentation

### `app.py`
- Sidebar: file uploader, date range filter, tag selectors, anomaly threshold, mandatory tags config
- Routes to each section via `st.tabs()`
- Calls `parser → metrics → charts` pipeline

---

## Error Handling

- Invalid or empty CSV: show clear error message, do not crash
- Missing expected columns: warn the user which columns are absent
- Empty tag values: treat as `"(untagged)"` not as null

---

## Tech Stack

| Package | Purpose |
|---------|---------|
| `streamlit` | UI framework |
| `pandas` | Data processing |
| `plotly` | Interactive charts |
| `openpyxl` | Excel support (optional) |

---

## Out of Scope

- Azure API integration (no live data pull)
- Data persistence between sessions
- Multi-user / authentication
- Alerting or notifications
