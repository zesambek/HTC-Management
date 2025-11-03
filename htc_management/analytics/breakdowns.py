"""Breakdown tables for the hard-time component analytics."""

from __future__ import annotations

import pandas as pd


def _ensure_dataframe(df: pd.DataFrame, required: set[str]) -> pd.DataFrame:
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {', '.join(sorted(missing))}")
    return df


def build_aircraft_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate overdue exposure by aircraft registration."""
    if df.empty:
        return pd.DataFrame(columns=["Aircraft", "Components", "Overdue", "Due ≤ 30d"])

    working = _ensure_dataframe(df, {"aircraft_registration", "is_overdue", "days_until_due"})
    grouped = working.groupby("aircraft_registration", dropna=False)

    result = grouped.agg(
        components=("aircraft_registration", "size"),
        overdue=("is_overdue", "sum"),
        due_30=("days_until_due", lambda s: ((s >= 0) & (s <= 30)).sum()),
    ).reset_index()

    result.rename(columns={"aircraft_registration": "Aircraft", "due_30": "Due ≤ 30d"}, inplace=True)
    result["Overdue"] = result["overdue"].astype(int)
    result["Components"] = result["components"].astype(int)
    result["Due ≤ 30d"] = result["Due ≤ 30d"].astype(int)
    result.drop(columns=["overdue", "components"], inplace=True)
    return result.sort_values(["Overdue", "Components"], ascending=[False, False]).reset_index(drop=True)


def build_part_breakdown(df: pd.DataFrame, *, top_n: int = 15) -> pd.DataFrame:
    """Return the most common overdue parts."""
    if df.empty:
        return pd.DataFrame(columns=["Part Name", "Occurrences", "Overdue"])

    required = {"part_name", "is_overdue"}
    working = _ensure_dataframe(df, required)
    grouped = working.groupby("part_name", dropna=False).agg(
        occurrences=("part_name", "size"),
        overdue=("is_overdue", "sum"),
    )
    result = grouped.reset_index().rename(columns={"part_name": "Part Name"})
    result["Occurrences"] = result["occurrences"].astype(int)
    result["Overdue"] = result["overdue"].astype(int)
    result.drop(columns=["occurrences", "overdue"], inplace=True)
    result = result.sort_values(["Overdue", "Occurrences"], ascending=[False, False]).head(top_n).reset_index(drop=True)
    return result


def build_due_bucket_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Summaries counts across due buckets."""
    if df.empty:
        return pd.DataFrame(columns=["Due Bucket", "Components"])

    if "due_bucket" not in df.columns:
        raise KeyError("Column 'due_bucket' not present in dataframe.")

    grouped = df.groupby("due_bucket", dropna=False).size().reset_index(name="Components")
    grouped.rename(columns={"due_bucket": "Due Bucket"}, inplace=True)
    return grouped.sort_values("Components", ascending=False).reset_index(drop=True)
