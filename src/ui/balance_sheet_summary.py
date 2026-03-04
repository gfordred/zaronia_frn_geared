"""
Sticky Asset/Liability Summary Component
=========================================

Displays clear balance sheet breakdown at top of every page.
Shows Assets, Liabilities, Equity, and key metrics.
"""

import streamlit as st
from typing import Dict, List


def render_balance_sheet_summary(
    portfolio_notional: float,
    repo_outstanding: float,
    seed_capital: float = 100_000_000,
    nav: float = None,
    current_date: str = None
) -> None:
    """
    Render sticky balance sheet summary strip
    
    Args:
        portfolio_notional: Total FRN notional (assets)
        repo_outstanding: Total repo borrowed (liabilities)
        seed_capital: Initial equity capital
        nav: Current NAV (if available)
        current_date: Current date for display
    """
    
    # Calculate metrics
    net_equity = portfolio_notional - repo_outstanding
    gearing = repo_outstanding / seed_capital if seed_capital > 0 else 0
    
    # Use NAV if provided, otherwise use net equity
    current_nav = nav if nav is not None else net_equity
    
    # ROE calculation (simplified - would need actual P&L)
    roe_estimate = ((current_nav - seed_capital) / seed_capital * 100) if seed_capital > 0 else 0
    
    # Create sticky container
    st.markdown("""
        <style>
        .balance-sheet-summary {
            position: sticky;
            top: 0;
            z-index: 999;
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8a 100%);
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .bs-header {
            font-size: 14px;
            font-weight: 600;
            color: #00d4ff;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .bs-value {
            font-size: 24px;
            font-weight: 700;
            color: white;
            margin-bottom: 3px;
        }
        .bs-label {
            font-size: 11px;
            color: #a0c4e8;
            text-transform: uppercase;
        }
        .bs-metric {
            text-align: center;
        }
        .bs-divider {
            border-left: 2px solid rgba(255, 255, 255, 0.2);
            height: 60px;
            margin: 0 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="balance-sheet-summary">', unsafe_allow_html=True)
    
    if current_date:
        st.markdown(f'<div class="bs-header">📊 Balance Sheet Summary - {current_date}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bs-header">📊 Balance Sheet Summary</div>', unsafe_allow_html=True)
    
    # Metrics row
    cols = st.columns([2, 0.1, 2, 0.1, 2, 0.1, 2, 0.1, 2])
    
    # Assets
    with cols[0]:
        st.markdown(f"""
            <div class="bs-metric">
                <div class="bs-value">R{portfolio_notional/1e9:.2f}B</div>
                <div class="bs-label">Total Assets</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Divider
    with cols[1]:
        st.markdown('<div class="bs-divider"></div>', unsafe_allow_html=True)
    
    # Liabilities
    with cols[2]:
        st.markdown(f"""
            <div class="bs-metric">
                <div class="bs-value">R{repo_outstanding/1e9:.2f}B</div>
                <div class="bs-label">Repo Liabilities</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Divider
    with cols[3]:
        st.markdown('<div class="bs-divider"></div>', unsafe_allow_html=True)
    
    # Equity
    with cols[4]:
        st.markdown(f"""
            <div class="bs-metric">
                <div class="bs-value">R{current_nav/1e6:.1f}M</div>
                <div class="bs-label">NAV (Equity)</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Divider
    with cols[5]:
        st.markdown('<div class="bs-divider"></div>', unsafe_allow_html=True)
    
    # Gearing
    with cols[6]:
        gearing_color = "#00ff88" if gearing <= 10 else "#ffa500" if gearing <= 15 else "#ff5252"
        st.markdown(f"""
            <div class="bs-metric">
                <div class="bs-value" style="color: {gearing_color};">{gearing:.2f}x</div>
                <div class="bs-label">Gearing Ratio</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Divider
    with cols[7]:
        st.markdown('<div class="bs-divider"></div>', unsafe_allow_html=True)
    
    # ROE
    with cols[8]:
        roe_color = "#00ff88" if roe_estimate > 0 else "#ff5252"
        st.markdown(f"""
            <div class="bs-metric">
                <div class="bs-value" style="color: {roe_color};">{roe_estimate:.1f}%</div>
                <div class="bs-label">ROE (Est.)</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add explanation expander
    with st.expander("ℹ️ Understanding the Balance Sheet"):
        st.markdown("""
        **Balance Sheet Equation:** Assets = Liabilities + Equity
        
        **Assets (R1.0B):**
        - Portfolio of FRN bonds purchased
        - Funded by: Seed Capital (R100M) + Repo Borrowing (R900M)
        
        **Liabilities (R900M):**
        - Repo outstanding (borrowed funds)
        - Must be repaid with interest
        
        **Equity / NAV:**
        - Seed Capital: R100M (initial investment)
        - Retained Earnings: Operating cashflows (coupons - repo interest)
        - **NAV = Assets - Liabilities** (what you actually own)
        
        **Gearing Ratio (9.0x):**
        - Formula: Repo Outstanding / Seed Capital
        - Shows leverage: For every R1 of equity, we borrowed R9
        - Higher gearing = Higher risk & return
        
        **ROE (Return on Equity):**
        - Estimated annual return on seed capital
        - Based on net operating cashflows (coupons - repo interest)
        - Target: 80-100% with 9x gearing
        
        ⚠️ **Important:** 
        - NAV is the true portfolio value (excludes borrowed funds)
        - Gross Cash includes repo principal (misleading!)
        - Always use NAV for performance measurement
        """)


def render_asset_liability_breakdown(
    positions: List[Dict],
    repos: List[Dict],
    seed_capital: float = 100_000_000
) -> None:
    """
    Render detailed asset/liability breakdown table
    
    Args:
        positions: List of FRN positions
        repos: List of repo trades
        seed_capital: Initial equity capital
    """
    
    st.markdown("##### 📋 Detailed Asset/Liability Breakdown")
    
    # Calculate totals
    total_assets = sum(p.get('notional', 0) for p in positions)
    total_liabilities = sum(r.get('cash_amount', 0) for r in repos if r.get('direction') == 'borrow_cash')
    net_equity = total_assets - total_liabilities
    
    # Create breakdown table
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**ASSETS**")
        
        # Group by counterparty
        cpty_breakdown = {}
        for pos in positions:
            cpty = pos.get('counterparty', 'Unknown')
            notional = pos.get('notional', 0)
            cpty_breakdown[cpty] = cpty_breakdown.get(cpty, 0) + notional
        
        for cpty, notional in sorted(cpty_breakdown.items(), key=lambda x: x[1], reverse=True):
            pct = (notional / total_assets * 100) if total_assets > 0 else 0
            st.metric(cpty, f"R{notional/1e6:.1f}M", delta=f"{pct:.1f}%")
        
        st.markdown("---")
        st.metric("**TOTAL ASSETS**", f"R{total_assets/1e9:.2f}B")
    
    with col2:
        st.markdown("**LIABILITIES**")
        
        # Repo breakdown
        st.metric("Repo Outstanding", f"R{total_liabilities/1e6:.1f}M")
        st.metric("Number of Repos", len(repos))
        
        avg_spread = sum(r.get('repo_spread_bps', 0) for r in repos) / len(repos) if repos else 0
        st.metric("Avg Repo Spread", f"{avg_spread:.0f} bps")
        
        st.markdown("---")
        st.metric("**NET EQUITY**", f"R{net_equity/1e6:.1f}M")
    
    # Gearing summary
    st.markdown("---")
    gearing = total_liabilities / seed_capital if seed_capital > 0 else 0
    
    cols = st.columns(3)
    cols[0].metric("Seed Capital", f"R{seed_capital/1e6:.0f}M")
    cols[1].metric("Gearing Ratio", f"{gearing:.2f}x")
    cols[2].metric("Funding %", f"{(total_liabilities/total_assets*100):.1f}%")
