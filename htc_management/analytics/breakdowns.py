"""Breakdown tables for the hard-time component analytics."""

from __future__ import annotations

import pandas as pd


def build_aircraft_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate overdue exposure by aircraft registration."""
    if df.empty or "aircraft_registration" not in df.columns:
        return pd.DataFrame(columns=["Aircraft", "Components", "Overdue", "Due ≤ 30d"])

    if "is_overdue" not in df.columns or "days_until_due" not in df.columns:
        return pd.DataFrame(columns=["Aircraft", "Components", "Overdue", "Due ≤ 30d"])

    working = df.copy()
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

    part_column = _resolve_part_column(df)
    if part_column is None or "is_overdue" not in df.columns:
        return pd.DataFrame(columns=["Part Name", "Occurrences", "Overdue"])

    working = df.rename(columns={part_column: "part_name"})
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
        return pd.DataFrame(columns=["Due Bucket", "Components"])

    grouped = df.groupby("due_bucket", dropna=False).size().reset_index(name="Components")
    grouped.rename(columns={"due_bucket": "Due Bucket"}, inplace=True)
    return grouped.sort_values("Components", ascending=False).reset_index(drop=True)


def build_config_slot_due_table(df: pd.DataFrame, *, top_n: int = 20) -> pd.DataFrame:
    """Return aggregated due-date stats per config slot."""
    required = {"config_slot", "due_date"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame(
            columns=["Config Slot", "Components", "Earliest Due", "Median Due", "Latest Due", "Avg Days Until Due"]
        )

    working = (
        df.dropna(subset=["config_slot", "due_date"])
        .assign(
            due_date=lambda frame: pd.to_datetime(frame["due_date"]).dt.tz_localize(None),
            days_until_due=lambda frame: frame.get("days_until_due"),
        )
    )
    if working.empty:
        return pd.DataFrame(
            columns=["Config Slot", "Components", "Earliest Due", "Median Due", "Latest Due", "Avg Days Until Due"]
        )

    top_slots = working["config_slot"].value_counts().head(top_n).index
    filtered = working[working["config_slot"].isin(top_slots)].copy()
    if filtered.empty:
        return pd.DataFrame(
            columns=["Config Slot", "Components", "Earliest Due", "Median Due", "Latest Due", "Avg Days Until Due"]
        )

    summary = (
        filtered.groupby("config_slot", dropna=False)
        .agg(
            components=("config_slot", "size"),
            earliest_due=("due_date", "min"),
            median_due=("due_date", "median"),
            latest_due=("due_date", "max"),
            avg_days_until=("days_until_due", "mean"),
        )
        .reset_index()
        .rename(
            columns={
                "config_slot": "Config Slot",
                "components": "Components",
                "earliest_due": "Earliest Due",
                "median_due": "Median Due",
                "latest_due": "Latest Due",
                "avg_days_until": "Avg Days Until Due",
            }
        )
    )

    if "Avg Days Until Due" in summary.columns:
        summary["Avg Days Until Due"] = summary["Avg Days Until Due"].round(1)

    summary = summary.sort_values(["Earliest Due", "Components"], ascending=[True, False]).reset_index(drop=True)
    return summary


def _resolve_part_column(df: pd.DataFrame) -> str | None:
    if "part_name" in df.columns:
        return "part_name"

    for column in df.columns:
        label = str(column).strip().lower()
        if "part name" in label or label.startswith("part") or "component" in label:
            return column
    return None
