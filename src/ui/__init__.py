"""
UI Module
=========

Unified chart factory, reusable components, and consistent theming.
"""

from .chart_factory import ChartFactory, create_chart, CHART_THEME
from .components import (
    render_metric_card,
    render_portfolio_strip,
    render_risk_gauge,
    render_data_table
)

__all__ = [
    'ChartFactory',
    'create_chart',
    'CHART_THEME',
    'render_metric_card',
    'render_portfolio_strip',
    'render_risk_gauge',
    'render_data_table'
]
