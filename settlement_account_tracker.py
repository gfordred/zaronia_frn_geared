"""
Settlement Account Tracker - Daily cashflow tracking
Shows all cash movements through the settlement account
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta


def calculate_settlement_account_history(portfolio, repo_trades, seed_capital=100_000_000):
    """
    Calculate complete settlement account history showing all cash movements
    
    Settlement Account tracks:
    - Seed capital injection
    - Repo borrowing (cash IN)
    - Portfolio purchases (cash OUT)
    - FRN coupon receipts (cash IN)
    - Repo interest payments (cash OUT)
    - Repo principal repayments (cash OUT)
    
    Returns:
        DataFrame with daily settlement account balance
    """
    
    # Get all transaction dates
    all_dates = []
    
    # Portfolio start dates
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        all_dates.append(start)
    
    # Repo dates
    for repo in repo_trades:
        spot = repo.get('spot_date')
        end = repo.get('end_date')
        if isinstance(spot, str):
            spot = datetime.strptime(spot, '%Y-%m-%d').date()
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d').date()
        all_dates.append(spot)
        all_dates.append(end)
    
    # If no trades, return simple seed capital entry
    if not all_dates:
        inception_date = date(2024, 1, 1)  # Default inception
        return pd.DataFrame([{
            'Date': inception_date,
            'Type': 'Seed Capital',
            'Description': 'Initial capital injection',
            'Cash IN': seed_capital,
            'Cash OUT': 0,
            'Net Cashflow': seed_capital,
            'Settlement Balance': seed_capital
        }])
    
    inception_date = min(all_dates)
    # Extend to 2 years in future for projections
    end_date = date.today() + timedelta(days=730)
    
    # Generate daily cashflows
    cashflows = []
    
    # Day 0: Seed capital injection
    cashflows.append({
        'Date': inception_date,
        'Type': 'Seed Capital',
        'Description': 'Initial capital injection',
        'Cash IN': seed_capital,
        'Cash OUT': 0,
        'Net Cashflow': seed_capital
    })
    
    # Repo borrowing (near leg - cash IN)
    for repo in repo_trades:
        spot = repo.get('spot_date')
        if isinstance(spot, str):
            spot = datetime.strptime(spot, '%Y-%m-%d').date()
        
        cash_amt = repo.get('cash_amount', 0)
        
        if repo.get('direction') == 'borrow_cash':
            cashflows.append({
                'Date': spot,
                'Type': 'Repo Borrowing',
                'Description': f"Repo {repo.get('id', 'Unknown')[:8]} - Borrow cash",
                'Cash IN': cash_amt,
                'Cash OUT': 0,
                'Net Cashflow': cash_amt
            })
    
    # Portfolio purchases (cash OUT)
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        
        notional = pos.get('notional', 0)
        
        cashflows.append({
            'Date': start,
            'Type': 'Portfolio Purchase',
            'Description': f"Buy {pos.get('name', 'Unknown')} - R{notional:,.0f}",
            'Cash IN': 0,
            'Cash OUT': notional,
            'Net Cashflow': -notional
        })
    
    # FRN Coupons (cash IN) - quarterly payments every 91 days
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        
        # Generate quarterly coupon dates (every 91 days from start)
        current_coupon_date = start + timedelta(days=91)
        while current_coupon_date <= min(maturity, end_date):
            # Estimate coupon: (JIBAR + spread) * notional * (91/365)
            jibar_rate = 6.6 / 100  # Default JIBAR
            coupon_rate = jibar_rate + (spread / 10000)
            coupon_amount = notional * coupon_rate * (91 / 365.0)
            
            cashflows.append({
                'Date': current_coupon_date,
                'Type': 'FRN Coupon',
                'Description': f"{pos.get('name', 'Unknown')} - Quarterly coupon",
                'Cash IN': coupon_amount,
                'Cash OUT': 0,
                'Net Cashflow': coupon_amount
            })
            
            current_coupon_date += timedelta(days=91)
    
    # Repo repayments (far leg - cash OUT)
    for repo in repo_trades:
        spot = repo.get('spot_date')
        end = repo.get('end_date')
        
        if isinstance(spot, str):
            spot = datetime.strptime(spot, '%Y-%m-%d').date()
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d').date()
        
        cash_amt = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        days = (end - spot).days
        
        # Calculate interest
        repo_rate = (6.6 / 100) + (spread / 10000)  # JIBAR + spread
        interest = cash_amt * repo_rate * (days / 365.0)
        
        if repo.get('direction') == 'borrow_cash':
            cashflows.append({
                'Date': end,
                'Type': 'Repo Repayment',
                'Description': f"Repo {repo.get('id', 'Unknown')[:8]} - Repay principal + interest",
                'Cash IN': 0,
                'Cash OUT': cash_amt + interest,
                'Net Cashflow': -(cash_amt + interest)
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(cashflows)
    
    if df.empty:
        return df
    
    # Sort by date
    df = df.sort_values('Date')
    
    # Calculate cumulative balance
    df['Settlement Balance'] = df['Net Cashflow'].cumsum()
    
    return df


def render_settlement_account_tracker(portfolio, repo_trades, seed_capital=100_000_000):
    """
    Render comprehensive settlement account tracker with tables and charts
    """
    
    st.markdown("##### 💰 Settlement Account Tracker")
    
    st.info(
        "**Settlement Account = Your Cash Account**\n\n" +
        "Tracks all cash movements:\n" +
        "- **Cash IN:** Seed capital, Repo borrowing, FRN coupons\n" +
        "- **Cash OUT:** Portfolio purchases, Repo repayments\n\n" +
        "**Balance Sheet Check:**\n" +
        "`Total Assets = Portfolio MV + Settlement Cash Balance`"
    )
    
    # Calculate settlement account history
    df_settlement = calculate_settlement_account_history(portfolio, repo_trades, seed_capital)
    
    if df_settlement.empty:
        st.warning("No settlement account data available.")
        return
    
    # Current settlement balance
    current_balance = df_settlement['Settlement Balance'].iloc[-1]
    total_cash_in = df_settlement['Cash IN'].sum()
    total_cash_out = df_settlement['Cash OUT'].sum()
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Cash Balance", f"R{current_balance/1e6:.1f}M")
    col2.metric("Total Cash IN", f"R{total_cash_in/1e6:.1f}M")
    col3.metric("Total Cash OUT", f"R{total_cash_out/1e6:.1f}M")
    col4.metric("Net Cashflow", f"R{(total_cash_in - total_cash_out)/1e6:.1f}M")
    
    # Settlement account balance chart
    st.markdown("###### Settlement Account Balance Over Time")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_settlement['Date'],
        y=df_settlement['Settlement Balance'] / 1e6,
        mode='lines+markers',
        name='Cash Balance',
        line=dict(color='#00d4ff', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.2)',
        hovertemplate='<b>%{x}</b><br>Balance: R%{y:.1f}M<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    
    fig.update_layout(
        title='Settlement Account Balance (Daily)',
        xaxis_title='Date',
        yaxis_title='Cash Balance (R Millions)',
        template='plotly_dark',
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Cashflow waterfall chart
    st.markdown("###### Cashflow Waterfall")
    
    # Aggregate by type
    cashflow_summary = df_settlement.groupby('Type').agg({
        'Cash IN': 'sum',
        'Cash OUT': 'sum',
        'Net Cashflow': 'sum'
    }).reset_index()
    
    fig_waterfall = go.Figure(go.Waterfall(
        name="Cashflows",
        orientation="v",
        measure=["relative"] * len(cashflow_summary) + ["total"],
        x=list(cashflow_summary['Type']) + ['Current Balance'],
        y=list(cashflow_summary['Net Cashflow'] / 1e6) + [current_balance / 1e6],
        text=[f"R{v/1e6:.1f}M" for v in cashflow_summary['Net Cashflow']] + [f"R{current_balance/1e6:.1f}M"],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#00ff88"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#00d4ff"}}
    ))
    
    fig_waterfall.update_layout(
        title="Settlement Account Waterfall (by Type)",
        yaxis_title="Cashflow (R Millions)",
        template='plotly_dark',
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig_waterfall, use_container_width=True)
    
    # Detailed transaction table
    st.markdown("###### All Settlement Account Transactions")
    
    st.dataframe(df_settlement.style.format({
        'Cash IN': 'R{:,.0f}',
        'Cash OUT': 'R{:,.0f}',
        'Net Cashflow': 'R{:+,.0f}',
        'Settlement Balance': 'R{:,.0f}'
    }).background_gradient(subset=['Settlement Balance'], cmap='RdYlGn'),
    use_container_width=True, height=400)
    
    # Export option
    if st.button("📥 Export Settlement Account History (CSV)", key="export_settlement_tracker"):
        csv = df_settlement.to_csv(index=False)
        st.download_button("Download CSV", csv, "settlement_account_history.csv", "text/csv")
