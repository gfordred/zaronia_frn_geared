"""
Funding Risk Analysis Module
Analyzes rollover risk when repo lenders don't roll loans
Critical for leveraged portfolio management
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import numpy as np


def analyze_repo_maturity_profile(repo_trades):
    """
    Analyze when repos mature and funding needs to be rolled
    
    Returns:
        DataFrame with maturity profile
    """
    
    maturity_data = []
    today = date.today()
    
    for repo in repo_trades:
        end_date = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        # Only active repos
        if end_date >= today:
            days_to_maturity = (end_date - today).days
            cash_amount = repo.get('cash_amount', 0)
            direction = repo.get('direction', 'borrow_cash')
            
            if direction == 'borrow_cash':
                maturity_data.append({
                    'Repo ID': repo.get('id', 'Unknown'),
                    'End Date': end_date,
                    'Days to Maturity': days_to_maturity,
                    'Cash Amount': cash_amount,
                    'Spread (bps)': repo.get('repo_spread_bps', 0),
                    'Collateral': repo.get('collateral_id', 'Unknown'),
                    'Maturity Bucket': get_maturity_bucket(days_to_maturity)
                })
    
    return pd.DataFrame(maturity_data)


def get_maturity_bucket(days):
    """Categorize maturity into buckets"""
    if days <= 7:
        return '0-7 days'
    elif days <= 30:
        return '8-30 days'
    elif days <= 90:
        return '31-90 days'
    else:
        return '90+ days'


def calculate_funding_gap_scenarios(portfolio, repo_trades, rollover_rates):
    """
    Calculate funding gap if repos don't roll
    
    Args:
        portfolio: List of positions
        repo_trades: List of repo trades
        rollover_rates: Dict of rollover assumptions (e.g., {'7d': 0.5, '30d': 0.8})
    
    Returns:
        DataFrame with scenarios
    """
    
    total_notional = sum(p.get('notional', 0) for p in portfolio)
    total_repo = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'borrow_cash' and 
                     (r['end_date'] if isinstance(r['end_date'], date) else datetime.strptime(r['end_date'], '%Y-%m-%d').date()) >= date.today())
    
    df_maturity = analyze_repo_maturity_profile(repo_trades)
    
    scenarios = []
    
    for bucket, rollover_rate in rollover_rates.items():
        bucket_repos = df_maturity[df_maturity['Maturity Bucket'] == bucket]
        bucket_amount = bucket_repos['Cash Amount'].sum() if len(bucket_repos) > 0 else 0
        
        # Amount that doesn't roll
        funding_gap = bucket_amount * (1 - rollover_rate)
        
        # Impact on gearing
        new_repo = total_repo - funding_gap
        new_gearing = new_repo / total_notional if total_notional > 0 else 0
        
        # Forced liquidation if gap too large
        forced_liquidation = 0
        if funding_gap > total_notional * 0.1:  # If gap > 10% of portfolio
            forced_liquidation = funding_gap - (total_notional * 0.1)
        
        scenarios.append({
            'Maturity Bucket': bucket,
            'Repos Maturing': bucket_amount,
            'Rollover Rate': rollover_rate * 100,
            'Amount Not Rolled': funding_gap,
            'New Total Repo': new_repo,
            'New Gearing': new_gearing,
            'Forced Liquidation': forced_liquidation,
            'Severity': 'High' if funding_gap > total_notional * 0.2 else 'Medium' if funding_gap > total_notional * 0.1 else 'Low'
        })
    
    return pd.DataFrame(scenarios)


def render_funding_risk_analysis(portfolio, repo_trades):
    """
    Render comprehensive funding risk analysis
    Focus on rollover risk when lenders don't roll loans
    """
    
    st.markdown("### ⚠️ Funding Risk Analysis")
    
    st.warning("""
    **Critical Funding Risk Considerations:**
    
    This section analyzes the risk that repo lenders may not roll (renew) their loans at maturity.
    
    **Key Risks:**
    - **Rollover Risk:** Lender refuses to renew repo at maturity
    - **Forced Liquidation:** Must sell positions to repay maturing repos
    - **Market Impact:** Forced sales may occur at unfavorable prices
    - **Gearing Collapse:** Loss of leverage reduces portfolio returns
    
    **Mitigation Strategies:**
    - Diversify repo counterparties
    - Stagger repo maturities
    - Maintain liquidity buffer
    - Have backup funding lines
    """)
    
    if not repo_trades:
        st.info("No active repos to analyze.")
        return
    
    # Calculate metrics
    total_notional = sum(p.get('notional', 0) for p in portfolio)
    total_repo = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'borrow_cash' and 
                     (r['end_date'] if isinstance(r['end_date'], date) else datetime.strptime(r['end_date'], '%Y-%m-%d').date()) >= date.today())
    current_gearing = total_repo / total_notional if total_notional > 0 else 0
    
    # Summary metrics
    st.markdown("##### Current Funding Position")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Repo Funding", f"R{total_repo/1e9:.2f}B")
    m2.metric("Portfolio Notional", f"R{total_notional/1e9:.2f}B")
    m3.metric("Current Gearing", f"{current_gearing:.2f}x")
    m4.metric("Funding Dependency", f"{(total_repo/total_notional)*100:.1f}%")
    
    # Maturity profile
    st.markdown("---")
    st.markdown("##### Repo Maturity Profile")
    
    df_maturity = analyze_repo_maturity_profile(repo_trades)
    
    if df_maturity.empty:
        st.info("No active repos maturing.")
        return
    
    # Maturity table
    st.dataframe(df_maturity.style.format({
        'Cash Amount': 'R{:,.2f}',
        'Spread (bps)': '{:.1f}'
    }), use_container_width=True, hide_index=True)
    
    # Maturity concentration chart
    fig_maturity = go.Figure()
    
    bucket_summary = df_maturity.groupby('Maturity Bucket')['Cash Amount'].sum().reset_index()
    bucket_order = ['0-7 days', '8-30 days', '31-90 days', '90+ days']
    bucket_summary['Maturity Bucket'] = pd.Categorical(bucket_summary['Maturity Bucket'], categories=bucket_order, ordered=True)
    bucket_summary = bucket_summary.sort_values('Maturity Bucket')
    
    colors = {'0-7 days': '#ff6b6b', '8-30 days': '#ffa500', '31-90 days': '#00ff88', '90+ days': '#00d4ff'}
    
    fig_maturity.add_trace(go.Bar(
        x=bucket_summary['Maturity Bucket'],
        y=bucket_summary['Cash Amount']/1e9,
        marker_color=[colors.get(b, '#ffffff') for b in bucket_summary['Maturity Bucket']],
        text=[f"R{v/1e9:.2f}B" for v in bucket_summary['Cash Amount']],
        textposition='outside'
    ))
    
    fig_maturity.update_layout(
        title='Repo Funding by Maturity Bucket',
        xaxis_title='Time to Maturity',
        yaxis_title='Funding Amount (R Billions)',
        template='plotly_dark',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig_maturity, use_container_width=True)
    
    # Rollover risk scenarios
    st.markdown("---")
    st.markdown("##### Rollover Risk Scenarios")
    
    st.info("""
    **Scenario Analysis:** What happens if repos don't roll?
    
    Assumptions for rollover rates by maturity bucket:
    - **0-7 days:** 50% rollover (high risk - short term)
    - **8-30 days:** 70% rollover (medium risk)
    - **31-90 days:** 85% rollover (lower risk)
    - **90+ days:** 95% rollover (lowest risk)
    """)
    
    rollover_assumptions = {
        '0-7 days': 0.5,
        '8-30 days': 0.7,
        '31-90 days': 0.85,
        '90+ days': 0.95
    }
    
    df_scenarios = calculate_funding_gap_scenarios(portfolio, repo_trades, rollover_assumptions)
    
    # Scenarios table
    st.dataframe(df_scenarios.style.format({
        'Repos Maturing': 'R{:,.2f}',
        'Rollover Rate': '{:.0f}%',
        'Amount Not Rolled': 'R{:,.2f}',
        'New Total Repo': 'R{:,.2f}',
        'New Gearing': '{:.2f}x',
        'Forced Liquidation': 'R{:,.2f}'
    }), use_container_width=True, hide_index=True)
    
    # Scenario impact chart
    fig_scenarios = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Funding Gap by Bucket', 'Gearing Impact'),
        specs=[[{"type": "bar"}, {"type": "scatter"}]]
    )
    
    # Funding gap
    fig_scenarios.add_trace(
        go.Bar(
            x=df_scenarios['Maturity Bucket'],
            y=df_scenarios['Amount Not Rolled']/1e9,
            name='Funding Gap',
            marker_color='#ff6b6b',
            text=[f"R{v/1e9:.2f}B" for v in df_scenarios['Amount Not Rolled']],
            textposition='outside'
        ),
        row=1, col=1
    )
    
    # Gearing impact
    fig_scenarios.add_trace(
        go.Scatter(
            x=df_scenarios['Maturity Bucket'],
            y=df_scenarios['New Gearing'],
            mode='lines+markers',
            name='New Gearing',
            line=dict(color='#ffa500', width=3),
            marker=dict(size=12)
        ),
        row=1, col=2
    )
    
    # Add current gearing line
    fig_scenarios.add_hline(
        y=current_gearing,
        line_dash="dash",
        line_color="cyan",
        annotation_text=f"Current: {current_gearing:.2f}x",
        row=1, col=2
    )
    
    fig_scenarios.update_xaxes(title_text="Maturity Bucket", row=1, col=1)
    fig_scenarios.update_xaxes(title_text="Maturity Bucket", row=1, col=2)
    fig_scenarios.update_yaxes(title_text="Gap (R Billions)", row=1, col=1)
    fig_scenarios.update_yaxes(title_text="Gearing (x)", row=1, col=2)
    
    fig_scenarios.update_layout(
        template='plotly_dark',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig_scenarios, use_container_width=True)
    
    # Risk summary
    st.markdown("---")
    st.markdown("##### Risk Summary & Recommendations")
    
    # Calculate risk metrics
    near_term_repos = df_maturity[df_maturity['Days to Maturity'] <= 30]['Cash Amount'].sum()
    near_term_pct = (near_term_repos / total_repo * 100) if total_repo > 0 else 0
    
    max_gap = df_scenarios['Amount Not Rolled'].max()
    max_gap_pct = (max_gap / total_notional * 100) if total_notional > 0 else 0
    
    # Risk level
    if near_term_pct > 50:
        risk_level = "🔴 **HIGH RISK**"
        risk_color = "red"
    elif near_term_pct > 30:
        risk_level = "🟠 **MEDIUM RISK**"
        risk_color = "orange"
    else:
        risk_level = "🟢 **LOW RISK**"
        risk_color = "green"
    
    st.markdown(f"**Overall Funding Risk Level:** {risk_level}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Key Metrics:**")
        st.markdown(f"- Near-term repos (≤30d): **R{near_term_repos/1e9:.2f}B** ({near_term_pct:.1f}% of total)")
        st.markdown(f"- Maximum funding gap: **R{max_gap/1e9:.2f}B** ({max_gap_pct:.1f}% of portfolio)")
        st.markdown(f"- Number of repos maturing: **{len(df_maturity)}**")
    
    with col2:
        st.markdown("**Recommendations:**")
        if near_term_pct > 50:
            st.markdown("- ⚠️ **URGENT:** Extend repo maturities immediately")
            st.markdown("- ⚠️ Reduce gearing to lower funding dependency")
            st.markdown("- ⚠️ Establish backup credit lines")
        elif near_term_pct > 30:
            st.markdown("- ⚠️ Consider extending some repo maturities")
            st.markdown("- Monitor lender relationships closely")
            st.markdown("- Prepare contingency funding plan")
        else:
            st.markdown("- ✅ Maturity profile is well-distributed")
            st.markdown("- Continue monitoring rollover rates")
            st.markdown("- Maintain diversified lender base")
