"""Export helpers for the hard-time component analytics."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, Tuple

import pandas as pd

from ..analytics.breakdowns import (
    build_aircraft_breakdown,
    build_part_breakdown,
    build_due_bucket_breakdown,
    build_config_slot_due_table,
)
from ..analytics.summaries import ComponentSummary, summary_to_frame

try:  # Optional dependency for PDF output
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _REPORTLAB_AVAILABLE = False


def export_excel_report(
    prepared_df: pd.DataFrame,
    summary: ComponentSummary,
    *,
    path: str | Path | None = None,
) -> bytes | Path:
    """
    Build an Excel workbook containing the enriched data and headline analytics.

    If ``path`` is provided, the workbook is written to disk and the path is returned.
    Otherwise the bytes object is returned for download workflows.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:  # type: ignore[arg-type]
        prepared_df.to_excel(writer, sheet_name="Components", index=False)
        summary_to_frame(summary).to_excel(writer, sheet_name="Summary", index=False)

        aircraft = build_aircraft_breakdown(prepared_df)
        if not aircraft.empty:
            aircraft.to_excel(writer, sheet_name="Aircraft Exposure", index=False)

        parts = build_part_breakdown(prepared_df)
        if not parts.empty:
            parts.to_excel(writer, sheet_name="Top Components", index=False)

        buckets = build_due_bucket_breakdown(prepared_df)
        if not buckets.empty:
            buckets.to_excel(writer, sheet_name="Due Buckets", index=False)

        config_slots = build_config_slot_due_table(prepared_df)
        if not config_slots.empty:
            config_slots.to_excel(writer, sheet_name="Config Slot Schedule", index=False)

    buffer.seek(0)
    if path is None:
        return buffer.getvalue()

    target = Path(path)
    target.write_bytes(buffer.read())
    return target


def build_pdf_report(prepared_df: pd.DataFrame, summary: ComponentSummary) -> bytes:
    """Create a lightweight PDF report summarising key metrics."""
    if not _REPORTLAB_AVAILABLE:  # pragma: no cover - optional dependency
        raise ImportError("ReportLab is required for PDF export. Install it via `pip install reportlab`.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    story = [Paragraph("Hard-Time Component Analytics", styles["Title"]), Spacer(1, 12)]

    summary_table = summary_to_frame(summary)
    story.extend(
        [
            Paragraph("Headline Metrics", styles["Heading2"]),
            _table(summary_table),
            Spacer(1, 12),
        ]
    )

    aircraft = build_aircraft_breakdown(prepared_df).head(15)
    if not aircraft.empty:
        story.extend([Paragraph("Aircraft Exposure", styles["Heading2"]), _table(aircraft), Spacer(1, 12)])

    parts = build_part_breakdown(prepared_df).head(15)
    if not parts.empty:
        story.extend([Paragraph("Top Components", styles["Heading2"]), _table(parts), Spacer(1, 12)])

    buckets = build_due_bucket_breakdown(prepared_df)
    if not buckets.empty:
        story.extend([Paragraph("Due Bucket Mix", styles["Heading2"]), _table(buckets), Spacer(1, 12)])

    config_slots = build_config_slot_due_table(prepared_df)
    if not config_slots.empty:
        story.extend([Paragraph("Config Slot Schedule", styles["Heading2"]), _table(config_slots.head(15)), Spacer(1, 12)])

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _table(df: pd.DataFrame) -> Table:
    values = [df.columns.tolist()] + df.astype(str).values.tolist()
    tbl = Table(values, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002b55")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    return tbl
