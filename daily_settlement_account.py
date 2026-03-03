"""
Daily Settlement Account Module
Provides day-by-day settlement account tracking for all repo trades

Features:
- Daily settlement account balance (every calendar day)
- Consolidated view across all repos
- Individual repo cashflow breakdown
- Cumulative balance tracking
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import streamlit as st


def generate_daily_settlement_account(repo_trades, start_date, end_date, jibar_rate=8.0):
    """
    Generate daily settlement account showing balance for every day
    
    Args:
        repo_trades: List of repo trade dictionaries
        start_date: Start date for daily view
        end_date: End date for daily view
        jibar_rate: JIBAR 3M rate for interest calculations
        
    Returns:
        DataFrame with daily settlement account balances
    """
    
    # Create date range (every day)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Initialize daily balance tracker
    daily_data = []
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # Track all cashflows on this date
        day_cashflows = []
        total_cashflow = 0.0
        
        for repo in repo_trades:
            spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            
            cash_amount = repo.get('cash_amount', 0)
            spread_bps = repo.get('repo_spread_bps', 0)
            direction = repo.get('direction', 'borrow_cash')
            repo_id = repo.get('id', 'Unknown')
            
            # Near leg cashflow
            if current_date_obj == spot_date:
                if direction == 'borrow_cash':
                    cf = cash_amount  # Receive cash
                    desc = f"{repo_id[:12]}: SELL asset, RECEIVE R{cash_amount:,.0f}"
                else:
                    cf = -cash_amount  # Pay cash
                    desc = f"{repo_id[:12]}: BUY asset, PAY R{cash_amount:,.0f}"
                
                day_cashflows.append({'Type': 'Near Leg', 'Amount': cf, 'Description': desc})
                total_cashflow += cf
            
            # Far leg cashflow
            if current_date_obj == end_date_repo:
                days = (end_date_repo - spot_date).days
                repo_rate = (jibar_rate + spread_bps) / 100
                interest = cash_amount * repo_rate * (days / 365.0)
                
                if direction == 'borrow_cash':
                    cf = -(cash_amount + interest)  # Pay back principal + interest
                    desc = f"{repo_id[:12]}: BUY back asset, PAY R{cash_amount + interest:,.0f}"
                else:
                    cf = cash_amount + interest  # Receive principal + interest
                    desc = f"{repo_id[:12]}: SELL back asset, RECEIVE R{cash_amount + interest:,.0f}"
                
                day_cashflows.append({'Type': 'Far Leg', 'Amount': cf, 'Description': desc})
                total_cashflow += cf
        
        daily_data.append({
            'Date': current_date_obj,
            'Cashflow': total_cashflow,
            'Events': len(day_cashflows),
            'Details': ' | '.join([d['Description'] for d in day_cashflows]) if day_cashflows else 'No activity'
        })
    
    df_daily = pd.DataFrame(daily_data)
    
    # Calculate cumulative balance
    df_daily['Cumulative Balance'] = df_daily['Cashflow'].cumsum()
    
    return df_daily


def render_daily_settlement_view(repo_trades, evaluation_date, jibar_rate=8.0):
    """
    Render daily settlement account view with chart and table
    """
    
    st.markdown("##### 💰 Daily Settlement Account")
    
    if not repo_trades:
        st.info("No repo trades for settlement account analysis.")
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    
    # Find min/max dates from repos
    all_dates = []
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        all_dates.extend([spot, end])
    
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
    else:
        min_date = evaluation_date - timedelta(days=90)
        max_date = evaluation_date + timedelta(days=90)
    
    with col1:
        start_date = st.date_input("Start Date", value=min_date, key="settle_start")
    
    with col2:
        end_date = st.date_input("End Date", value=max_date, key="settle_end")
    
    # Generate daily settlement account
    df_daily = generate_daily_settlement_account(repo_trades, start_date, end_date, jibar_rate)
    
    # Summary metrics
    total_inflows = df_daily[df_daily['Cashflow'] > 0]['Cashflow'].sum()
    total_outflows = df_daily[df_daily['Cashflow'] < 0]['Cashflow'].sum()
    net_cashflow = df_daily['Cashflow'].sum()
    final_balance = df_daily['Cumulative Balance'].iloc[-1] if not df_daily.empty else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inflows", f"R{total_inflows:,.0f}", help="Cash received")
    m2.metric("Total Outflows", f"R{total_outflows:,.0f}", help="Cash paid")
    m3.metric("Net Cashflow", f"R{net_cashflow:,.0f}")
    m4.metric("Final Balance", f"R{final_balance:,.0f}", 
             delta=f"{'Surplus' if final_balance > 0 else 'Deficit'}")
    
    # Chart: Daily cashflows and cumulative balance
    st.markdown("###### Daily Cashflows & Cumulative Balance")
    
    fig_daily = go.Figure()
    
    # Add daily cashflow bars
    colors = ['#00ff88' if cf > 0 else '#ff6b6b' for cf in df_daily['Cashflow']]
    fig_daily.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Cashflow'],
        name='Daily Cashflow',
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>Cashflow: R%{y:,.0f}<extra></extra>'
    ))
    
    # Add cumulative balance line
    fig_daily.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['Cumulative Balance'],
        name='Cumulative Balance',
        mode='lines+markers',
        line=dict(color='orange', width=3),
        marker=dict(size=6),
        yaxis='y2'
    ))
    
    # Add zero line
    fig_daily.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
    
    fig_daily.update_layout(
        title='Daily Settlement Account Activity',
        xaxis_title='Date',
        yaxis_title='Daily Cashflow (R)',
        yaxis2=dict(title='Cumulative Balance (R)', overlaying='y', side='right'),
        template='plotly_dark',
        hovermode='x unified',
        height=500,
        barmode='relative'
    )
    
    st.plotly_chart(fig_daily, use_container_width=True)
    
    # Detailed daily table
    st.markdown("###### Daily Settlement Account Detail")
    
    # Filter to show only days with activity
    show_all = st.checkbox("Show all days (including zero activity)", value=False, key="show_all_days")
    
    if show_all:
        df_display = df_daily.copy()
    else:
        df_display = df_daily[df_daily['Events'] > 0].copy()
    
    # Format and display
    st.dataframe(df_display.style.format({
        'Cashflow': 'R{:,.2f}',
        'Cumulative Balance': 'R{:,.2f}',
        'Events': '{:.0f}'
    }).background_gradient(subset=['Cumulative Balance'], cmap='RdYlGn'),
    use_container_width=True, height=400)
    
    # Export option
    if st.button("📥 Export Daily Settlement Account (CSV)", key="export_daily_settle"):
        csv = df_daily.to_csv(index=False)
        st.download_button("Download CSV", csv, "daily_settlement_account.csv", "text/csv")


def create_master_repo_table(repo_trades, jibar_rate=8.0):
    """
    Create comprehensive master table for all repo trades
    
    Returns:
        DataFrame with all repo details
    """
    
    master_data = []
    
    for repo in repo_trades:
        trade_date = repo['trade_date'] if isinstance(repo['trade_date'], date) else datetime.strptime(repo['trade_date'], '%Y-%m-%d').date()
        spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end_date = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        direction = repo.get('direction', 'borrow_cash')
        collateral = repo.get('collateral_id', 'None')
        
        days = (end_date - spot_date).days
        repo_rate = (jibar_rate + spread) / 100
        interest = cash * repo_rate * (days / 365.0)
        
        # Near leg cashflow
        near_cf = cash if direction == 'borrow_cash' else -cash
        
        # Far leg cashflow
        far_cf = -(cash + interest) if direction == 'borrow_cash' else (cash + interest)
        
        # Net cashflow
        net_cf = near_cf + far_cf
        
        master_data.append({
            'Repo ID': repo.get('id', 'Unknown'),
            'Direction': 'Borrow' if direction == 'borrow_cash' else 'Lend',
            'Trade Date': trade_date,
            'Spot Date': spot_date,
            'End Date': end_date,
            'Days': days,
            'Cash (M)': cash / 1e6,
            'Spread (bps)': spread,
            'Repo Rate (%)': repo_rate * 100,
            'Interest': interest,
            'Near Leg CF': near_cf,
            'Far Leg CF': far_cf,
            'Net CF': net_cf,
            'Collateral': collateral if collateral else 'None'
        })
    
    return pd.DataFrame(master_data)


def render_master_repo_table(repo_trades, jibar_rate=8.0):
    """
    Render master repo table with all trades
    """
    
    st.markdown("##### 📋 Master Repo Table")
    
    if not repo_trades:
        st.info("No repo trades to display.")
        return
    
    df_master = create_master_repo_table(repo_trades, jibar_rate)
    
    # Display with formatting
    st.dataframe(df_master.style.format({
        'Cash (M)': 'R{:.2f}M',
        'Spread (bps)': '{:.1f}',
        'Repo Rate (%)': '{:.4f}',
        'Interest': 'R{:,.0f}',
        'Near Leg CF': 'R{:,.0f}',
        'Far Leg CF': 'R{:,.0f}',
        'Net CF': 'R{:,.0f}'
    }).background_gradient(subset=['Net CF'], cmap='RdYlGn'),
    use_container_width=True, height=500)
    
    # Summary row
    st.markdown("**Summary:**")
    total_cash = df_master['Cash (M)'].sum()
    total_interest = df_master['Interest'].sum()
    total_net_cf = df_master['Net CF'].sum()
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Notional", f"R{total_cash:.1f}M")
    s2.metric("Total Interest", f"R{total_interest:,.0f}")
    s3.metric("Total Net CF", f"R{total_net_cf:,.0f}")
    s4.metric("Avg Spread", f"{df_master['Spread (bps)'].mean():.1f} bps")
    
    # Export
    if st.button("📥 Export Master Repo Table (CSV)", key="export_master_repo"):
        csv = df_master.to_csv(index=False)
        st.download_button("Download CSV", csv, "master_repo_table.csv", "text/csv")
