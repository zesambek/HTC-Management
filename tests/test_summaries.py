from __future__ import annotations

import pandas as pd

from htc_management.analytics.preparation import prepare_component_dataframe
from htc_management.analytics.summaries import build_summary, summary_to_frame
from htc_management.analytics.breakdowns import (
    build_aircraft_breakdown,
    build_part_breakdown,
    build_due_bucket_breakdown,
    build_config_slot_due_table,
)
from htc_management.analytics.profiling import analyze_column_types
from htc_management.analytics.timeseries import build_due_time_series
from htc_management.analytics.visuals import build_config_slot_due_scatter


def _prepared_sample() -> pd.DataFrame:
    raw = pd.DataFrame(
        [
            {
                "Part Name": "Part A",
                "Installed on": "BOEING 787-8 - ET-ATG",
                "DUE_DATE": "2024-09-10",
                "Config slot": "76-11-00-ZA2",
            },
            {
                "Part Name": "Part B",
                "Installed on": "BOEING 787-8 - ET-ATG",
                "DUE_DATE": "2024-08-10",
                "Config slot": "76-11-00-ZA2",
            },
            {
                "Part Name": "Part B",
                "Installed on": "BOEING 787-9 - ET-AUR",
                "DUE_DATE": "2024-10-10",
                "Config slot": "32-11-00-ZA7",
            },
        ]
    )
    return prepare_component_dataframe(raw, reference_date=pd.Timestamp("2024-09-01"))


def test_build_summary_outputs_expected_metrics():
    prepared = _prepared_sample()
    summary = build_summary(prepared)
    assert summary.total_components == 3
    assert summary.unique_parts == 2
    assert summary.unique_aircraft == 2
    assert summary.overdue_components == 1
    assert summary.due_within_30_days == 1

    frame = summary_to_frame(prepared, summary)
    assert {"Metric", "All components"}.issubset(frame.columns)
    assert not frame.empty


def test_breakdowns_return_expected_shapes():
    prepared = _prepared_sample()

    aircraft = build_aircraft_breakdown(prepared)
    assert {"Aircraft", "Components", "Overdue"}.issubset(aircraft.columns)
    assert not aircraft.empty

    parts = build_part_breakdown(prepared)
    assert {"Part Name", "Occurrences", "Overdue"}.issubset(parts.columns)
    assert not parts.empty

    buckets = build_due_bucket_breakdown(prepared)
    assert {"Due Bucket", "Components"}.issubset(buckets.columns)
    assert not buckets.empty


def test_analyze_column_types_generates_metrics():
    prepared = _prepared_sample()
    profile = analyze_column_types(prepared)
    assert {"Column", "Pandas dtype", "Numeric-compatible %"}.issubset(profile.columns)
    assert not profile.empty


def test_build_due_time_series_returns_frame_and_summary():
    prepared = _prepared_sample()
    result = build_due_time_series(prepared, freq="D")
    assert {"period", "due_count", "trend"}.issubset(result.frame.columns)
    assert result.frame["due_count"].sum() == len(prepared.dropna(subset=["due_date"]))


def test_build_config_slot_due_scatter_returns_figure():
    prepared = _prepared_sample()
    fig = build_config_slot_due_scatter(prepared, top_n=5)
    assert fig.data is not None


def test_build_config_slot_due_table_outputs_expected_columns():
    prepared = _prepared_sample()
    table = build_config_slot_due_table(prepared, top_n=5)
    assert {"Config Slot", "Components", "Earliest Due"}.issubset(table.columns)
