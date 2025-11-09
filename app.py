"""Streamlit dashboard for the hard-time component analysis."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

from htc_management import DEFAULT_REPORT_PATH, load_report, prepare_component_dataframe
from htc_management.analytics import (
    build_summary,
    summary_to_frame,
    build_aircraft_breakdown,
    build_part_breakdown,
    build_due_bucket_breakdown,
    analyze_column_types,
    build_due_time_series,
    build_config_slot_due_scatter,
    build_config_slot_due_table,
)
from htc_management.analytics.visuals import (
    build_aircraft_due_chart,
    build_due_bucket_chart,
    build_part_exposure_chart,
    build_timeline_chart,
    build_due_time_series_chart,
    build_overdue_scatter_chart,
    create_days_distribution_plot,
)
from htc_management.reporting import export_excel_report, build_pdf_report, build_summary_pdf

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


SERIAL_COLUMN_CANDIDATES = (
    "serial_number",
    "Serial Number",
    "serial no / batch no",
    "Serial No / Batch No",
    "Serial",
)


def _serial_series(df: pd.DataFrame) -> pd.Series | None:
    for column in SERIAL_COLUMN_CANDIDATES:
        if column in df.columns:
            return df[column]
    return None


def _figure_to_pdf_bytes(fig):
    try:
        return pio.to_image(fig, format="pdf")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"PDF export unavailable for this chart: {exc}")
        return None


def _df_to_excel_bytes(df: pd.DataFrame, *, sheet_name: str = "Filtered") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:  # type: ignore[arg-type]
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer.seek(0)
    return buffer.getvalue()


def _build_summary_attachments(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    attachments: dict[str, pd.DataFrame] = {}

    days = pd.to_numeric(df.get("days_until_due"), errors="coerce")
    if days is not None and not days.empty:
        due_30 = df[(days >= 0) & (days <= 30)]
        if not due_30.empty:
            attachments["Due ≤ 30d"] = due_30
        due_90 = df[(days >= 0) & (days <= 90)]
        if not due_90.empty:
            attachments["Due ≤ 90d"] = due_90

    serial_series = _serial_series(df)
    if serial_series is not None:
        mask = serial_series.astype("string").str.contains("XXX", case=False, na=False)
        serial_subset = df[mask]
        if not serial_subset.empty:
            attachments["Serials with XXX"] = serial_subset

    return attachments


def _render_summary_table(summary_table: pd.DataFrame, df: pd.DataFrame) -> None:
    attachments = _build_summary_attachments(df)
    cohort_labels = [column for column in summary_table.columns if column != "Metric"]

    st.markdown("### Summary metrics")
    container = st.container()

    with container:
        header_html = "".join(
            f"<th style='padding:8px 12px;text-align:center;background:#f4f6f8;font-weight:600;color:#475467'>{label}</th>"
            for label in ["Metric", *cohort_labels, "Attachment"]
        )
        rows_html = []
        for _, row in summary_table.iterrows():
            metric = str(row["Metric"])
            cells = [f"<td style='padding:10px 12px;text-align:left;font-weight:600;color:#101828'>{metric}</td>"]
            for label in cohort_labels:
                cells.append(
                    f"<td style='padding:10px 12px;text-align:center;color:#344054'>{row[label]}</td>"
                )

            attachment_cell = "<td style='padding:10px 12px;text-align:center;color:#98a2b3'>—</td>"
            dataset = attachments.get(metric)
            if dataset is not None and not dataset.empty:
                key = metric.lower().replace("≤", "le").replace(" ", "_")
                bytes_payload = _df_to_excel_bytes(dataset, sheet_name=metric)
                download_button = st.download_button(
                    "Download XLSX",
                    data=bytes_payload,
                    file_name=f"{key}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"summary_attach_{key}",
                )
                attachment_cell = "<td style='padding:10px 12px;text-align:center;'></td>"
            rows_html.append(f"<tr>{''.join(cells)}{attachment_cell}</tr>")

        table_html = (
            "<table style='width:100%;border-collapse:collapse;border-radius:12px;overflow:hidden;"
            "box-shadow:0 10px 40px rgba(15,23,42,0.08);font-size:15px;'>"
            f"<thead style='background:#f8fafc'>{header_html}</thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table>"
        )
        st.markdown(table_html, unsafe_allow_html=True)


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

    summary_table = summary_to_frame(prepared, summary)
    _render_summary_table(summary_table, prepared)
    try:
        summary_pdf = build_summary_pdf(summary_table)
    except ImportError as exc:
        st.warning(str(exc))
    else:
        _download_bytes(
            summary_pdf,
            file_name="summary_metrics.pdf",
            mime="application/pdf",
            label="Download PDF summary",
            key="summary_pdf_dl",
        )

    st.subheader("Column type overview")
    st.dataframe(analyze_column_types(prepared), use_container_width=True, hide_index=True)

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

    st.subheader("Time-series trend (weekly)")
    ts_result = build_due_time_series(prepared)
    st.plotly_chart(build_due_time_series_chart(ts_result.frame), use_container_width=True)
    if ts_result.model_summary:
        if ts_result.slope is not None:
            st.caption(f"OLS slope: {ts_result.slope:.2f} components/week")
        with st.expander("Time-series regression details"):
            st.code(ts_result.model_summary)

    st.subheader("Overdue scatter diagnostics")
    scatter_fig, scatter_summary = build_overdue_scatter_chart(prepared)
    st.plotly_chart(scatter_fig, use_container_width=True)
    if scatter_summary:
        with st.expander("Overdue vs age OLS summary"):
            st.code(scatter_summary)

    st.subheader("Distribution of days until due")
    st.pyplot(create_days_distribution_plot(prepared), clear_figure=True)

    st.subheader("Config slot vs due date")
    config_slot_fig = build_config_slot_due_scatter(prepared)
    st.plotly_chart(config_slot_fig, use_container_width=True)
    pdf_bytes = _figure_to_pdf_bytes(config_slot_fig)
    if pdf_bytes:
        _download_bytes(
            pdf_bytes,
            file_name="config_slot_due_scatter.pdf",
            mime="application/pdf",
            label="Download config-slot plot (PDF)",
            key="config_slot_pdf",
        )
    slot_table = build_config_slot_due_table(prepared)
    st.dataframe(slot_table, use_container_width=True)
    if not slot_table.empty:
        st.download_button(
            "Download config-slot schedule (CSV)",
            slot_table.to_csv(index=False).encode("utf-8"),
            "config_slot_due_schedule.csv",
            "text/csv",
            use_container_width=True,
            key="config_slot_csv",
        )

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
