"""
Valuation Date Banner Component
================================

Displays clear valuation date throughout the app.
Shows current date used for all calculations and pricing.
"""

import streamlit as st
from datetime import date


def render_valuation_date_banner(valuation_date: date = None, show_warning: bool = False) -> None:
    """
    Render valuation date banner at top of page
    
    Args:
        valuation_date: Date used for calculations (defaults to today)
        show_warning: Show warning if not using today's date
    """
    
    if valuation_date is None:
        valuation_date = date.today()
    
    is_today = valuation_date == date.today()
    
    # Styling
    st.markdown("""
        <style>
        .valuation-banner {
            background: linear-gradient(90deg, #1e3a5f 0%, #2d5a8a 100%);
            padding: 10px 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #00d4ff;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .valuation-banner.warning {
            border-left-color: #ffa500;
            background: linear-gradient(90deg, #5f3a1e 0%, #8a5a2d 100%);
        }
        .val-label {
            font-size: 11px;
            color: #a0c4e8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 3px;
        }
        .val-date {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        .val-status {
            font-size: 12px;
            color: #00ff88;
            margin-top: 3px;
        }
        .val-status.warning {
            color: #ffa500;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Banner
    banner_class = "valuation-banner warning" if show_warning and not is_today else "valuation-banner"
    
    st.markdown(f"""
        <div class="{banner_class}">
            <div>
                <div class="val-label">📅 Valuation Date</div>
                <div class="val-date">{valuation_date.strftime('%A, %d %B %Y')}</div>
                <div class="val-status {'warning' if not is_today else ''}">
                    {'⚠️ Historical valuation' if not is_today else '✓ Current (today)'}
                </div>
            </div>
            <div style="text-align: right; color: #a0c4e8; font-size: 11px;">
                All prices, yields, and risk metrics<br/>
                calculated as of this date
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_compact_valuation_date(valuation_date: date = None) -> None:
    """
    Render compact valuation date for inline display
    
    Args:
        valuation_date: Date used for calculations (defaults to today)
    """
    
    if valuation_date is None:
        valuation_date = date.today()
    
    is_today = valuation_date == date.today()
    color = "#00ff88" if is_today else "#ffa500"
    icon = "✓" if is_today else "⚠️"
    
    st.markdown(f"""
        <div style="background: rgba(0,0,0,0.2); padding: 5px 10px; border-radius: 5px; 
                    display: inline-block; border-left: 3px solid {color};">
            <span style="color: #a0c4e8; font-size: 10px;">VALUATION DATE:</span>
            <span style="color: white; font-weight: 600; margin-left: 5px;">{valuation_date.strftime('%Y-%m-%d')}</span>
            <span style="color: {color}; margin-left: 5px;">{icon}</span>
        </div>
    """, unsafe_allow_html=True)
