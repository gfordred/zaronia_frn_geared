"""
Yield Attribution Engine - Gearing Impact Analysis
Calculates and displays how repo financing boosts portfolio yields

Key Concepts:
- Gross Yield: FRN coupon income / Portfolio Notional
- Repo Cost: Repo interest / Repo Outstanding
- Net Yield: (FRN Income - Repo Cost) / Portfolio Notional
- Gearing Benefit: How leverage amplifies returns

With 10x gearing, even small spread differences create significant yield enhancement
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def calculate_geared_yields(portfolio, repo_trades, jibar_rate=8.0):
    """
    Calculate comprehensive yield metrics showing gearing impact
    
    Returns:
        dict with all yield components
    """
    
    # Portfolio metrics
    total_notional = sum(pos.get('notional', 0) for pos in portfolio)
    
    # Calculate repo outstanding first (needed for geared income calculation)
    repo_cost = 0
    total_repo_outstanding = 0
    
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        # Check if active
        if end >= date.today():
            cash = repo.get('cash_amount', 0)
            spread_bps = repo.get('repo_spread_bps', 0)
            direction = repo.get('direction', 'borrow_cash')
            
            if direction == 'borrow_cash':
                total_repo_outstanding += cash
                # Repo rate = JIBAR (%) + spread (bps converted to %)
                repo_rate = (jibar_rate / 100) + (spread_bps / 10000)
                annual_cost = cash * repo_rate
                repo_cost += annual_cost
    
    # Gearing metrics - CORRECTED
    # Gearing = Repo Outstanding / Seed Capital (NOT Total Notional)
    # This shows true leverage: how many times we've borrowed relative to equity
    SEED_CAPITAL = 100_000_000  # R100M
    gearing = total_repo_outstanding / SEED_CAPITAL if SEED_CAPITAL > 0 else 0
    
    # Calculate FRN income (annual) on TOTAL GEARED ASSETS
    # With gearing, we earn on: Base Portfolio + Borrowed Funds invested in FRNs
    total_geared_notional = total_notional + total_repo_outstanding
    
    frn_income = 0
    for pos in portfolio:
        notional = pos.get('notional', 0)
        spread_bps = pos.get('issue_spread', 0)
        # Coupon rate = JIBAR (%) + spread (bps converted to %)
        coupon_rate = (jibar_rate / 100) + (spread_bps / 10000)
        # Scale income by gearing factor (earning on geared notional, not just base)
        geared_notional = notional * (1 + gearing)
        annual_income = geared_notional * coupon_rate
        frn_income += annual_income
    
    # Average spreads (in bps)
    avg_frn_spread = sum(pos.get('issue_spread', 0) for pos in portfolio) / len(portfolio) if portfolio else 0
    avg_repo_spread = sum(r.get('repo_spread_bps', 0) for r in repo_trades if r.get('direction') == 'borrow_cash') / len([r for r in repo_trades if r.get('direction') == 'borrow_cash']) if repo_trades else 0
    spread_pickup = avg_frn_spread - avg_repo_spread  # in bps
    
    # CORRECT BANK-GRADE YIELD CALCULATIONS
    # For a leveraged portfolio earning on geared assets:
    
    # 1. Gross Yield = FRN coupon rate (JIBAR + avg spread)
    gross_yield = jibar_rate + (avg_frn_spread / 100)  # in %
    
    # 2. Repo Cost Rate = Repo rate (JIBAR + avg repo spread)
    repo_cost_rate = jibar_rate + (avg_repo_spread / 100)  # in %
    
    # 3. Net Yield on Equity = Gross Yield + (Spread Pickup × (Gearing - 1))
    # This is the return on equity invested, accounting for leverage benefit
    # Formula: We earn gross yield on notional + spread pickup on borrowed amount
    net_yield = gross_yield + ((spread_pickup / 100) * (gearing - 1))
    
    # 4. Gearing Benefit = Spread Pickup × (Gearing - 1)
    # This shows the additional yield from leverage (excluding base yield)
    gearing_benefit = (spread_pickup / 100) * (gearing - 1)  # in %
    
    # 5. Net income calculation (for reference)
    net_income = frn_income - repo_cost
    
    # Return on Equity = Net Yield (already calculated above)
    # For a leveraged portfolio, ROE is the net yield on equity invested
    # This equals: Gross Yield + Gearing Benefit
    roe = net_yield
    
    return {
        'total_notional': total_notional,
        'total_repo_outstanding': total_repo_outstanding,
        'gearing': gearing,
        'frn_income': frn_income,
        'repo_cost': repo_cost,
        'net_income': net_income,
        'gross_yield': gross_yield,
        'repo_cost_rate': repo_cost_rate,
        'net_yield': net_yield,
        'avg_frn_spread': avg_frn_spread,
        'avg_repo_spread': avg_repo_spread,
        'spread_pickup': spread_pickup,
        'gearing_benefit': gearing_benefit,
        'roe': roe,
        'jibar_rate': jibar_rate
    }


def render_yield_attribution(portfolio, repo_trades, jibar_rate=8.0):
    """
    Render comprehensive yield attribution showing gearing impact
    """
    
    st.markdown("##### 💰 Yield Attribution & Gearing Impact")
    
    st.info("""
    **Gearing Impact on Yields:**
    
    With 10x gearing, the portfolio earns on R30B of assets while only investing R3B of capital.
    
    **Formula:**
    - **Gross Yield** = FRN Income / Portfolio Notional
    - **Net Yield** = (FRN Income - Repo Cost) / Portfolio Notional
    - **Gearing Benefit** = Spread Pickup × Gearing Ratio
    
    Even a small spread advantage (FRN spread > Repo spread) gets multiplied by the gearing!
    """)
    
    # Calculate yields
    metrics = calculate_geared_yields(portfolio, repo_trades, jibar_rate)
    
    # Display key metrics
    st.markdown("###### Key Yield Metrics")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross Yield", f"{metrics['gross_yield']:.2f}%", 
             help="FRN coupon income / Portfolio notional")
    m2.metric("Repo Cost Rate", f"{metrics['repo_cost_rate']:.2f}%",
             help="Repo interest / Repo outstanding")
    m3.metric("Net Yield", f"{metrics['net_yield']:.2f}%",
             help="(FRN income - Repo cost) / Portfolio notional")
    m4.metric("Gearing", f"{metrics['gearing']:.2f}x",
             help="Repo outstanding / Portfolio notional")
    
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("FRN Spread (avg)", f"{metrics['avg_frn_spread']:.0f} bps")
    m6.metric("Repo Spread (avg)", f"{metrics['avg_repo_spread']:.0f} bps")
    m7.metric("Spread Pickup", f"{metrics['spread_pickup']:.0f} bps",
             help="FRN spread - Repo spread")
    m8.metric("Gearing Benefit", f"{metrics['gearing_benefit']*100:.2f}%",
             help="Spread pickup × Gearing")
    
    # Bar charts for visual comparison
    st.markdown("###### Visual Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Yield comparison bar chart
        fig_yields_bar = go.Figure()
        
        fig_yields_bar.add_trace(go.Bar(
            x=['Gross Yield', 'Repo Cost', 'Net Yield'],
            y=[metrics['gross_yield'], metrics['repo_cost_rate'], metrics['net_yield']],
            marker_color=['#00ff88', '#ff6b6b', '#00d4ff'],
            text=[f"{metrics['gross_yield']:.2f}%", 
                  f"{metrics['repo_cost_rate']:.2f}%", 
                  f"{metrics['net_yield']:.2f}%"],
            textposition='outside'
        ))
        
        fig_yields_bar.update_layout(
            title='Yield Comparison',
            yaxis_title='Yield (%)',
            template='plotly_dark',
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig_yields_bar, use_container_width=True)
    
    with col2:
        # Spread comparison bar chart
        fig_spreads_bar = go.Figure()
        
        fig_spreads_bar.add_trace(go.Bar(
            x=['FRN Spread', 'Repo Spread', 'Pickup'],
            y=[metrics['avg_frn_spread'], metrics['avg_repo_spread'], metrics['spread_pickup']],
            marker_color=['#00ff88', '#ffa500', '#00d4ff'],
            text=[f"{metrics['avg_frn_spread']:.0f} bps", 
                  f"{metrics['avg_repo_spread']:.0f} bps", 
                  f"{metrics['spread_pickup']:.0f} bps"],
            textposition='outside'
        ))
        
        fig_spreads_bar.update_layout(
            title='Spread Breakdown',
            yaxis_title='Spread (bps)',
            template='plotly_dark',
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig_spreads_bar, use_container_width=True)
    
    # Notional by counterparty bar chart
    st.markdown("###### Portfolio Breakdown by Counterparty")
    
    cpty_notionals = {}
    for pos in portfolio:
        cpty = pos.get('counterparty', 'Unknown')
        notional = pos.get('notional', 0)
        if cpty in cpty_notionals:
            cpty_notionals[cpty] += notional
        else:
            cpty_notionals[cpty] = notional
    
    fig_cpty_bar = go.Figure()
    
    fig_cpty_bar.add_trace(go.Bar(
        x=list(cpty_notionals.keys()),
        y=[v/1e6 for v in cpty_notionals.values()],
        marker_color=['#00d4ff', '#00ff88', '#ffa500', '#ff6b6b', '#9b59b6', '#3498db'],
        text=[f"R{v/1e6:.0f}M" for v in cpty_notionals.values()],
        textposition='outside'
    ))
    
    fig_cpty_bar.update_layout(
        title='Notional by Counterparty',
        xaxis_title='Counterparty',
        yaxis_title='Notional (R Millions)',
        template='plotly_dark',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig_cpty_bar, use_container_width=True)
    
    # Detailed breakdown
    st.markdown("###### Income & Cost Breakdown")
    
    breakdown_data = {
        'Component': [
            'Portfolio Notional',
            'Repo Outstanding',
            'Gearing Ratio',
            '',
            'JIBAR 3M',
            'Avg FRN Spread',
            'Avg Repo Spread',
            'Spread Pickup',
            '',
            'FRN Income (annual)',
            'Repo Cost (annual)',
            'Net Income',
            '',
            'Gross Yield',
            'Repo Cost Rate',
            'Net Yield',
            'Gearing Benefit',
            'Return on Equity'
        ],
        'Value': [
            f"R{metrics['total_notional']:,.2f}",
            f"R{metrics['total_repo_outstanding']:,.2f}",
            f"{metrics['gearing']:.2f}x",
            '',
            f"{metrics['jibar_rate']:.2f}%",
            f"{metrics['avg_frn_spread']:.0f} bps",
            f"{metrics['avg_repo_spread']:.0f} bps",
            f"{metrics['spread_pickup']:.0f} bps",
            '',
            f"R{metrics['frn_income']:,.2f}",
            f"R{metrics['repo_cost']:,.2f}",
            f"R{metrics['net_income']:,.2f}",
            '',
            f"{metrics['gross_yield']:.2f}%",
            f"{metrics['repo_cost_rate']:.2f}%",
            f"{metrics['net_yield']:.2f}%",
            f"{metrics['gearing_benefit']*100:.2f}%",
            f"{metrics['roe']:.2f}%"
        ]
    }
    
    df_breakdown = pd.DataFrame(breakdown_data)
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
    
    # Waterfall chart
    st.markdown("###### Yield Waterfall")
    
    fig = go.Figure(go.Waterfall(
        name="Yield Components",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["JIBAR 3M", "FRN Spread", "Gearing Benefit", "Gross Yield"],
        y=[metrics['jibar_rate'], 
           metrics['avg_frn_spread']/100, 
           metrics['gearing_benefit'],
           metrics['gross_yield']],
        text=[f"{metrics['jibar_rate']:.2f}%",
              f"+{metrics['avg_frn_spread']:.0f}bps",
              f"+{metrics['gearing_benefit']*100:.2f}%",
              f"{metrics['gross_yield']:.2f}%"],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#00ff88"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#00d4ff"}}
    ))
    
    fig.update_layout(
        title="Gross Yield Build-Up (with Gearing Impact)",
        yaxis_title="Yield (%)",
        template='plotly_dark',
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Gearing sensitivity
    st.markdown("###### Gearing Sensitivity Analysis")
    
    gearing_scenarios = [1, 2, 5, 10, 15, 20]
    scenario_data = []
    
    for g in gearing_scenarios:
        scenario_net_yield = metrics['jibar_rate'] + (metrics['avg_frn_spread']/100) + (metrics['spread_pickup']/100 * g) - (metrics['avg_repo_spread']/100 * g)
        scenario_data.append({
            'Gearing': f"{g}x",
            'Net Yield (%)': scenario_net_yield
        })
    
    df_scenarios = pd.DataFrame(scenario_data)
    
    fig_sens = go.Figure()
    
    fig_sens.add_trace(go.Scatter(
        x=[s['Gearing'] for s in scenario_data],
        y=[s['Net Yield (%)'] for s in scenario_data],
        mode='lines+markers',
        name='Net Yield',
        line=dict(color='#ffa500', width=3),
        marker=dict(size=12),
        text=[f"{s['Net Yield (%)']:.2f}%" for s in scenario_data],
        textposition='top center'
    ))
    
    # Mark current gearing
    current_idx = min(range(len(gearing_scenarios)), key=lambda i: abs(gearing_scenarios[i] - metrics['gearing']))
    fig_sens.add_trace(go.Scatter(
        x=[scenario_data[current_idx]['Gearing']],
        y=[scenario_data[current_idx]['Net Yield (%)']],
        mode='markers',
        marker=dict(size=20, color='red', symbol='star'),
        name='Current Gearing',
        showlegend=True
    ))
    
    fig_sens.update_layout(
        title='Net Yield vs Gearing Ratio',
        xaxis_title='Gearing',
        yaxis_title='Net Yield (%)',
        template='plotly_dark',
        height=400
    )
    
    st.plotly_chart(fig_sens, use_container_width=True)
    
    # Key insights
    st.markdown("###### Key Insights")
    
    if metrics['spread_pickup'] > 0:
        st.success(f"""
        ✅ **Positive Carry Trade**
        
        - FRN spread ({metrics['avg_frn_spread']:.0f} bps) > Repo spread ({metrics['avg_repo_spread']:.0f} bps)
        - Spread pickup: {metrics['spread_pickup']:.0f} bps
        - With {metrics['gearing']:.1f}x gearing, this adds {metrics['gearing_benefit']*100:.2f}% to yield
        - Net yield: {metrics['net_yield']:.2f}% (vs {metrics['jibar_rate']:.2f}% JIBAR)
        """)
    else:
        st.warning(f"""
        ⚠️ **Negative Carry**
        
        - Repo spread ({metrics['avg_repo_spread']:.0f} bps) > FRN spread ({metrics['avg_frn_spread']:.0f} bps)
        - This reduces net yield
        - Consider reducing gearing or improving FRN spreads
        """)


def render_composition_over_time(portfolio, repo_trades):
    """
    Render portfolio composition evolution as layered area chart
    Shows composition by counterparty over entire history
    """
    
    st.markdown("##### 📊 Portfolio Composition Over Time")
    
    # Get inception date (earliest start date)
    all_dates = []
    for pos in portfolio:
        start = pos.get('start_date')
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        all_dates.append(start)
    
    if not all_dates:
        st.warning("No portfolio positions to display.")
        return
    
    inception_date = min(all_dates)
    end_date = date.today()
    
    # Generate daily date range
    date_range = pd.date_range(start=inception_date, end=end_date, freq='D')
    
    # Calculate composition for each day
    composition_data = []
    
    for current_date in date_range:
        current_date_obj = current_date.date()
        
        # Calculate notional by counterparty on this date
        cpty_notionals = {}
        
        for pos in portfolio:
            start = pos.get('start_date')
            maturity = pos.get('maturity')
            
            if isinstance(start, str):
                start = datetime.strptime(start, '%Y-%m-%d').date()
            if isinstance(maturity, str):
                maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
            
            # Check if position is active on this date
            if start <= current_date_obj <= maturity:
                cpty = pos.get('counterparty', 'Unknown')
                notional = pos.get('notional', 0)
                
                if cpty in cpty_notionals:
                    cpty_notionals[cpty] += notional
                else:
                    cpty_notionals[cpty] = notional
        
        # Add to data
        row = {'Date': current_date_obj}
        row.update(cpty_notionals)
        composition_data.append(row)
    
    df_comp = pd.DataFrame(composition_data)
    df_comp = df_comp.fillna(0)
    
    # Get all counterparties
    counterparties = [col for col in df_comp.columns if col != 'Date']
    
    # Create layered area chart
    fig = go.Figure()
    
    # Color palette
    colors = ['#00d4ff', '#00ff88', '#ffa500', '#ff6b6b', '#9b59b6', '#3498db', '#e74c3c']
    
    for idx, cpty in enumerate(counterparties):
        fig.add_trace(go.Scatter(
            x=df_comp['Date'],
            y=df_comp[cpty] / 1e6,  # Convert to millions
            name=cpty,
            mode='lines',
            stackgroup='one',
            fillcolor=colors[idx % len(colors)],
            line=dict(width=0.5, color=colors[idx % len(colors)])
        ))
    
    fig.update_layout(
        title='Portfolio Composition Over Time (Layered Area)',
        xaxis_title='Date',
        yaxis_title='Notional (R Millions)',
        template='plotly_dark',
        height=600,
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary stats
    st.markdown("###### Current Composition")
    current_comp = df_comp.iloc[-1]
    total_current = sum(current_comp[cpty] for cpty in counterparties)
    
    comp_summary = []
    for cpty in counterparties:
        if current_comp[cpty] > 0:
            comp_summary.append({
                'Counterparty': cpty,
                'Notional': f"R{current_comp[cpty]:,.2f}",
                'Percentage': f"{(current_comp[cpty] / total_current * 100):.2f}%" if total_current > 0 else "0%"
            })
    
    st.dataframe(pd.DataFrame(comp_summary), use_container_width=True, hide_index=True)
    
    # Yield vs Maturity bubble chart
    st.markdown("###### Yield Distribution by Position")
    st.markdown("**Position Yields (bubble size = notional)**")
    
    yield_data = []
    current_date = date.today()
    
    for pos in portfolio:
        name = pos.get('name', 'Unknown')
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        cpty = pos.get('counterparty', 'Unknown')
        maturity = pos.get('maturity')
        
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        # Calculate years to maturity
        days_to_maturity = (maturity - current_date).days
        years_to_maturity = days_to_maturity / 365.25
        
        # Gross yield = JIBAR + spread
        gross_yield = 8.0 + (spread / 100)
        
        yield_data.append({
            'Position': name[:20],
            'Counterparty': cpty,
            'Notional (M)': notional / 1e6,
            'Spread (bps)': spread,
            'Gross Yield (%)': gross_yield,
            'Years to Maturity': years_to_maturity
        })
    
    df_yields = pd.DataFrame(yield_data)
    
    # Create bubble chart with Gross Yield vs Years to Maturity
    fig_yields = px.scatter(
        df_yields,
        x='Years to Maturity',
        y='Gross Yield (%)',
        size='Notional (M)',
        color='Counterparty',
        hover_data=['Position', 'Spread (bps)', 'Notional (M)'],
        title='Gross Yield vs Years to Maturity (bubble size = notional)',
        color_discrete_map={
            'Republic of SA': '#00d4ff',
            'ABSA': '#00ff88',
            'Standard Bank': '#ffa500',
            'Nedbank': '#ff6b6b',
            'FirstRand': '#9b59b6',
            'Investec': '#3498db'
        }
    )
    
    fig_yields.update_layout(
        template='plotly_dark',
        height=500,
        xaxis_title='Years to Maturity',
        yaxis_title='Gross Yield (%)',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    fig_yields.update_traces(
        marker=dict(
            sizemode='diameter',
            sizeref=2.*max(df_yields['Notional (M)'])/(80.**2),  # MUCH smaller bubbles - professional look
            sizemin=2,  # Minimum 2px
            line=dict(width=0.3, color='rgba(255,255,255,0.3)')  # Very subtle border
        ),
        opacity=0.85  # Slight transparency for overlapping bubbles
    )
    
    st.plotly_chart(fig_yields, use_container_width=True)
    
    # Yield Attribution by Counterparty
    st.markdown("###### Yield Attribution by Counterparty/Bank")
    
    cpty_attribution = {}
    total_notional = sum(p.get('notional', 0) for p in portfolio)
    
    for pos in portfolio:
        cpty = pos.get('counterparty', 'Unknown')
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        
        if cpty not in cpty_attribution:
            cpty_attribution[cpty] = {
                'notional': 0,
                'weighted_spread': 0,
                'count': 0
            }
        
        cpty_attribution[cpty]['notional'] += notional
        cpty_attribution[cpty]['weighted_spread'] += spread * notional
        cpty_attribution[cpty]['count'] += 1
    
    # Calculate weighted average spreads and yields
    cpty_table = []
    for cpty, data in sorted(cpty_attribution.items(), key=lambda x: x[1]['notional'], reverse=True):
        avg_spread = data['weighted_spread'] / data['notional'] if data['notional'] > 0 else 0
        gross_yield = 8.0 + (avg_spread / 100)  # JIBAR + spread
        weight = (data['notional'] / total_notional * 100) if total_notional > 0 else 0
        contribution = gross_yield * (weight / 100)
        
        cpty_table.append({
            'Counterparty': cpty,
            'Positions': data['count'],
            'Notional': f"R{data['notional']/1e6:.1f}M",
            'Weight': f"{weight:.1f}%",
            'Avg Spread': f"{avg_spread:.0f} bps",
            'Gross Yield': f"{gross_yield:.2f}%",
            'Yield Contribution': f"{contribution:.2f}%"
        })
    
    df_cpty_attr = pd.DataFrame(cpty_table)
    st.dataframe(df_cpty_attr, use_container_width=True, hide_index=True)
    
    # Yield Attribution by Individual Asset
    st.markdown("###### Yield Attribution by Individual Asset")
    
    asset_table = []
    for pos in sorted(portfolio, key=lambda x: x.get('notional', 0), reverse=True):
        name = pos.get('name', 'Unknown')
        cpty = pos.get('counterparty', 'Unknown')
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        maturity = pos.get('maturity')
        
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        years_to_mat = (maturity - current_date).days / 365.25
        gross_yield = 8.0 + (spread / 100)
        weight = (notional / total_notional * 100) if total_notional > 0 else 0
        contribution = gross_yield * (weight / 100)
        
        asset_table.append({
            'Position': name,
            'Counterparty': cpty,
            'Notional': f"R{notional/1e6:.1f}M",
            'Weight': f"{weight:.1f}%",
            'Spread': f"{spread:.0f} bps",
            'Gross Yield': f"{gross_yield:.2f}%",
            'Years to Mat': f"{years_to_mat:.1f}y",
            'Yield Contribution': f"{contribution:.2f}%"
        })
    
    df_asset_attr = pd.DataFrame(asset_table)
    st.dataframe(df_asset_attr, use_container_width=True, hide_index=True)
    
    # Yield Attribution by Term Bucket
    st.markdown("###### Yield Attribution by Term Bucket")
    
    # Define term buckets
    term_buckets = {
        '0-1Y': (0, 1),
        '1-2Y': (1, 2),
        '2-3Y': (2, 3),
        '3-5Y': (3, 5),
        '5-7Y': (5, 7),
        '7-10Y': (7, 10),
        '10Y+': (10, 100)
    }
    
    bucket_attribution = {bucket: {'notional': 0, 'weighted_spread': 0, 'count': 0} 
                         for bucket in term_buckets.keys()}
    
    for pos in portfolio:
        notional = pos.get('notional', 0)
        spread = pos.get('issue_spread', 0)
        maturity = pos.get('maturity')
        
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        years_to_mat = (maturity - current_date).days / 365.25
        
        # Assign to bucket
        for bucket, (min_y, max_y) in term_buckets.items():
            if min_y <= years_to_mat < max_y:
                bucket_attribution[bucket]['notional'] += notional
                bucket_attribution[bucket]['weighted_spread'] += spread * notional
                bucket_attribution[bucket]['count'] += 1
                break
    
    # Calculate bucket yields
    bucket_table = []
    for bucket, data in bucket_attribution.items():
        if data['notional'] > 0:
            avg_spread = data['weighted_spread'] / data['notional']
            gross_yield = 8.0 + (avg_spread / 100)
            weight = (data['notional'] / total_notional * 100) if total_notional > 0 else 0
            contribution = gross_yield * (weight / 100)
            
            bucket_table.append({
                'Term Bucket': bucket,
                'Positions': data['count'],
                'Notional': f"R{data['notional']/1e6:.1f}M",
                'Weight': f"{weight:.1f}%",
                'Avg Spread': f"{avg_spread:.0f} bps",
                'Gross Yield': f"{gross_yield:.2f}%",
                'Yield Contribution': f"{contribution:.2f}%"
            })
    
    df_bucket_attr = pd.DataFrame(bucket_table)
    st.dataframe(df_bucket_attr, use_container_width=True, hide_index=True)
