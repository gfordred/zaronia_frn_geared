"""
Repo Cost Attribution Module
=============================

Analyzes repo financing costs with detailed attribution by:
- Individual repo trades
- Counterparty
- Term buckets
- Time series evolution

Shows how repo costs impact net yield and ROE.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime
from plotly.subplots import make_subplots


def calculate_repo_cost_attribution(repo_trades, jibar_rate=8.0):
    """
    Calculate detailed repo cost attribution
    
    Returns:
        dict with repo cost breakdowns
    """
    
    current_date = date.today()
    total_repo_cost = 0
    total_repo_outstanding = 0
    
    # Individual repo analysis
    repo_details = []
    
    for repo in repo_trades:
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        
        # Check if active
        if end >= current_date and repo.get('direction') == 'borrow_cash':
            cash = repo.get('cash_amount', 0)
            spread_bps = repo.get('repo_spread_bps', 0)
            repo_id = repo.get('id', 'Unknown')
            collateral_name = repo.get('collateral_name', 'Unknown')
            
            # Calculate cost
            repo_rate = (jibar_rate / 100) + (spread_bps / 10000)
            annual_cost = cash * repo_rate
            
            # Days to maturity
            days_to_mat = (end - current_date).days
            years_to_mat = days_to_mat / 365.25
            
            total_repo_cost += annual_cost
            total_repo_outstanding += cash
            
            repo_details.append({
                'id': repo_id,
                'collateral': collateral_name,
                'cash_amount': cash,
                'spread_bps': spread_bps,
                'repo_rate': repo_rate * 100,
                'annual_cost': annual_cost,
                'days_to_mat': days_to_mat,
                'years_to_mat': years_to_mat,
                'spot_date': spot,
                'end_date': end
            })
    
    # Calculate averages
    avg_repo_spread = sum(r['spread_bps'] for r in repo_details) / len(repo_details) if repo_details else 0
    avg_repo_rate = jibar_rate + (avg_repo_spread / 100)
    
    return {
        'total_repo_cost': total_repo_cost,
        'total_repo_outstanding': total_repo_outstanding,
        'avg_repo_spread': avg_repo_spread,
        'avg_repo_rate': avg_repo_rate,
        'repo_details': repo_details,
        'num_repos': len(repo_details)
    }


def render_repo_cost_attribution(repo_trades, jibar_rate=6.6):
    """
    Render comprehensive repo cost attribution analysis
    """
    
    st.markdown("##### 💰 Repo Cost Attribution")
    
    # Calculate attribution
    repo_attr = calculate_repo_cost_attribution(repo_trades, jibar_rate)
    
    # Summary metrics
    st.markdown("###### Summary Totals")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Repo Outstanding", f"R{repo_attr['total_repo_outstanding']/1e6:.1f}M")
    col2.metric("Annual Repo Cost", f"R{repo_attr['total_repo_cost']/1e6:.2f}M")
    col3.metric("Avg Repo Spread", f"{repo_attr['avg_repo_spread']:.0f} bps")
    col4.metric("Avg Repo Rate", f"{repo_attr['avg_repo_rate']:.2f}%")
    
    # Pie chart - Cost by collateral
    st.markdown("###### Repo Cost Distribution by Collateral")
    
    if repo_attr['repo_details']:
        df_repos = pd.DataFrame(repo_attr['repo_details'])
        
        # Group by collateral
        collateral_costs = df_repos.groupby('collateral').agg({
            'annual_cost': 'sum',
            'cash_amount': 'sum'
        }).reset_index()
        
        fig_pie = px.pie(
            collateral_costs,
            values='annual_cost',
            names='collateral',
            title='Annual Repo Cost by Collateral',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Cost: R%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
        )
        
        fig_pie.update_layout(
            template='plotly_dark',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Individual repo table
        st.markdown("###### Individual Repo Cost Attribution")
        
        repo_table = []
        for repo in sorted(repo_attr['repo_details'], key=lambda x: x['annual_cost'], reverse=True):
            weight = (repo['annual_cost'] / repo_attr['total_repo_cost'] * 100) if repo_attr['total_repo_cost'] > 0 else 0
            
            repo_table.append({
                'Collateral': repo['collateral'][:30],
                'Cash Amount': f"R{repo['cash_amount']/1e6:.1f}M",
                'Spread': f"{repo['spread_bps']:.0f} bps",
                'Repo Rate': f"{repo['repo_rate']:.2f}%",
                'Annual Cost': f"R{repo['annual_cost']/1e6:.3f}M",
                'Cost Weight': f"{weight:.1f}%",
                'Days to Mat': f"{repo['days_to_mat']:.0f}d"
            })
        
        df_repo_table = pd.DataFrame(repo_table)
        
        # Color-code by cost weight
        st.dataframe(
            df_repo_table,
            use_container_width=True,
            hide_index=True
        )
        
        # Stacked bar chart - Cost over time (by maturity buckets)
        st.markdown("###### Repo Cost by Maturity Profile")
        
        # Define maturity buckets
        maturity_buckets = {
            '0-1M': (0, 30),
            '1-3M': (30, 90),
            '3-6M': (90, 180),
            '6-12M': (180, 365),
            '1Y+': (365, 10000)
        }
        
        bucket_costs = {bucket: 0 for bucket in maturity_buckets.keys()}
        bucket_outstanding = {bucket: 0 for bucket in maturity_buckets.keys()}
        
        for repo in repo_attr['repo_details']:
            days = repo['days_to_mat']
            for bucket, (min_d, max_d) in maturity_buckets.items():
                if min_d <= days < max_d:
                    bucket_costs[bucket] += repo['annual_cost']
                    bucket_outstanding[bucket] += repo['cash_amount']
                    break
        
        # Create stacked bar
        fig_maturity = go.Figure()
        
        colors = ['#00d4ff', '#00ff88', '#ffa500', '#ff6b6b', '#9b59b6']
        
        for idx, (bucket, cost) in enumerate(bucket_costs.items()):
            if cost > 0:
                fig_maturity.add_trace(go.Bar(
                    name=bucket,
                    x=['Repo Cost'],
                    y=[cost/1e6],
                    marker_color=colors[idx % len(colors)],
                    text=f"R{cost/1e6:.2f}M",
                    textposition='inside',
                    hovertemplate=f'<b>{bucket}</b><br>Cost: R%{{y:.2f}}M<extra></extra>'
                ))
        
        fig_maturity.update_layout(
            barmode='stack',
            title='Annual Repo Cost by Maturity Bucket',
            yaxis_title='Annual Cost (R millions)',
            template='plotly_dark',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig_maturity, use_container_width=True)
        
        # Term bucket table
        st.markdown("###### Repo Cost by Term Bucket")
        
        bucket_table = []
        for bucket, cost in bucket_costs.items():
            if cost > 0:
                outstanding = bucket_outstanding[bucket]
                weight = (cost / repo_attr['total_repo_cost'] * 100) if repo_attr['total_repo_cost'] > 0 else 0
                avg_rate = (cost / outstanding * 100) if outstanding > 0 else 0
                
                bucket_table.append({
                    'Term Bucket': bucket,
                    'Outstanding': f"R{outstanding/1e6:.1f}M",
                    'Annual Cost': f"R{cost/1e6:.3f}M",
                    'Cost Weight': f"{weight:.1f}%",
                    'Avg Rate': f"{avg_rate:.2f}%"
                })
        
        df_bucket_table = pd.DataFrame(bucket_table)
        st.dataframe(df_bucket_table, use_container_width=True, hide_index=True)
        
        # Summary insights
        with st.expander("💡 Repo Cost Insights"):
            st.markdown(f"""
            **Total Repo Financing Cost:** R{repo_attr['total_repo_cost']/1e6:.2f}M per annum
            
            **Cost Breakdown:**
            - Number of active repos: {repo_attr['num_repos']}
            - Total repo outstanding: R{repo_attr['total_repo_outstanding']/1e6:.1f}M
            - Average repo spread: {repo_attr['avg_repo_spread']:.0f} bps
            - Average all-in repo rate: {repo_attr['avg_repo_rate']:.2f}%
            
            **Key Observations:**
            - Largest cost contributor: {repo_table[0]['Collateral']} (R{repo_table[0]['Annual Cost']})
            - Repo costs reduce net yield by approximately {(repo_attr['total_repo_cost']/repo_attr['total_repo_outstanding']*100):.2f}%
            - With gearing, spread pickup must exceed repo spread to generate positive carry
            
            **Formula:**
            - Repo Cost = Repo Outstanding × (JIBAR + Repo Spread)
            - Annual Cost = R{repo_attr['total_repo_outstanding']/1e6:.0f}M × {repo_attr['avg_repo_rate']:.2f}% = R{repo_attr['total_repo_cost']/1e6:.2f}M
            """)
    else:
        st.info("No active repo trades to analyze.")


def render_net_yield_waterfall(frn_income, repo_cost, seed_capital=100_000_000):
    """
    Render waterfall chart showing FRN income → Repo cost → Net income
    """
    
    st.markdown("###### Net Yield Waterfall (Income - Costs)")
    
    net_income = frn_income - repo_cost
    roe = (net_income / seed_capital * 100) if seed_capital > 0 else 0
    
    fig = go.Figure(go.Waterfall(
        name="Income & Costs",
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["FRN Income", "Repo Cost", "Net Income"],
        y=[frn_income/1e6, -repo_cost/1e6, net_income/1e6],
        text=[f"R{frn_income/1e6:.2f}M", f"-R{repo_cost/1e6:.2f}M", f"R{net_income/1e6:.2f}M"],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#00ff88"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#00d4ff"}}
    ))
    
    fig.update_layout(
        title=f"Annual Income Waterfall (ROE: {roe:.2f}%)",
        yaxis_title="Amount (R millions)",
        template='plotly_dark',
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
