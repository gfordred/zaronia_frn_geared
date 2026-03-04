"""
UI Module
=========

Unified chart factory and reusable UI components.
"""

from .chart_factory import ChartFactory, CHART_THEME, create_chart
from .components import (
    render_metric_card,
    render_portfolio_strip,
    render_risk_gauge,
    render_data_table,
    render_section_header,
    render_alert,
    render_key_value_pairs,
    render_tabs_with_counts,
    render_filter_panel,
    render_download_button
)
from .balance_sheet_summary import (
    render_balance_sheet_summary,
    render_asset_liability_breakdown
)

__all__ = [
    'ChartFactory',
    'CHART_THEME',
    'create_chart',
    'render_metric_card',
    'render_portfolio_strip',
    'render_risk_gauge',
    'render_data_table',
    'render_section_header',
    'render_alert',
    'render_key_value_pairs',
    'render_tabs_with_counts',
    'render_filter_panel',
    'render_download_button',
    'render_balance_sheet_summary',
    'render_asset_liability_breakdown'
]
