"""Analytics helpers for the hard-time component report."""

from .preparation import prepare_component_dataframe
from .summaries import ComponentSummary, build_summary, summary_to_frame
from .breakdowns import build_aircraft_breakdown, build_part_breakdown, build_due_bucket_breakdown
from .visuals import (
    build_due_bucket_chart,
    build_aircraft_due_chart,
    build_part_exposure_chart,
    build_timeline_chart,
    build_due_time_series_chart,
    build_overdue_scatter_chart,
    build_config_slot_due_scatter,
    create_days_distribution_plot,
)
from .profiling import analyze_column_types
from .timeseries import build_due_time_series

__all__ = [
    "prepare_component_dataframe",
    "ComponentSummary",
    "build_summary",
    "summary_to_frame",
    "build_aircraft_breakdown",
    "build_part_breakdown",
    "build_due_bucket_breakdown",
    "build_due_bucket_chart",
    "build_aircraft_due_chart",
    "build_part_exposure_chart",
    "build_timeline_chart",
    "build_due_time_series_chart",
    "build_overdue_scatter_chart",
    "build_config_slot_due_scatter",
    "create_days_distribution_plot",
    "analyze_column_types",
    "build_due_time_series",
]
