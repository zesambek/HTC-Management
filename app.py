"""Streamlit dashboard for the hard-time component analysis."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from htc_management import DEFAULT_REPORT_PATH, load_report, prepare_component_dataframe
from htc_management.analytics import (
    build_summary,
    summary_to_frame,
    build_aircraft_breakdown,
    build_part_breakdown,
    build_due_bucket_breakdown,
)
from htc_management.analytics.visuals import (
    build_aircraft_due_chart,
    build_due_bucket_chart,
    build_part_exposure_chart,
    build_timeline_chart,
)
from htc_management.reporting import export_excel_report, build_pdf_report

st.set_page_config(page_title="Hard-Time Component Analytics", layout="wide")
st.title("🛠️ Hard-Time Component Analytics")


@st.cache_data(show_spinner=False)
def _load_workbook(path: str | Path, sheet: str | int | None) -> pd.DataFrame:
    return load_report(path, sheet_name=sheet)


def _download_bytes(data: bytes, *, file_name: str, mime: str, label: str, key: str) -> None:
    st.download_button(
        label,
        data=data,
        file_name=file_name,
        mime=mime,
        use_container_width=True,
        key=key,
    )


def main() -> None:
    with st.sidebar:
        st.header("Data source")
        default_path = DEFAULT_REPORT_PATH
        st.caption(f"Default workbook: `{default_path.name}`")
        uploaded = st.file_uploader("Upload XLS workbook", type=["xls", "xlsx"])
        sheet_name = st.text_input("Sheet name (optional)")
        if uploaded is not None:
            data = pd.read_excel(uploaded, sheet_name=sheet_name or 0)
        else:
            data = _load_workbook(default_path, sheet=sheet_name or 0)

    st.subheader("Raw data (preview)")
    st.dataframe(data.head(200), use_container_width=True)

    prepared = prepare_component_dataframe(data)
    summary = build_summary(prepared)

    st.subheader("Summary metrics")
    st.dataframe(summary_to_frame(summary), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(build_aircraft_due_chart(prepared), use_container_width=True)
    with col2:
        st.plotly_chart(build_due_bucket_chart(prepared), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(build_part_exposure_chart(prepared), use_container_width=True)
    with col4:
        st.plotly_chart(build_timeline_chart(prepared), use_container_width=True)

    st.subheader("Tabular breakdowns")
    tabs = st.tabs(["Aircraft", "Components", "Due buckets"])
    with tabs[0]:
        st.dataframe(build_aircraft_breakdown(prepared), use_container_width=True)
    with tabs[1]:
        st.dataframe(build_part_breakdown(prepared), use_container_width=True)
    with tabs[2]:
        st.dataframe(build_due_bucket_breakdown(prepared), use_container_width=True)

    st.subheader("Downloads")
    excel_bytes = export_excel_report(prepared, summary)
    _download_bytes(
        excel_bytes,
        file_name="hard_time_analytics.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        label="📊 Download Excel workbook",
        key="download_excel",
    )

    try:
        pdf_bytes = build_pdf_report(prepared, summary)
    except ImportError as exc:
        st.warning(str(exc))
    else:
        _download_bytes(
            pdf_bytes,
            file_name="hard_time_analytics.pdf",
            mime="application/pdf",
            label="📄 Download PDF summary",
            key="download_pdf",
        )


if __name__ == "__main__":
    main()
