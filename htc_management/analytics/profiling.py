"""Column type analysis and dataframe diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ColumnTypeProfile:
    column: str
    pandas_dtype: str
    inferred_type: str
    non_null_pct: float
    numeric_compat_pct: float
    unique_ratio: float
    sample_values: str


def analyze_column_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a dataframe describing the schema/dtype characteristics of each column.

    Metrics included:
    - pandas dtype + inferred dtype
    - percentage of non-null rows
    - percentage of values that can be coerced to numeric
    - uniqueness ratio (unique / total)
    - sample values (first three non-null values)
    """

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Column",
                "Pandas dtype",
                "Inferred type",
                "Non-null %",
                "Numeric-compatible %",
                "Unique ratio",
                "Sample",
            ]
        )

    profiles: List[ColumnTypeProfile] = []
    total_rows = max(len(df), 1)
    for column in df.columns:
        series = df[column]
        pandas_dtype = str(series.dtype)
        inferred = pd.api.types.infer_dtype(series, skipna=True)

        non_null_pct = float(series.notna().mean() * 100.0)

        numeric_values = pd.to_numeric(series, errors="coerce")
        numeric_pct = float(numeric_values.notna().mean() * 100.0)

        unique_ratio = float(series.nunique(dropna=True) / total_rows) if total_rows else 0.0

        sample_values = ", ".join(series.dropna().astype(str).head(3).tolist())

        profiles.append(
            ColumnTypeProfile(
                column=str(column),
                pandas_dtype=pandas_dtype,
                inferred_type=inferred,
                non_null_pct=round(non_null_pct, 2),
                numeric_compat_pct=round(numeric_pct, 2),
                unique_ratio=round(unique_ratio, 3),
                sample_values=sample_values,
            )
        )

    return pd.DataFrame(
        {
            "Column": [profile.column for profile in profiles],
            "Pandas dtype": [profile.pandas_dtype for profile in profiles],
            "Inferred type": [profile.inferred_type for profile in profiles],
            "Non-null %": [profile.non_null_pct for profile in profiles],
            "Numeric-compatible %": [profile.numeric_compat_pct for profile in profiles],
            "Unique ratio": [profile.unique_ratio for profile in profiles],
            "Sample": [profile.sample_values for profile in profiles],
        }
    )
