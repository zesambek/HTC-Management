from __future__ import annotations

import pandas as pd

from htc_management.analytics.preparation import prepare_component_dataframe


def _sample_raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Part Name": "THRUST CONTROL MODULE ASSY",
                "OEM Part No": "4260-0029-8",
                "Serial No / Batch No": "44788L",
                "Installed on": "BOEING 787-8 - ET-ATG",
                "Config slot": "76-11-00-ZA2-11-001-HTC",
                "DUE_DATE": "2025-01-15",
                "TASK": "TSFN8002C5FM",
                "POSITION": "ET-ATG",
            },
            {
                "Part Name": "MAIN LANDING GEAR ASSY-LEFT",
                "OEM Part No": "510Z1210-13",
                "Serial No / Batch No": "11MDT0033",
                "Installed on": "BOEING 787-8 - ET-AOT",
                "Config slot": "32-11-00-ZA7-31-001-HTC",
                "DUE_DATE": "2024-10-05",
                "TASK": "TSFN800AZW93",
                "POSITION": "ET-AOT",
            },
        ]
    )


def test_prepare_component_dataframe_adds_expected_columns():
    prepared = prepare_component_dataframe(_sample_raw_frame(), reference_date=pd.Timestamp("2024-09-01"))
    assert {"due_date", "days_until_due", "due_bucket", "aircraft_registration", "aircraft_type"}.issubset(
        prepared.columns
    )
    first = prepared.iloc[0]
    assert first["aircraft_registration"] == "ET-ATG"
    assert first["aircraft_type"] == "BOEING 787-8"
    assert first["is_overdue"] is False

    second = prepared.iloc[1]
    assert second["is_overdue"] is True
    assert second["due_bucket"] == "Overdue"
