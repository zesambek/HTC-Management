"""Utilities for loading the hard-time component report."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

DEFAULT_REPORT_NAME = "HardTimeReport_New (2).xls"
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent.parent / DEFAULT_REPORT_NAME


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
        return pd.read_excel(target, sheet_name=sheet_name, engine=read_excel_kwargs.pop("engine", "xlrd"), **read_excel_kwargs)
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "Reading legacy .xls files requires the 'xlrd' package. "
            "Install it via `pip install xlrd` and retry."
        ) from exc


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
