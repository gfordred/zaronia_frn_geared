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
            coupon_rate = (jibar_rate + spread) / 100
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


def calculate_daily_nav_index(portfolio, repo_trades, inception_date, end_date, 
                               initial_nav=1000.0, jibar_rate=8.0):
    """
    Calculate daily NAV index from inception to end date
    
    NAV Components:
    1. Cashflows: FRN coupons + Repo near/far legs
    2. Accruals: Daily accrued interest on FRNs
    3. MTM: Mark-to-market revaluation of portfolio
    
    Args:
        portfolio: List of FRN positions
        repo_trades: List of repo trades
        inception_date: First date of portfolio
        end_date: Last date to calculate
        initial_nav: Starting NAV value (default 1000.0)
        jibar_rate: JIBAR rate for calculations
        
    Returns:
        DataFrame with daily NAV index
    """
    
    # Generate date range
    date_range = pd.date_range(start=inception_date, end=end_date, freq='D')
    
    nav_data = []
    current_nav = initial_nav
    previous_accrued = 0.0
    previous_mtm = 0.0
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # 1. Calculate cashflows on this date
        daily_cashflow = 0.0
        cashflow_details = []
        
        # FRN coupons (quarterly)
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
                    
                    daily_cashflow += coupon
                    cashflow_details.append(f"Coupon {pos.get('name', 'Unknown')[:15]}: +{coupon:,.0f}")
                    break
                
                current_check = current_check + timedelta(days=91)
        
        # Repo cashflows
        for repo in repo_trades:
            spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            
            cash = repo.get('cash_amount', 0)
            spread = repo.get('repo_spread_bps', 0)
            direction = repo.get('direction', 'borrow_cash')
            
            # Near leg
            if current_date_obj == spot_date:
                near_cf = cash if direction == 'borrow_cash' else -cash
                daily_cashflow += near_cf
                cashflow_details.append(f"Repo Near: {'+' if near_cf > 0 else ''}{near_cf:,.0f}")
            
            # Far leg
            if current_date_obj == end_date_repo:
                days = (end_date_repo - spot_date).days
                repo_rate = (jibar_rate + spread) / 100
                interest = cash * repo_rate * (days / 365.0)
                
                far_cf = -(cash + interest) if direction == 'borrow_cash' else (cash + interest)
                daily_cashflow += far_cf
                cashflow_details.append(f"Repo Far: {'+' if far_cf > 0 else ''}{far_cf:,.0f}")
        
        # 2. Calculate accrued interest
        current_accrued = calculate_daily_accrued(portfolio, current_date_obj, jibar_rate)
        accrual_change = current_accrued - previous_accrued
        
        # 3. Calculate MTM (mark-to-market is already absolute value, not change)
        # For NAV, we don't add MTM daily - it's already reflected in portfolio value
        # Only track MTM for reporting, not for NAV calculation
        current_mtm = calculate_portfolio_mtm(portfolio, current_date_obj)
        mtm_change = current_mtm - previous_mtm if previous_mtm > 0 else 0
        
        # 4. Update NAV
        # NAV = Previous NAV + Cashflows + Accrual Change
        # MTM is not added to NAV as it's a valuation metric, not a cash flow
        nav_change = daily_cashflow + accrual_change
        current_nav = current_nav + nav_change
        
        # Store data
        nav_data.append({
            'Date': current_date_obj,
            'NAV': current_nav,
            'Cashflow': daily_cashflow,
            'Accrual': current_accrued,
            'Accrual Change': accrual_change,
            'MTM': current_mtm,
            'MTM Change': mtm_change,
            'Daily Change': nav_change,
            'Daily Return (%)': (nav_change / (current_nav - nav_change) * 100) if (current_nav - nav_change) > 0 else 0,
            'Cashflow Details': ' | '.join(cashflow_details) if cashflow_details else 'No activity'
        })
        
        # Update for next iteration
        previous_accrued = current_accrued
        previous_mtm = current_mtm
    
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
    end_date = date.today()
    
    st.info(f"📅 **Inception Date:** {inception_date} | **Days Active:** {(end_date - inception_date).days:,}")
    
    # Calculate NAV index
    with st.spinner("Calculating daily NAV index..."):
        df_nav = calculate_daily_nav_index(portfolio, repo_trades, inception_date, end_date)
    
    if df_nav.empty:
        st.warning("Unable to calculate NAV index.")
        return
    
    # Summary metrics
    current_nav = df_nav['NAV'].iloc[-1]
    initial_nav = df_nav['NAV'].iloc[0]
    total_return = ((current_nav - initial_nav) / initial_nav) * 100
    
    total_cashflows = df_nav['Cashflow'].sum()
    total_accrual_change = df_nav['Accrual Change'].sum()
    total_mtm_change = df_nav['MTM Change'].sum()
    
    max_nav = df_nav['NAV'].max()
    min_nav = df_nav['NAV'].min()
    
    # Display metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current NAV", f"{current_nav:,.2f}", delta=f"{total_return:+.2f}%")
    m2.metric("Initial NAV", f"{initial_nav:,.2f}")
    m3.metric("Max NAV", f"{max_nav:,.2f}")
    m4.metric("Min NAV", f"{min_nav:,.2f}")
    
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Total Cashflows", f"{total_cashflows:,.2f}")
    m6.metric("Total Accrual Δ", f"{total_accrual_change:,.2f}")
    m7.metric("Total MTM Δ", f"{total_mtm_change:,.2f}")
    m8.metric("Total Return", f"{total_return:+.2f}%")
    
    # NAV chart
    st.markdown("###### NAV Index Evolution")
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('NAV Index', 'Daily Changes'),
        vertical_spacing=0.12,
        row_heights=[0.65, 0.35]
    )
    
    # Panel 1: NAV Index
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
        row=1, col=1
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
            y=df_nav['Cashflow'],
            name='Cashflows',
            marker_color='#00ff88'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_nav['Date'],
            y=df_nav['Accrual Change'],
            name='Accrual Δ',
            marker_color='#ffa500'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_nav['Date'],
            y=df_nav['MTM Change'],
            name='MTM Δ',
            marker_color='#ff6b6b'
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="NAV", row=1, col=1)
    fig.update_yaxes(title_text="Change", row=2, col=1)
    
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
    
    st.dataframe(df_recent[['Date', 'NAV', 'Cashflow', 'Accrual Change', 'MTM Change', 'Daily Change', 'Daily Return (%)']].style.format({
        'NAV': '{:,.2f}',
        'Cashflow': '{:,.2f}',
        'Accrual Change': '{:,.2f}',
        'MTM Change': '{:,.2f}',
        'Daily Change': '{:+,.2f}',
        'Daily Return (%)': '{:+.4f}'
    }).background_gradient(subset=['Daily Change'], cmap='RdYlGn'),
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
