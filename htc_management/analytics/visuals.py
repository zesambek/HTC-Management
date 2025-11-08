"""Plotly and Matplotlib visualisations for the hard-time component analytics."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import statsmodels.api as sm
from matplotlib import pyplot as plt


def _empty_figure(message: str):
    fig = px.scatter()
    fig.add_annotation(text=message, showarrow=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def build_aircraft_due_chart(df: pd.DataFrame):
    if df.empty or {"aircraft_registration", "days_until_due"} - set(df.columns):
        return _empty_figure("No aircraft exposure data available.")

    data = (
        df.groupby("aircraft_registration")
        .agg(
            total=("aircraft_registration", "size"),
            overdue=("is_overdue", "sum"),
            due_30=("days_until_due", lambda s: ((s >= 0) & (s <= 30)).sum()),
        )
        .reset_index()
    )
    fig = px.bar(
        data,
        x="aircraft_registration",
        y=["overdue", "due_30"],
        labels={"value": "Component count", "aircraft_registration": "Aircraft"},
        title="Component exposure by aircraft",
    )
    fig.update_layout(barmode="stack", legend_title_text="Status", height=400)
    return fig


def build_due_bucket_chart(df: pd.DataFrame):
    if df.empty or "due_bucket" not in df.columns:
        return _empty_figure("No due status data available.")
    counts = df["due_bucket"].value_counts().reset_index()
    counts.columns = ["Due bucket", "Components"]
    fig = px.pie(counts, names="Due bucket", values="Components", title="Due status distribution")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=400)
    return fig


def build_part_exposure_chart(df: pd.DataFrame, *, top_n: int = 10):
    if df.empty or "part_name" not in df.columns:
        return _empty_figure("No component data available.")
    counts = (
        df.groupby("part_name")
        .size()
        .reset_index(name="Components")
        .sort_values("Components", ascending=False)
        .head(top_n)
    )
    fig = px.bar(
        counts,
        x="Components",
        y="part_name",
        orientation="h",
        labels={"part_name": "Part name"},
        title=f"Top {top_n} components by count",
    )
    fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
    return fig


def build_timeline_chart(df: pd.DataFrame):
    if df.empty or "due_date" not in df.columns:
        return _empty_figure("Due date information unavailable.")
    timeline = (
        df.dropna(subset=["due_date"])
        .assign(due_day=lambda frame: frame["due_date"].dt.to_period("D").dt.to_timestamp())
        .groupby("due_day")
        .size()
        .reset_index(name="Components")
        .sort_values("due_day")
    )
    if timeline.empty:
        return _empty_figure("No scheduled due dates captured.")
    fig = px.line(timeline, x="due_day", y="Components", title="Upcoming due timeline")
    fig.update_layout(height=400, xaxis_title="Due date", yaxis_title="Components due")
    return fig


def build_due_time_series_chart(ts_frame: pd.DataFrame):
    """Plot resampled due counts with an optional trend line."""
    if ts_frame.empty or "due_count" not in ts_frame.columns:
        return _empty_figure("Insufficient data for time-series analysis.")

    fig = px.line(
        ts_frame,
        x="period",
        y="due_count",
        title="Weekly due-volume trend",
        labels={"period": "Week", "due_count": "Components due"},
    )
    if "trend" in ts_frame.columns and ts_frame["trend"].notna().any():
        fig.add_trace(
            px.line(ts_frame, x="period", y="trend").data[0]
        )
        fig.data[-1].name = "Trend (OLS)"
        fig.data[-1].line.color = "#FF6B6B"
    fig.update_layout(height=420, legend_title_text="")
    return fig


def build_overdue_scatter_chart(df: pd.DataFrame) -> Tuple[object, str | None]:
    """Return a scatter chart (Plotly) plus an OLS summary for overdue components."""
    required = {"days_overdue", "age_days"}
    if df.empty or not required.issubset(df.columns):
        return _empty_figure("No overdue duration data available."), None

    working = df.dropna(subset=["days_overdue", "age_days"])
    working = working[working["days_overdue"] > 0]
    if working.empty:
        return _empty_figure("No overdue components to plot."), None

    color_arg = "aircraft_type" if "aircraft_type" in working.columns else None
    hover = ["part_name"] if "part_name" in working.columns else None

    fig = px.scatter(
        working,
        x="age_days",
        y="days_overdue",
        color=color_arg,
        hover_data=hover,
        labels={"age_days": "Component age (days)", "days_overdue": "Days overdue"},
        title="Overdue exposure vs installation age",
    )
    fig.update_layout(height=420)

    summary_text = None
    if len(working) >= 3:
        X = sm.add_constant(working["age_days"])
        model = sm.OLS(working["days_overdue"], X).fit()
        working = working.copy()
        working["regression"] = model.predict(X)
        fig.add_trace(px.line(working.sort_values("age_days"), x="age_days", y="regression").data[0])
        fig.data[-1].name = "OLS fit"
        fig.data[-1].line.color = "#FF9F43"
        summary_text = model.summary().as_text()

    return fig, summary_text


def create_days_distribution_plot(df: pd.DataFrame):
    """Return a Matplotlib histogram for days_until_due."""
    fig, ax = plt.subplots(figsize=(6, 4))
    if df.empty or "days_until_due" not in df.columns:
        ax.text(0.5, 0.5, "No due-date deltas available.", ha="center", va="center")
        ax.axis("off")
        return fig

    series = df["days_until_due"].dropna()
    if series.empty:
        ax.text(0.5, 0.5, "No due-date deltas available.", ha="center", va="center")
        ax.axis("off")
        return fig

    overdue = series[series < 0]
    upcoming = series[series >= 0]

    ax.hist(overdue, bins=20, alpha=0.7, label="Overdue", color="#ff6b6b")
    ax.hist(upcoming, bins=20, alpha=0.7, label="Upcoming", color="#1dd3b0")
    ax.set_title("Distribution of days until due")
    ax.set_xlabel("Days from today")
    ax.set_ylabel("Component count")
    ax.legend()
    fig.tight_layout()
    return fig


def build_config_slot_due_scatter(df: pd.DataFrame, *, top_n: int = 20):
    """Scatter plot of days-until-due by config slot (top N most common)."""
    required = {"config_slot", "due_date"}
    if df.empty or not required.issubset(df.columns):
        return _empty_figure("Config slot or due date data unavailable.")

    working = df.dropna(subset=["config_slot", "due_date"]).copy()
    if working.empty:
        return _empty_figure("No config slot entries with due dates available.")

    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    working["due_date"] = pd.to_datetime(working["due_date"]).dt.tz_localize(None)

    if "days_until_due" not in working.columns:
        working["days_until_due"] = (working["due_date"] - today).dt.total_seconds() / 86400.0
    else:
        mask_na = working["days_until_due"].isna()
        working.loc[mask_na, "days_until_due"] = (working.loc[mask_na, "due_date"] - today).dt.total_seconds() / 86400.0

    counts = working["config_slot"].value_counts().head(top_n).index
    filtered = working[working["config_slot"].isin(counts)].copy()
    if filtered.empty:
        return _empty_figure("Insufficient data after filtering top config slots.")

    hover_fields: list[str] = ["due_date"]
    if "part_name" in filtered.columns:
        hover_fields.append("part_name")
    if "task_code" in filtered.columns:
        hover_fields.append("task_code")

    color_field = "aircraft_registration" if "aircraft_registration" in filtered.columns else None

    fig = px.scatter(
        filtered.sort_values("days_until_due"),
        x="days_until_due",
        y="config_slot",
        color=color_field,
        hover_data=hover_fields,
        title=f"Due exposure by config slot (top {len(counts)} slots)",
        labels={"days_until_due": "Days until due (negative = overdue)", "config_slot": "Config slot"},
    )
    fig.update_layout(
        height=420,
        yaxis={"categoryorder": "total ascending"},
        xaxis=dict(zeroline=True, zerolinecolor="#777", zerolinewidth=1),
    )
    return fig
