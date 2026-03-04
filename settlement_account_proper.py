"""
Professional Settlement Account Module with Proper Accounting
=============================================================

Best Practice Accounting:
1. OPERATING CASHFLOWS (impact NAV/P&L):
   - FRN coupon income (received)
   - Repo interest expense (paid on borrowed funds)
   - Repo interest income (earned on lent funds)

2. FINANCING CASHFLOWS (balance sheet, NOT in NAV):
   - Repo principal borrowed (liability increase)
   - Repo principal repaid (liability decrease)
   - Repo principal lent (asset increase)
   - Repo principal returned (asset decrease)

3. INVESTMENT CASHFLOWS:
   - FRN purchases (asset increase)
   - FRN sales/maturities (asset decrease)

NAV = Initial Capital + Cumulative Operating Cashflows
Cumulative Cashflow for NAV = Operating only (excludes financing principal)
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import streamlit as st
from historical_jibar_lookup import (
    load_historical_jibar, 
    get_jibar3m_on_date, 
    calculate_repo_rate_accurate,
    calculate_realized_coupon_accurate
)


def generate_professional_settlement_account(portfolio, repo_trades, seed_capital, inception_date, end_date, jibar_rate=6.63):
    """
    Generate professional settlement account with proper accounting separation
    
    Args:
        portfolio: List of FRN positions
        repo_trades: List of repo trades
        seed_capital: Initial equity capital (e.g., R100M)
        inception_date: Portfolio inception date
        end_date: End date for analysis
        jibar_rate: JIBAR 3M rate for coupon/interest calculations (fallback only)
        
    Returns:
        DataFrame with daily settlement account including:
        - Operating cashflows (P&L impact)
        - Financing cashflows (balance sheet)
        - NAV evolution
        - Detailed ledger entries
    """
    
    # Load historical JIBAR data for accurate rate lookups
    df_historical = load_historical_jibar()
    
    # Create daily date range - extend 12 months into future for projections
    future_end = end_date + timedelta(days=365)
    date_range = pd.date_range(start=inception_date, end=future_end, freq='D')
    
    daily_ledger = []
    
    # Day 0: Initial capital injection
    daily_ledger.append({
        'Date': inception_date,
        'Type': 'Initial Capital',
        'Category': 'Equity',
        'Description': 'Seed capital injection',
        'Operating_CF': 0,
        'Financing_CF': 0,
        'Investment_CF': seed_capital,
        'Total_CF': seed_capital,
        'Counterparty': 'Shareholder'
    })
    
    # Process each day
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # FRN Coupons (Operating - Income)
        for pos in portfolio:
            start = pos.get('start_date')
            maturity = pos.get('maturity')
            notional = pos.get('notional', 0)
            spread_bps = pos.get('issue_spread', 0)
            name = pos.get('name', 'Unknown')
            cpty = pos.get('counterparty', 'Unknown')
            
            if isinstance(start, str):
                start = datetime.strptime(start, '%Y-%m-%d').date()
            if isinstance(maturity, str):
                maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
            
            # Check if position is active
            if start <= current_date_obj <= maturity:
                # Generate quarterly coupons (simplified - every 91 days from start)
                days_from_start = (current_date_obj - start).days
                if days_from_start > 0 and days_from_start % 91 == 0:
                    # Use actual historical JIBAR3M on reset date (91 days before payment)
                    reset_date = current_date_obj - timedelta(days=91)
                    actual_jibar = get_jibar3m_on_date(reset_date, df_historical, jibar_rate)
                    
                    # Calculate realized coupon using actual JIBAR
                    coupon_amount = calculate_realized_coupon_accurate(
                        reset_date, 
                        current_date_obj, 
                        notional, 
                        spread_bps,
                        df_historical,
                        jibar_rate
                    )
                    
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'FRN Coupon',
                        'Category': 'Operating',
                        'Description': f'{name} - Coupon payment (JIBAR {actual_jibar:.2f}% + {spread_bps}bps)',
                        'Operating_CF': coupon_amount,
                        'Financing_CF': 0,
                        'Investment_CF': 0,
                        'Total_CF': coupon_amount,
                        'Counterparty': cpty
                    })
        
        # Repo Transactions
        for repo in repo_trades:
            spot_date = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end_date_repo = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            
            cash_amount = repo.get('cash_amount', 0)
            spread_bps = repo.get('repo_spread_bps', 0)
            direction = repo.get('direction', 'borrow_cash')
            repo_id = repo.get('id', 'Unknown')
            
            # NEAR LEG - Financing Cashflow (Balance Sheet)
            if current_date_obj == spot_date:
                if direction == 'borrow_cash':
                    # Borrow cash: Receive cash (liability increase)
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Near Leg',
                        'Category': 'Financing',
                        'Description': f'{repo_id[:12]} - Borrow cash (sell asset)',
                        'Operating_CF': 0,  # NOT operating income
                        'Financing_CF': cash_amount,  # Financing inflow
                        'Investment_CF': 0,
                        'Total_CF': cash_amount,
                        'Counterparty': 'Repo Counterparty'
                    })
                else:
                    # Lend cash: Pay cash (asset increase)
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Near Leg',
                        'Category': 'Financing',
                        'Description': f'{repo_id[:12]} - Lend cash (buy asset)',
                        'Operating_CF': 0,
                        'Financing_CF': -cash_amount,  # Financing outflow
                        'Investment_CF': 0,
                        'Total_CF': -cash_amount,
                        'Counterparty': 'Repo Counterparty'
                    })
            
            # FAR LEG - Split into Principal (Financing) and Interest (Operating)
            if current_date_obj == end_date_repo:
                # Use actual historical JIBAR3M on repo spot date
                actual_jibar_spot = get_jibar3m_on_date(spot_date, df_historical, jibar_rate)
                repo_rate = calculate_repo_rate_accurate(spot_date, spread_bps, df_historical, jibar_rate)
                
                days = (end_date_repo - spot_date).days
                interest = cash_amount * (repo_rate / 100) * (days / 365.0)
                
                if direction == 'borrow_cash':
                    # Repay borrowed cash
                    # Principal repayment = Financing outflow
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Far Leg - Principal',
                        'Category': 'Financing',
                        'Description': f'{repo_id[:12]} - Repay principal (buy back asset)',
                        'Operating_CF': 0,
                        'Financing_CF': -cash_amount,  # Financing outflow
                        'Investment_CF': 0,
                        'Total_CF': -cash_amount,
                        'Counterparty': 'Repo Counterparty'
                    })
                    
                    # Interest payment = Operating expense (using actual JIBAR on spot date)
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Interest Expense',
                        'Category': 'Operating',
                        'Description': f'{repo_id[:12]} - Interest expense (JIBAR {actual_jibar_spot:.2f}% + {spread_bps}bps)',
                        'Operating_CF': -interest,  # Operating expense
                        'Financing_CF': 0,
                        'Investment_CF': 0,
                        'Total_CF': -interest,
                        'Counterparty': 'Repo Counterparty'
                    })
                else:
                    # Receive lent cash back
                    # Principal return = Financing inflow
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Far Leg - Principal',
                        'Category': 'Financing',
                        'Description': f'{repo_id[:12]} - Receive principal (sell back asset)',
                        'Operating_CF': 0,
                        'Financing_CF': cash_amount,  # Financing inflow
                        'Investment_CF': 0,
                        'Total_CF': cash_amount,
                        'Counterparty': 'Repo Counterparty'
                    })
                    
                    # Interest received = Operating income
                    daily_ledger.append({
                        'Date': current_date_obj,
                        'Type': 'Repo Interest Income',
                        'Category': 'Operating',
                        'Description': f'{repo_id[:12]} - Interest income',
                        'Operating_CF': interest,  # Operating income
                        'Financing_CF': 0,
                        'Investment_CF': 0,
                        'Total_CF': interest,
                        'Counterparty': 'Repo Counterparty'
                    })
    
    # Convert to DataFrame
    df_ledger = pd.DataFrame(daily_ledger)
    
    if df_ledger.empty:
        return df_ledger
    
    # Sort by date
    df_ledger = df_ledger.sort_values('Date').reset_index(drop=True)
    
    # Calculate cumulative balances
    df_ledger['Cumulative_Operating'] = df_ledger['Operating_CF'].cumsum()
    df_ledger['Cumulative_Financing'] = df_ledger['Financing_CF'].cumsum()
    df_ledger['Cumulative_Investment'] = df_ledger['Investment_CF'].cumsum()
    df_ledger['Cumulative_Total'] = df_ledger['Total_CF'].cumsum()
    
    # NAV = Seed Capital + Cumulative Operating Cashflows
    df_ledger['NAV'] = seed_capital + df_ledger['Cumulative_Operating']
    
    # Cash Balance = Cumulative Total Cashflows (all categories)
    df_ledger['Cash_Balance'] = df_ledger['Cumulative_Total']
    
    return df_ledger


def aggregate_daily_settlement(df_ledger):
    """Aggregate ledger entries by day for cleaner visualization"""
    
    if df_ledger.empty:
        return df_ledger
    
    daily_agg = df_ledger.groupby('Date').agg({
        'Operating_CF': 'sum',
        'Financing_CF': 'sum',
        'Investment_CF': 'sum',
        'Total_CF': 'sum',
        'Cumulative_Operating': 'last',
        'Cumulative_Financing': 'last',
        'Cumulative_Investment': 'last',
        'Cumulative_Total': 'last',
        'NAV': 'last',
        'Cash_Balance': 'last'
    }).reset_index()
    
    return daily_agg


def render_professional_settlement_account(portfolio, repo_trades, seed_capital=100000000, jibar_rate=6.63):
    """
    Render professional settlement account with proper accounting
    """
    
    st.markdown("##### 💰 Professional Settlement Account (Proper Accounting)")
    
    st.info("""
    **Accounting Best Practice:**
    
    - **Operating Cashflows** (impact NAV/P&L): FRN coupons, repo interest
    - **Financing Cashflows** (balance sheet): Repo principal borrowed/repaid
    - **Investment Cashflows**: Initial capital, FRN purchases
    
    **NAV = Seed Capital + Cumulative Operating Cashflows**
    
    ⚠️ Repo principal is NOT income - it's a liability!
    """)
    
    # Get date range
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
    
    if not all_dates:
        st.warning("No dates found in portfolio or repos.")
        return
    
    inception_date = min(all_dates)
    end_date = date.today()
    
    st.markdown(f"**Inception Date:** {inception_date} | **Seed Capital:** R{seed_capital/1e6:.1f}M")
    
    # Generate settlement account
    df_ledger = generate_professional_settlement_account(
        portfolio, repo_trades, seed_capital, inception_date, end_date, jibar_rate
    )
    
    if df_ledger.empty:
        st.warning("No settlement account data generated.")
        return
    
    # Aggregate by day
    df_daily = aggregate_daily_settlement(df_ledger)
    
    # Summary metrics
    total_operating = df_ledger['Operating_CF'].sum()
    total_financing = df_ledger['Financing_CF'].sum()
    current_nav = df_daily['NAV'].iloc[-1] if not df_daily.empty else seed_capital
    current_cash = df_daily['Cash_Balance'].iloc[-1] if not df_daily.empty else seed_capital
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current NAV", f"R{current_nav/1e6:.2f}M", 
             delta=f"{((current_nav/seed_capital - 1) * 100):.2f}%")
    m2.metric("Operating CF (Total)", f"R{total_operating/1e6:.2f}M")
    m3.metric("Financing CF (Net)", f"R{total_financing/1e6:.2f}M")
    m4.metric("Cash Balance", f"R{current_cash/1e6:.2f}M")
    
    # Multi-panel chart
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            'Daily Cashflows by Category',
            'NAV Evolution (Operating CF Only)',
            'Cash Balance (All Cashflows)'
        ),
        vertical_spacing=0.1,
        row_heights=[0.35, 0.35, 0.3]
    )
    
    # Panel 1: Daily cashflows by category
    fig.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Operating_CF'],
        name='Operating CF',
        marker_color='#00ff88',
        legendgroup='cf'
    ), row=1, col=1)
    
    fig.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Financing_CF'],
        name='Financing CF',
        marker_color='#ffa500',
        legendgroup='cf'
    ), row=1, col=1)
    
    fig.add_trace(go.Bar(
        x=df_daily['Date'],
        y=df_daily['Investment_CF'],
        name='Investment CF',
        marker_color='#00d4ff',
        legendgroup='cf'
    ), row=1, col=1)
    
    # Panel 2: NAV evolution
    fig.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['NAV'] / 1e6,
        name='NAV',
        mode='lines',
        line=dict(color='#00ff88', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 136, 0.2)',
        legendgroup='nav'
    ), row=2, col=1)
    
    # Add seed capital line
    fig.add_hline(y=seed_capital/1e6, line_dash="dash", line_color="white", 
                 opacity=0.5, row=2, col=1,
                 annotation_text=f"Seed Capital (R{seed_capital/1e6:.0f}M)")
    
    # Panel 3: Cash balance
    fig.add_trace(go.Scatter(
        x=df_daily['Date'],
        y=df_daily['Cash_Balance'] / 1e6,
        name='Cash Balance',
        mode='lines',
        line=dict(color='orange', width=3),
        fill='tozeroy',
        fillcolor='rgba(255, 165, 0, 0.2)',
        legendgroup='cash'
    ), row=3, col=1)
    
    # Update axes
    fig.update_yaxes(title_text="Cashflow (R)", row=1, col=1)
    fig.update_yaxes(title_text="NAV (R millions)", row=2, col=1)
    fig.update_yaxes(title_text="Cash (R millions)", row=3, col=1)
    fig.update_xaxes(title_text="Date", row=3, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=1000,
        hovermode='x unified',
        barmode='relative',
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed ledger table
    st.markdown("###### Detailed Transaction Ledger")
    
    show_all = st.checkbox("Show all transactions", value=False, key="show_all_ledger")
    
    if show_all:
        df_display = df_ledger.copy()
    else:
        df_display = df_ledger.head(100).copy()
    
    st.dataframe(df_display.style.format({
        'Operating_CF': 'R{:,.0f}',
        'Financing_CF': 'R{:,.0f}',
        'Investment_CF': 'R{:,.0f}',
        'Total_CF': 'R{:,.0f}',
        'NAV': 'R{:,.0f}',
        'Cash_Balance': 'R{:,.0f}'
    }), use_container_width=True, height=400)
    
    # Export
    if st.button("📥 Export Settlement Account (CSV)", key="export_settlement"):
        csv = df_ledger.to_csv(index=False)
        st.download_button("Download CSV", csv, "settlement_account.csv", "text/csv")
    
    # Category breakdown
    st.markdown("###### Cashflow Summary by Category")
    
    category_summary = df_ledger.groupby('Category').agg({
        'Operating_CF': 'sum',
        'Financing_CF': 'sum',
        'Investment_CF': 'sum',
        'Total_CF': 'sum'
    }).reset_index()
    
    st.dataframe(category_summary.style.format({
        'Operating_CF': 'R{:,.0f}',
        'Financing_CF': 'R{:,.0f}',
        'Investment_CF': 'R{:,.0f}',
        'Total_CF': 'R{:,.0f}'
    }).background_gradient(cmap='RdYlGn'), use_container_width=True)
