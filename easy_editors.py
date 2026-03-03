"""
Easy Editors Module - Simplified Editing for Holdings and Repos
Provides user-friendly inline editing with quick forms and buttons

Features:
- Quick edit forms for individual holdings
- Quick edit forms for individual repos
- Delete buttons with confirmation
- Inline editing with immediate save
- All charts show data from inception by default
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import uuid


def render_easy_portfolio_editor(portfolio, save_callback):
    """
    Easy-to-use portfolio editor with quick edit forms
    """
    
    st.markdown("##### ✏️ Edit Portfolio Holdings")
    
    if not portfolio:
        st.info("No holdings. Add a position below.")
        portfolio = []
    
    # Quick add new position
    with st.expander("➕ Add New Position", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_name = st.text_input("Name", value="", key="quick_add_name")
            new_cpty = st.selectbox("Counterparty", 
                ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec', 'Republic of SA'],
                key="quick_add_cpty")
            new_notional = st.number_input("Notional (millions)", value=100.0, step=10.0, key="quick_add_not")
        
        with col2:
            new_start = st.date_input("Start Date", value=date.today(), key="quick_add_start")
            new_maturity = st.date_input("Maturity", value=date.today() + timedelta(days=365*3), key="quick_add_mat")
            new_issue_spread = st.number_input("Issue Spread (bps)", value=100.0, step=5.0, key="quick_add_iss")
        
        with col3:
            new_dm = st.number_input("DM (bps)", value=100.0, step=5.0, key="quick_add_dm")
            new_index = st.selectbox("Index", ['JIBAR 3M', 'ZARONIA'], key="quick_add_idx")
            new_book = st.selectbox("Book", 
                ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec', 'Government'],
                key="quick_add_book")
        
        if st.button("➕ Add Position", type="primary", key="quick_add_btn"):
            new_pos = {
                'id': f'POS_{uuid.uuid4().hex[:8]}',
                'name': new_name if new_name else f"{new_cpty}_FRN_{new_maturity.year}",
                'counterparty': new_cpty,
                'book': new_book,
                'notional': new_notional * 1e6,
                'start_date': new_start,
                'maturity': new_maturity,
                'issue_spread': new_issue_spread,
                'dm': new_dm,
                'index': new_index,
                'lookback': 0
            }
            current_positions = portfolio.copy()
            current_positions.append(new_pos)
            save_callback(current_positions)
            st.success(f"✅ Added: {new_pos['name']}")
            st.rerun()
    
    # Edit existing positions
    st.markdown("---")
    st.markdown("###### Edit Existing Positions")
    
    for idx, pos in enumerate(portfolio):
        with st.expander(f"📝 {pos.get('name', 'Unknown')} - R{pos.get('notional', 0)/1e6:.1f}M", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                edit_name = st.text_input("Name", value=pos.get('name', ''), key=f"edit_name_{idx}")
                edit_cpty = st.selectbox("Counterparty", 
                    ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec', 'Republic of SA'],
                    index=['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec', 'Republic of SA'].index(pos.get('counterparty', 'ABSA')) if pos.get('counterparty') in ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec', 'Republic of SA'] else 0,
                    key=f"edit_cpty_{idx}")
                edit_notional = st.number_input("Notional (M)", value=pos.get('notional', 0)/1e6, step=10.0, key=f"edit_not_{idx}")
            
            with col2:
                edit_start = st.date_input("Start", value=pos.get('start_date') if isinstance(pos.get('start_date'), date) else datetime.strptime(pos.get('start_date'), '%Y-%m-%d').date(), key=f"edit_start_{idx}")
                edit_mat = st.date_input("Maturity", value=pos.get('maturity') if isinstance(pos.get('maturity'), date) else datetime.strptime(pos.get('maturity'), '%Y-%m-%d').date(), key=f"edit_mat_{idx}")
                edit_iss = st.number_input("Issue Spread (bps)", value=float(pos.get('issue_spread', 100.0)), step=5.0, key=f"edit_iss_{idx}")
            
            with col3:
                edit_dm = st.number_input("DM (bps)", value=float(pos.get('dm', 100.0)), step=5.0, key=f"edit_dm_{idx}")
                edit_idx_sel = st.selectbox("Index", ['JIBAR 3M', 'ZARONIA'], 
                    index=0 if pos.get('index') == 'JIBAR 3M' else 1,
                    key=f"edit_idx_{idx}")
                edit_book = st.selectbox("Book",
                    ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec', 'Government'],
                    index=['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec', 'Government'].index(pos.get('book', 'ABSA')) if pos.get('book') in ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec', 'Government'] else 0,
                    key=f"edit_book_{idx}")
            
            # Action buttons
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button("💾 Save Changes", key=f"save_{idx}", type="primary"):
                    updated_positions = portfolio.copy()
                    updated_positions[idx] = {
                        'id': pos.get('id'),
                        'name': edit_name,
                        'counterparty': edit_cpty,
                        'book': edit_book,
                        'notional': edit_notional * 1e6,
                        'start_date': edit_start,
                        'maturity': edit_mat,
                        'issue_spread': edit_iss,
                        'dm': edit_dm,
                        'index': edit_idx_sel,
                        'lookback': pos.get('lookback', 0)
                    }
                    save_callback(updated_positions)
                    st.success(f"✅ Updated: {edit_name}")
                    st.rerun()
            
            with btn_col2:
                if st.button("🗑️ Delete", key=f"del_{idx}"):
                    if st.session_state.get(f'confirm_del_{idx}', False):
                        updated_positions = portfolio.copy()
                        del updated_positions[idx]
                        save_callback(updated_positions)
                        st.success(f"✅ Deleted: {pos.get('name')}")
                        st.session_state[f'confirm_del_{idx}'] = False
                        st.rerun()
                    else:
                        st.session_state[f'confirm_del_{idx}'] = True
                        st.warning("⚠️ Click again to confirm deletion")


def render_easy_repo_editor(repo_trades, portfolio, save_callback):
    """
    Easy-to-use repo editor with quick edit forms
    """
    
    st.markdown("##### ✏️ Edit Repo Trades")
    
    if not repo_trades:
        st.info("No repo trades. Add a trade below.")
        repo_trades = []
    
    # Quick add new repo
    with st.expander("➕ Add New Repo Trade", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_direction = st.selectbox("Direction", ["borrow_cash", "lend_cash"], 
                format_func=lambda x: "Borrow Cash" if x == "borrow_cash" else "Lend Cash",
                key="quick_repo_dir")
            new_cash = st.number_input("Cash Amount (M)", value=100.0, step=10.0, key="quick_repo_cash")
            new_spread = st.number_input("Repo Spread (bps)", value=10.0, step=5.0, key="quick_repo_spread")
        
        with col2:
            new_trade_date = st.date_input("Trade Date", value=date.today(), key="quick_repo_trade")
            new_spot_date = st.date_input("Spot Date", value=date.today() + timedelta(days=3), key="quick_repo_spot")
            new_end_date = st.date_input("End Date", value=date.today() + timedelta(days=90), key="quick_repo_end")
        
        with col3:
            new_collateral = st.selectbox("Collateral", 
                ["None"] + [p.get('id', '') for p in portfolio],
                format_func=lambda x: "No Collateral" if x == "None" else next((p.get('name', x) for p in portfolio if p.get('id') == x), x),
                key="quick_repo_coll")
            new_cpn_to_lender = st.checkbox("Coupon to Lender", value=False, key="quick_repo_cpn")
        
        # Validation
        repo_days = (new_end_date - new_spot_date).days
        if repo_days > 90:
            st.warning(f"⚠️ Repo term is {repo_days} days. Recommended max: 90 days")
        
        if st.button("➕ Add Repo Trade", type="primary", key="quick_repo_add"):
            new_repo = {
                'id': f'REPO_{uuid.uuid4().hex[:8]}',
                'trade_date': new_trade_date,
                'spot_date': new_spot_date,
                'end_date': new_end_date,
                'cash_amount': new_cash * 1e6,
                'repo_spread_bps': new_spread,
                'direction': new_direction,
                'collateral_id': new_collateral if new_collateral != "None" else None,
                'coupon_to_lender': new_cpn_to_lender
            }
            current_repos = repo_trades.copy()
            current_repos.append(new_repo)
            save_callback(current_repos)
            st.success(f"✅ Added repo: {new_repo['id']}")
            st.rerun()
    
    # Edit existing repos
    st.markdown("---")
    st.markdown("###### Edit Existing Repo Trades")
    
    for idx, repo in enumerate(repo_trades):
        spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
        end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
        days = (end - spot).days
        
        with st.expander(f"📝 {repo.get('id', 'Unknown')} - R{repo.get('cash_amount', 0)/1e6:.1f}M ({days}d)", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                edit_dir = st.selectbox("Direction", ["borrow_cash", "lend_cash"],
                    index=0 if repo.get('direction') == 'borrow_cash' else 1,
                    format_func=lambda x: "Borrow Cash" if x == "borrow_cash" else "Lend Cash",
                    key=f"edit_repo_dir_{idx}")
                edit_cash = st.number_input("Cash (M)", value=float(repo.get('cash_amount', 0))/1e6, step=10.0, key=f"edit_repo_cash_{idx}")
                edit_spread = st.number_input("Spread (bps)", value=float(repo.get('repo_spread_bps', 10.0)), step=5.0, key=f"edit_repo_spread_{idx}")
            
            with col2:
                edit_trade = st.date_input("Trade Date", 
                    value=repo['trade_date'] if isinstance(repo['trade_date'], date) else datetime.strptime(repo['trade_date'], '%Y-%m-%d').date(),
                    key=f"edit_repo_trade_{idx}")
                edit_spot = st.date_input("Spot Date",
                    value=spot,
                    key=f"edit_repo_spot_{idx}")
                edit_end = st.date_input("End Date",
                    value=end,
                    key=f"edit_repo_end_{idx}")
            
            with col3:
                edit_coll = st.selectbox("Collateral",
                    ["None"] + [p.get('id', '') for p in portfolio],
                    index=0 if not repo.get('collateral_id') else ([p.get('id', '') for p in portfolio].index(repo.get('collateral_id')) + 1 if repo.get('collateral_id') in [p.get('id', '') for p in portfolio] else 0),
                    format_func=lambda x: "No Collateral" if x == "None" else next((p.get('name', x) for p in portfolio if p.get('id') == x), x),
                    key=f"edit_repo_coll_{idx}")
                edit_cpn = st.checkbox("Coupon to Lender", value=repo.get('coupon_to_lender', False), key=f"edit_repo_cpn_{idx}")
            
            # Validation
            edit_days = (edit_end - edit_spot).days
            if edit_days > 90:
                st.warning(f"⚠️ Term: {edit_days} days (max recommended: 90)")
            
            # Action buttons
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button("💾 Save Changes", key=f"save_repo_{idx}", type="primary"):
                    updated_repos = repo_trades.copy()
                    updated_repos[idx] = {
                        'id': repo.get('id'),
                        'trade_date': edit_trade,
                        'spot_date': edit_spot,
                        'end_date': edit_end,
                        'cash_amount': edit_cash * 1e6,
                        'repo_spread_bps': edit_spread,
                        'direction': edit_dir,
                        'collateral_id': edit_coll if edit_coll != "None" else None,
                        'coupon_to_lender': edit_cpn
                    }
                    save_callback(updated_repos)
                    st.success(f"✅ Updated: {repo.get('id')}")
                    st.rerun()
            
            with btn_col2:
                if st.button("🗑️ Delete", key=f"del_repo_{idx}"):
                    if st.session_state.get(f'confirm_del_repo_{idx}', False):
                        updated_repos = repo_trades.copy()
                        del updated_repos[idx]
                        save_callback(updated_repos)
                        st.success(f"✅ Deleted: {repo.get('id')}")
                        st.session_state[f'confirm_del_repo_{idx}'] = False
                        st.rerun()
                    else:
                        st.session_state[f'confirm_del_repo_{idx}'] = True
                        st.warning("⚠️ Click again to confirm deletion")


# Configuration for charts to show all data from inception
CHART_CONFIG = {
    'show_all_data_by_default': True,
    'default_lookback': None,  # None = show all history
    'allow_user_selection': True,  # Still allow users to change if needed
    'inception_label': 'All History (Since Inception)'
}


def get_chart_date_range(inception_date, end_date, user_selection=None):
    """
    Helper function to get date range for charts
    Default: Show all data from inception
    
    Args:
        inception_date: First date of data
        end_date: Last date of data
        user_selection: Optional user-selected lookback (e.g., "1 Year")
        
    Returns:
        (start_date, end_date) tuple
    """
    if user_selection and user_selection != "All History":
        # User wants specific period
        lookback_map = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 730
        }
        if user_selection in lookback_map:
            start_date = end_date - timedelta(days=lookback_map[user_selection])
            return start_date, end_date
    
    # Default: show all history from inception
    return inception_date, end_date
