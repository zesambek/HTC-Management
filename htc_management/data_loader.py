"""Utilities for loading the hard-time component report."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

DEFAULT_REPORT_NAME = "HardTimeReport_New (2).xls"
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent.parent / DEFAULT_REPORT_NAME

_EXPECTED_HEADER_TOKENS = {
    "part name",
    "oem part no",
    "serial no / batch no",
    "serial number",
    "installed on",
    "config slot",
    "due_date",
    "due date",
    "task",
    "position",
}
_EMPTY_SENTINELS = {"", "none", "nan", "null", "na"}


def load_report(
    path: str | Path | None = None,
    *,
    sheet_name: str | int | None = 0,
    **read_excel_kwargs: Mapping[str, object],
) -> pd.DataFrame:
    """
    Read the maintenance report into a DataFrame.

    Parameters
    ----------
    path:
        Optional filesystem path. Defaults to the project-level workbook bundled with the repository.
    sheet_name:
        Worksheet to read. Mirrors ``pandas.read_excel``.
    read_excel_kwargs:
        Extra keyword arguments forwarded to ``pandas.read_excel``.

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    FileNotFoundError
        If the workbook path does not exist.
    ImportError
        When ``xlrd`` is not installed (required for legacy XLS files).
    """

    target = Path(path) if path is not None else DEFAULT_REPORT_PATH
    if not target.exists():
        raise FileNotFoundError(f"Workbook not found: {target}")

    try:
        frame = pd.read_excel(
            target,
            sheet_name=sheet_name,
            engine=read_excel_kwargs.pop("engine", "xlrd"),
            **read_excel_kwargs,
        )
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "Reading legacy .xls files requires the 'xlrd' package. "
            "Install it via `pip install xlrd` and retry."
        ) from exc

    return _clean_workbook_frame(frame)


def available_sheets(path: str | Path | None = None) -> Iterable[str]:
    """Return the worksheet names available in the report workbook."""
    target = Path(path) if path is not None else DEFAULT_REPORT_PATH
    if not target.exists():
        raise FileNotFoundError(f"Workbook not found: {target}")

    try:
        xls = pd.ExcelFile(target, engine="xlrd")
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "Inspecting legacy .xls files requires the 'xlrd' package. "
            "Install it via `pip install xlrd` and retry."
        ) from exc

    return xls.sheet_names


def _clean_workbook_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Repair common header issues (extra top rows / unnamed columns)."""
    if df.empty:
        return df

    df = _promote_header_row(df)
    df = df.dropna(axis=1, how="all")

    df.columns = _deduplicate_headers([str(col).strip() for col in df.columns])

    col_series = pd.Series(df.columns, dtype="string")
    unnamed_mask = col_series.str.lower().str.startswith("unnamed")
    noise_mask = col_series.str.contains("hardtime", case=False, na=False)
    df = df.loc[:, ~(unnamed_mask | noise_mask).values]

    df = df.loc[:, df.notna().any(axis=0)]
    return df.reset_index(drop=True)


def _promote_header_row(df: pd.DataFrame) -> pd.DataFrame:
    """Use the first data row as column headers when Jasper exports prepend metadata."""
    if df.empty:
        return df

    max_scan = min(len(df), 10)
    for idx in range(max_scan):
        row = df.iloc[idx]
        normalized = {
            str(value).strip().lower()
            for value in row
            if str(value).strip().lower() not in _EMPTY_SENTINELS
        }
        overlap = _EXPECTED_HEADER_TOKENS.intersection(normalized)
        if len(overlap) < 4:
            continue

        new_columns = _deduplicate_headers(
            [
                _safe_column_label(value, position=index)
                for index, value in enumerate(row)
            ]
        )
        cleaned = df.iloc[idx + 1 :].copy()
        cleaned.columns = new_columns
        cleaned.reset_index(drop=True, inplace=True)
        return cleaned

    return df.rename(columns=lambda c: str(c).strip())


def _safe_column_label(value: object, *, position: int) -> str:
    text = str(value).strip()
    if not text or text.lower() in _EMPTY_SENTINELS:
        return f"column_{position+1}"
    return text


def _deduplicate_headers(headers: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: dict[str, int] = {}
    for header in headers:
        candidate = header or "column"
        count = seen.get(candidate, 0) + 1
        seen[candidate] = count
        if count > 1:
            candidate = f"{candidate}_{count}"
        result.append(candidate)
    return result
