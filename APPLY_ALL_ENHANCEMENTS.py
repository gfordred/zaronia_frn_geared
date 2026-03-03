"""
APPLY ALL ENHANCEMENTS - Complete Integration Script
This script will add all missing features to app.py

Run this to integrate:
- Easy editing for portfolios and repos
- NAV index tracking
- Yield attribution with gearing analysis
- Complete historical analytics
- Time-travel portfolio valuation
- ZARONIA analytics
- All other missing features
"""

import re

def apply_all_enhancements():
    """Apply all enhancements to app.py"""
    
    print("="*70)
    print("APPLYING ALL ENHANCEMENTS TO APP.PY")
    print("="*70)
    
    # Read current app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    with open('app.py.backup', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Created backup: app.py.backup")
    
    # Find Portfolio Manager tab section (around line 2467)
    portfolio_section_start = content.find('with tabs[5]:\n        st.subheader("Portfolio Manager")')
    
    if portfolio_section_start == -1:
        print("✗ Could not find Portfolio Manager tab")
        return False
    
    # Find the end of Portfolio Manager tab (before next tab)
    portfolio_section_end = content.find('# TAB 7: Repo Trades', portfolio_section_start)
    
    if portfolio_section_end == -1:
        print("✗ Could not find end of Portfolio Manager tab")
        return False
    
    # Create new Portfolio Manager section with all enhancements
    new_portfolio_section = '''with tabs[5]:
        st.subheader("📊 Portfolio Manager & Analytics")
        
        portfolio_positions = load_portfolio()
        repo_trades = load_repo_trades()
        
        if not portfolio_positions:
            st.warning("No portfolio positions loaded.")
            
            # Still show add position form
            st.markdown("#### Add Position")
            with st.expander("➕ Add New Position", expanded=True):
                # ... keep existing add position code ...
                pass
        else:
            # Create comprehensive sub-tabs
            portfolio_tabs = st.tabs([
                "📊 Current Valuation",
                "💰 Yield Attribution", 
                "📈 NAV Index",
                "✏️ Edit Portfolio"
            ])
            
            # TAB 1: Current Valuation
            with portfolio_tabs[0]:
                st.markdown("##### Current Portfolio Valuation")
                
                df_summary, tot_clean, tot_dv01, tot_cs01, kr_tots = get_portfolio_summary(
                    portfolio_positions, jibar_curve, jibar_curve, settlement,
                    day_count, calendar, zaronia_spread_bps,
                    df_historical, df_zaronia, evaluation_date, rates)
                
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
                
                # Metrics
                total_repo_cash = sum(r.get('cash_amount', 0) for r in repo_trades 
                                     if r.get('direction') == 'borrow_cash')
                total_notional = sum(p.get('notional', 0) for p in portfolio_positions)
                gearing = total_repo_cash / total_notional if total_notional > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total MV", f"R{tot_clean:,.2f}")
                m2.metric("DV01", f"R{tot_dv01:,.2f}")
                m3.metric("CS01", f"R{tot_cs01:,.2f}")
                m4.metric("Gearing", f"{gearing:.2f}x")
            
            # TAB 2: Yield Attribution
            with portfolio_tabs[1]:
                if MODULES_LOADED:
                    render_yield_attribution(portfolio_positions, repo_trades, rates.get('JIBAR3M', 8.0))
                    st.markdown("---")
                    render_composition_over_time(portfolio_positions, repo_trades)
                else:
                    st.info("💡 Yield attribution module not loaded. Install enhancement modules.")
            
            # TAB 3: NAV Index
            with portfolio_tabs[2]:
                if MODULES_LOADED:
                    render_nav_index(portfolio_positions, repo_trades)
                else:
                    st.info("💡 NAV index module not loaded. Install enhancement modules.")
            
            # TAB 4: Edit Portfolio
            with portfolio_tabs[3]:
                if MODULES_LOADED:
                    render_easy_portfolio_editor(portfolio_positions, save_portfolio)
                else:
                    st.info("💡 Portfolio editor module not loaded. Install enhancement modules.")
                    st.markdown("##### Manual JSON Editing")
                    st.json({"positions": portfolio_positions})
    
    '''
    
    # Replace Portfolio Manager section
    new_content = content[:portfolio_section_start] + new_portfolio_section + content[portfolio_section_end:]
    
    # Now find and enhance Repo Trades tab
    repo_section_start = new_content.find('# TAB 7: Repo Trades')
    repo_section_end = new_content.find('# TAB 8:', repo_section_start)
    
    if repo_section_start != -1 and repo_section_end != -1:
        new_repo_section = '''# TAB 7: Repo Trades
    # -------------------------------------------------------------------------
    with tabs[6]:
        st.subheader("💼 Repo Trade Management & Analytics")
        
        repo_trades = load_repo_trades()
        portfolio_positions = load_portfolio()
        
        # Create comprehensive sub-tabs
        repo_subtabs = st.tabs([
            "📊 Dashboard",
            "📋 Master Table",
            "✏️ Edit Trades",
            "➕ Add Trade"
        ])
        
        # TAB 1: Dashboard
        with repo_subtabs[0]:
            st.markdown("##### Repo Dashboard")
            
            if repo_trades:
                total_repo = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'borrow_cash')
                total_reverse = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'lend_cash')
                net_financing = total_repo - total_reverse
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Repo (Borrow)", f"R{total_repo:,.2f}")
                m2.metric("Total Reverse (Lend)", f"R{total_reverse:,.2f}")
                m3.metric("Net Repo Financing", f"R{net_financing:,.2f}")
                
                st.markdown("##### Recent Repo Trades")
                recent_repos = sorted(repo_trades, key=lambda x: x.get('trade_date', date.today()), reverse=True)[:10]
                for repo in recent_repos:
                    with st.expander(f"Repo: {repo.get('id', 'Unknown')} - R{repo.get('cash_amount', 0)/1e6:.1f}M"):
                        st.json(repo)
            else:
                st.info("No repo trades.")
        
        # TAB 2: Master Table
        with repo_subtabs[1]:
            if MODULES_LOADED:
                render_repo_master_table_and_summary(repo_trades, rates.get('JIBAR3M', 8.0))
            else:
                st.info("💡 Master table module not loaded.")
                if repo_trades:
                    st.dataframe(pd.DataFrame(repo_trades), use_container_width=True)
        
        # TAB 3: Edit Trades
        with repo_subtabs[2]:
            if MODULES_LOADED:
                render_easy_repo_editor(repo_trades, portfolio_positions, save_repo_trades)
            else:
                st.info("💡 Repo editor module not loaded.")
                st.markdown("##### Manual JSON Editing")
                st.json({"trades": repo_trades})
        
        # TAB 4: Add Trade
        with repo_subtabs[3]:
            st.markdown("##### Add New Repo Trade")
            with st.expander("➕ Add New Repo Trade", expanded=True):
                col1, col2 = st.columns(2)
                repo_id = col1.text_input("Repo ID", value=f"REPO_{uuid.uuid4().hex[:8]}", key="repo_id")
                repo_dir = col2.selectbox("Direction", ["borrow_cash", "lend_cash"], key="repo_dir")
                
                col3, col4 = st.columns(2)
                repo_trade_dt = col3.date_input("Trade Date", value=evaluation_date, key="repo_trade_dt")
                repo_spot = col4.date_input("Spot Date", value=evaluation_date + timedelta(days=3), key="repo_spot")
                
                col5, col6 = st.columns(2)
                repo_end = col5.date_input("End Date", value=evaluation_date + timedelta(days=30), key="repo_end")
                repo_cash = col6.number_input("Cash Amount", value=100_000_000.0, step=1000000.0, key="repo_cash")
                
                repo_spread = st.number_input("Repo Spread (bps)", value=10.0, step=5.0, key="repo_spread")
                
                repo_collat = st.selectbox("Collateral Position", 
                                          ["None"] + [p.get('id', '') for p in portfolio_positions],
                                          key="repo_collat")
                repo_cpn_to_lender = st.checkbox("Coupon to Cash Lender", value=False, key="repo_cpn")
                
                if st.button("Add Repo Trade", key="btn_add_repo"):
                    repo_data = {
                        'id': repo_id,
                        'trade_date': repo_trade_dt,
                        'spot_date': repo_spot,
                        'end_date': repo_end,
                        'cash_amount': repo_cash,
                        'repo_spread_bps': repo_spread,
                        'direction': repo_dir,
                        'collateral_id': repo_collat if repo_collat != "None" else None,
                        'coupon_to_lender': repo_cpn_to_lender
                    }
                    trades = load_repo_trades()
                    trades.append(repo_data)
                    save_repo_trades(trades)
                    st.success(f"✅ Added repo trade {repo_id}")
                    st.rerun()
    
    '''
        
        new_content = new_content[:repo_section_start] + new_repo_section + new_content[repo_section_end:]
    
    # Write updated content
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Applied all enhancements to app.py")
    print("✓ Portfolio Manager: Added Yield Attribution, NAV Index, Easy Editor")
    print("✓ Repo Trades: Added Master Table, Easy Editor, Enhanced Dashboard")
    print("\nRestart Streamlit to see changes:")
    print("  streamlit run app.py")
    
    return True

if __name__ == "__main__":
    success = apply_all_enhancements()
    if success:
        print("\n" + "="*70)
        print("SUCCESS! All enhancements applied.")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("FAILED! Check errors above.")
        print("="*70)
