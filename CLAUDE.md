# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dashboard
python3 -m streamlit run app.py

# Run all tests
python3 -m pytest

# Run a single test file
python3 -m pytest tests/test_parser.py -v

# Run a single test
python3 -m pytest tests/test_metrics.py::test_cost_by_service_aggregates_correctly -v

# Run with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Install dependencies
pip install -r requirements-dev.txt
```

## Architecture

Single-page Streamlit app with a clean pipeline: **CSV upload → parse → metrics → charts**.

`app.py` is the entry point. It auto-detects uploaded CSVs as either cost reports or waste/orphan reports (by sniffing for `issue_type`/`recommended_action` columns), then routes them to the appropriate parser.

### src/ modules

| Module | Responsibility |
|--------|---------------|
| `parser.py` | Ingests Azure Cost Management CSVs. Handles many column name variants (standard export, custom exports, month-abbreviation dates). Normalises to: `date`, `cost`, `service_name`, `resource_group_name`, `tags`. Tags are always parsed to `dict`. |
| `metrics.py` | Pure aggregation functions over the normalised cost DataFrame: `cost_by_service`, `cost_by_tag`, `cost_over_time`, `detect_anomalies` (7-day rolling mean), `tagging_compliance`. |
| `charts.py` | Thin Plotly wrappers. Each function receives a DataFrame and returns a `go.Figure`. No business logic. |
| `orphans.py` | Heuristic orphan detection over cost CSVs. Uses `ORPHAN_PRONE_SERVICES` list + missing mandatory tags + near-zero cost + status column to assign Alto/Médio/Baixo confidence. |
| `waste_parser.py` | Loads dedicated waste/orphan CSVs (e.g. Azure Advisor exports). Expects `issue_type`, `severity`, `monthly_savings`, `recommended_action`. `waste_summary()` returns aggregated KPIs. |

### Column normalisation pattern

Both `parser.py` and `waste_parser.py` use the same pattern: strip spaces/underscores/parens/dots from column names, lowercase, then look up in a `_COLUMN_MAP`. First match wins — duplicates get their original name.

### Tab structure (app.py)

7 tabs: Overview · Por Serviço · Por Equipa · Tendências · Anomalias · Tagging · Orfãos

Tab 7 (Orfãos) renders in two modes:
- **Rich mode** — when waste CSVs are uploaded: KPI metrics, severity/category/issue-type charts, filterable table
- **Heuristic mode** — always shown below, from the cost CSV via `detect_orphans()`

## Supported CSV formats

`parser.py` handles column name variants from multiple Azure export types. When adding support for a new format, add entries to `_COLUMN_MAP` in `parser.py` (keys must be fully lowercased with spaces, underscores, and parens removed).

Date parsing tries formats in order: `%Y-%m-%d`, `%Y/%m/%d`, `%d/%m/%Y`, `%m/%d/%Y`, `%Y-%m`, then month abbreviations (`Jan`, `Feb`…) defaulting to year 2024.
