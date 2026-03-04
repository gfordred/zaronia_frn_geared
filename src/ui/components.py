"""
Reusable UI Components - CANONICAL
===================================

Consistent UI components for the trading platform.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, List, Any


def render_metric_card(label: str, value: str, 
                      delta: Optional[str] = None,
                      help_text: Optional[str] = None,
                      color: str = "primary"):
    """
    Render a metric card with consistent styling.
    
    Args:
        label: Metric label
        value: Metric value (formatted string)
        delta: Optional delta value
        help_text: Optional help tooltip
        color: Color scheme ('primary', 'success', 'warning', 'danger')
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text
    )


def render_portfolio_strip(portfolio_metrics: Dict[str, Any],
                          sticky: bool = True):
    """
    Render sticky portfolio summary strip at top of page.
    
    **CANONICAL PORTFOLIO STRIP**
    
    Args:
        portfolio_metrics: Dictionary with portfolio metrics
        sticky: Whether to make the strip sticky (CSS)
    """
    # Create container for sticky strip
    if sticky:
        st.markdown("""
        <style>
        .portfolio-strip {
            position: sticky;
            top: 0;
            z-index: 999;
            background: #0E1117;
            padding: 1rem 0;
            border-bottom: 2px solid #00D9FF;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="portfolio-strip">', unsafe_allow_html=True)
    
    # Display metrics in columns
    cols = st.columns(6)
    
    with cols[0]:
        st.metric(
            "Total MV",
            f"R{portfolio_metrics.get('total_mv', 0):,.0f}",
            help="Total market value of portfolio"
        )
    
    with cols[1]:
        st.metric(
            "DV01",
            f"R{portfolio_metrics.get('dv01', 0):,.0f}",
            help="Dollar value of 1bp parallel shift"
        )
    
    with cols[2]:
        st.metric(
            "CS01",
            f"R{portfolio_metrics.get('cs01', 0):,.0f}",
            help="Credit spread sensitivity"
        )
    
    with cols[3]:
        st.metric(
            "Gearing",
            f"{portfolio_metrics.get('gearing', 0):.2f}x",
            help="Repo outstanding / Portfolio notional"
        )
    
    with cols[4]:
        st.metric(
            "Net Yield",
            f"{portfolio_metrics.get('net_yield', 0):.2f}%",
            help="Net yield on equity"
        )
    
    with cols[5]:
        st.metric(
            "Positions",
            f"{portfolio_metrics.get('position_count', 0)}",
            help="Number of active positions"
        )
    
    if sticky:
        st.markdown('</div>', unsafe_allow_html=True)


def render_risk_gauge(value: float, limit: float, 
                     label: str, format_str: str = "R{:,.0f}"):
    """
    Render a risk gauge showing utilization vs limit.
    
    Args:
        value: Current value
        limit: Limit value
        label: Gauge label
        format_str: Format string for values
    """
    utilization = (value / limit * 100) if limit > 0 else 0
    
    # Color based on utilization
    if utilization < 70:
        color = "🟢"
    elif utilization < 90:
        color = "🟡"
    else:
        color = "🔴"
    
    st.markdown(f"**{color} {label}**")
    st.progress(min(utilization / 100, 1.0))
    st.caption(f"{format_str.format(value)} / {format_str.format(limit)} ({utilization:.1f}%)")


def render_data_table(df: pd.DataFrame, 
                     title: Optional[str] = None,
                     height: Optional[int] = None,
                     use_container_width: bool = True):
    """
    Render a data table with consistent styling.
    
    Args:
        df: DataFrame to display
        title: Optional table title
        height: Optional fixed height
        use_container_width: Whether to use full container width
    """
    if title:
        st.markdown(f"**{title}**")
    
    st.dataframe(
        df,
        height=height,
        use_container_width=use_container_width
    )


def render_section_header(title: str, subtitle: Optional[str] = None,
                         icon: Optional[str] = None):
    """
    Render a section header with consistent styling.
    
    Args:
        title: Section title
        subtitle: Optional subtitle
        icon: Optional emoji icon
    """
    header_text = f"{icon} {title}" if icon else title
    st.markdown(f"### {header_text}")
    
    if subtitle:
        st.caption(subtitle)
    
    st.markdown("---")


def render_alert(message: str, alert_type: str = "info"):
    """
    Render an alert message.
    
    Args:
        message: Alert message
        alert_type: Type of alert ('info', 'success', 'warning', 'error')
    """
    alert_methods = {
        'info': st.info,
        'success': st.success,
        'warning': st.warning,
        'error': st.error
    }
    
    method = alert_methods.get(alert_type, st.info)
    method(message)


def render_key_value_pairs(data: Dict[str, Any], columns: int = 2):
    """
    Render key-value pairs in a grid layout.
    
    Args:
        data: Dictionary of key-value pairs
        columns: Number of columns in grid
    """
    items = list(data.items())
    cols = st.columns(columns)
    
    for idx, (key, value) in enumerate(items):
        col_idx = idx % columns
        with cols[col_idx]:
            st.markdown(f"**{key}:** {value}")


def render_tabs_with_counts(tab_names: List[str], 
                           counts: Optional[List[int]] = None) -> List:
    """
    Render tabs with optional counts in labels.
    
    Args:
        tab_names: List of tab names
        counts: Optional list of counts for each tab
    
    Returns:
        List of tab objects
    """
    if counts:
        labels = [f"{name} ({count})" for name, count in zip(tab_names, counts)]
    else:
        labels = tab_names
    
    return st.tabs(labels)


def render_filter_panel(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render a filter panel with various filter types.
    
    Args:
        filters: Dictionary defining filters
            Example: {
                'counterparty': {'type': 'multiselect', 'options': [...], 'label': 'Counterparty'},
                'min_notional': {'type': 'number', 'min': 0, 'max': 1e9, 'label': 'Min Notional'}
            }
    
    Returns:
        Dictionary with selected filter values
    """
    st.markdown("**Filters**")
    
    selected_filters = {}
    
    for key, config in filters.items():
        filter_type = config.get('type')
        label = config.get('label', key)
        
        if filter_type == 'multiselect':
            selected_filters[key] = st.multiselect(
                label,
                options=config.get('options', []),
                default=config.get('default', [])
            )
        
        elif filter_type == 'selectbox':
            selected_filters[key] = st.selectbox(
                label,
                options=config.get('options', []),
                index=config.get('default', 0)
            )
        
        elif filter_type == 'number':
            selected_filters[key] = st.number_input(
                label,
                min_value=config.get('min', 0),
                max_value=config.get('max', 1e9),
                value=config.get('default', 0)
            )
        
        elif filter_type == 'date':
            selected_filters[key] = st.date_input(
                label,
                value=config.get('default')
            )
        
        elif filter_type == 'slider':
            selected_filters[key] = st.slider(
                label,
                min_value=config.get('min', 0),
                max_value=config.get('max', 100),
                value=config.get('default', 50)
            )
    
    return selected_filters


def render_download_button(data: Any, filename: str, 
                          label: str = "Download",
                          file_type: str = "csv"):
    """
    Render a download button for data export.
    
    Args:
        data: Data to download (DataFrame or string)
        filename: Filename for download
        label: Button label
        file_type: File type ('csv', 'json', 'excel')
    """
    if isinstance(data, pd.DataFrame):
        if file_type == 'csv':
            data_str = data.to_csv(index=False)
            mime = 'text/csv'
        elif file_type == 'json':
            data_str = data.to_json(orient='records')
            mime = 'application/json'
        elif file_type == 'excel':
            # For Excel, would need to use BytesIO
            data_str = data.to_csv(index=False)
            mime = 'text/csv'
            filename = filename.replace('.xlsx', '.csv')
    else:
        data_str = str(data)
        mime = 'text/plain'
    
    st.download_button(
        label=label,
        data=data_str,
        file_name=filename,
        mime=mime
    )
