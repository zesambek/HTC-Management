"""Command-line entrypoint for generating analytics outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from htc_management import DEFAULT_REPORT_PATH, load_report, prepare_component_dataframe
from htc_management.analytics import build_summary
from htc_management.reporting import export_excel_report, build_pdf_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate analytics for the hard-time maintenance report.")
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to the raw XLS report (defaults to the repository sample).",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Worksheet name to load. Defaults to the first sheet.",
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=Path("hard_time_analytics.xlsx"),
        help="Destination path for the Excel analytics workbook.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("hard_time_analytics.pdf"),
        help="Destination path for the PDF summary report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_report(args.workbook, sheet_name=args.sheet)
    prepared = prepare_component_dataframe(df)
    summary = build_summary(prepared)

    export_excel_report(prepared, summary, path=args.excel)

    try:
        pdf_bytes = build_pdf_report(prepared, summary)
    except ImportError as exc:
        print(f"[WARN] PDF export skipped: {exc}")
    else:
        args.pdf.write_bytes(pdf_bytes)

    print(f"Analytics generated:\n - Excel: {args.excel}\n - PDF: {args.pdf if args.pdf.exists() else 'skipped'}")


if __name__ == "__main__":
    main()
