"""
Historical Analytics Module - Time-Series Portfolio & Repo Analytics
Provides comprehensive historical views of portfolio composition, gearing, yields, and cashflows

Features:
- Historical repo outstanding balance
- Gearing ratio evolution
- Portfolio composition over time
- Funding/gearing split
- Gross yield evolution
- Cashflow waterfall charts
- Attribution analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def calculate_historical_repo_balance(repo_trades, start_date, end_date):
    """
    Calculate repo outstanding balance for each day in date range
    
    Args:
        repo_trades: List of repo trade dicts
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        DataFrame with daily repo balances
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    daily_balances = []
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # Calculate outstanding balance on this date
        borrow_balance = 0.0
        lend_balance = 0.0
        active_borrows = 0
        active_lends = 0
        
        for repo in repo_trades:
            spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            
            # Check if repo is active on this date
            if spot_date <= current_date_obj <= end_date_repo:
                cash = repo.get('cash_amount', 0)
                direction = repo.get('direction', 'borrow_cash')
                
                if direction == 'borrow_cash':
                    borrow_balance += cash
                    active_borrows += 1
                else:
                    lend_balance += cash
                    active_lends += 1
        
        net_balance = borrow_balance - lend_balance
        
        daily_balances.append({
            'Date': current_date_obj,
            'Borrow Balance': borrow_balance,
            'Lend Balance': lend_balance,
            'Net Balance': net_balance,
            'Active Borrows': active_borrows,
            'Active Lends': active_lends,
            'Total Active': active_borrows + active_lends
        })
    
    return pd.DataFrame(daily_balances)


def calculate_historical_gearing(portfolio, repo_trades, start_date, end_date):
    """
    Calculate gearing ratio for each day
    
    Gearing = Repo Outstanding / Portfolio Notional
    
    Args:
        portfolio: List of portfolio positions
        repo_trades: List of repo trades
        start_date: Start date
        end_date: End date
        
    Returns:
        DataFrame with daily gearing ratios
    """
    # Calculate total portfolio notional
    total_notional = sum(pos.get('notional', 0) for pos in portfolio)
    
    # Get daily repo balances
    df_repo = calculate_historical_repo_balance(repo_trades, start_date, end_date)
    
    # Calculate gearing
    df_repo['Gearing Ratio'] = df_repo['Borrow Balance'] / total_notional if total_notional > 0 else 0
    df_repo['Gearing (x)'] = df_repo['Gearing Ratio']
    
    return df_repo


def render_repo_outstanding_chart(repo_trades, start_date, end_date):
    """
    Render historical repo outstanding balance chart
    """
    st.markdown("##### 📊 Historical Repo Outstanding Balance")
    
    if not repo_trades:
        st.info("No repo trades for historical analysis.")
        return
    
    # Calculate daily balances
    df_balance = calculate_historical_repo_balance(repo_trades, start_date, end_date)
    
    # Create chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Repo Outstanding Balance', 'Active Repo Count'),
        vertical_spacing=0.12,
        row_heights=[0.7, 0.3]
    )
    
    # Balance chart
    fig.add_trace(
        go.Scatter(
            x=df_balance['Date'],
            y=df_balance['Borrow Balance'],
            name='Borrow Balance',
            fill='tozeroy',
            line=dict(color='#00d4ff', width=2),
            stackgroup='one'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_balance['Date'],
            y=-df_balance['Lend Balance'],
            name='Lend Balance',
            fill='tozeroy',
            line=dict(color='#ff6b6b', width=2),
            stackgroup='two'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_balance['Date'],
            y=df_balance['Net Balance'],
            name='Net Balance',
            mode='lines',
            line=dict(color='orange', width=3, dash='dash')
        ),
        row=1, col=1
    )
    
    # Active count chart
    fig.add_trace(
        go.Bar(
            x=df_balance['Date'],
            y=df_balance['Active Borrows'],
            name='Active Borrows',
            marker_color='#00d4ff'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_balance['Date'],
            y=df_balance['Active Lends'],
            name='Active Lends',
            marker_color='#ff6b6b'
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Balance (R)", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=700,
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    st.markdown("###### Summary Statistics")
    
    avg_borrow = df_balance['Borrow Balance'].mean()
    max_borrow = df_balance['Borrow Balance'].max()
    avg_net = df_balance['Net Balance'].mean()
    max_active = df_balance['Total Active'].max()
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Avg Borrow Balance", f"R{avg_borrow/1e6:,.1f}M")
    s2.metric("Max Borrow Balance", f"R{max_borrow/1e6:,.1f}M")
    s3.metric("Avg Net Balance", f"R{avg_net/1e6:,.1f}M")
    s4.metric("Max Active Repos", f"{max_active:.0f}")


def render_gearing_evolution_chart(portfolio, repo_trades, start_date, end_date):
    """
    Render gearing ratio evolution chart
    """
    st.markdown("##### ⚡ Gearing Ratio Evolution")
    
    if not portfolio or not repo_trades:
        st.info("Need both portfolio and repo trades for gearing analysis.")
        return
    
    # Calculate gearing
    df_gearing = calculate_historical_gearing(portfolio, repo_trades, start_date, end_date)
    
    # Create chart
    fig = go.Figure()
    
    # Gearing ratio line
    fig.add_trace(go.Scatter(
        x=df_gearing['Date'],
        y=df_gearing['Gearing (x)'],
        name='Gearing Ratio',
        mode='lines+markers',
        line=dict(color='#ffa500', width=3),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(255, 165, 0, 0.2)'
    ))
    
    # Add reference lines
    fig.add_hline(y=1.0, line_dash="dash", line_color="white", opacity=0.5, 
                  annotation_text="1x Gearing", annotation_position="right")
    fig.add_hline(y=2.0, line_dash="dash", line_color="red", opacity=0.5,
                  annotation_text="2x Gearing", annotation_position="right")
    
    fig.update_layout(
        title='Portfolio Gearing Ratio Over Time',
        xaxis_title='Date',
        yaxis_title='Gearing (x)',
        template='plotly_dark',
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Gearing statistics
    st.markdown("###### Gearing Statistics")
    
    current_gearing = df_gearing['Gearing (x)'].iloc[-1] if not df_gearing.empty else 0
    avg_gearing = df_gearing['Gearing (x)'].mean()
    max_gearing = df_gearing['Gearing (x)'].max()
    min_gearing = df_gearing['Gearing (x)'].min()
    
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Current Gearing", f"{current_gearing:.2f}x")
    g2.metric("Average Gearing", f"{avg_gearing:.2f}x")
    g3.metric("Max Gearing", f"{max_gearing:.2f}x")
    g4.metric("Min Gearing", f"{min_gearing:.2f}x")


def calculate_portfolio_cashflows(portfolio, repo_trades, start_date, end_date, jibar_rate=8.0):
    """
    Calculate all portfolio cashflows (FRN coupons + repo cashflows)
    
    Args:
        portfolio: List of FRN positions
        repo_trades: List of repo trades
        start_date: Start date
        end_date: End date
        jibar_rate: JIBAR rate for calculations
        
    Returns:
        DataFrame with all cashflows
    """
    import QuantLib as ql
    
    all_cashflows = []
    
    # FRN coupons (quarterly)
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        # Generate quarterly coupon dates
        current = start
        while current <= maturity:
            if start_date <= current <= end_date:
                # Estimate coupon amount
                coupon_rate = (jibar_rate + spread) / 100
                coupon_amount = notional * coupon_rate * 0.25  # Quarterly
                
                all_cashflows.append({
                    'Date': current,
                    'Type': 'FRN Coupon',
                    'Position': pos.get('name', 'Unknown'),
                    'Amount': coupon_amount,
                    'Category': 'Income'
                })
            
            # Next quarter
            current = current + timedelta(days=91)
    
    # Repo cashflows
    for repo in repo_trades:
        spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        direction = repo.get('direction', 'borrow_cash')
        
        # Near leg
        if start_date <= spot_date <= end_date:
            near_amount = cash if direction == 'borrow_cash' else -cash
            all_cashflows.append({
                'Date': spot_date,
                'Type': 'Repo Near Leg',
                'Position': repo.get('id', 'Unknown'),
                'Amount': near_amount,
                'Category': 'Financing' if direction == 'borrow_cash' else 'Investment'
            })
        
        # Far leg
        if start_date <= end_date_repo <= end_date:
            days = (end_date_repo - spot_date).days
            repo_rate = (jibar_rate + spread) / 100
            interest = cash * repo_rate * (days / 365.0)
            
            far_amount = -(cash + interest) if direction == 'borrow_cash' else (cash + interest)
            all_cashflows.append({
                'Date': end_date_repo,
                'Type': 'Repo Far Leg',
                'Position': repo.get('id', 'Unknown'),
                'Amount': far_amount,
                'Category': 'Financing' if direction == 'borrow_cash' else 'Investment'
            })
    
    df_cf = pd.DataFrame(all_cashflows)
    if not df_cf.empty:
        df_cf = df_cf.sort_values('Date')
        df_cf['Cumulative'] = df_cf['Amount'].cumsum()
    
    return df_cf


def render_cashflow_waterfall(portfolio, repo_trades, start_date, end_date, jibar_rate=8.0):
    """
    Render comprehensive cashflow waterfall chart
    """
    st.markdown("##### 💧 Cashflow Waterfall Analysis")
    
    # Calculate cashflows
    df_cf = calculate_portfolio_cashflows(portfolio, repo_trades, start_date, end_date, jibar_rate)
    
    if df_cf.empty:
        st.info("No cashflows in selected period.")
        return
    
    # Aggregate by type
    cf_by_type = df_cf.groupby('Type')['Amount'].sum().reset_index()
    
    # Create waterfall
    fig = go.Figure(go.Waterfall(
        name="Cashflows",
        orientation="v",
        measure=["relative"] * len(cf_by_type) + ["total"],
        x=list(cf_by_type['Type']) + ['Net Cashflow'],
        y=list(cf_by_type['Amount']) + [df_cf['Amount'].sum()],
        text=[f"R{v/1e6:,.1f}M" for v in cf_by_type['Amount']] + [f"R{df_cf['Amount'].sum()/1e6:,.1f}M"],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#00ff88"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#ffa500"}}
    ))
    
    fig.update_layout(
        title="Cashflow Waterfall by Type",
        template='plotly_dark',
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Time-series cashflow chart
    st.markdown("###### Cashflow Time-Series")
    
    fig_ts = go.Figure()
    
    # Daily cashflows
    colors = ['#00ff88' if amt > 0 else '#ff6b6b' for amt in df_cf['Amount']]
    fig_ts.add_trace(go.Bar(
        x=df_cf['Date'],
        y=df_cf['Amount'],
        name='Cashflows',
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>Type: %{text}<br>Amount: R%{y:,.0f}<extra></extra>',
        text=df_cf['Type']
    ))
    
    # Cumulative line
    fig_ts.add_trace(go.Scatter(
        x=df_cf['Date'],
        y=df_cf['Cumulative'],
        name='Cumulative',
        mode='lines+markers',
        line=dict(color='orange', width=3),
        yaxis='y2'
    ))
    
    fig_ts.update_layout(
        title='Cashflows Over Time',
        xaxis_title='Date',
        yaxis_title='Cashflow (R)',
        yaxis2=dict(title='Cumulative (R)', overlaying='y', side='right'),
        template='plotly_dark',
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_ts, use_container_width=True)
    
    # Cashflow summary table
    st.markdown("###### Cashflow Summary by Category")
    
    cf_summary = df_cf.groupby('Category').agg({
        'Amount': ['sum', 'count', 'mean']
    }).reset_index()
    cf_summary.columns = ['Category', 'Total Amount', 'Count', 'Average']
    
    st.dataframe(cf_summary.style.format({
        'Total Amount': 'R{:,.0f}',
        'Count': '{:.0f}',
        'Average': 'R{:,.0f}'
    }).background_gradient(subset=['Total Amount'], cmap='RdYlGn'),
    use_container_width=True)


def render_portfolio_composition_over_time(portfolio, start_date, end_date):
    """
    Render portfolio composition evolution
    """
    st.markdown("##### 🥧 Portfolio Composition Over Time")
    
    if not portfolio:
        st.info("No portfolio positions.")
        return
    
    # Current composition by counterparty
    cpty_notional = {}
    for pos in portfolio:
        cpty = pos.get('counterparty', 'Unknown')
        notional = pos.get('notional', 0)
        if cpty in cpty_notional:
            cpty_notional[cpty] += notional
        else:
            cpty_notional[cpty] = notional
    
    # Pie chart
    fig_pie = px.pie(
        values=list(cpty_notional.values()),
        names=list(cpty_notional.keys()),
        title='Portfolio Composition by Counterparty',
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4
    )
    fig_pie.update_layout(template='plotly_dark')
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Maturity buckets
    maturity_buckets = {'0-1Y': 0, '1-2Y': 0, '2-3Y': 0, '3-5Y': 0, '5Y+': 0}
    
    for pos in portfolio:
        maturity = pos.get('maturity')
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        years_to_mat = (maturity - date.today()).days / 365.25
        notional = pos.get('notional', 0)
        
        if years_to_mat < 1:
            maturity_buckets['0-1Y'] += notional
        elif years_to_mat < 2:
            maturity_buckets['1-2Y'] += notional
        elif years_to_mat < 3:
            maturity_buckets['2-3Y'] += notional
        elif years_to_mat < 5:
            maturity_buckets['3-5Y'] += notional
        else:
            maturity_buckets['5Y+'] += notional
    
    # Bar chart
    fig_bar = go.Figure(go.Bar(
        x=list(maturity_buckets.keys()),
        y=[v/1e6 for v in maturity_buckets.values()],
        marker_color='#00d4ff',
        text=[f"R{v/1e6:,.1f}M" for v in maturity_buckets.values()],
        textposition='outside'
    ))
    
    fig_bar.update_layout(
        title='Portfolio by Maturity Bucket',
        xaxis_title='Maturity Bucket',
        yaxis_title='Notional (R millions)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)


def render_yield_evolution(portfolio, jibar_rate=8.0):
    """
    Render gross yield evolution by position
    """
    st.markdown("##### 📈 Gross Yield Analysis")
    
    if not portfolio:
        st.info("No portfolio positions.")
        return
    
    # Calculate gross yields
    yield_data = []
    
    for pos in portfolio:
        name = pos.get('name', 'Unknown')
        spread = pos.get('issue_spread', 0)
        notional = pos.get('notional', 0)
        
        gross_yield = jibar_rate + (spread / 100)
        
        yield_data.append({
            'Position': name,
            'Counterparty': pos.get('counterparty', 'Unknown'),
            'Notional': notional,
            'Spread (bps)': spread,
            'Gross Yield (%)': gross_yield
        })
    
    df_yields = pd.DataFrame(yield_data)
    
    # Scatter plot
    fig = px.scatter(
        df_yields,
        x='Spread (bps)',
        y='Gross Yield (%)',
        size='Notional',
        color='Counterparty',
        hover_data=['Position'],
        title='Gross Yield vs Spread (bubble size = notional)'
    )
    
    fig.update_layout(template='plotly_dark', height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary by counterparty
    st.markdown("###### Weighted Average Yields by Counterparty")
    
    wa_yields = df_yields.groupby('Counterparty').apply(
        lambda x: (x['Gross Yield (%)'] * x['Notional']).sum() / x['Notional'].sum()
    ).reset_index()
    wa_yields.columns = ['Counterparty', 'WA Gross Yield (%)']
    
    st.dataframe(wa_yields.style.format({
        'WA Gross Yield (%)': '{:.3f}%'
    }).background_gradient(subset=['WA Gross Yield (%)'], cmap='RdYlGn'),
    use_container_width=True)
