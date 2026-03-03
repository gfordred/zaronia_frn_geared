"""
ZARONIA Analytics Module - Enhanced OIS Curve Analysis
Comprehensive ZARONIA (SA OIS) curve analytics using QuantLib best practices

Features:
- ZARONIA time-series with JIBAR comparison
- JIBAR-ZARONIA spread evolution
- ZARONIA OIS curve construction
- 3D surface plots for ZARONIA evolution
- Discount factor analysis
- Forward rate projections
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import QuantLib as ql


def render_zaronia_time_series(df_historical, df_zaronia, evaluation_date):
    """
    Render comprehensive ZARONIA time-series analysis
    
    QuantLib Best Practice:
    - ZARONIA is the SA overnight index swap (OIS) rate
    - Used for OIS curve construction and discounting
    - Spread to JIBAR reflects credit/liquidity premium
    """
    
    st.markdown("##### 📈 ZARONIA & JIBAR Time-Series Analysis")
    
    st.info("""
    **ZARONIA (ZAR Overnight Index Average):**
    - South African overnight index swap rate
    - Risk-free rate benchmark (no credit risk)
    - Used for OIS curve construction and discounting
    - Spread to JIBAR reflects credit/liquidity premium in money markets
    """)
    
    if df_historical is None or df_zaronia is None:
        st.warning("Historical data not available.")
        return
    
    # Merge datasets
    df_merged = df_historical.copy()
    df_merged = df_merged.join(df_zaronia[['ZARONIA']], how='left')
    
    # Calculate spread
    df_merged['JIBAR_ZARONIA_Spread'] = (df_merged['JIBAR3M'] - df_merged['ZARONIA']) * 100  # in bps
    
    # Date range selector
    col1, col2 = st.columns(2)
    
    lookback_options = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365,
        "2 Years": 730,
        "All History": None
    }
    
    with col1:
        lookback = st.selectbox("Lookback Period", list(lookback_options.keys()), index=3, key="zaronia_lookback")
    
    with col2:
        show_spread = st.checkbox("Show Spread Chart", value=True, key="show_zaronia_spread")
    
    # Filter data
    if lookback_options[lookback]:
        cutoff_date = pd.Timestamp(evaluation_date) - pd.Timedelta(days=lookback_options[lookback])
        df_plot = df_merged[df_merged.index >= cutoff_date].copy()
    else:
        df_plot = df_merged.copy()
    
    # Create comprehensive chart
    if show_spread:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('JIBAR 3M vs ZARONIA', 'JIBAR-ZARONIA Spread'),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
        # Panel 1: Rates
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=df_plot['JIBAR3M'],
                name='JIBAR 3M',
                line=dict(color='#00d4ff', width=2),
                mode='lines'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=df_plot['ZARONIA'],
                name='ZARONIA',
                line=dict(color='#00ff88', width=2),
                mode='lines'
            ),
            row=1, col=1
        )
        
        # Panel 2: Spread
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=df_plot['JIBAR_ZARONIA_Spread'],
                name='Spread (bps)',
                line=dict(color='#ffa500', width=3),
                fill='tozeroy',
                fillcolor='rgba(255, 165, 0, 0.2)'
            ),
            row=2, col=1
        )
        
        # Add mean line to spread
        mean_spread = df_plot['JIBAR_ZARONIA_Spread'].mean()
        fig.add_hline(
            y=mean_spread,
            line_dash="dash",
            line_color="white",
            opacity=0.5,
            annotation_text=f"Mean: {mean_spread:.1f} bps",
            annotation_position="right",
            row=2, col=1
        )
        
        fig.update_yaxes(title_text="Rate (%)", row=1, col=1)
        fig.update_yaxes(title_text="Spread (bps)", row=2, col=1)
        
        height = 700
    else:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_plot.index,
            y=df_plot['JIBAR3M'],
            name='JIBAR 3M',
            line=dict(color='#00d4ff', width=3),
            mode='lines'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_plot.index,
            y=df_plot['ZARONIA'],
            name='ZARONIA',
            line=dict(color='#00ff88', width=3),
            mode='lines'
        ))
        
        fig.update_yaxes(title_text="Rate (%)")
        height = 500
    
    fig.update_xaxes(title_text="Date")
    fig.update_layout(
        template='plotly_dark',
        hovermode='x unified',
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    st.markdown("###### Summary Statistics")
    
    current_jibar = df_plot['JIBAR3M'].iloc[-1] if not df_plot.empty else 0
    current_zaronia = df_plot['ZARONIA'].iloc[-1] if not df_plot.empty else 0
    current_spread = df_plot['JIBAR_ZARONIA_Spread'].iloc[-1] if not df_plot.empty else 0
    
    avg_spread = df_plot['JIBAR_ZARONIA_Spread'].mean()
    std_spread = df_plot['JIBAR_ZARONIA_Spread'].std()
    max_spread = df_plot['JIBAR_ZARONIA_Spread'].max()
    min_spread = df_plot['JIBAR_ZARONIA_Spread'].min()
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Current JIBAR 3M", f"{current_jibar:.3f}%")
    s2.metric("Current ZARONIA", f"{current_zaronia:.3f}%")
    s3.metric("Current Spread", f"{current_spread:.1f} bps")
    s4.metric("Avg Spread", f"{avg_spread:.1f} bps")
    
    s5, s6, s7, s8 = st.columns(4)
    s5.metric("Std Dev", f"{std_spread:.1f} bps")
    s6.metric("Max Spread", f"{max_spread:.1f} bps")
    s7.metric("Min Spread", f"{min_spread:.1f} bps")
    s8.metric("Range", f"{max_spread - min_spread:.1f} bps")


def render_zaronia_3d_surface(df_zaronia, evaluation_date):
    """
    Render 3D surface plot of ZARONIA evolution
    
    QuantLib Concept:
    - Shows term structure evolution over time
    - Z-axis: ZARONIA rate
    - Y-axis: Time (tenor)
    - X-axis: Historical dates
    """
    
    st.markdown("##### 🌐 ZARONIA 3D Surface Evolution")
    
    st.info("""
    **3D Surface Interpretation:**
    - **X-axis:** Historical dates (time progression)
    - **Y-axis:** Tenor (overnight to forward projections)
    - **Z-axis:** ZARONIA rate (%)
    - **Color:** Rate level (blue=low, red=high)
    
    This visualization shows how the ZARONIA term structure evolved over time.
    """)
    
    if df_zaronia is None or df_zaronia.empty:
        st.warning("ZARONIA data not available.")
        return
    
    # Lookback selector
    lookback_days = st.slider("Lookback Days", 30, 730, 180, key="zaronia_3d_lookback")
    
    end_date = pd.Timestamp(evaluation_date)
    start_date = end_date - pd.Timedelta(days=lookback_days)
    
    df_period = df_zaronia[(df_zaronia.index >= start_date) & (df_zaronia.index <= end_date)].copy()
    
    if df_period.empty:
        st.warning("No data for selected period.")
        return
    
    # Sample data to reduce points
    sample_freq = max(1, len(df_period) // 100)
    df_sampled = df_period.iloc[::sample_freq]
    
    # Create synthetic term structure (ZARONIA is overnight, project forward)
    tenors = [0, 0.25, 0.5, 1, 2, 3, 5, 10]  # in years
    
    # Build surface data
    dates_numeric = [(d - df_sampled.index.min()).days for d in df_sampled.index]
    
    Z = []
    for _, row in df_sampled.iterrows():
        zaronia_spot = row['ZARONIA']
        # Simple forward projection (flat for demonstration)
        rates = [zaronia_spot] * len(tenors)
        Z.append(rates)
    
    Z = np.array(Z).T
    
    # Create 3D surface
    fig = go.Figure(data=[go.Surface(
        x=dates_numeric,
        y=tenors,
        z=Z,
        colorscale='Viridis',
        colorbar=dict(title="Rate (%)", x=1.1)
    )])
    
    fig.update_layout(
        title='ZARONIA Term Structure Evolution (3D Surface)',
        scene=dict(
            xaxis_title='Days from Start',
            yaxis_title='Tenor (Years)',
            zaxis_title='ZARONIA Rate (%)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
        ),
        template='plotly_dark',
        height=700
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_zaronia_ois_curve_analysis(jibar_curve, zaronia_curve, settlement, day_count, zaronia_spread_bps):
    """
    Render ZARONIA OIS curve analysis
    
    QuantLib Best Practice:
    - ZARONIA curve built using daily bootstrapping
    - Each day: ZARONIA rate = JIBAR overnight forward - spread
    - Discount factors derived from compounded overnight rates
    - Used for risk-free discounting in derivatives
    """
    
    st.markdown("##### 📊 ZARONIA OIS Curve Analysis")
    
    st.info("""
    **ZARONIA OIS Curve Construction (QuantLib):**
    
    1. **Daily Bootstrapping:** Build curve day-by-day from overnight rates
    2. **Forward Calculation:** ZARONIA = JIBAR overnight forward - spread
    3. **Compounding:** Discount factors from compounded overnight rates
    4. **Usage:** Risk-free discounting for FRN valuation
    
    **Formula:**
    ```
    DF(t) = DF(t-1) / (1 + ZARONIA(t) × dt)
    ```
    
    Where dt = day count fraction (ACT/365)
    """)
    
    # Calculate curve points
    tenors_years = [0.25, 0.5, 1, 2, 3, 5, 7, 10]
    
    curve_data = []
    
    for tenor_years in tenors_years:
        maturity = settlement + ql.Period(int(tenor_years * 12), ql.Months)
        
        # JIBAR zero rate
        jibar_zero = jibar_curve.zeroRate(maturity, day_count, ql.Compounded, ql.Annual).rate() * 100
        
        # ZARONIA zero rate
        zaronia_zero = zaronia_curve.zeroRate(maturity, day_count, ql.Compounded, ql.Annual).rate() * 100
        
        # Discount factors
        jibar_df = jibar_curve.discount(maturity)
        zaronia_df = zaronia_curve.discount(maturity)
        
        # Spread
        spread = (jibar_zero - zaronia_zero) * 100  # in bps
        
        curve_data.append({
            'Tenor': f'{tenor_years}Y',
            'JIBAR Zero (%)': jibar_zero,
            'ZARONIA Zero (%)': zaronia_zero,
            'Spread (bps)': spread,
            'JIBAR DF': jibar_df,
            'ZARONIA DF': zaronia_df,
            'DF Ratio': zaronia_df / jibar_df if jibar_df > 0 else 1.0
        })
    
    df_curve = pd.DataFrame(curve_data)
    
    # Display table
    st.markdown("###### ZARONIA vs JIBAR Curve Comparison")
    
    st.dataframe(df_curve.style.format({
        'JIBAR Zero (%)': '{:.4f}',
        'ZARONIA Zero (%)': '{:.4f}',
        'Spread (bps)': '{:.2f}',
        'JIBAR DF': '{:.6f}',
        'ZARONIA DF': '{:.6f}',
        'DF Ratio': '{:.6f}'
    }).background_gradient(subset=['Spread (bps)'], cmap='RdYlGn_r'),
    use_container_width=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Zero rates comparison
        fig_zero = go.Figure()
        
        fig_zero.add_trace(go.Scatter(
            x=df_curve['Tenor'],
            y=df_curve['JIBAR Zero (%)'],
            name='JIBAR Zero',
            mode='lines+markers',
            line=dict(color='#00d4ff', width=3),
            marker=dict(size=10)
        ))
        
        fig_zero.add_trace(go.Scatter(
            x=df_curve['Tenor'],
            y=df_curve['ZARONIA Zero (%)'],
            name='ZARONIA Zero',
            mode='lines+markers',
            line=dict(color='#00ff88', width=3),
            marker=dict(size=10)
        ))
        
        fig_zero.update_layout(
            title='Zero Rate Curves',
            xaxis_title='Tenor',
            yaxis_title='Zero Rate (%)',
            template='plotly_dark',
            height=400
        )
        
        st.plotly_chart(fig_zero, use_container_width=True)
    
    with col2:
        # Discount factors
        fig_df = go.Figure()
        
        fig_df.add_trace(go.Scatter(
            x=df_curve['Tenor'],
            y=df_curve['JIBAR DF'],
            name='JIBAR DF',
            mode='lines+markers',
            line=dict(color='#00d4ff', width=3),
            marker=dict(size=10)
        ))
        
        fig_df.add_trace(go.Scatter(
            x=df_curve['Tenor'],
            y=df_curve['ZARONIA DF'],
            name='ZARONIA DF',
            mode='lines+markers',
            line=dict(color='#00ff88', width=3),
            marker=dict(size=10)
        ))
        
        fig_df.update_layout(
            title='Discount Factor Curves',
            xaxis_title='Tenor',
            yaxis_title='Discount Factor',
            template='plotly_dark',
            height=400
        )
        
        st.plotly_chart(fig_df, use_container_width=True)
    
    # Spread chart
    st.markdown("###### JIBAR-ZARONIA Spread by Tenor")
    
    fig_spread = go.Figure()
    
    fig_spread.add_trace(go.Bar(
        x=df_curve['Tenor'],
        y=df_curve['Spread (bps)'],
        marker_color='#ffa500',
        text=df_curve['Spread (bps)'].apply(lambda x: f'{x:.1f}'),
        textposition='outside'
    ))
    
    # Add input spread reference line
    fig_spread.add_hline(
        y=zaronia_spread_bps,
        line_dash="dash",
        line_color="white",
        opacity=0.7,
        annotation_text=f"Input Spread: {zaronia_spread_bps:.1f} bps",
        annotation_position="right"
    )
    
    fig_spread.update_layout(
        title='JIBAR-ZARONIA Spread Term Structure',
        xaxis_title='Tenor',
        yaxis_title='Spread (bps)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig_spread, use_container_width=True)
    
    # Key insights
    st.markdown("###### Key Insights")
    
    avg_spread = df_curve['Spread (bps)'].mean()
    spread_slope = df_curve['Spread (bps)'].iloc[-1] - df_curve['Spread (bps)'].iloc[0]
    
    i1, i2, i3 = st.columns(3)
    i1.metric("Average Spread", f"{avg_spread:.2f} bps")
    i2.metric("Spread Slope (10Y - 3M)", f"{spread_slope:+.2f} bps")
    i3.metric("Input Spread", f"{zaronia_spread_bps:.1f} bps")
    
    if abs(spread_slope) < 1:
        shape = "**Flat** - Spread consistent across tenors"
    elif spread_slope > 0:
        shape = "**Upward Sloping** - Spread widens with maturity"
    else:
        shape = "**Downward Sloping** - Spread tightens with maturity"
    
    st.info(f"**Spread Curve Shape:** {shape}")
