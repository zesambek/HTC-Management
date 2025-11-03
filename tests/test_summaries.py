from __future__ import annotations

import pandas as pd

from htc_management.analytics.preparation import prepare_component_dataframe
from htc_management.analytics.summaries import build_summary, summary_to_frame
from htc_management.analytics.breakdowns import (
    build_aircraft_breakdown,
    build_part_breakdown,
    build_due_bucket_breakdown,
)


def _prepared_sample() -> pd.DataFrame:
    raw = pd.DataFrame(
        [
            {
                "Part Name": "Part A",
                "Installed on": "BOEING 787-8 - ET-ATG",
                "DUE_DATE": "2024-09-10",
            },
            {
                "Part Name": "Part B",
                "Installed on": "BOEING 787-8 - ET-ATG",
                "DUE_DATE": "2024-08-10",
            },
            {
                "Part Name": "Part B",
                "Installed on": "BOEING 787-9 - ET-AUR",
                "DUE_DATE": "2024-10-10",
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

    frame = summary_to_frame(summary)
    assert {"Metric", "Value"}.issubset(frame.columns)
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
