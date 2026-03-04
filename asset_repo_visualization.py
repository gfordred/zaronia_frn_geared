"""
Asset Borrowing & Repo Risk Visualization
==========================================

Visual dashboard showing:
- Which assets are pledged as collateral
- Repo outstanding vs asset value
- Haircut analysis
- Funding risk concentration
- Collateral coverage ratios
"""

import pandas as pd
import numpy as np
from datetime import date, datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def analyze_asset_repo_mapping(portfolio, repo_trades):
    """
    Map which assets are repo'd and calculate coverage metrics
    """
    
    # Get active positions
    active_positions = []
    for pos in portfolio:
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        if start <= date.today() <= maturity:
            active_positions.append(pos)
    
    # Get active repos
    active_repos = []
    for repo in repo_trades:
        spot = repo.get('spot_date')
        end = repo.get('end_date')
        
        if isinstance(spot, str):
            spot = datetime.strptime(spot, '%Y-%m-%d').date()
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d').date()
        
        if spot <= date.today() <= end:
            active_repos.append(repo)
    
    # Calculate metrics
    total_asset_value = sum(p.get('notional', 0) for p in active_positions)
    total_repo_cash = sum(r.get('cash_amount', 0) for r in active_repos if r.get('direction') == 'borrow_cash')
    
    # Estimate which assets are pledged (simplified - assumes pro-rata)
    pledged_ratio = min(total_repo_cash / total_asset_value, 1.0) if total_asset_value > 0 else 0
    
    asset_mapping = []
    for pos in active_positions:
        notional = pos.get('notional', 0)
        pledged_amount = notional * pledged_ratio
        free_amount = notional - pledged_amount
        
        asset_mapping.append({
            'Name': pos.get('name', 'Unknown'),
            'Counterparty': pos.get('counterparty', 'Unknown'),
            'Total_Notional': notional,
            'Pledged_Amount': pledged_amount,
            'Free_Amount': free_amount,
            'Pledged_Pct': pledged_ratio * 100,
            'Maturity': pos.get('maturity')
        })
    
    return pd.DataFrame(asset_mapping), total_asset_value, total_repo_cash, pledged_ratio


def calculate_haircut_metrics(portfolio, repo_trades):
    """
    Calculate haircut and overcollateralization metrics
    """
    
    total_asset_value = sum(p.get('notional', 0) for p in portfolio)
    total_repo_cash = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'borrow_cash')
    
    # Implied haircut
    if total_repo_cash > 0:
        implied_haircut = (total_asset_value - total_repo_cash) / total_asset_value * 100
    else:
        implied_haircut = 0
    
    # Overcollateralization
    if total_repo_cash > 0:
        overcollat_ratio = total_asset_value / total_repo_cash
    else:
        overcollat_ratio = 0
    
    # Available borrowing capacity (assuming 10% haircut)
    standard_haircut = 0.10
    max_borrowing = total_asset_value * (1 - standard_haircut)
    available_capacity = max_borrowing - total_repo_cash
    
    return {
        'total_asset_value': total_asset_value,
        'total_repo_cash': total_repo_cash,
        'implied_haircut': implied_haircut,
        'overcollat_ratio': overcollat_ratio,
        'max_borrowing': max_borrowing,
        'available_capacity': available_capacity,
        'utilization_pct': (total_repo_cash / max_borrowing * 100) if max_borrowing > 0 else 0
    }


def create_asset_repo_waterfall(df_mapping, total_asset_value, total_repo_cash):
    """
    Create waterfall chart showing asset allocation
    """
    
    pledged = df_mapping['Pledged_Amount'].sum()
    free = df_mapping['Free_Amount'].sum()
    
    fig = go.Figure(go.Waterfall(
        name="Asset Allocation",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["Total Assets", "Pledged to Repos", "Free/Unencumbered", "Net Position"],
        textposition="outside",
        text=[f"R{total_asset_value/1e9:.2f}B", 
              f"-R{pledged/1e9:.2f}B", 
              f"R{free/1e9:.2f}B",
              f"R{free/1e9:.2f}B"],
        y=[total_asset_value, -pledged, free, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        increasing={"marker": {"color": "#00ff88"}},
        totals={"marker": {"color": "#00d4ff"}}
    ))
    
    fig.update_layout(
        title="Asset Allocation: Pledged vs Free",
        yaxis_title="Value (R)",
        template="plotly_dark",
        height=500,
        showlegend=False
    )
    
    return fig


def create_collateral_coverage_chart(haircut_metrics):
    """
    Create gauge chart showing collateral coverage
    """
    
    coverage_pct = haircut_metrics['overcollat_ratio'] * 100 - 100  # Excess coverage
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=haircut_metrics['overcollat_ratio'] * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Collateral Coverage", 'font': {'size': 24}},
        delta={'reference': 100, 'suffix': '%'},
        gauge={
            'axis': {'range': [None, 150], 'ticksuffix': '%'},
            'bar': {'color': "#00d4ff"},
            'steps': [
                {'range': [0, 100], 'color': "#ff6b6b"},
                {'range': [100, 110], 'color': "#ffa500"},
                {'range': [110, 150], 'color': "#00ff88"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 110
            }
        }
    ))
    
    fig.update_layout(
        template="plotly_dark",
        height=400,
        font={'color': "white", 'family': "Arial"}
    )
    
    return fig


def create_funding_capacity_chart(haircut_metrics):
    """
    Create chart showing funding capacity utilization
    """
    
    max_borrow = haircut_metrics['max_borrowing']
    current = haircut_metrics['total_repo_cash']
    available = haircut_metrics['available_capacity']
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Funding Capacity'],
        y=[current],
        name='Current Repo',
        marker_color='#ff6b6b',
        text=f"R{current/1e9:.2f}B",
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        x=['Funding Capacity'],
        y=[available],
        name='Available',
        marker_color='#00ff88',
        text=f"R{available/1e9:.2f}B",
        textposition='inside'
    ))
    
    fig.add_hline(
        y=max_borrow,
        line_dash="dash",
        line_color="white",
        annotation_text=f"Max Capacity: R{max_borrow/1e9:.2f}B",
        annotation_position="right"
    )
    
    fig.update_layout(
        title="Funding Capacity Utilization",
        yaxis_title="Amount (R)",
        barmode='stack',
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    return fig


def create_asset_status_sankey(df_mapping, total_repo_cash):
    """
    Create Sankey diagram showing asset flow from holdings to repo
    """
    
    # Prepare data for Sankey
    # Nodes: Assets by counterparty -> Pledged/Free
    
    counterparties = df_mapping['Counterparty'].unique()
    
    # Build node list
    nodes = list(counterparties) + ['Pledged to Repos', 'Free/Unencumbered']
    node_colors = ['#00d4ff'] * len(counterparties) + ['#ff6b6b', '#00ff88']
    
    # Build links
    source = []
    target = []
    value = []
    link_colors = []
    
    for idx, cpty in enumerate(counterparties):
        cpty_data = df_mapping[df_mapping['Counterparty'] == cpty]
        pledged = cpty_data['Pledged_Amount'].sum()
        free = cpty_data['Free_Amount'].sum()
        
        if pledged > 0:
            source.append(idx)
            target.append(len(counterparties))  # Pledged
            value.append(pledged)
            link_colors.append('rgba(255, 107, 107, 0.4)')
        
        if free > 0:
            source.append(idx)
            target.append(len(counterparties) + 1)  # Free
            value.append(free)
            link_colors.append('rgba(0, 255, 136, 0.4)')
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=link_colors
        )
    )])
    
    fig.update_layout(
        title="Asset Flow: Holdings → Repo Collateral",
        font=dict(size=12, color='white'),
        template="plotly_dark",
        height=600
    )
    
    return fig


def create_maturity_ladder_with_repo(portfolio, repo_trades):
    """
    Create maturity ladder showing asset maturities vs repo maturities
    """
    
    # Get maturity dates
    asset_maturities = []
    for pos in portfolio:
        mat = pos.get('maturity')
        if isinstance(mat, str):
            mat = datetime.strptime(mat, '%Y-%m-%d').date()
        
        if mat and mat >= date.today():
            asset_maturities.append({
                'Date': mat,
                'Type': 'Asset Maturity',
                'Amount': pos.get('notional', 0),
                'Name': pos.get('name', 'Unknown')
            })
    
    repo_maturities = []
    for repo in repo_trades:
        end = repo.get('end_date')
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d').date()
        
        if end and end >= date.today():
            repo_maturities.append({
                'Date': end,
                'Type': 'Repo Maturity',
                'Amount': repo.get('cash_amount', 0),
                'Name': repo.get('id', 'Unknown')
            })
    
    df_assets = pd.DataFrame(asset_maturities)
    df_repos = pd.DataFrame(repo_maturities)
    
    fig = go.Figure()
    
    if not df_assets.empty:
        fig.add_trace(go.Scatter(
            x=df_assets['Date'],
            y=df_assets['Amount'] / 1e9,
            mode='markers',
            name='Asset Maturities',
            marker=dict(size=12, color='#00ff88', symbol='diamond'),
            text=df_assets['Name'],
            hovertemplate='<b>%{text}</b><br>Date: %{x}<br>Amount: R%{y:.2f}B<extra></extra>'
        ))
    
    if not df_repos.empty:
        fig.add_trace(go.Scatter(
            x=df_repos['Date'],
            y=df_repos['Amount'] / 1e9,
            mode='markers',
            name='Repo Maturities',
            marker=dict(size=12, color='#ff6b6b', symbol='square'),
            text=df_repos['Name'],
            hovertemplate='<b>%{text}</b><br>Date: %{x}<br>Amount: R%{y:.2f}B<extra></extra>'
        ))
    
    fig.update_layout(
        title="Maturity Ladder: Assets vs Repo Obligations",
        xaxis_title="Maturity Date",
        yaxis_title="Amount (R Billions)",
        template="plotly_dark",
        height=500,
        hovermode='closest'
    )
    
    return fig


def render_asset_repo_visualization(portfolio, repo_trades):
    """
    Main rendering function for asset/repo risk visualization
    """
    
    st.markdown("##### 🏦 Asset Borrowing & Repo Risk Dashboard")
    
    st.info("""
    **Collateral & Funding Risk Analysis:**
    
    This dashboard shows how your assets are utilized:
    - **Pledged Assets:** Collateral posted for repo borrowing
    - **Free Assets:** Unencumbered assets available for additional funding
    - **Haircut Analysis:** Overcollateralization and safety margins
    - **Funding Capacity:** How much more can you borrow
    - **Maturity Mismatches:** Asset vs repo maturity profiles
    
    **Key Risk Metrics:**
    - Collateral coverage should be > 110% (10% haircut)
    - Avoid maturity mismatches (repos maturing before assets)
    - Monitor concentration of pledged assets by counterparty
    """)
    
    if not portfolio or not repo_trades:
        st.warning("No portfolio or repo data available for analysis.")
        return
    
    # Calculate metrics
    df_mapping, total_assets, total_repos, pledged_ratio = analyze_asset_repo_mapping(portfolio, repo_trades)
    haircut_metrics = calculate_haircut_metrics(portfolio, repo_trades)
    
    # Summary metrics
    st.markdown("###### Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric(
        "Total Assets",
        f"R{total_assets/1e9:.2f}B"
    )
    
    col2.metric(
        "Repo Outstanding",
        f"R{total_repos/1e9:.2f}B",
        delta=f"{pledged_ratio*100:.1f}% pledged"
    )
    
    col3.metric(
        "Implied Haircut",
        f"{haircut_metrics['implied_haircut']:.1f}%",
        delta="Safe" if haircut_metrics['implied_haircut'] >= 10 else "Low"
    )
    
    col4.metric(
        "Coverage Ratio",
        f"{haircut_metrics['overcollat_ratio']:.2f}x",
        delta="Good" if haircut_metrics['overcollat_ratio'] >= 1.1 else "Tight"
    )
    
    col5.metric(
        "Available Capacity",
        f"R{haircut_metrics['available_capacity']/1e9:.2f}B",
        delta=f"{haircut_metrics['utilization_pct']:.1f}% used"
    )
    
    # Create tabs for different views
    viz_tabs = st.tabs([
        "📊 Asset Allocation",
        "🔄 Asset Flow (Sankey)",
        "📈 Coverage & Capacity",
        "📅 Maturity Ladder",
        "📋 Detailed Mapping"
    ])
    
    # Tab 1: Asset Allocation Waterfall
    with viz_tabs[0]:
        st.markdown("**Asset Allocation Waterfall**")
        fig_waterfall = create_asset_repo_waterfall(df_mapping, total_assets, total_repos)
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
        # Summary
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pledged to Repos", f"R{df_mapping['Pledged_Amount'].sum()/1e9:.2f}B")
        with col2:
            st.metric("Free/Unencumbered", f"R{df_mapping['Free_Amount'].sum()/1e9:.2f}B")
    
    # Tab 2: Sankey Flow
    with viz_tabs[1]:
        st.markdown("**Asset Flow Diagram**")
        fig_sankey = create_asset_status_sankey(df_mapping, total_repos)
        st.plotly_chart(fig_sankey, use_container_width=True)
    
    # Tab 3: Coverage & Capacity
    with viz_tabs[2]:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Collateral Coverage**")
            fig_coverage = create_collateral_coverage_chart(haircut_metrics)
            st.plotly_chart(fig_coverage, use_container_width=True)
        
        with col2:
            st.markdown("**Funding Capacity**")
            fig_capacity = create_funding_capacity_chart(haircut_metrics)
            st.plotly_chart(fig_capacity, use_container_width=True)
    
    # Tab 4: Maturity Ladder
    with viz_tabs[3]:
        st.markdown("**Maturity Ladder: Assets vs Repos**")
        fig_ladder = create_maturity_ladder_with_repo(portfolio, repo_trades)
        st.plotly_chart(fig_ladder, use_container_width=True)
        
        st.info("""
        **Maturity Mismatch Risk:**
        - 🟢 Green diamonds = Asset maturities (cash inflows)
        - 🔴 Red squares = Repo maturities (cash outflows)
        - **Risk:** Repos maturing before assets = need to refinance or sell assets
        """)
    
    # Tab 5: Detailed Table
    with viz_tabs[4]:
        st.markdown("**Detailed Asset Mapping**")
        
        if not df_mapping.empty:
            st.dataframe(
                df_mapping.style.format({
                    'Total_Notional': 'R{:,.0f}',
                    'Pledged_Amount': 'R{:,.0f}',
                    'Free_Amount': 'R{:,.0f}',
                    'Pledged_Pct': '{:.1f}%'
                }).background_gradient(subset=['Pledged_Pct'], cmap='RdYlGn_r'),
                use_container_width=True,
                hide_index=True
            )
            
            # Export option
            if st.button("📥 Export Asset Mapping (CSV)"):
                csv = df_mapping.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "asset_repo_mapping.csv",
                    "text/csv"
                )
        else:
            st.warning("No asset mapping data available.")
    
    # Risk warnings
    st.markdown("---")
    st.markdown("###### ⚠️ Risk Alerts")
    
    alerts = []
    
    if haircut_metrics['implied_haircut'] < 5:
        alerts.append({
            'Severity': 'High',
            'Alert': 'Low Haircut',
            'Detail': f"Implied haircut {haircut_metrics['implied_haircut']:.1f}% is below 5%",
            'Action': 'Reduce repo borrowing or add more collateral'
        })
    
    if haircut_metrics['overcollat_ratio'] < 1.05:
        alerts.append({
            'Severity': 'High',
            'Alert': 'Tight Coverage',
            'Detail': f"Coverage ratio {haircut_metrics['overcollat_ratio']:.2f}x is below 1.05x",
            'Action': 'Risk of margin call if asset values decline'
        })
    
    if haircut_metrics['utilization_pct'] > 90:
        alerts.append({
            'Severity': 'Medium',
            'Alert': 'High Utilization',
            'Detail': f"Using {haircut_metrics['utilization_pct']:.1f}% of borrowing capacity",
            'Action': 'Limited capacity for additional funding'
        })
    
    if pledged_ratio > 0.95:
        alerts.append({
            'Severity': 'Medium',
            'Alert': 'Highly Encumbered',
            'Detail': f"{pledged_ratio*100:.1f}% of assets are pledged",
            'Action': 'Very little free collateral for flexibility'
        })
    
    if alerts:
        df_alerts = pd.DataFrame(alerts)
        st.dataframe(
            df_alerts.style.applymap(
                lambda x: 'background-color: #ff6b6b' if x == 'High' else ('background-color: #ffa500' if x == 'Medium' else ''),
                subset=['Severity']
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No risk alerts. Collateral and funding position looks healthy.")
