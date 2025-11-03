"""Plotly visualisations for the hard-time component analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


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
