"""
Counterparty Risk Management Module
====================================

Professional credit risk management for FRN portfolio:
- Counterparty exposure limits (notional-based)
- DV01/CS01 risk limits by counterparty
- Concentration risk scoring
- Breach detection and alerts
- Risk-adjusted exposure metrics

Best Practice:
- Republic of SA: Max 50% of portfolio (sovereign risk)
- Banks: Max 20% each (single-name concentration)
- Total DV01/CS01 limits to manage interest rate risk
- Herfindahl Index for concentration measurement
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class CounterpartyRiskLimits:
    """Default risk limits - can be customized"""
    
    # Notional exposure limits (% of total portfolio)
    REPUBLIC_SA_MAX = 0.50  # 50% max to sovereign
    BANK_MAX = 0.20  # 20% max to any single bank
    
    # DV01 limits (absolute R value)
    TOTAL_DV01_LIMIT = 500_000  # R500k total DV01
    COUNTERPARTY_DV01_LIMIT = 150_000  # R150k per counterparty
    
    # CS01 limits (absolute R value)
    TOTAL_CS01_LIMIT = 300_000  # R300k total CS01
    COUNTERPARTY_CS01_LIMIT = 100_000  # R100k per counterparty
    
    # Concentration thresholds (Herfindahl Index)
    CONCENTRATION_LOW = 0.15  # Below = well diversified
    CONCENTRATION_MEDIUM = 0.25  # 0.15-0.25 = moderate
    CONCENTRATION_HIGH = 0.35  # Above = highly concentrated


def calculate_counterparty_exposures(portfolio, evaluation_date=None):
    """
    Calculate detailed counterparty exposures
    
    Returns:
        DataFrame with counterparty-level metrics
    """
    
    if evaluation_date is None:
        evaluation_date = date.today()
    
    # Group by counterparty
    cpty_data = {}
    
    for pos in portfolio:
        cpty = pos.get('counterparty', 'Unknown')
        notional = pos.get('notional', 0)
        
        # Check if position is active on evaluation date
        # Active = started on or before eval_date AND matures on or after eval_date
        start = pos.get('start_date')
        maturity = pos.get('maturity')
        
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(maturity, str):
            maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
        
        # Position is active if: start_date <= eval_date AND eval_date <= maturity
        if start > evaluation_date or evaluation_date > maturity:
            continue
        
        # Initialize counterparty if new
        if cpty not in cpty_data:
            cpty_data[cpty] = {
                'counterparty': cpty,
                'notional': 0,
                'num_positions': 0,
                'dv01': 0,
                'cs01': 0,
                'avg_maturity': 0,
                'positions': []
            }
        
        # Calculate DV01 and CS01
        years_to_mat = (maturity - evaluation_date).days / 365.25
        
        # DV01 = notional × duration × 0.01%
        # For FRNs, duration ≈ time to next reset (0.25 years)
        duration = min(0.25, years_to_mat)
        dv01 = notional * duration * 0.0001
        
        # CS01 = notional × years_to_mat × 0.01% × spread_duration_factor
        # Spread duration ≈ 30% of maturity for FRNs
        cs01 = notional * years_to_mat * 0.0001 * 0.3
        
        # Accumulate
        cpty_data[cpty]['notional'] += notional
        cpty_data[cpty]['num_positions'] += 1
        cpty_data[cpty]['dv01'] += dv01
        cpty_data[cpty]['cs01'] += cs01
        cpty_data[cpty]['avg_maturity'] += years_to_mat * notional
        cpty_data[cpty]['positions'].append(pos)
    
    # Calculate weighted average maturity
    for cpty in cpty_data:
        if cpty_data[cpty]['notional'] > 0:
            cpty_data[cpty]['avg_maturity'] /= cpty_data[cpty]['notional']
    
    df = pd.DataFrame(list(cpty_data.values()))
    
    if df.empty:
        return df
    
    # Calculate percentages
    total_notional = df['notional'].sum()
    df['pct_of_portfolio'] = (df['notional'] / total_notional) * 100
    
    # Determine counterparty type
    df['type'] = df['counterparty'].apply(
        lambda x: 'Sovereign' if 'Republic' in x or 'SA' in x else 'Bank'
    )
    
    return df


def check_limit_breaches(df_exposures, limits=None):
    """
    Check for limit breaches and calculate risk scores
    
    Returns:
        DataFrame with breach flags and risk scores
    """
    
    if limits is None:
        limits = CounterpartyRiskLimits()
    
    if df_exposures.empty:
        return df_exposures
    
    df = df_exposures.copy()
    
    # Check notional exposure limits
    df['notional_limit'] = df.apply(
        lambda row: limits.REPUBLIC_SA_MAX * 100 if row['type'] == 'Sovereign' 
        else limits.BANK_MAX * 100,
        axis=1
    )
    
    df['notional_breach'] = df['pct_of_portfolio'] > df['notional_limit']
    df['notional_utilization'] = (df['pct_of_portfolio'] / df['notional_limit']) * 100
    
    # Check DV01 limits
    df['dv01_limit'] = limits.COUNTERPARTY_DV01_LIMIT
    df['dv01_breach'] = df['dv01'] > df['dv01_limit']
    df['dv01_utilization'] = (df['dv01'] / df['dv01_limit']) * 100
    
    # Check CS01 limits
    df['cs01_limit'] = limits.COUNTERPARTY_CS01_LIMIT
    df['cs01_breach'] = df['cs01'] > df['cs01_limit']
    df['cs01_utilization'] = (df['cs01'] / df['cs01_limit']) * 100
    
    # Calculate risk score (0-100, higher = riskier)
    # Factors: utilization, concentration, number of positions
    df['risk_score'] = (
        df['notional_utilization'] * 0.4 +  # 40% weight on notional
        df['dv01_utilization'] * 0.3 +      # 30% weight on DV01
        df['cs01_utilization'] * 0.3        # 30% weight on CS01
    ).clip(0, 100)
    
    # Risk rating
    df['risk_rating'] = df['risk_score'].apply(
        lambda x: 'Low' if x < 50 else 'Medium' if x < 80 else 'High'
    )
    
    return df


def calculate_concentration_metrics(df_exposures):
    """
    Calculate portfolio concentration metrics
    
    Returns:
        dict with concentration metrics
    """
    
    if df_exposures.empty:
        return {}
    
    total_notional = df_exposures['notional'].sum()
    
    # Herfindahl-Hirschman Index (HHI)
    # Sum of squared market shares (0 = perfect diversification, 1 = single counterparty)
    hhi = sum((df_exposures['notional'] / total_notional) ** 2)
    
    # Effective number of counterparties
    # 1/HHI = how many equal-sized counterparties would give same concentration
    effective_n = 1 / hhi if hhi > 0 else 0
    
    # Top 3 concentration
    top3_pct = df_exposures.nlargest(3, 'notional')['pct_of_portfolio'].sum()
    
    # Concentration rating
    if hhi < CounterpartyRiskLimits.CONCENTRATION_LOW:
        concentration_rating = 'Low (Well Diversified)'
    elif hhi < CounterpartyRiskLimits.CONCENTRATION_MEDIUM:
        concentration_rating = 'Medium (Moderate Concentration)'
    elif hhi < CounterpartyRiskLimits.CONCENTRATION_HIGH:
        concentration_rating = 'High (Concentrated)'
    else:
        concentration_rating = 'Very High (Highly Concentrated)'
    
    return {
        'hhi': hhi,
        'effective_n': effective_n,
        'top3_pct': top3_pct,
        'num_counterparties': len(df_exposures),
        'concentration_rating': concentration_rating
    }


def render_counterparty_risk_manager(portfolio, evaluation_date=None):
    """
    Render comprehensive counterparty risk management interface
    """
    
    st.markdown("##### 🏦 Counterparty Risk Management")
    
    st.info("""
    **Credit Risk Management Framework:**
    
    Professional counterparty risk limits ensure portfolio diversification and manage single-name concentration risk.
    
    **Exposure Limits:**
    - **Republic of SA (Sovereign):** Max 50% of portfolio notional
    - **Banks (Single-Name):** Max 20% of portfolio notional per bank
    
    **Risk Limits:**
    - **DV01 (Interest Rate Risk):** Max R150k per counterparty, R500k total
    - **CS01 (Spread Risk):** Max R100k per counterparty, R300k total
    
    **Risk Scoring:** Combines notional utilization (40%), DV01 utilization (30%), and CS01 utilization (30%)
    """)
    
    if not portfolio:
        st.warning("No portfolio positions to analyze.")
        return
    
    # Calculate exposures
    df_exp = calculate_counterparty_exposures(portfolio, evaluation_date)
    
    if df_exp.empty:
        st.warning("No active positions for selected date.")
        return
    
    # Check breaches
    df_exp = check_limit_breaches(df_exp)
    
    # Calculate concentration
    concentration = calculate_concentration_metrics(df_exp)
    
    # -------------------------------------------------------------------------
    # Section 1: Limit Configuration (Editable)
    # -------------------------------------------------------------------------
    
    st.markdown("###### 📋 Risk Limit Configuration")
    
    with st.expander("⚙️ Customize Risk Limits", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Notional Exposure Limits (%)**")
            republic_limit = st.slider(
                "Republic of SA Max",
                min_value=10, max_value=100, value=50, step=5,
                help="Maximum % of portfolio notional to sovereign",
                key="republic_limit"
            )
            
            bank_limit = st.slider(
                "Single Bank Max",
                min_value=5, max_value=50, value=20, step=5,
                help="Maximum % of portfolio notional to any single bank",
                key="bank_limit"
            )
        
        with col2:
            st.markdown("**Risk Limits (R)**")
            total_dv01_limit = st.number_input(
                "Total DV01 Limit",
                min_value=100_000, max_value=2_000_000, value=500_000, step=50_000,
                help="Maximum total portfolio DV01",
                key="total_dv01_limit"
            )
            
            cpty_dv01_limit = st.number_input(
                "Counterparty DV01 Limit",
                min_value=50_000, max_value=500_000, value=150_000, step=25_000,
                help="Maximum DV01 per counterparty",
                key="cpty_dv01_limit"
            )
        
        # Update limits if customized
        custom_limits = CounterpartyRiskLimits()
        custom_limits.REPUBLIC_SA_MAX = republic_limit / 100
        custom_limits.BANK_MAX = bank_limit / 100
        custom_limits.TOTAL_DV01_LIMIT = total_dv01_limit
        custom_limits.COUNTERPARTY_DV01_LIMIT = cpty_dv01_limit
        
        # Recalculate with custom limits
        df_exp = check_limit_breaches(df_exp, custom_limits)
    
    # -------------------------------------------------------------------------
    # Section 2: Summary Metrics
    # -------------------------------------------------------------------------
    
    st.markdown("###### 📊 Portfolio Risk Summary")
    
    total_notional = df_exp['notional'].sum()
    total_dv01 = df_exp['dv01'].sum()
    total_cs01 = df_exp['cs01'].sum()
    num_breaches = (df_exp['notional_breach'] | df_exp['dv01_breach'] | df_exp['cs01_breach']).sum()
    
    m1, m2, m3, m4, m5 = st.columns(5)
    
    m1.metric(
        "Total Notional",
        f"R{total_notional/1e6:.1f}M",
        help="Total portfolio notional"
    )
    
    m2.metric(
        "Total DV01",
        f"R{total_dv01:,.0f}",
        delta=f"{((total_dv01/CounterpartyRiskLimits.TOTAL_DV01_LIMIT - 1) * 100):+.1f}%" if total_dv01 > CounterpartyRiskLimits.TOTAL_DV01_LIMIT else None,
        delta_color="inverse",
        help="Total interest rate risk (1bp move)"
    )
    
    m3.metric(
        "Total CS01",
        f"R{total_cs01:,.0f}",
        delta=f"{((total_cs01/CounterpartyRiskLimits.TOTAL_CS01_LIMIT - 1) * 100):+.1f}%" if total_cs01 > CounterpartyRiskLimits.TOTAL_CS01_LIMIT else None,
        delta_color="inverse",
        help="Total spread risk (1bp move)"
    )
    
    m4.metric(
        "Counterparties",
        f"{len(df_exp)}",
        help="Number of unique counterparties"
    )
    
    m5.metric(
        "Limit Breaches",
        f"{num_breaches}",
        delta="⚠️" if num_breaches > 0 else "✓",
        delta_color="inverse",
        help="Number of counterparties breaching limits"
    )
    
    # Concentration metrics
    st.markdown("###### 🎯 Concentration Metrics")
    
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric(
        "HHI Index",
        f"{concentration['hhi']:.3f}",
        help="Herfindahl-Hirschman Index (0=diversified, 1=concentrated)"
    )
    
    c2.metric(
        "Effective N",
        f"{concentration['effective_n']:.1f}",
        help="Equivalent number of equal-sized counterparties"
    )
    
    c3.metric(
        "Top 3 Concentration",
        f"{concentration['top3_pct']:.1f}%",
        help="% of portfolio in top 3 counterparties"
    )
    
    c4.metric(
        "Rating",
        concentration['concentration_rating'].split('(')[0].strip(),
        help=concentration['concentration_rating']
    )
    
    # -------------------------------------------------------------------------
    # Section 3: Counterparty Exposure Table
    # -------------------------------------------------------------------------
    
    st.markdown("###### 📋 Counterparty Exposure & Limit Compliance")
    
    # Prepare display table
    df_display = df_exp[[
        'counterparty', 'type', 'num_positions', 'notional', 'pct_of_portfolio',
        'notional_limit', 'notional_utilization', 'notional_breach',
        'dv01', 'dv01_limit', 'dv01_utilization', 'dv01_breach',
        'cs01', 'cs01_limit', 'cs01_utilization', 'cs01_breach',
        'risk_score', 'risk_rating', 'avg_maturity'
    ]].copy()
    
    df_display = df_display.rename(columns={
        'counterparty': 'Counterparty',
        'type': 'Type',
        'num_positions': 'Positions',
        'notional': 'Notional',
        'pct_of_portfolio': 'Portfolio %',
        'notional_limit': 'Limit %',
        'notional_utilization': 'Util %',
        'notional_breach': 'Breach',
        'dv01': 'DV01',
        'dv01_limit': 'DV01 Limit',
        'dv01_utilization': 'DV01 Util %',
        'dv01_breach': 'DV01 Breach',
        'cs01': 'CS01',
        'cs01_limit': 'CS01 Limit',
        'cs01_utilization': 'CS01 Util %',
        'cs01_breach': 'CS01 Breach',
        'risk_score': 'Risk Score',
        'risk_rating': 'Rating',
        'avg_maturity': 'Avg Maturity (Y)'
    })
    
    # Sort by notional descending
    df_display = df_display.sort_values('Notional', ascending=False)
    
    # Format and display
    st.dataframe(
        df_display.style.format({
            'Notional': 'R{:,.0f}',
            'Portfolio %': '{:.2f}%',
            'Limit %': '{:.1f}%',
            'Util %': '{:.1f}%',
            'DV01': 'R{:,.0f}',
            'DV01 Limit': 'R{:,.0f}',
            'DV01 Util %': '{:.1f}%',
            'CS01': 'R{:,.0f}',
            'CS01 Limit': 'R{:,.0f}',
            'CS01 Util %': '{:.1f}%',
            'Risk Score': '{:.1f}',
            'Avg Maturity (Y)': '{:.2f}'
        }).background_gradient(subset=['Risk Score'], cmap='RdYlGn_r')
        .applymap(lambda x: 'background-color: #ff6b6b' if x == True else '', subset=['Breach', 'DV01 Breach', 'CS01 Breach']),
        use_container_width=True,
        height=400
    )
    
    # Breach alerts
    if num_breaches > 0:
        st.error(f"⚠️ **{num_breaches} Limit Breach(es) Detected**")
        
        breach_details = []
        for _, row in df_exp.iterrows():
            if row['notional_breach']:
                breach_details.append(f"- **{row['counterparty']}**: Notional exposure {row['pct_of_portfolio']:.1f}% exceeds {row['notional_limit']:.1f}% limit")
            if row['dv01_breach']:
                breach_details.append(f"- **{row['counterparty']}**: DV01 R{row['dv01']:,.0f} exceeds R{row['dv01_limit']:,.0f} limit")
            if row['cs01_breach']:
                breach_details.append(f"- **{row['counterparty']}**: CS01 R{row['cs01']:,.0f} exceeds R{row['cs01_limit']:,.0f} limit")
        
        for detail in breach_details:
            st.markdown(detail)
    else:
        st.success("✅ All counterparty exposures within limits")
    
    # -------------------------------------------------------------------------
    # Section 4: Visualizations
    # -------------------------------------------------------------------------
    
    st.markdown("###### 📈 Risk Visualizations")
    
    # Create multi-panel chart
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Notional Exposure by Counterparty',
            'DV01 & CS01 by Counterparty',
            'Risk Score Heatmap',
            'Limit Utilization'
        ),
        specs=[
            [{'type': 'bar'}, {'type': 'bar'}],
            [{'type': 'bar'}, {'type': 'bar'}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # Panel 1: Notional exposure
    colors_notional = ['#ff6b6b' if breach else '#00ff88' 
                       for breach in df_exp['notional_breach']]
    
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['pct_of_portfolio'],
            name='Notional %',
            marker_color=colors_notional,
            text=df_exp['pct_of_portfolio'].round(1),
            textposition='outside',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add limit line
    fig.add_hline(
        y=CounterpartyRiskLimits.REPUBLIC_SA_MAX * 100,
        line_dash="dash",
        line_color="orange",
        annotation_text="Sovereign Limit",
        row=1, col=1
    )
    
    fig.add_hline(
        y=CounterpartyRiskLimits.BANK_MAX * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Bank Limit",
        row=1, col=1
    )
    
    # Panel 2: DV01 & CS01
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['dv01'],
            name='DV01',
            marker_color='#00d4ff',
            showlegend=True
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['cs01'],
            name='CS01',
            marker_color='#ffa500',
            showlegend=True
        ),
        row=1, col=2
    )
    
    # Panel 3: Risk scores
    colors_risk = df_exp['risk_rating'].map({
        'Low': '#00ff88',
        'Medium': '#ffa500',
        'High': '#ff6b6b'
    })
    
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['risk_score'],
            name='Risk Score',
            marker_color=colors_risk,
            text=df_exp['risk_rating'],
            textposition='outside',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Panel 4: Utilization
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['notional_utilization'],
            name='Notional Util',
            marker_color='#00d4ff',
            showlegend=True
        ),
        row=2, col=2
    )
    
    fig.add_trace(
        go.Bar(
            x=df_exp['counterparty'],
            y=df_exp['dv01_utilization'],
            name='DV01 Util',
            marker_color='#ffa500',
            showlegend=True
        ),
        row=2, col=2
    )
    
    # Add 100% line
    fig.add_hline(y=100, line_dash="dash", line_color="red", row=2, col=2)
    
    # Update layout
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title_text="Portfolio %", row=1, col=1)
    fig.update_yaxes(title_text="Risk (R)", row=1, col=2)
    fig.update_yaxes(title_text="Score (0-100)", row=2, col=1)
    fig.update_yaxes(title_text="Utilization %", row=2, col=2)
    
    fig.update_layout(
        template='plotly_dark',
        height=800,
        showlegend=True,
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # Section 5: Recommendations
    # -------------------------------------------------------------------------
    
    st.markdown("###### 💡 Risk Management Recommendations")
    
    recommendations = []
    
    # Check for high concentration
    if concentration['hhi'] > CounterpartyRiskLimits.CONCENTRATION_HIGH:
        recommendations.append({
            'priority': 'High',
            'issue': 'Portfolio Concentration',
            'recommendation': f"HHI of {concentration['hhi']:.3f} indicates high concentration. Consider diversifying across more counterparties.",
            'action': 'Add positions with underweight counterparties or reduce overweight exposures'
        })
    
    # Check for breaches
    for _, row in df_exp.iterrows():
        if row['notional_breach']:
            recommendations.append({
                'priority': 'High',
                'issue': f"{row['counterparty']} Notional Breach",
                'recommendation': f"Exposure of {row['pct_of_portfolio']:.1f}% exceeds {row['notional_limit']:.1f}% limit",
                'action': f"Reduce exposure by R{(row['notional'] - (row['notional_limit']/100 * total_notional)):,.0f}"
            })
        
        if row['dv01_breach']:
            recommendations.append({
                'priority': 'Medium',
                'issue': f"{row['counterparty']} DV01 Breach",
                'recommendation': f"DV01 of R{row['dv01']:,.0f} exceeds R{row['dv01_limit']:,.0f} limit",
                'action': 'Reduce notional or shift to shorter-dated positions'
            })
    
    # Check for high risk scores
    high_risk = df_exp[df_exp['risk_score'] > 80]
    for _, row in high_risk.iterrows():
        if not row['notional_breach'] and not row['dv01_breach']:  # Don't duplicate
            recommendations.append({
                'priority': 'Medium',
                'issue': f"{row['counterparty']} High Risk Score",
                'recommendation': f"Risk score of {row['risk_score']:.1f} indicates elevated risk",
                'action': 'Monitor closely and consider reducing exposure'
            })
    
    if recommendations:
        df_rec = pd.DataFrame(recommendations)
        df_rec = df_rec.sort_values('priority', ascending=False)
        
        st.dataframe(
            df_rec.style.applymap(
                lambda x: 'background-color: #ff6b6b' if x == 'High' else 'background-color: #ffa500' if x == 'Medium' else '',
                subset=['priority']
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No immediate risk management actions required. Portfolio is well-balanced.")
    
    # Export option
    if st.button("📥 Export Counterparty Risk Report (CSV)", key="export_cpty_risk"):
        csv = df_display.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "counterparty_risk_report.csv",
            "text/csv",
            key="download_cpty_risk"
        )
