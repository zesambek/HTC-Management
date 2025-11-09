"""Summary metrics for the hard-time component report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ComponentSummary:
    """Lightweight container for headline analytics."""

    total_components: int
    unique_parts: int
    unique_aircraft: int
    overdue_components: int
    due_within_30_days: int
    average_days_until_due: float
    average_days_overdue: float
    report_date: pd.Timestamp


def build_summary(df: pd.DataFrame) -> ComponentSummary:
    """Generate headline KPIs from the prepared component dataframe."""
    if df.empty:
        zero = ComponentSummary(
            total_components=0,
            unique_parts=0,
            unique_aircraft=0,
            overdue_components=0,
            due_within_30_days=0,
            average_days_until_due=float("nan"),
            average_days_overdue=float("nan"),
            report_date=pd.Timestamp.utcnow().normalize(),
        )
        return zero

    total = len(df)
    unique_parts = df.get("part_name", pd.Series(dtype="string")).nunique(dropna=True)
    unique_aircraft = df.get("aircraft_registration", pd.Series(dtype="string")).replace("", np.nan).nunique(dropna=True)

    overdue_mask = df.get("is_overdue", pd.Series([False] * total)).fillna(False).astype(bool)
    overdue_components = int(overdue_mask.sum())

    days_until_due = df.get("days_until_due", pd.Series(dtype="float"))
    days_overdue = df.get("days_overdue", pd.Series(dtype="float"))

    due_within_30 = 0
    if not days_until_due.empty:
        due_within_30 = int(((days_until_due >= 0) & (days_until_due <= 30)).sum())

    avg_until_due = float(days_until_due.mean()) if not days_until_due.empty else float("nan")
    if not np.isnan(avg_until_due):
        avg_until_due = round(avg_until_due, 2)

    if not days_overdue.empty and overdue_components:
        avg_overdue = float(days_overdue[overdue_mask].mean())
    elif not days_overdue.empty:
        avg_overdue = float(days_overdue.mean())
    else:
        avg_overdue = float("nan")

    if not np.isnan(avg_overdue):
        avg_overdue = round(avg_overdue, 2)

    report_date = pd.Timestamp.utcnow().normalize()

    return ComponentSummary(
        total_components=int(total),
        unique_parts=int(unique_parts),
        unique_aircraft=int(unique_aircraft),
        overdue_components=overdue_components,
        due_within_30_days=due_within_30,
        average_days_until_due=avg_until_due,
        average_days_overdue=avg_overdue,
        report_date=report_date,
    )


def summary_to_frame(df: pd.DataFrame, summary: ComponentSummary) -> pd.DataFrame:
    """
    Convert summary metrics into a multi-column dataframe covering key cohorts.

    Columns: All, With due date, Overdue, Due ≤ 30d.
    """

    cohorts: Dict[str, pd.DataFrame] = {
        "All components": df,
        "With due date": df.dropna(subset=["due_date"]) if "due_date" in df.columns else df.iloc[0:0],
        "Overdue": df[df.get("is_overdue", pd.Series(False, index=df.index)).fillna(False)],
        "Due ≤ 30d": df[
            (df.get("days_until_due", pd.Series(dtype="float")).fillna(np.inf) >= 0)
            & (df.get("days_until_due", pd.Series(dtype="float")).fillna(np.inf) <= 30)
        ],
    }

    metrics: List[tuple[str, callable]] = [
        ("Total components", lambda frame: len(frame)),
        ("Unique parts", lambda frame: frame.get("part_name", pd.Series(dtype="string")).nunique(dropna=True)),
        ("Unique aircraft", lambda frame: frame.get("aircraft_registration", pd.Series(dtype="string")).replace("", np.nan).nunique(dropna=True)),
        ("Average days until due", lambda frame: frame.get("days_until_due", pd.Series(dtype="float")).mean()),
        ("Average days overdue", lambda frame: frame.get("days_overdue", pd.Series(dtype="float")).mean()),
    ]

    rows: List[Dict[str, object]] = []
    for label, func in metrics:
        row = {"Metric": label}
        for cohort_label, cohort_df in cohorts.items():
            value = func(cohort_df) if not cohort_df.empty else float("nan")
            row[cohort_label] = _format_metric_value(value)
        rows.append(row)

    rows.append(
        {
            "Metric": "Report generated",
            "All components": summary.report_date.strftime("%Y-%m-%d"),
            "With due date": "—",
            "Overdue": "—",
            "Due ≤ 30d": "—",
        }
    )

    return pd.DataFrame(rows)


def _format_metric_value(value: object) -> str:
    if value is None or (isinstance(value, float) and (pd.isna(value))):
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return str(value)
