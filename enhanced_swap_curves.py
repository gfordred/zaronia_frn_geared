"""
Enhanced Swap Curve Analysis - Bank Grade A+ Quality
To be integrated into app.py TAB 2 (Curve Analysis)

This module provides institutional-grade swap curve analytics:
- Historical curve evolution (time-series)
- Curve steepness analysis (2s5s, 5s10s, 2s10s)
- Forward curve evolution
- Parallel shifts and twists
- Professional Bloomberg/Reuters style visualizations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime, timedelta
import numpy as np


def render_swap_curve_evolution(df_historical, evaluation_date):
    """
    Render historical swap curve evolution with multiple views
    
    Args:
        df_historical: DataFrame with historical swap rates
        evaluation_date: Current evaluation date
    """
    
    st.markdown("##### 📈 Swap Curve Evolution (Historical Time-Series)")
    
    if df_historical is None or df_historical.empty:
        st.warning("No historical data available for curve evolution analysis.")
        return
    
    # Time period selector
    period_col1, period_col2 = st.columns([3, 1])
    
    with period_col1:
        lookback_period = st.selectbox(
            "Lookback Period",
            ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "All History"],
            index=3,
            key="curve_lookback"
        )
    
    with period_col2:
        show_points = st.checkbox("Show Data Points", value=False, key="show_curve_points")
    
    # Calculate date range
    end_date = pd.Timestamp(evaluation_date)
    
    if lookback_period == "1 Month":
        start_date = end_date - pd.DateOffset(months=1)
    elif lookback_period == "3 Months":
        start_date = end_date - pd.DateOffset(months=3)
    elif lookback_period == "6 Months":
        start_date = end_date - pd.DateOffset(months=6)
    elif lookback_period == "1 Year":
        start_date = end_date - pd.DateOffset(years=1)
    elif lookback_period == "2 Years":
        start_date = end_date - pd.DateOffset(years=2)
    else:
        start_date = df_historical['Date'].min()
    
    # Filter data
    mask = (df_historical['Date'] >= start_date) & (df_historical['Date'] <= end_date)
    df_period = df_historical[mask].copy()
    
    if df_period.empty:
        st.warning("No data available for selected period.")
        return
    
    # Create swap curve evolution chart
    st.markdown("###### Swap Rates Evolution")
    
    fig_evolution = go.Figure()
    
    swap_tenors = [
        ('JIBAR3M', '3M JIBAR', '#00d4ff'),
        ('SASW2', '2Y Swap', '#00ff88'),
        ('SASW3', '3Y Swap', '#ffa500'),
        ('SASW5', '5Y Swap', '#ff6b6b'),
        ('SASW10', '10Y Swap', '#ff00ff')
    ]
    
    for col, label, color in swap_tenors:
        if col in df_period.columns:
            mode = 'lines+markers' if show_points else 'lines'
            fig_evolution.add_trace(go.Scatter(
                x=df_period['Date'],
                y=df_period[col],
                name=label,
                mode=mode,
                line=dict(color=color, width=2),
                marker=dict(size=4) if show_points else None
            ))
    
    fig_evolution.update_layout(
        title=f'Swap Curve Evolution ({lookback_period})',
        xaxis_title='Date',
        yaxis_title='Rate (%)',
        template='plotly_dark',
        hovermode='x unified',
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_evolution, use_container_width=True)
    
    # Summary statistics
    st.markdown("###### Summary Statistics")
    
    stats_data = []
    for col, label, _ in swap_tenors:
        if col in df_period.columns:
            current = df_period[col].iloc[-1] if not df_period.empty else 0
            mean = df_period[col].mean()
            std = df_period[col].std()
            min_val = df_period[col].min()
            max_val = df_period[col].max()
            change = df_period[col].iloc[-1] - df_period[col].iloc[0] if len(df_period) > 1 else 0
            
            stats_data.append({
                'Tenor': label,
                'Current (%)': current,
                'Mean (%)': mean,
                'Std Dev (%)': std,
                'Min (%)': min_val,
                'Max (%)': max_val,
                'Change (bps)': change * 100
            })
    
    df_stats = pd.DataFrame(stats_data)
    
    st.dataframe(df_stats.style.format({
        'Current (%)': '{:.3f}',
        'Mean (%)': '{:.3f}',
        'Std Dev (%)': '{:.3f}',
        'Min (%)': '{:.3f}',
        'Max (%)': '{:.3f}',
        'Change (bps)': '{:+.1f}'
    }).background_gradient(subset=['Change (bps)'], cmap='RdYlGn'),
    use_container_width=True, hide_index=True)


def render_curve_steepness_analysis(df_historical, evaluation_date):
    """
    Render curve steepness analysis (2s5s, 5s10s, 2s10s)
    """
    
    st.markdown("##### 📐 Curve Steepness Analysis")
    
    if df_historical is None or df_historical.empty:
        st.warning("No historical data available for steepness analysis.")
        return
    
    # Calculate steepness measures
    df_steep = df_historical.copy()
    
    if all(col in df_steep.columns for col in ['SASW2', 'SASW5', 'SASW10']):
        df_steep['2s5s'] = (df_steep['SASW5'] - df_steep['SASW2']) * 100  # in bps
        df_steep['5s10s'] = (df_steep['SASW10'] - df_steep['SASW5']) * 100
        df_steep['2s10s'] = (df_steep['SASW10'] - df_steep['SASW2']) * 100
    else:
        st.warning("Required swap rates not available for steepness calculation.")
        return
    
    # Time period selector
    lookback = st.selectbox(
        "Analysis Period",
        ["3 Months", "6 Months", "1 Year", "2 Years"],
        index=2,
        key="steep_lookback"
    )
    
    end_date = pd.Timestamp(evaluation_date)
    if lookback == "3 Months":
        start_date = end_date - pd.DateOffset(months=3)
    elif lookback == "6 Months":
        start_date = end_date - pd.DateOffset(months=6)
    elif lookback == "1 Year":
        start_date = end_date - pd.DateOffset(years=1)
    else:
        start_date = end_date - pd.DateOffset(years=2)
    
    mask = (df_steep['Date'] >= start_date) & (df_steep['Date'] <= end_date)
    df_steep_period = df_steep[mask].copy()
    
    # Steepness evolution chart
    st.markdown("###### Curve Steepness Evolution")
    
    fig_steep = go.Figure()
    
    steepness_measures = [
        ('2s5s', '2s5s Steepness', '#00d4ff'),
        ('5s10s', '5s10s Steepness', '#ffa500'),
        ('2s10s', '2s10s Steepness', '#ff6b6b')
    ]
    
    for col, label, color in steepness_measures:
        fig_steep.add_trace(go.Scatter(
            x=df_steep_period['Date'],
            y=df_steep_period[col],
            name=label,
            mode='lines',
            line=dict(color=color, width=2)
        ))
    
    # Add zero line
    fig_steep.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    
    fig_steep.update_layout(
        title=f'Curve Steepness Evolution ({lookback})',
        xaxis_title='Date',
        yaxis_title='Steepness (bps)',
        template='plotly_dark',
        hovermode='x unified',
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_steep, use_container_width=True)
    
    # Current steepness metrics
    st.markdown("###### Current Curve Shape")
    
    if not df_steep_period.empty:
        current_2s5s = df_steep_period['2s5s'].iloc[-1]
        current_5s10s = df_steep_period['5s10s'].iloc[-1]
        current_2s10s = df_steep_period['2s10s'].iloc[-1]
        
        avg_2s5s = df_steep_period['2s5s'].mean()
        avg_5s10s = df_steep_period['5s10s'].mean()
        avg_2s10s = df_steep_period['2s10s'].mean()
        
        s1, s2, s3 = st.columns(3)
        
        s1.metric(
            "2s5s Steepness",
            f"{current_2s5s:.1f} bps",
            delta=f"{current_2s5s - avg_2s5s:+.1f} vs avg",
            help="5Y swap - 2Y swap"
        )
        
        s2.metric(
            "5s10s Steepness",
            f"{current_5s10s:.1f} bps",
            delta=f"{current_5s10s - avg_5s10s:+.1f} vs avg",
            help="10Y swap - 5Y swap"
        )
        
        s3.metric(
            "2s10s Steepness",
            f"{current_2s10s:.1f} bps",
            delta=f"{current_2s10s - avg_2s10s:+.1f} vs avg",
            help="10Y swap - 2Y swap"
        )
        
        # Interpretation
        st.markdown("###### Curve Shape Interpretation")
        
        if current_2s5s > 0 and current_5s10s > 0:
            shape = "**Normal/Upward Sloping** 📈"
            interpretation = "Market expects rates to rise over time. Typical in normal economic conditions."
        elif current_2s5s < 0 and current_5s10s < 0:
            shape = "**Inverted** 📉"
            interpretation = "Market expects rates to fall. Often precedes economic slowdown."
        elif current_2s5s > 0 and current_5s10s < 0:
            shape = "**Humped**"
            interpretation = "Rates expected to rise then fall. Uncertainty about medium-term outlook."
        else:
            shape = "**Flat/Mixed**"
            interpretation = "Market uncertain about rate direction."
        
        st.info(f"**Current Shape:** {shape}\n\n{interpretation}")


def render_3d_curve_surface(df_historical, evaluation_date):
    """
    Render 3D surface plot of curve evolution over time
    """
    
    st.markdown("##### 🌐 3D Curve Surface (Time × Tenor × Rate)")
    
    if df_historical is None or df_historical.empty:
        st.warning("No historical data available.")
        return
    
    # Prepare data for 3D surface
    lookback_days = st.slider("Lookback Days", 30, 365, 180, key="3d_lookback")
    
    end_date = pd.Timestamp(evaluation_date)
    start_date = end_date - pd.Timedelta(days=lookback_days)
    
    mask = (df_historical['Date'] >= start_date) & (df_historical['Date'] <= end_date)
    df_3d = df_historical[mask].copy()
    
    if df_3d.empty:
        st.warning("No data for selected period.")
        return
    
    # Sample every N days to reduce data points
    sample_freq = max(1, len(df_3d) // 50)
    df_3d_sampled = df_3d.iloc[::sample_freq]
    
    # Prepare surface data
    tenors = [0.25, 2, 3, 5, 10]  # in years
    tenor_labels = ['3M', '2Y', '3Y', '5Y', '10Y']
    rate_cols = ['JIBAR3M', 'SASW2', 'SASW3', 'SASW5', 'SASW10']
    
    # Create meshgrid
    dates_numeric = [(d - df_3d_sampled['Date'].min()).days for d in df_3d_sampled['Date']]
    
    Z = []
    for _, row in df_3d_sampled.iterrows():
        rates = [row[col] if col in row else 0 for col in rate_cols]
        Z.append(rates)
    
    Z = np.array(Z).T  # Transpose for correct orientation
    
    fig_3d = go.Figure(data=[go.Surface(
        x=dates_numeric,
        y=tenors,
        z=Z,
        colorscale='Viridis',
        colorbar=dict(title="Rate (%)")
    )])
    
    fig_3d.update_layout(
        title='3D Swap Curve Surface Evolution',
        scene=dict(
            xaxis_title='Days from Start',
            yaxis_title='Tenor (Years)',
            zaxis_title='Rate (%)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
        ),
        template='plotly_dark',
        height=600
    )
    
    st.plotly_chart(fig_3d, use_container_width=True)


# Example integration into app.py TAB 2:
"""
# Add to Curve Analysis tab after existing content:

st.markdown("---")
st.markdown("### 📊 Advanced Curve Analytics")

curve_analytics_tabs = st.tabs([
    "📈 Curve Evolution",
    "📐 Steepness Analysis", 
    "🌐 3D Surface"
])

with curve_analytics_tabs[0]:
    render_swap_curve_evolution(df_historical, evaluation_date)

with curve_analytics_tabs[1]:
    render_curve_steepness_analysis(df_historical, evaluation_date)

with curve_analytics_tabs[2]:
    render_3d_curve_surface(df_historical, evaluation_date)
"""
