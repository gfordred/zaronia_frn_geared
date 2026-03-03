"""
Enhanced Repo Trades Tab - Bank Grade A+ Quality
To be integrated into app.py TAB 7

This module provides comprehensive repo trade analytics with:
- Dashboard with key metrics
- Maturity ladder visualization
- P&L analytics
- Term structure analysis
- Professional institutional-grade charts
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime, timedelta
import uuid


def render_repo_dashboard(repo_trades, evaluation_date, rates):
    """Render comprehensive repo dashboard with analytics"""
    
    st.markdown("##### 📊 Repo Book Overview")
    
    if not repo_trades:
        st.info("No repo trades. Add trades in the 'Add Trade' tab.")
        return
    
    # Calculate summary metrics
    borrow_trades = [r for r in repo_trades if r.get('direction') == 'borrow_cash']
    lend_trades = [r for r in repo_trades if r.get('direction') == 'lend_cash']
    
    total_borrow = sum(r.get('cash_amount', 0) for r in borrow_trades)
    total_lend = sum(r.get('cash_amount', 0) for r in lend_trades)
    net_financing = total_borrow - total_lend
    
    # Weighted average spreads
    wa_borrow_spread = (sum(r.get('cash_amount', 0) * r.get('repo_spread_bps', 0) for r in borrow_trades) / total_borrow 
                       if total_borrow > 0 else 0)
    wa_lend_spread = (sum(r.get('cash_amount', 0) * r.get('repo_spread_bps', 0) for r in lend_trades) / total_lend 
                     if total_lend > 0 else 0)
    
    # Display metrics - Row 1
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Trades", f"{len(repo_trades)}", help="Number of active repo trades")
    m2.metric("Gross Borrowing", f"R{total_borrow/1e6:.1f}M", help="Total cash borrowed via repos")
    m3.metric("Gross Lending", f"R{total_lend/1e6:.1f}M", help="Total cash lent via reverse repos")
    m4.metric("Net Financing", f"R{net_financing/1e6:.1f}M", 
             delta=f"{'Net Borrower' if net_financing > 0 else 'Net Lender'}")
    
    # Display metrics - Row 2
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Borrow Trades", f"{len(borrow_trades)}")
    m6.metric("Lend Trades", f"{len(lend_trades)}")
    m7.metric("WA Borrow Spread", f"{wa_borrow_spread:.1f} bps", help="Weighted average borrowing spread")
    m8.metric("WA Lend Spread", f"{wa_lend_spread:.1f} bps", help="Weighted average lending spread")
    
    # Maturity Ladder Chart
    st.markdown("---")
    st.markdown("##### 📅 Repo Maturity Ladder")
    
    maturity_data = []
    for repo in repo_trades:
        end_date = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        cash = repo.get('cash_amount', 0)
        direction = repo.get('direction', 'borrow_cash')
        
        maturity_data.append({
            'End Date': end_date,
            'Cash Amount': cash if direction == 'borrow_cash' else -cash,
            'Direction': 'Borrow' if direction == 'borrow_cash' else 'Lend',
            'Repo ID': repo.get('id', 'Unknown')[:12]
        })
    
    df_maturity = pd.DataFrame(maturity_data).sort_values('End Date')
    df_maturity['Cumulative'] = df_maturity['Cash Amount'].cumsum()
    
    # Create maturity ladder chart
    fig_ladder = go.Figure()
    
    # Add bars for each maturity
    colors = ['#00d4ff' if d == 'Borrow' else '#ff6b6b' for d in df_maturity['Direction']]
    fig_ladder.add_trace(go.Bar(
        x=df_maturity['End Date'],
        y=df_maturity['Cash Amount'],
        name='Repo Maturities',
        marker_color=colors,
        text=df_maturity['Repo ID'],
        hovertemplate='<b>%{text}</b><br>Maturity: %{x}<br>Amount: R%{y:,.0f}<extra></extra>'
    ))
    
    # Add cumulative line
    fig_ladder.add_trace(go.Scatter(
        x=df_maturity['End Date'],
        y=df_maturity['Cumulative'],
        name='Cumulative Financing',
        mode='lines+markers',
        line=dict(color='#ffa500', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig_ladder.update_layout(
        title='Repo Maturity Ladder & Cumulative Financing Profile',
        xaxis_title='Maturity Date',
        yaxis_title='Cash Amount (R)',
        yaxis2=dict(title='Cumulative Financing (R)', overlaying='y', side='right'),
        template='plotly_dark',
        hovermode='x unified',
        height=500,
        barmode='relative',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_ladder, use_container_width=True)
    
    # Pie Charts Row
    st.markdown("---")
    st.markdown("##### 📊 Portfolio Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Direction split
        if total_borrow > 0 or total_lend > 0:
            fig_dir = px.pie(
                values=[total_borrow, total_lend],
                names=['Borrow Cash', 'Lend Cash'],
                title='Repo Direction Split (by Notional)',
                color_discrete_sequence=['#00d4ff', '#ff6b6b'],
                hole=0.4
            )
            fig_dir.update_layout(template='plotly_dark')
            fig_dir.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_dir, use_container_width=True)
    
    with col2:
        # Term structure buckets
        term_buckets = {'0-30d': 0, '31-60d': 0, '61-90d': 0, '90d+': 0}
        for repo in repo_trades:
            spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
            end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
            days = (end - spot).days
            cash = repo.get('cash_amount', 0)
            
            if days <= 30:
                term_buckets['0-30d'] += cash
            elif days <= 60:
                term_buckets['31-60d'] += cash
            elif days <= 90:
                term_buckets['61-90d'] += cash
            else:
                term_buckets['90d+'] += cash
        
        fig_term = px.pie(
            values=list(term_buckets.values()),
            names=list(term_buckets.keys()),
            title='Term Structure (by Notional)',
            color_discrete_sequence=px.colors.sequential.Blues_r,
            hole=0.4
        )
        fig_term.update_layout(template='plotly_dark')
        fig_term.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_term, use_container_width=True)


def render_repo_analytics(repo_trades, evaluation_date, rates):
    """Render detailed repo analytics and P&L"""
    
    st.markdown("##### 📈 Repo Analytics & P&L")
    
    if not repo_trades:
        st.info("No repo trades for analytics.")
        return
    
    # Spread term structure scatter
    st.markdown("###### Repo Spread Term Structure")
    
    spread_data = []
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        days = (end - spot).days
        
        spread_data.append({
            'Days': days,
            'Spread (bps)': repo.get('repo_spread_bps', 0),
            'Direction': 'Borrow' if repo.get('direction') == 'borrow_cash' else 'Lend',
            'Repo ID': repo.get('id', 'Unknown')[:12],
            'Cash (M)': repo.get('cash_amount', 0) / 1e6
        })
    
    df_spread = pd.DataFrame(spread_data)
    
    fig_spread_term = px.scatter(
        df_spread,
        x='Days',
        y='Spread (bps)',
        color='Direction',
        size='Cash (M)',
        hover_data=['Repo ID', 'Cash (M)'],
        title='Repo Spread by Term (bubble size = notional)',
        color_discrete_map={'Borrow': '#00d4ff', 'Lend': '#ff6b6b'}
    )
    fig_spread_term.update_layout(template='plotly_dark', height=450)
    fig_spread_term.update_traces(marker=dict(line=dict(width=1, color='white')))
    st.plotly_chart(fig_spread_term, use_container_width=True)
    
    # P&L Summary
    st.markdown("---")
    st.markdown("###### Estimated P&L Summary")
    
    total_interest_paid = 0
    total_interest_earned = 0
    
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        days = (end - spot).days
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        repo_rate = (rates.get('JIBAR3M', 8.0) + spread) / 100
        interest = cash * repo_rate * (days / 365.0)
        
        if repo.get('direction') == 'borrow_cash':
            total_interest_paid += interest
        else:
            total_interest_earned += interest
    
    net_interest = total_interest_earned - total_interest_paid
    
    pnl1, pnl2, pnl3, pnl4 = st.columns(4)
    pnl1.metric("Interest Paid", f"R{total_interest_paid:,.0f}", delta="Funding Cost", delta_color="inverse")
    pnl2.metric("Interest Earned", f"R{total_interest_earned:,.0f}", delta="Income", delta_color="normal")
    pnl3.metric("Net Interest P&L", f"R{net_interest:,.0f}", 
               delta=f"{'Profit' if net_interest > 0 else 'Loss'}")
    pnl4.metric("Net Margin", f"{(net_interest / (total_interest_paid + total_interest_earned) * 100) if (total_interest_paid + total_interest_earned) > 0 else 0:.2f}%")
    
    # P&L breakdown chart
    st.markdown("###### P&L Breakdown by Trade")
    
    pnl_data = []
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        days = (end - spot).days
        cash = repo.get('cash_amount', 0)
        spread = repo.get('repo_spread_bps', 0)
        repo_rate = (rates.get('JIBAR3M', 8.0) + spread) / 100
        interest = cash * repo_rate * (days / 365.0)
        
        direction = repo.get('direction', 'borrow_cash')
        pnl = -interest if direction == 'borrow_cash' else interest
        
        pnl_data.append({
            'Repo ID': repo.get('id', 'Unknown')[:12],
            'P&L': pnl,
            'Direction': 'Borrow' if direction == 'borrow_cash' else 'Lend'
        })
    
    df_pnl = pd.DataFrame(pnl_data).sort_values('P&L')
    
    fig_pnl = go.Figure()
    colors = ['#ff6b6b' if p < 0 else '#00ff88' for p in df_pnl['P&L']]
    fig_pnl.add_trace(go.Bar(
        x=df_pnl['Repo ID'],
        y=df_pnl['P&L'],
        marker_color=colors,
        text=df_pnl['P&L'].apply(lambda x: f"R{x:,.0f}"),
        textposition='outside'
    ))
    
    fig_pnl.update_layout(
        title='P&L by Repo Trade (Red=Cost, Green=Income)',
        xaxis_title='Repo ID',
        yaxis_title='P&L (R)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig_pnl, use_container_width=True)


# Example usage in app.py:
"""
# In TAB 7, replace the current content with:

repo_subtabs = st.tabs(["📊 Dashboard", "📋 All Trades", "📈 Analytics", "➕ Add Trade", "🔍 Details"])

with repo_subtabs[0]:
    render_repo_dashboard(repo_trades, evaluation_date, rates)

with repo_subtabs[2]:
    render_repo_analytics(repo_trades, evaluation_date, rates)
"""
