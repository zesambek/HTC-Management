"""Data preparation logic for the hard-time component report."""

from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd

_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")
_MULTI_UNDERSCORE = re.compile(r"_+")
_REGISTRATION_PATTERN = re.compile(r"\b[A-Z]{2}-[A-Z0-9]{2,}\b")

COLUMN_ALIASES = {
    "part_name": "part_name",
    "oem_part_no": "oem_part_number",
    "oem_part_number": "oem_part_number",
    "serial_no_batch_no": "serial_number",
    "serial_number": "serial_number",
    "installed_on": "installation_site",
    "config_slot": "config_slot",
    "config_slot_definition": "config_slot",
    "due_date": "due_date",
    "task": "task_code",
    "task_code": "task_code",
    "position": "position",
    "aircraft": "installation_site",
    "aircraft_description": "installation_site",
    "due": "due_date",
    "due_dt": "due_date",
    "due_dt_local": "due_date",
    "due_dt_utc": "due_date",
}

DATE_COLUMN_HINT = "date"


def _canonicalise(column: str) -> str:
    """Convert column headers to snake_case strings."""
    clean = _NON_ALNUM.sub("_", column.strip().lower())
    clean = _MULTI_UNDERSCORE.sub("_", clean).strip("_")
    return clean


def _build_rename_map(columns: Iterable[str]) -> dict[str, str]:
    rename_map: dict[str, str] = {}
    for column in columns:
        canonical = _canonicalise(column)
        target = COLUMN_ALIASES.get(canonical, canonical)
        rename_map[column] = target
    return rename_map


def _parse_datetime(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if pd.api.types.is_datetime64tz_dtype(parsed):
        parsed = parsed.dt.tz_convert(None)
    return parsed


def _extract_registration(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    match = _REGISTRATION_PATTERN.search(str(value))
    return match.group(0) if match else ""


def _extract_aircraft_type(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value)
    if " - " in text:
        prefix = text.split(" - ", 1)[0]
        return prefix.strip()
    return ""


def _compute_due_bucket(days_until_due: float) -> str:
    if pd.isna(days_until_due):
        return "Unknown"
    if days_until_due < 0:
        return "Overdue"
    if days_until_due <= 7:
        return "Due ≤ 7d"
    if days_until_due <= 30:
        return "Due ≤ 30d"
    if days_until_due <= 90:
        return "Due ≤ 90d"
    return "Due > 90d"


def prepare_component_dataframe(df: pd.DataFrame, *, reference_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Return a normalized copy of the hard-time report ready for analytics.

    The function standardises column names, parses date columns, and adds derived metrics:
      * ``days_until_due`` and ``days_overdue``
      * ``is_overdue`` boolean flag
      * ``due_bucket`` categorical label
      * ``aircraft_registration`` and ``aircraft_type`` inferred from the installation site string
    """

    if df.empty:
        return df.copy()

    rename_map = _build_rename_map(df.columns)
    working = df.rename(columns=rename_map).copy()

    reference_date = reference_date or pd.Timestamp.utcnow().tz_localize(None).normalize()

    for column in working.columns:
        if DATE_COLUMN_HINT in column and working[column].dtype != "datetime64[ns]":
            working[column] = _parse_datetime(working[column])

    if "due_date" not in working.columns:
        working["due_date"] = pd.NaT
    else:
        working["due_date"] = _parse_datetime(working["due_date"])
        working = working.dropna(subset=["due_date"])

    due_delta = (working["due_date"] - reference_date).dt.total_seconds() / 86400.0
    working["days_until_due"] = due_delta
    working["is_overdue"] = due_delta < 0
    working["days_overdue"] = np.where(working["is_overdue"], -due_delta, 0.0)

    site_source = working.get("installation_site")
    if site_source is None:
        site_source = pd.Series([""] * len(working), index=working.index, dtype="string")

    working["aircraft_registration"] = site_source.apply(_extract_registration).astype("string")
    working["aircraft_type"] = site_source.apply(_extract_aircraft_type).astype("string")

    # fall back to config slot / position for missing registrations
    missing_mask = working["aircraft_registration"] == ""
    if missing_mask.any():
        config_series = (
            working["config_slot"]
            if "config_slot" in working
            else pd.Series([""] * len(working), index=working.index, dtype="string")
        )
        position_series = (
            working["position"]
            if "position" in working
            else pd.Series([""] * len(working), index=working.index, dtype="string")
        )
        fallback = config_series.astype("string").where(~missing_mask, position_series.astype("string"))
        working.loc[missing_mask, "aircraft_registration"] = fallback.loc[missing_mask].apply(_extract_registration)

    working["due_bucket"] = working["days_until_due"].apply(_compute_due_bucket).astype("string")

    return working
