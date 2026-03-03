"""
Editable Portfolio Module
Allows users to view and edit portfolio holdings directly in tables

Features:
- Editable portfolio table with all key fields
- Add/delete positions
- Bulk updates
- Validation and error checking
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import uuid


def render_editable_portfolio(portfolio_positions, save_callback):
    """
    Render editable portfolio table
    
    Args:
        portfolio_positions: List of portfolio position dicts
        save_callback: Function to call to save updated portfolio
    """
    
    st.markdown("##### 📝 Editable Portfolio Holdings")
    
    if not portfolio_positions:
        st.info("No portfolio positions. Add positions below.")
        portfolio_positions = []
    
    # Convert to DataFrame for editing
    portfolio_data = []
    for pos in portfolio_positions:
        portfolio_data.append({
            'ID': pos.get('id', ''),
            'Name': pos.get('name', ''),
            'Counterparty': pos.get('counterparty', ''),
            'Book': pos.get('book', ''),
            'Notional (M)': pos.get('notional', 0) / 1e6,
            'Start Date': pos.get('start_date', date.today()),
            'Maturity': pos.get('maturity', date.today()),
            'Issue Spread (bps)': pos.get('issue_spread', 0),
            'DM (bps)': pos.get('dm', 0),
            'Index': pos.get('index', 'JIBAR 3M'),
            'Lookback': pos.get('lookback', 0)
        })
    
    df_portfolio = pd.DataFrame(portfolio_data)
    
    # Editable table
    st.markdown("###### Edit Portfolio Positions")
    st.caption("⚠️ Changes are saved when you click 'Save Portfolio' button below")
    
    edited_df = st.data_editor(
        df_portfolio,
        column_config={
            'ID': st.column_config.TextColumn('ID', disabled=True, width='small'),
            'Name': st.column_config.TextColumn('Name', width='medium'),
            'Counterparty': st.column_config.SelectboxColumn(
                'Counterparty',
                options=['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec', 'Capitec'],
                width='medium'
            ),
            'Book': st.column_config.SelectboxColumn(
                'Book',
                options=['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec'],
                width='medium'
            ),
            'Notional (M)': st.column_config.NumberColumn(
                'Notional (M)',
                min_value=0.0,
                max_value=10000.0,
                step=1.0,
                format='R%.2fM'
            ),
            'Start Date': st.column_config.DateColumn('Start Date'),
            'Maturity': st.column_config.DateColumn('Maturity'),
            'Issue Spread (bps)': st.column_config.NumberColumn(
                'Issue Spread (bps)',
                min_value=0.0,
                max_value=1000.0,
                step=5.0,
                format='%.1f'
            ),
            'DM (bps)': st.column_config.NumberColumn(
                'DM (bps)',
                min_value=-500.0,
                max_value=1000.0,
                step=5.0,
                format='%.1f'
            ),
            'Index': st.column_config.SelectboxColumn(
                'Index',
                options=['JIBAR 3M', 'ZARONIA'],
                width='small'
            ),
            'Lookback': st.column_config.NumberColumn(
                'Lookback',
                min_value=0,
                max_value=10,
                step=1
            )
        },
        num_rows="dynamic",  # Allow adding/deleting rows
        use_container_width=True,
        height=500,
        key="portfolio_editor"
    )
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 Save Portfolio", type="primary", key="save_portfolio_btn"):
            # Convert back to position format
            updated_positions = []
            for idx, row in edited_df.iterrows():
                pos = {
                    'id': row['ID'] if row['ID'] else f"POS_{uuid.uuid4().hex[:8]}",
                    'name': row['Name'],
                    'counterparty': row['Counterparty'],
                    'book': row['Book'],
                    'notional': row['Notional (M)'] * 1e6,
                    'start_date': row['Start Date'],
                    'maturity': row['Maturity'],
                    'issue_spread': row['Issue Spread (bps)'],
                    'dm': row['DM (bps)'],
                    'index': row['Index'],
                    'lookback': int(row['Lookback'])
                }
                updated_positions.append(pos)
            
            # Save via callback
            save_callback(updated_positions)
            st.success(f"✅ Saved {len(updated_positions)} positions")
            st.rerun()
    
    with col2:
        if st.button("🔄 Reload from File", key="reload_portfolio_btn"):
            st.rerun()
    
    with col3:
        if st.button("📥 Export to CSV", key="export_portfolio_csv"):
            csv = edited_df.to_csv(index=False)
            st.download_button("Download CSV", csv, "portfolio.csv", "text/csv")
    
    with col4:
        if st.button("🗑️ Clear All", key="clear_portfolio_btn"):
            if st.session_state.get('confirm_clear', False):
                save_callback([])
                st.success("Portfolio cleared")
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("Click again to confirm clearing all positions")
    
    # Quick add position
    st.markdown("---")
    st.markdown("###### Quick Add Position")
    
    with st.expander("➕ Add New Position", expanded=False):
        col_a, col_b = st.columns(2)
        
        with col_a:
            new_name = st.text_input("Name", value="", key="new_pos_name")
            new_cpty = st.selectbox("Counterparty", 
                                   ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec'],
                                   key="new_pos_cpty")
            new_notional = st.number_input("Notional (M)", value=100.0, step=10.0, key="new_pos_notional")
            new_start = st.date_input("Start Date", value=date.today(), key="new_pos_start")
        
        with col_b:
            new_book = st.selectbox("Book",
                                   ['ABSA', 'Rand Merchant Bank', 'Nedbank', 'Standard Bank', 'Investec'],
                                   key="new_pos_book")
            new_maturity = st.date_input("Maturity", value=date.today() + timedelta(days=365*3), key="new_pos_mat")
            new_spread = st.number_input("Issue Spread (bps)", value=100.0, step=5.0, key="new_pos_spread")
            new_dm = st.number_input("DM (bps)", value=100.0, step=5.0, key="new_pos_dm")
        
        if st.button("Add Position", key="add_pos_btn", type="primary"):
            new_pos = {
                'id': f"POS_{uuid.uuid4().hex[:8]}",
                'name': new_name if new_name else f"FRN_{new_cpty}_{new_maturity.year}",
                'counterparty': new_cpty,
                'book': new_book,
                'notional': new_notional * 1e6,
                'start_date': new_start,
                'maturity': new_maturity,
                'issue_spread': new_spread,
                'dm': new_dm,
                'index': 'JIBAR 3M',
                'lookback': 0
            }
            
            current_positions = portfolio_positions.copy()
            current_positions.append(new_pos)
            save_callback(current_positions)
            st.success(f"✅ Added position: {new_pos['name']}")
            st.rerun()
    
    # Summary statistics
    st.markdown("---")
    st.markdown("###### Portfolio Summary")
    
    if not edited_df.empty:
        total_notional = edited_df['Notional (M)'].sum()
        avg_spread = edited_df['Issue Spread (bps)'].mean()
        avg_dm = edited_df['DM (bps)'].mean()
        num_positions = len(edited_df)
        
        # Calculate weighted average maturity
        edited_df['Years to Mat'] = edited_df.apply(
            lambda row: (row['Maturity'] - date.today()).days / 365.25 if isinstance(row['Maturity'], date) else 0,
            axis=1
        )
        wa_maturity = (edited_df['Notional (M)'] * edited_df['Years to Mat']).sum() / total_notional if total_notional > 0 else 0
        
        sum1, sum2, sum3, sum4 = st.columns(4)
        sum1.metric("Total Positions", f"{num_positions}")
        sum2.metric("Total Notional", f"R{total_notional:.1f}M")
        sum3.metric("Avg Issue Spread", f"{avg_spread:.1f} bps")
        sum4.metric("WA Maturity", f"{wa_maturity:.2f} years")
        
        # Counterparty breakdown
        st.markdown("###### Exposure by Counterparty")
        cpty_exposure = edited_df.groupby('Counterparty')['Notional (M)'].sum().sort_values(ascending=False)
        
        cpty_df = pd.DataFrame({
            'Counterparty': cpty_exposure.index,
            'Notional (M)': cpty_exposure.values,
            'Percentage': (cpty_exposure.values / total_notional * 100) if total_notional > 0 else 0
        })
        
        st.dataframe(cpty_df.style.format({
            'Notional (M)': 'R{:.2f}M',
            'Percentage': '{:.1f}%'
        }).background_gradient(subset=['Notional (M)'], cmap='Blues'),
        use_container_width=True)


def render_bulk_operations(portfolio_positions, save_callback):
    """
    Render bulk operations panel
    """
    
    st.markdown("##### ⚙️ Bulk Operations")
    
    with st.expander("Bulk Update Spreads", expanded=False):
        st.caption("Apply spread adjustments to multiple positions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            filter_cpty = st.multiselect(
                "Filter by Counterparty",
                ['ABSA', 'Standard Bank', 'Nedbank', 'FirstRand', 'Investec'],
                key="bulk_filter_cpty"
            )
        
        with col2:
            spread_adjustment = st.number_input(
                "Spread Adjustment (bps)",
                value=0.0,
                step=5.0,
                help="Add this amount to issue_spread and dm",
                key="bulk_spread_adj"
            )
        
        if st.button("Apply Bulk Adjustment", key="apply_bulk_btn"):
            updated_positions = []
            count = 0
            
            for pos in portfolio_positions:
                pos_copy = pos.copy()
                
                # Check if position matches filter
                if not filter_cpty or pos.get('counterparty') in filter_cpty:
                    pos_copy['issue_spread'] = pos.get('issue_spread', 0) + spread_adjustment
                    pos_copy['dm'] = pos.get('dm', 0) + spread_adjustment
                    count += 1
                
                updated_positions.append(pos_copy)
            
            save_callback(updated_positions)
            st.success(f"✅ Updated {count} positions")
            st.rerun()
    
    with st.expander("Round All Spreads", expanded=False):
        st.caption("Round all spreads to nearest 5 bps")
        
        if st.button("Round Spreads to 5 bps", key="round_spreads_btn"):
            updated_positions = []
            
            for pos in portfolio_positions:
                pos_copy = pos.copy()
                pos_copy['issue_spread'] = round(pos.get('issue_spread', 0) / 5) * 5
                pos_copy['dm'] = round(pos.get('dm', 0) / 5) * 5
                updated_positions.append(pos_copy)
            
            save_callback(updated_positions)
            st.success("✅ Rounded all spreads")
            st.rerun()
