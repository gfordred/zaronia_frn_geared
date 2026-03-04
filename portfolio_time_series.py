"""
Professional Portfolio Time Series Analytics
Fast, robust daily valuation and composition tracking
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import numpy as np


def calculate_daily_portfolio_metrics(portfolio, repo_trades, start_date, end_date):
    """
    Calculate comprehensive daily portfolio metrics
    Optimized for speed with vectorized operations
    
    Returns:
        DataFrame with daily metrics
    """
    
    # Generate date range
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Pre-process positions and repos for fast lookup
    positions_df = pd.DataFrame(portfolio)
    positions_df['start_date'] = pd.to_datetime(positions_df['start_date'])
    positions_df['maturity'] = pd.to_datetime(positions_df['maturity'])
    
    repos_df = pd.DataFrame(repo_trades)
    repos_df['spot_date'] = pd.to_datetime(repos_df['spot_date'])
    repos_df['end_date'] = pd.to_datetime(repos_df['end_date'])
    
    # Calculate daily metrics
    daily_data = []
    
    for current_date in date_range:
        # Active positions
        active_positions = positions_df[
            (positions_df['start_date'] <= current_date) & 
            (positions_df['maturity'] >= current_date)
        ]
        
        # Active repos
        active_repos = repos_df[
            (repos_df['spot_date'] <= current_date) & 
            (repos_df['end_date'] >= current_date) &
            (repos_df['direction'] == 'borrow_cash')
        ]
        
        # Metrics
        total_notional = active_positions['notional'].sum() if len(active_positions) > 0 else 0
        total_repo = active_repos['cash_amount'].sum() if len(active_repos) > 0 else 0
        gearing = total_repo / total_notional if total_notional > 0 else 0
        
        # Composition by counterparty
        composition = {}
        if len(active_positions) > 0:
            for cpty in active_positions['counterparty'].unique():
                cpty_notional = active_positions[active_positions['counterparty'] == cpty]['notional'].sum()
                composition[cpty] = cpty_notional
        
        # Average spreads
        avg_frn_spread = active_positions['issue_spread'].mean() if len(active_positions) > 0 else 0
        avg_repo_spread = active_repos['repo_spread_bps'].mean() if len(active_repos) > 0 else 0
        
        daily_data.append({
            'Date': current_date.date(),
            'Total Notional': total_notional,
            'Total Repo': total_repo,
            'Gearing': gearing,
            'Num Positions': len(active_positions),
            'Num Repos': len(active_repos),
            'Avg FRN Spread': avg_frn_spread,
            'Avg Repo Spread': avg_repo_spread,
            'Spread Pickup': avg_frn_spread - avg_repo_spread,
            **{f'Notional_{cpty}': amt for cpty, amt in composition.items()}
        })
    
    return pd.DataFrame(daily_data)


def render_portfolio_time_series(portfolio, repo_trades):
    """
    Render comprehensive portfolio time series analytics
    Professional, robust, and fast
    """
    
    st.markdown("### 📊 Portfolio Time Series Analytics")
    
    st.info("""
    **Daily Portfolio Metrics:**
    - Portfolio notional and composition evolution
    - Gearing and leverage tracking
    - Spread dynamics over time
    - Counterparty exposure trends
    """)
    
    if not portfolio:
        st.warning("No portfolio data available.")
        return
    
    # Get date range
    all_dates = []
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        all_dates.append(start)
    
    inception_date = min(all_dates) if all_dates else date.today() - timedelta(days=365)
    end_date = date.today() + timedelta(days=365)  # Extend 12 months into future
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From Date",
            value=max(inception_date, end_date - timedelta(days=180)),
            min_value=inception_date,
            max_value=end_date,
            key="ts_start"
        )
    with col2:
        end_date_input = st.date_input(
            "To Date",
            value=end_date,
            min_value=inception_date,
            max_value=end_date,
            key="ts_end"
        )
    
    # Calculate daily metrics
    with st.spinner("Calculating daily portfolio metrics..."):
        df_daily = calculate_daily_portfolio_metrics(portfolio, repo_trades, start_date, end_date_input)
    
    if df_daily.empty:
        st.warning("No data for selected date range.")
        return
    
    # Summary metrics
    st.markdown("##### Summary Statistics")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Days Tracked", len(df_daily))
    m2.metric("Avg Notional", f"R{df_daily['Total Notional'].mean()/1e9:.2f}B")
    m3.metric("Avg Gearing", f"{df_daily['Gearing'].mean():.2f}x")
    m4.metric("Avg Spread Pickup", f"{df_daily['Spread Pickup'].mean():.0f} bps")
    
    # Chart 1: Portfolio Notional and Gearing
    st.markdown("##### Portfolio Size & Leverage Evolution")
    
    fig1 = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )
    
    fig1.add_trace(
        go.Scatter(
            x=df_daily['Date'],
            y=df_daily['Total Notional']/1e9,
            name='Portfolio Notional',
            mode='lines',
            line=dict(color='#00d4ff', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.2)'
        ),
        secondary_y=False
    )
    
    fig1.add_trace(
        go.Scatter(
            x=df_daily['Date'],
            y=df_daily['Gearing'],
            name='Gearing Ratio',
            mode='lines',
            line=dict(color='#ffa500', width=2, dash='dot')
        ),
        secondary_y=True
    )
    
    fig1.update_xaxes(title_text="Date")
    fig1.update_yaxes(title_text="Notional (R Billions)", secondary_y=False)
    fig1.update_yaxes(title_text="Gearing (x)", secondary_y=True)
    
    fig1.update_layout(
        template='plotly_dark',
        height=400,
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Chart 2: Portfolio Composition Over Time (Stacked Area)
    st.markdown("##### Portfolio Composition by Counterparty")
    
    # Get all counterparty columns
    cpty_cols = [col for col in df_daily.columns if col.startswith('Notional_')]
    
    if cpty_cols:
        fig2 = go.Figure()
        
        # Color mapping
        colors = {
            'Notional_Republic of SA': '#00d4ff',
            'Notional_ABSA': '#00ff88',
            'Notional_Standard Bank': '#ffa500',
            'Notional_Nedbank': '#ff6b6b',
            'Notional_FirstRand': '#9b59b6',
            'Notional_Investec': '#3498db'
        }
        
        for col in cpty_cols:
            cpty_name = col.replace('Notional_', '')
            fig2.add_trace(go.Scatter(
                x=df_daily['Date'],
                y=df_daily[col]/1e9,
                name=cpty_name,
                mode='lines',
                stackgroup='one',
                line=dict(width=0.5),
                fillcolor=colors.get(col, '#ffffff')
            ))
        
        fig2.update_layout(
            title='Portfolio Composition Evolution',
            xaxis_title='Date',
            yaxis_title='Notional (R Billions)',
            template='plotly_dark',
            height=400,
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Chart 3: Spread Dynamics
    st.markdown("##### Spread Dynamics")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['Avg FRN Spread'],
        name='FRN Spread',
        mode='lines',
        line=dict(color='#00ff88', width=2)
    ))
    
    fig3.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['Avg Repo Spread'],
        name='Repo Spread',
        mode='lines',
        line=dict(color='#ff6b6b', width=2)
    ))
    
    fig3.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['Spread Pickup'],
        name='Spread Pickup',
        mode='lines',
        line=dict(color='#00d4ff', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.2)'
    ))
    
    fig3.update_layout(
        title='Average Spreads Over Time',
        xaxis_title='Date',
        yaxis_title='Spread (bps)',
        template='plotly_dark',
        height=400,
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # Chart 4: Position and Repo Count
    st.markdown("##### Activity Levels")
    
    fig4 = go.Figure()
    
    fig4.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Num Positions'],
        name='Active Positions',
        marker_color='#00ff88'
    ))
    
    fig4.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Num Repos'],
        name='Active Repos',
        marker_color='#ffa500'
    ))
    
    fig4.update_layout(
        title='Number of Active Positions and Repos',
        xaxis_title='Date',
        yaxis_title='Count',
        template='plotly_dark',
        height=400,
        barmode='group',
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig4, use_container_width=True)
    
    # Data table
    st.markdown("##### Daily Metrics Table")
    
    # Format for display
    df_display = df_daily.copy()
    df_display['Total Notional'] = df_display['Total Notional'].apply(lambda x: f"R{x/1e9:.2f}B")
    df_display['Total Repo'] = df_display['Total Repo'].apply(lambda x: f"R{x/1e9:.2f}B")
    df_display['Gearing'] = df_display['Gearing'].apply(lambda x: f"{x:.2f}x")
    df_display['Avg FRN Spread'] = df_display['Avg FRN Spread'].apply(lambda x: f"{x:.0f} bps")
    df_display['Avg Repo Spread'] = df_display['Avg Repo Spread'].apply(lambda x: f"{x:.0f} bps")
    df_display['Spread Pickup'] = df_display['Spread Pickup'].apply(lambda x: f"{x:.0f} bps")
    
    display_cols = ['Date', 'Total Notional', 'Total Repo', 'Gearing', 'Num Positions', 'Num Repos', 
                    'Avg FRN Spread', 'Avg Repo Spread', 'Spread Pickup']
    
    st.dataframe(df_display[display_cols].tail(50), use_container_width=True, hide_index=True)
