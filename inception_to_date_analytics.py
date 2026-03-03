"""
Inception-to-Date Analytics Module
Shows complete history from day 1: cashflows, exposure, risk evolution

Features:
- Historical cashflows from inception
- DV01/CS01 evolution over time
- Counterparty exposure evolution
- Concentration risk tracking
- Maturity profile changes
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def get_inception_date(portfolio, repo_trades):
    """Get earliest date from portfolio and repos"""
    all_dates = []
    
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if start:
            all_dates.append(start)
    
    for repo in repo_trades:
        trade_date = repo.get('trade_date')
        if isinstance(trade_date, str):
            trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
        if trade_date:
            all_dates.append(trade_date)
    
    return min(all_dates) if all_dates else date.today() - timedelta(days=365)


def calculate_inception_cashflows(portfolio, repo_trades, inception_date, end_date, jibar_rate=8.0):
    """Calculate ALL cashflows from inception to end date"""
    
    all_cashflows = []
    
    # FRN coupons (quarterly from start dates)
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        name = pos.get('name', 'Unknown')
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        # Generate quarterly coupons
        current = start
        quarter = 0
        while current <= min(maturity, end_date):
            if current >= inception_date:
                coupon_rate = (jibar_rate + spread) / 100
                coupon_amount = notional * coupon_rate * 0.25
                
                all_cashflows.append({
                    'Date': current,
                    'Type': 'FRN Coupon',
                    'Position': name,
                    'Amount': coupon_amount,
                    'Category': 'Income',
                    'Counterparty': pos.get('counterparty', 'Unknown')
                })
            
            quarter += 1
            current = start + timedelta(days=91 * quarter)
    
    # Repo cashflows
    for repo in repo_trades:
        spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        direction = repo.get('direction', 'borrow_cash')
        repo_id = repo.get('id', 'Unknown')
        
        # Near leg
        if inception_date <= spot_date <= end_date:
            near_amount = cash if direction == 'borrow_cash' else -cash
            all_cashflows.append({
                'Date': spot_date,
                'Type': 'Repo Near Leg',
                'Position': repo_id,
                'Amount': near_amount,
                'Category': 'Financing' if direction == 'borrow_cash' else 'Investment',
                'Counterparty': 'Repo'
            })
        
        # Far leg
        if inception_date <= end_date_repo <= end_date:
            days = (end_date_repo - spot_date).days
            repo_rate = (jibar_rate + spread) / 100
            interest = cash * repo_rate * (days / 365.0)
            
            far_amount = -(cash + interest) if direction == 'borrow_cash' else (cash + interest)
            all_cashflows.append({
                'Date': end_date_repo,
                'Type': 'Repo Far Leg',
                'Position': repo_id,
                'Amount': far_amount,
                'Category': 'Financing' if direction == 'borrow_cash' else 'Investment',
                'Counterparty': 'Repo'
            })
    
    df = pd.DataFrame(all_cashflows)
    if not df.empty:
        df = df.sort_values('Date')
        df['Cumulative'] = df['Amount'].cumsum()
    
    return df


def render_inception_cashflows(portfolio, repo_trades, jibar_rate=8.0):
    """Render complete cashflow history from day 1"""
    
    st.markdown("##### 💰 Complete Cashflow History (Inception to Date)")
    
    inception_date = get_inception_date(portfolio, repo_trades)
    end_date = date.today()
    
    st.info(f"📅 Portfolio Inception: **{inception_date}** | Days Active: **{(end_date - inception_date).days}**")
    
    # Calculate all cashflows
    df_cf = calculate_inception_cashflows(portfolio, repo_trades, inception_date, end_date, jibar_rate)
    
    if df_cf.empty:
        st.warning("No cashflows found.")
        return
    
    # Summary metrics
    total_inflows = df_cf[df_cf['Amount'] > 0]['Amount'].sum()
    total_outflows = df_cf[df_cf['Amount'] < 0]['Amount'].sum()
    net_cashflow = df_cf['Amount'].sum()
    total_events = len(df_cf)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inflows", f"R{total_inflows/1e6:,.1f}M")
    m2.metric("Total Outflows", f"R{total_outflows/1e6:,.1f}M")
    m3.metric("Net Cashflow", f"R{net_cashflow/1e6:,.1f}M")
    m4.metric("Total Events", f"{total_events:,}")
    
    # Comprehensive chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Daily Cashflows', 'Cumulative Cashflow'),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # Daily cashflows
    colors = ['#00ff88' if amt > 0 else '#ff6b6b' for amt in df_cf['Amount']]
    fig.add_trace(
        go.Bar(
            x=df_cf['Date'],
            y=df_cf['Amount'],
            name='Cashflows',
            marker_color=colors,
            hovertemplate='<b>%{x}</b><br>Type: %{text}<br>Amount: R%{y:,.0f}<extra></extra>',
            text=df_cf['Type']
        ),
        row=1, col=1
    )
    
    # Cumulative
    fig.add_trace(
        go.Scatter(
            x=df_cf['Date'],
            y=df_cf['Cumulative'],
            name='Cumulative',
            mode='lines',
            line=dict(color='orange', width=3),
            fill='tozeroy',
            fillcolor='rgba(255, 165, 0, 0.2)'
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Cashflow (R)", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative (R)", row=2, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=800,
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Breakdown by category
    st.markdown("###### Cashflow Breakdown by Category")
    
    cf_by_cat = df_cf.groupby('Category').agg({
        'Amount': ['sum', 'count', 'mean']
    }).reset_index()
    cf_by_cat.columns = ['Category', 'Total', 'Count', 'Average']
    
    st.dataframe(cf_by_cat.style.format({
        'Total': 'R{:,.0f}',
        'Count': '{:,.0f}',
        'Average': 'R{:,.0f}'
    }).background_gradient(subset=['Total'], cmap='RdYlGn'),
    use_container_width=True)


def calculate_risk_evolution(portfolio, inception_date, end_date, dv01_per_position=2000):
    """Calculate DV01/CS01 evolution over time"""
    
    date_range = pd.date_range(start=inception_date, end=end_date, freq='W')
    
    risk_data = []
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        total_notional = 0
        total_dv01 = 0
        total_cs01 = 0
        active_positions = 0
        
        cpty_exposure = {}
        
        for pos in portfolio:
            start = pos.get('start_date')
            maturity = pos.get('maturity')
            
            if isinstance(start, str):
                start = datetime.strptime(start, '%Y-%m-%d').date()
            if isinstance(maturity, str):
                maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
            
            # Check if position is active
            if start <= current_date_obj <= maturity:
                notional = pos.get('notional', 0)
                total_notional += notional
                
                # Estimate DV01/CS01 (more realistic values)
                years_to_mat = (maturity - current_date_obj).days / 365.25
                # DV01 = notional * duration * 0.01% (1bp move)
                # For FRNs, duration is approximately time to next reset (0.25 years)
                duration = min(0.25, years_to_mat)  # FRN duration ~3 months
                dv01 = notional * duration * 0.0001  # 1bp sensitivity
                cs01 = notional * years_to_mat * 0.0001 * 0.3  # Spread sensitivity
                
                total_dv01 += dv01
                total_cs01 += cs01
                active_positions += 1
                
                # Counterparty exposure
                cpty = pos.get('counterparty', 'Unknown')
                if cpty in cpty_exposure:
                    cpty_exposure[cpty] += notional
                else:
                    cpty_exposure[cpty] = notional
        
        # Calculate concentration (Herfindahl index)
        if total_notional > 0:
            concentration = sum((exp / total_notional) ** 2 for exp in cpty_exposure.values())
        else:
            concentration = 0
        
        risk_data.append({
            'Date': current_date_obj,
            'Total Notional': total_notional,
            'DV01': total_dv01,
            'CS01': total_cs01,
            'Active Positions': active_positions,
            'Concentration Index': concentration,
            'Num Counterparties': len(cpty_exposure)
        })
    
    return pd.DataFrame(risk_data)


def render_risk_evolution(portfolio):
    """Render risk exposure evolution from inception"""
    
    st.markdown("##### 📊 Risk Exposure Evolution (Inception to Date)")
    
    inception_date = get_inception_date(portfolio, [])
    end_date = date.today()
    
    # Calculate risk evolution
    df_risk = calculate_risk_evolution(portfolio, inception_date, end_date)
    
    if df_risk.empty:
        st.warning("No risk data available.")
        return
    
    # Multi-panel chart
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Portfolio Notional & Active Positions', 'DV01 & CS01 Evolution', 'Concentration Risk'),
        vertical_spacing=0.1,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]]
    )
    
    # Panel 1: Notional & Positions
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['Total Notional'] / 1e6,
            name='Total Notional',
            line=dict(color='#00d4ff', width=3),
            fill='tozeroy'
        ),
        row=1, col=1, secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['Active Positions'],
            name='Active Positions',
            line=dict(color='orange', width=2, dash='dash')
        ),
        row=1, col=1, secondary_y=True
    )
    
    # Panel 2: DV01 & CS01
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['DV01'],
            name='DV01',
            line=dict(color='#ff6b6b', width=3)
        ),
        row=2, col=1, secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['CS01'],
            name='CS01',
            line=dict(color='#00ff88', width=2, dash='dot')
        ),
        row=2, col=1, secondary_y=True
    )
    
    # Panel 3: Concentration
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['Concentration Index'],
            name='Concentration Index',
            line=dict(color='#ffa500', width=3),
            fill='tozeroy'
        ),
        row=3, col=1, secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_risk['Date'],
            y=df_risk['Num Counterparties'],
            name='# Counterparties',
            line=dict(color='#ff00ff', width=2, dash='dash')
        ),
        row=3, col=1, secondary_y=True
    )
    
    # Update axes
    fig.update_yaxes(title_text="Notional (R millions)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Count", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="DV01 (R)", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="CS01 (R)", row=2, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Concentration", row=3, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Count", row=3, col=1, secondary_y=True)
    
    fig.update_layout(
        template='plotly_dark',
        height=1000,
        hovermode='x unified',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    st.markdown("###### Risk Summary Statistics")
    
    current_notional = df_risk['Total Notional'].iloc[-1] if not df_risk.empty else 0
    peak_notional = df_risk['Total Notional'].max()
    current_dv01 = df_risk['DV01'].iloc[-1] if not df_risk.empty else 0
    peak_dv01 = df_risk['DV01'].max()
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Current Notional", f"R{current_notional/1e6:,.1f}M")
    s2.metric("Peak Notional", f"R{peak_notional/1e6:,.1f}M")
    s3.metric("Current DV01", f"R{current_dv01:,.0f}")
    s4.metric("Peak DV01", f"R{peak_dv01:,.0f}")
