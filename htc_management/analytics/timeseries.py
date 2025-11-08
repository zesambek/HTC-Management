"""Time-series utilities for component due dates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(slots=True)
class TimeSeriesResult:
    frame: pd.DataFrame
    model_summary: str | None
    slope: float | None


def build_due_time_series(df: pd.DataFrame, freq: str = "W") -> TimeSeriesResult:
    """Return a resampled time series of due-date counts plus a trend estimate via OLS."""
    if df.empty or "due_date" not in df.columns:
        empty = pd.DataFrame(columns=["period", "due_count", "trend"])
        return TimeSeriesResult(frame=empty, model_summary=None, slope=None)

    indexed = df.dropna(subset=["due_date"]).copy()
    if indexed.empty:
        empty = pd.DataFrame(columns=["period", "due_count", "trend"])
        return TimeSeriesResult(frame=empty, model_summary=None, slope=None)

    indexed["due_date"] = pd.to_datetime(indexed["due_date"]).dt.tz_localize(None)
    indexed = indexed.set_index("due_date").sort_index()

    counts = (
        indexed.resample(freq)
        .size()
        .rename("due_count")
        .to_frame()
    )

    if counts.empty:
        empty = pd.DataFrame(columns=["period", "due_count", "trend"])
        return TimeSeriesResult(frame=empty, model_summary=None, slope=None)

    counts = counts.reset_index().rename(columns={"due_date": "period"})

    model_summary = None
    slope = None
    counts["trend"] = np.nan
    if len(counts) >= 3:
        x = np.arange(len(counts))
        X = sm.add_constant(x)
        model = sm.OLS(counts["due_count"], X).fit()
        counts["trend"] = model.predict(X)
        model_summary = model.summary().as_text()
        slope = float(model.params.iloc[1]) if len(model.params) > 1 else None

    return TimeSeriesResult(frame=counts, model_summary=model_summary, slope=slope)
