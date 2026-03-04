"""
NAV Index Engine - Professional Portfolio NAV Tracking
Calculates daily Net Asset Value index since inception with:
- Cashflow adjustments (coupons, repo flows)
- Accrual adjustments (daily accrued interest)
- MTM adjustments (mark-to-market revaluation)

NAV Formula:
NAV(t) = NAV(t-1) + Cashflows(t) + Accruals(t) + MTM_Change(t)
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def calculate_daily_accrued(portfolio, current_date, jibar_rate=8.0):
    """
    Calculate total accrued interest for portfolio on a specific date
    
    Args:
        portfolio: List of FRN positions
        current_date: Date to calculate accrued for
        jibar_rate: JIBAR 3M rate for coupon estimation
        
    Returns:
        Total accrued interest
    """
    total_accrued = 0.0
    
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        # Check if position is active
        if start <= current_date <= maturity:
            notional = pos.get('notional', 0)
            spread = pos.get('issue_spread', 0)
            
            # Find last coupon date (quarterly from start)
            last_coupon = start
            current_check = start
            while current_check <= current_date:
                if current_check <= current_date:
                    last_coupon = current_check
                current_check = current_check + timedelta(days=91)
            
            # Days since last coupon
            days_accrued = (current_date - last_coupon).days
            
            # Accrued interest
            coupon_rate = (jibar_rate / 100) + (spread / 10000)
            accrued = notional * coupon_rate * (days_accrued / 365.0)
            
            total_accrued += accrued
    
    return total_accrued


def calculate_portfolio_mtm(portfolio, current_date, base_price=100.0):
    """
    Calculate mark-to-market value of portfolio
    Simplified: uses base price with small random variation for demonstration
    In production: would use actual curve building and pricing
    
    Args:
        portfolio: List of positions
        current_date: Valuation date
        base_price: Base clean price (default 100)
        
    Returns:
        Total MTM value
    """
    total_mtm = 0.0
    
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        if start <= current_date <= maturity:
            notional = pos.get('notional', 0)
            
            # Simplified MTM: base price with small variation
            # In production: use actual pricing engine
            years_to_mat = (maturity - current_date).days / 365.25
            price_adjustment = (5.0 - years_to_mat) * 0.1  # Longer = lower price
            clean_price = base_price + price_adjustment
            
            mtm = notional * (clean_price / 100.0)
            total_mtm += mtm
    
    return total_mtm


def build_nav_index(portfolio, repo_trades, inception_date, end_date, initial_nav=100_000_000, jibar_rate=8.0):
    """
    Build daily NAV index from inception to today
    
    NAV Components (OPERATING CASHFLOWS ONLY):
    1. Seed Capital (initial)
    2. FRN Coupon Income (quarterly) - INCLUDED
    3. Repo Interest Expense (daily accrual) - INCLUDED
    
    EXCLUDED (Financing Cashflows):
    - Repo Principal Borrowed/Repaid - NOT included in NAV
    - These are balance sheet movements, not P&L
    
    Args:
        portfolio: List of FRN positions
        repo_trades: List of repo trades
        inception_date: Start date for NAV calculation
        end_date: End date for NAV calculation
        initial_nav: Initial NAV value (default R100M = seed capital)
        jibar_rate: JIBAR 3M rate for calculations
        
    Returns:
        DataFrame with daily NAV index
    """
    
    # Generate date range
    date_range = pd.date_range(start=inception_date, end=end_date, freq='D')
    
    nav_data = []
    current_nav = initial_nav
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # FRN coupon income (quarterly)
        frn_cf = 0.0
        for pos in portfolio:
            start = pos.get('start_date')
            if isinstance(start, str):
                start = datetime.strptime(start, '%Y-%m-%d').date()
            
            # Check if coupon date (quarterly from start)
            current_check = start
            while current_check <= current_date_obj:
                if current_check == current_date_obj and current_check != start:
                    # Coupon payment
                    notional = pos.get('notional', 0)
                    spread_bps = pos.get('issue_spread', 0)
                    coupon_rate = (jibar_rate / 100) + (spread_bps / 10000)
                    coupon = notional * coupon_rate * 0.25  # Quarterly
                    frn_cf += coupon
                    break
                
                current_check = current_check + timedelta(days=91)
        
        # Repo INTEREST EXPENSE ONLY (exclude principal - it's a liability, not P&L)
        repo_interest_expense = 0.0
        for repo in repo_trades:
            spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            
            # ONLY count interest expense on maturity date
            # Principal borrowed/repaid is NOT included in NAV (it's a balance sheet item)
            if current_date_obj == end_date_repo and repo.get('direction') == 'borrow_cash':
                cash = repo.get('cash_amount', 0)
                spread = repo.get('repo_spread_bps', 0)
                days = (end_date_repo - spot_date).days
                repo_rate = (jibar_rate / 100) + (spread / 10000)
                interest = cash * repo_rate * (days / 365.0)
                repo_interest_expense -= interest  # Negative = expense
        
        # Update NAV (Operating Cashflows Only)
        # FRN coupons (income) + Repo interest (expense)
        # Repo principal is EXCLUDED - it's a liability, not income
        daily_change = frn_cf + repo_interest_expense
        current_nav += daily_change
        
        # Store data
        nav_data.append({
            'Date': current_date_obj,
            'NAV': current_nav,
            'FRN_Coupons': frn_cf,
            'Repo_Interest': repo_interest_expense,
            'Daily_Change': daily_change
        })
    
    return pd.DataFrame(nav_data)


def render_nav_index(portfolio, repo_trades):
    """
    Render NAV index visualization and analysis
    """
    
    st.markdown("##### 📈 Portfolio NAV Index (Since Inception)")
    
    st.info("""
    **NAV (Net Asset Value) Index Methodology:**
    
    **Formula:** `NAV(t) = NAV(t-1) + Cashflows(t) + Accrual_Change(t) + MTM_Change(t)`
    
    **Components:**
    1. **Cashflows:** FRN coupons received + Repo near/far leg cashflows
    2. **Accrual Change:** Daily change in accrued interest on FRNs
    3. **MTM Change:** Mark-to-market revaluation of portfolio
    
    **Base:** NAV starts at 1,000.00 on inception date
    
    **Professional Standard:** Follows hedge fund NAV calculation methodology
    """)
    
    if not portfolio:
        st.warning("No portfolio positions for NAV calculation.")
        return
    
    # Get inception date
    all_dates = []
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        all_dates.append(start)
    
    for repo in repo_trades:
        trade_date = repo.get('trade_date')
        if isinstance(trade_date, str):
            trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
        all_dates.append(trade_date)
    
    inception_date = min(all_dates) if all_dates else date.today() - timedelta(days=365)
    end_date = date.today() + timedelta(days=365)  # Extend 12 months into future
    
    st.info(f"📅 **Inception Date:** {inception_date} | **Days Active:** {(date.today() - inception_date).days:,} | **Projection:** +12 months")
    
    # Calculate NAV index
    with st.spinner("Calculating daily NAV index..."):
        # Use seed capital (R100M) as initial NAV
        df_nav = build_nav_index(portfolio, repo_trades, inception_date, end_date, initial_nav=100_000_000)
    
    if df_nav.empty:
        st.warning("Unable to calculate NAV index.")
        return
    
    # Summary metrics
    current_nav = df_nav['NAV'].iloc[-1]
    initial_nav = df_nav['NAV'].iloc[0]
    total_return_pct = ((current_nav - initial_nav) / initial_nav) * 100
    
    # Calculate APY (annualized)
    days_elapsed = (end_date - inception_date).days
    years_elapsed = days_elapsed / 365.25
    apy = ((current_nav / initial_nav) ** (1 / years_elapsed) - 1) * 100 if years_elapsed > 0 else 0
    
    total_frn_coupons = df_nav['FRN_Coupons'].sum()
    total_repo_interest = df_nav['Repo_Interest'].sum()
    total_daily_change = df_nav['Daily_Change'].sum()
    
    max_nav = df_nav['NAV'].max()
    min_nav = df_nav['NAV'].min()
    
    # Display metrics with smaller text
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 20px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current NAV", f"{current_nav:,.2f}", delta=f"{total_return_pct:+.2f}%")
    m2.metric("Initial NAV", f"{initial_nav:,.2f}")
    m3.metric("Max NAV", f"{max_nav:,.2f}")
    m4.metric("Min NAV", f"{min_nav:,.2f}")
    
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Total FRN Coupons", f"R{total_frn_coupons/1e6:.1f}M")
    m6.metric("Total Repo Interest", f"R{total_repo_interest/1e6:.1f}M")
    m7.metric("Net P&L", f"R{total_daily_change/1e6:.1f}M")
    m8.metric("APY (Annualized)", f"{apy:+.2f}%")
    
    # NAV chart with dual y-axis
    st.markdown("###### NAV Index Evolution")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('NAV Index (with MTM on right axis)', 'Daily Changes'),
        vertical_spacing=0.12,
        row_heights=[0.65, 0.35],
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )
    
    # Panel 1: NAV Index (primary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df_nav['Date'],
            y=df_nav['NAV'],
            name='NAV Index',
            mode='lines',
            line=dict(color='#00d4ff', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.2)'
        ),
        row=1, col=1,
        secondary_y=False
    )
    
    # Panel 1: Daily Change (secondary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df_nav['Date'],
            y=df_nav['Daily_Change'],
            name='Daily P&L',
            mode='lines',
            line=dict(color='#ff6b6b', width=2, dash='dot'),
            opacity=0.7
        ),
        row=1, col=1,
        secondary_y=True
    )
    
    # Add initial NAV reference line
    fig.add_hline(
        y=initial_nav,
        line_dash="dash",
        line_color="white",
        opacity=0.5,
        annotation_text=f"Initial: {initial_nav:,.2f}",
        annotation_position="left",
        row=1, col=1
    )
    
    # Panel 2: Daily changes breakdown
    fig.add_trace(
        go.Bar(
            x=df_nav['Date'],
            y=df_nav['FRN_Coupons'],
            name='FRN Coupons',
            marker_color='#00ff88'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_nav['Date'],
            y=df_nav['Repo_Interest'],
            name='Repo Interest',
            marker_color='#ff6b6b'
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="NAV (R)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Daily P&L (R)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Cashflow (R)", row=2, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=800,
        hovermode='x unified',
        barmode='relative',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed NAV table (last 30 days)
    st.markdown("###### Recent NAV History (Last 30 Days)")
    
    df_recent = df_nav.tail(30).copy()
    
    st.dataframe(df_recent[['Date', 'NAV', 'FRN_Coupons', 'Repo_Interest', 'Daily_Change']].style.format({
        'NAV': '{:,.0f}',
        'FRN_Coupons': '{:,.0f}',
        'Repo_Interest': '{:,.0f}',
        'Daily_Change': '{:+,.0f}'
    }).background_gradient(subset=['Daily_Change'], cmap='RdYlGn'),
    use_container_width=True, height=400)
    
    # Export
    if st.button("📥 Export Full NAV History (CSV)", key="export_nav"):
        csv = df_nav.to_csv(index=False)
        st.download_button("Download CSV", csv, "nav_index_history.csv", "text/csv")


def render_repo_master_table_and_summary(repo_trades, jibar_rate=8.0):
    """
    Render comprehensive repo master table and inception summary
    """
    
    st.markdown("##### 📋 Master Repo Trades Table")
    
    if not repo_trades:
        st.info("No repo trades.")
        return
    
    # Build master table
    master_data = []
    
    repo_interest_expense = 0.0
    for repo in repo_trades:
        trade_date = repo['trade_date'] if isinstance(repo['trade_date'], date) else datetime.strptime(repo['trade_date'], '%Y-%m-%d').date()
        spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end_date = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        direction = repo.get('direction', 'borrow_cash')
        collateral = repo.get('collateral_id', 'None')
        
        days = (end_date - spot_date).days
        repo_rate = (jibar_rate / 100) + (spread / 10000)
        interest = cash * repo_rate * (days / 365.0)
        
        if end_date == date.today() and direction == 'borrow_cash':
            repo_interest_expense -= interest
        
        near_cf = cash if direction == 'borrow_cash' else -cash
        far_cf = -(cash + interest) if direction == 'borrow_cash' else (cash + interest)
        net_cf = near_cf + far_cf
        
        master_data.append({
            'Repo ID': repo.get('id', 'Unknown'),
            'Direction': 'Borrow' if direction == 'borrow_cash' else 'Lend',
            'Trade Date': trade_date,
            'Spot Date': spot_date,
            'End Date': end_date,
            'Days': days,
            'Cash Amount': cash,
            'Spread (bps)': spread,
            'Repo Rate (%)': repo_rate * 100,
            'Interest': interest,
            'Near Leg CF': near_cf,
            'Far Leg CF': far_cf,
            'Net CF': net_cf,
            'Collateral': collateral if collateral else 'None',
            'Status': 'Matured' if end_date < date.today() else 'Active'
        })
    
    df_master = pd.DataFrame(master_data)
    
    # Display master table
    st.dataframe(df_master.style.format({
        'Cash Amount': 'R{:,.2f}',
        'Spread (bps)': '{:.2f}',
        'Repo Rate (%)': '{:.4f}',
        'Interest': 'R{:,.2f}',
        'Near Leg CF': 'R{:,.2f}',
        'Far Leg CF': 'R{:,.2f}',
        'Net CF': 'R{:,.2f}'
    }).background_gradient(subset=['Net CF'], cmap='RdYlGn'),
    use_container_width=True, height=500)
    
    # Summary since inception
    st.markdown("---")
    st.markdown("##### 📊 Repo Summary Since Inception")
    
    # Calculate summary statistics
    total_trades = len(df_master)
    borrow_trades = len(df_master[df_master['Direction'] == 'Borrow'])
    lend_trades = len(df_master[df_master['Direction'] == 'Lend'])
    
    total_cash = df_master['Cash Amount'].sum()
    total_interest_paid = df_master[df_master['Direction'] == 'Borrow']['Interest'].sum()
    total_interest_earned = df_master[df_master['Direction'] == 'Lend']['Interest'].sum()
    net_interest = total_interest_earned - total_interest_paid
    
    avg_spread = df_master['Spread (bps)'].mean()
    avg_days = df_master['Days'].mean()
    
    total_near_cf = df_master['Near Leg CF'].sum()
    total_far_cf = df_master['Far Leg CF'].sum()
    total_net_cf = df_master['Net CF'].sum()
    
    # Display summary table
    summary_data = {
        'Metric': [
            'Total Trades',
            'Borrow Trades',
            'Lend Trades',
            'Total Cash Amount',
            'Total Interest Paid',
            'Total Interest Earned',
            'Net Interest P&L',
            'Average Spread',
            'Average Term (Days)',
            'Total Near Leg CF',
            'Total Far Leg CF',
            'Total Net CF'
        ],
        'Value': [
            f"{total_trades:,}",
            f"{borrow_trades:,}",
            f"{lend_trades:,}",
            f"R{total_cash:,.2f}",
            f"R{total_interest_paid:,.2f}",
            f"R{total_interest_earned:,.2f}",
            f"R{net_interest:,.2f}",
            f"{avg_spread:.2f} bps",
            f"{avg_days:.1f}",
            f"R{total_near_cf:,.2f}",
            f"R{total_far_cf:,.2f}",
            f"R{total_net_cf:,.2f}"
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    # Export
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Master Table (CSV)", key="export_master"):
            csv = df_master.to_csv(index=False)
            st.download_button("Download", csv, "repo_master_table.csv", "text/csv")
    
    with col2:
        if st.button("📥 Export Summary (CSV)", key="export_summary"):
            csv = df_summary.to_csv(index=False)
            st.download_button("Download", csv, "repo_summary.csv", "text/csv")
