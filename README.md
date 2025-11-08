# HTC Management – Hard-Time Component Analytics

This repository contains a lightweight analytics toolkit that transforms the *HardTimeReport_New (2).xls* workbook into actionable insights. It includes:

- Reusable pandas-based preparation and summarisation helpers (`htc_management.analytics`)
- A Streamlit dashboard (`app.py`) with interactive charts and download options
- CLI tooling (`cli.py`) for generating Excel/PDF reports
- Pytest coverage for the core data preparation and summary layers

The implementation takes inspiration from the `non_routine_overdue_tasks` project and adapts the architecture to the hard-time component dataset.

## Getting started

1. Create a virtual environment (optional but recommended) and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run app.py
```

3. Or generate offline artefacts via the CLI:

```bash
python cli.py --workbook "HardTimeReport_New (2).xls"
```

## Package overview

| Module | Responsibility |
| --- | --- |
| `htc_management/data_loader.py` | Loading the legacy `.xls` workbook (requires `xlrd`) |
| `htc_management/analytics/preparation.py` | Column normalisation, date parsing, enriched metrics, aircraft parsing |
| `htc_management/analytics/summaries.py` | Headline KPI computation (`ComponentSummary`) |
| `htc_management/analytics/breakdowns.py` | Aircraft/part/due bucket aggregations |
| `htc_management/analytics/profiling.py` | Column dtype diagnostics shown in the UI |
| `htc_management/analytics/timeseries.py` | Weekly due-date resampling + statsmodels OLS trend detection |
| `htc_management/analytics/visuals.py` | Plotly + Matplotlib figures (time series, scatter, histogram, etc.) |
| `htc_management/reporting/exporters.py` | Excel + PDF export helpers |

## Testing

Run the test suite with:

```bash
pytest
```

Tests focus on the pure preparation and aggregation layers so they remain fast and deterministic. Streamlit and visualisation components are intentionally thin wrappers over these tested modules.

## Sample data

The bundled `HardTimeReport_New (2).xls` file acts as the default data source. You can point the CLI/app to fresh exports without modifying the codebase.
