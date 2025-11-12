"""Plotly and Matplotlib visualisations for the hard-time component analytics."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import statsmodels.api as sm
from matplotlib import pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ListedColormap
import seaborn as sns

sns.set_theme(style="whitegrid")
_BLUE = "#2563eb"
_RED = "#dc2626"
_GREEN = "#059669"
_PALETTE = [_RED, "#0284c7", "#22c55e", "#f59e0b", "#6366f1"]


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
    """Seaborn scatter with layered due windows and threshold markers."""
    required = {"config_slot", "due_date"}
    if df.empty or not required.issubset(df.columns):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "Config slot data unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    working = df.dropna(subset=["config_slot", "due_date"]).copy()
    if working.empty:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No config slot entries with due dates available", ha="center", va="center")
        ax.axis("off")
        return fig

    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    working["due_date"] = pd.to_datetime(working["due_date"]).dt.tz_localize(None)
    working["days_until_due"] = (
        working["due_date"] - today
    ).dt.total_seconds() / 86400.0

    counts = working["config_slot"].value_counts().head(top_n).index
    filtered = working[working["config_slot"].isin(counts)].copy()
    if filtered.empty:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "Insufficient slots after filtering", ha="center", va="center")
        ax.axis("off")
        return fig

    filtered["due_window"] = pd.cut(
        filtered["days_until_due"],
        bins=[-np.inf, 0, 30, 90, np.inf],
        labels=["Overdue", "Due ≤ 30d", "Due ≤ 90d", "Due > 90d"],
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.scatterplot(
        data=filtered,
        x="days_until_due",
        y="config_slot",
        hue="due_window",
        palette=["#ef4444", "#f59e0b", "#22c55e", "#2563eb"],
        ax=ax,
        alpha=0.8,
    )
    ax.axvline(0, color="#475467", linestyle="--", linewidth=1)
    ax.axvline(30, color="#22c55e", linestyle=":", linewidth=1)
    ax.axvline(90, color="#2563eb", linestyle=":", linewidth=1)
    ax.set_xlabel("Days until due (negative = overdue)")
    ax.set_ylabel("Config slot")
    ax.set_title(f"Due exposure by config slot (top {len(counts)} slots)")
    ax.legend(title="Due window", loc="upper right")
    fig.tight_layout()
    return fig


def build_aircraft_exposure_matplot(df: pd.DataFrame):
    """Seaborn bar chart for component exposure by aircraft."""
    if df.empty or "aircraft_registration" not in df.columns:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No aircraft exposure data", ha="center", va="center")
        ax.axis("off")
        return fig

    working = df.copy()
    working["status"] = np.where(working.get("is_overdue", False), "Overdue", "Current")
    exposure = (
        working.groupby(["aircraft_registration", "status"])
        .size()
        .reset_index(name="components")
    )

    fig, ax = plt.subplots(figsize=(9, 4))
    sns.barplot(
        data=exposure,
        x="aircraft_registration",
        y="components",
        hue="status",
        palette=[_RED, _BLUE],
        ax=ax,
    )
    ax.set_xlabel("Aircraft")
    ax.set_ylabel("Component count")
    ax.set_title("Component exposure by aircraft")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def build_due_status_donut(df: pd.DataFrame):
    """Matplotlib donut for due-bucket split."""
    if df.empty or "due_bucket" not in df.columns:
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.text(0.5, 0.5, "Due bucket data unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    counts = df["due_bucket"].value_counts()
    fig, ax = plt.subplots(figsize=(4, 4))
    wedges, texts = ax.pie(
        counts.values,
        labels=[f"{label} ({value/counts.sum():.1%})" for label, value in counts.items()],
        colors=sns.color_palette("Blues", len(counts)),
        startangle=90,
        wedgeprops=dict(width=0.45),
    )
    ax.set_title("Due status distribution")
    return fig


def build_top_components_matplot(df: pd.DataFrame, *, top_n: int = 10):
    """Horizontal bar chart for most common components."""
    if df.empty or "part_name" not in df.columns:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "Component data unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    counts = (
        df.value_counts("part_name")
        .reset_index(name="components")
        .head(top_n)
        .sort_values("components", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(data=counts, x="components", y="part_name", color=_BLUE, ax=ax)
    ax.set_xlabel("Components")
    ax.set_ylabel("")
    ax.set_title(f"Top {top_n} components by count")
    fig.tight_layout()
    return fig


def build_due_timeline_matplot(df: pd.DataFrame):
    """Matplotlib line chart with rolling average for due-date timeline."""
    if df.empty or "due_date" not in df.columns:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Due timeline unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    timeline = (
        df.dropna(subset=["due_date"])
        .assign(period=lambda frame: frame["due_date"].dt.to_period("W").dt.to_timestamp())
        .groupby("period")
        .size()
        .rename("components")
        .reset_index()
    )
    if timeline.empty:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Due timeline unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    timeline["rolling"] = timeline["components"].rolling(4, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(timeline["period"], timeline["components"], color=_BLUE, alpha=0.4, label="Weekly")
    ax.plot(timeline["period"], timeline["rolling"], color=_GREEN, linewidth=2, label="4-week avg")
    ax.set_title("Upcoming due timeline")
    ax.set_xlabel("Due date (weekly)")
    ax.set_ylabel("Components due")
    ax.legend()
    fig.tight_layout()
    return fig


def build_part_aircraft_heatmap(df: pd.DataFrame, *, max_parts: int = 40, max_aircraft: int = 30) -> plt.Figure:
    """Color-coded heatmap where each cell reflects earliest due status for part vs aircraft."""

    required = {"part_name", "aircraft_registration", "days_until_due"}
    if df.empty or required - set(df.columns):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "Heatmap unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    pivot = df.pivot_table(
        index="part_name",
        columns="aircraft_registration",
        values="days_until_due",
        aggfunc="min",
    )
    if pivot.empty:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "Heatmap unavailable", ha="center", va="center")
        ax.axis("off")
        return fig

    row_order = pivot.notna().sum(axis=1).sort_values(ascending=False).index[:max_parts]
    col_order = pivot.notna().sum(axis=0).sort_values(ascending=False).index[:max_aircraft]
    pivot = pivot.loc[row_order, col_order]

    def classify(value: float) -> int:
        if pd.isna(value):
            return 0
        if value < 0:
            return 1
        if value <= 30:
            return 2
        if value <= 60:
            return 3
        return 4

    matrix = pivot.applymap(classify).astype(int)
    colors = ["#0f172a", "#ef4444", "#f97316", "#fde047", "#22c55e"]
    cmap = ListedColormap(colors)

    fig, ax = plt.subplots(figsize=(max(8, 0.3 * len(col_order)), max(6, 0.25 * len(row_order))))
    im = ax.imshow(matrix.values, cmap=cmap, vmin=-0.5, vmax=len(colors) - 0.5, aspect="auto")
    ax.set_xticks(range(len(col_order)))
    ax.set_xticklabels(col_order, rotation=45, ha="right")
    ax.set_yticks(range(len(row_order)))
    ax.set_yticklabels(row_order)
    ax.set_xlabel("Aircraft registration")
    ax.set_ylabel("Part name")
    ax.set_title("Part vs aircraft due status (earliest obligation)")

    cbar = fig.colorbar(
        ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-0.5, vmax=len(colors) - 0.5)),
        ticks=range(len(colors)),
        ax=ax,
    )
    cbar.ax.set_yticklabels(["Not applicable", "Overdue", "Due ≤ 30d", "Due ≤ 60d", "Due > 60d"])

    fig.tight_layout()
    return fig
