#!/usr/bin/env python3
"""
Generator script to build the complete new app.py
"""

# Read the good header (lines 1-651)
with open('app.py', 'r', encoding='utf-8') as f:
    header = f.read()

# Build all remaining sections
sections = []

# Section 3: FRN Pricing Engine
sections.append("""
# =============================================================================
# SECTION 3: FRN PRICING ENGINE (Proper Projection/Discount Separation)
# =============================================================================

def get_lookup_dict(df, col_name):
    \"\"\"Create {date: value} dict for O(1) lookup.\"\"\"
    if df is None or col_name not in df.columns:
        return {}
    if not isinstance(df.index, pd.DatetimeIndex):
        return {}
    return {ts.date(): val for ts, val in zip(df.index, df[col_name]) if pd.notna(val)}


def get_historical_rate(date_lookup, df, col_name='JIBAR3M'):
    \"\"\"Lookup historical rate with asof fallback.\"\"\"
    if df is None:
        return None
    ts_lookup = pd.Timestamp(date_lookup)
    if isinstance(df.index, pd.DatetimeIndex):
        if ts_lookup in df.index:
            val = df.at[ts_lookup, col_name]
            if pd.notna(val):
                return val / 100.0
        try:
            prev_ts = df.index.asof(ts_lookup)
            if pd.notna(prev_ts):
                val = df.at[prev_ts, col_name]
                if pd.notna(val):
                    return val / 100.0
        except Exception:
            pass
    return None


def calculate_compounded_zaronia(start, end, lookback_days, calendar, day_count,
                                  df_zaronia, curve, df_jibar=None,
                                  zaronia_spread_bps=0.0,
                                  zaronia_dict=None, jibar_dict=None):
    \"\"\"Calculate compounded daily ZARONIA with lookback.\"\"\"
    d = start
    comp_factor = 1.0
    spread_adj = zaronia_spread_bps / 10000.0
    max_iter = 5000
    n = 0

    while d < end and n < max_iter:
        n += 1
        next_d = calendar.advance(d, 1, ql.Days)
        if next_d > end:
            next_d = end
        dt = day_count.yearFraction(d, next_d)
        obs_date = calendar.advance(d, -lookback_days, ql.Days)
        rate = None

        py_obs = date(obs_date.year(), obs_date.month(), obs_date.dayOfMonth())
        if zaronia_dict:
            v = zaronia_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0
        if rate is None and jibar_dict:
            v = jibar_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0 - spread_adj
        if rate is None and df_zaronia is not None:
            rate = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_zaronia, 'ZARONIA')
        if rate is None and df_jibar is not None:
            j = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_jibar, 'JIBAR3M')
            if j is not None:
                rate = j - spread_adj
        if rate is None:
            obs_next = calendar.advance(obs_date, 1, ql.Days)
            rate = curve.forwardRate(obs_date, obs_next, day_count, ql.Simple).rate()

        comp_factor *= (1.0 + rate * dt)
        d = next_d

    if n >= max_iter:
        return curve.forwardRate(start, end, day_count, ql.Simple).rate()

    total_dt = day_count.yearFraction(start, end)
    if total_dt < 1e-10:
        return 0.0
    return (comp_factor - 1.0) / total_dt


def price_frn(nominal, issue_spread_bps, dm_bps, start_date, end_date,
              proj_curve, disc_base_curve, settlement_date,
              day_count, calendar,
              index_type='JIBAR 3M',
              zaronia_spread_bps=0.0, lookback=0,
              df_hist=None, df_zaronia=None,
              zaronia_dict=None, jibar_dict=None,
              return_df=True):
    \"\"\"
    Price FRN with proper projection/discount curve separation.
    Discount curve = ZeroSpreadedTermStructure(disc_base_curve, dm_bps).
    \"\"\"
    start_ql = to_ql_date(start_date)
    end_ql = to_ql_date(end_date)
    sett_ql = to_ql_date(settlement_date)

    schedule = ql.Schedule(start_ql, end_ql,
                           ql.Period(3, ql.Months),
                           calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
                           ql.DateGeneration.Forward, False)
    dates = list(schedule)

    # Build discount curve with DM spread
    dm_spread = ql.SimpleQuote(dm_bps / 10000.0)
    disc_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(disc_base_curve),
        ql.QuoteHandle(dm_spread),
        ql.Compounded, ql.Annual, day_count)
    disc_curve.enableExtrapolation()

    ref_date = proj_curve.referenceDate()
    rows = []
    total_pv = 0.0
    accrued = 0.0

    # Accrued interest
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        if d_s <= sett_ql < d_e:
            fwd = _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                                   zaronia_spread_bps, lookback, calendar, day_count,
                                   df_hist, df_zaronia, zaronia_dict, jibar_dict)
            t_acc = day_count.yearFraction(d_s, sett_ql)
            accrued = nominal * (fwd + issue_spread_bps / 10000.0) * t_acc
            break

    # Cashflow PV
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        if d_e <= sett_ql:
            continue

        fwd, rate_type = _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                                          zaronia_spread_bps, lookback, calendar, day_count,
                                          df_hist, df_zaronia, zaronia_dict, jibar_dict,
                                          return_type=True)

        t_period = day_count.yearFraction(d_s, d_e)
        coupon_rate = fwd + issue_spread_bps / 10000.0
        coupon_amt = nominal * coupon_rate * t_period

        df_val = disc_curve.discount(d_e) / disc_curve.discount(sett_ql)

        is_last = (i == len(dates) - 1)
        principal = nominal if is_last else 0.0
        total_pay = coupon_amt + principal
        pv = df_val * total_pay
        total_pv += pv

        if return_df:
            rows.append({
                'Start Date': d_s.ISO(),
                'End Date': d_e.ISO(),
                'Days': day_count.dayCount(d_s, d_e),
                'Rate Type': rate_type,
                'Index Rate (%)': fwd * 100,
                'Spread (bps)': issue_spread_bps,
                'Total Rate (%)': coupon_rate * 100,
                'Period (yrs)': t_period,
                'Coupon': coupon_amt,
                'Principal': principal,
                'Total Payment': total_pay,
                'Disc Factor': df_val,
                'PV': pv,
                'Type': 'Coupon+Principal' if is_last else 'Coupon',
            })

    clean = total_pv - accrued
    df_out = pd.DataFrame(rows) if return_df else None
    return total_pv, accrued, clean, df_out


def _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                     zaronia_spread_bps, lookback, calendar, day_count,
                     df_hist, df_zaronia, zaronia_dict, jibar_dict,
                     return_type=False):
    \"\"\"Get forward coupon index rate for a period.\"\"\"
    if index_type == 'ZARONIA':
        fwd = calculate_compounded_zaronia(d_s, d_e, lookback, calendar, day_count,
                                           df_zaronia, proj_curve, df_jibar=df_hist,
                                           zaronia_spread_bps=zaronia_spread_bps,
                                           zaronia_dict=zaronia_dict, jibar_dict=jibar_dict)
        rtype = f'Comp. ZARONIA (lb={lookback}d)'
    elif d_s < ref_date:
        fwd = None
        py_ds = date(d_s.year(), d_s.month(), d_s.dayOfMonth())
        if jibar_dict:
            v = jibar_dict.get(py_ds)
            if v is not None:
                fwd = v / 100.0
        if fwd is None and df_hist is not None:
            fwd = get_historical_rate(pd.to_datetime(d_s.ISO()), df_hist, 'JIBAR3M')
        if fwd is None:
            fwd = proj_curve.forwardRate(ref_date, ref_date + (d_e - d_s), day_count, ql.Simple).rate()
        rtype = 'Historical JIBAR'
    else:
        fwd = proj_curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate()
        rtype = 'Forward JIBAR'

    return (fwd, rtype) if return_type else fwd


def calculate_dv01_cs01(nominal, issue_spread, dm, start, end,
                         proj_curve, disc_base_curve, settlement,
                         day_count, calendar, index_type,
                         zaronia_spread_bps, lookback,
                         df_hist, df_zaronia, zaronia_dict, jibar_dict,
                         eval_date, rates_dict):
    \"\"\"Calculate DV01 and CS01/DM01.\"\"\"
    _, _, base_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)

    # DV01
    shifted_jibar, _, _ = build_jibar_curve(eval_date, rates_dict, shift_bps=1.0)
    shifted_proj = (build_zaronia_curve_daily(shifted_jibar, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else shifted_jibar)
    _, _, shifted_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        shifted_proj, shifted_jibar, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)
    dv01 = (base_clean - shifted_clean) * 10.0

    # CS01/DM01
    _, _, dm_clean, _ = price_frn(
        nominal, issue_spread, dm + 1.0, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)
    cs01 = (base_clean - dm_clean) * 10.0

    return dv01, cs01


def calculate_key_rate_dv01(nominal, issue_spread, dm, start, end,
                              disc_base_curve, settlement,
                              day_count, calendar, index_type,
                              zaronia_spread_bps, lookback,
                              df_hist, df_zaronia, zaronia_dict, jibar_dict,
                              eval_date, rates_dict, base_clean):
    \"\"\"Calculate key-rate DV01 for standard tenors.\"\"\"
    tenors = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y']
    kr_curves = build_key_rate_curves(eval_date, rates_dict, day_count, tenors)
    results = {}
    for tenor, kr_proj in kr_curves.items():
        try:
            proj = (build_zaronia_curve_daily(kr_proj, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else kr_proj)
            _, _, kr_clean, _ = price_frn(
                nominal, issue_spread, dm, start, end,
                proj, kr_proj, settlement,
                day_count, calendar, index_type,
                zaronia_spread_bps, lookback, df_hist, df_zaronia,
                zaronia_dict, jibar_dict, return_df=False)
            results[tenor] = (base_clean - kr_clean) * 10.0
        except Exception:
            results[tenor] = 0.0
    return results


def solve_dm(target_all_in, nominal, issue_spread, start, end,
             proj_curve, disc_base_curve, settlement,
             day_count, calendar, index_type,
             zaronia_spread_bps, lookback,
             df_hist, df_zaronia, zaronia_dict, jibar_dict,
             initial_guess=None):
    \"\"\"Solve for DM given target all-in price.\"\"\"
    x0 = initial_guess if initial_guess is not None else issue_spread
    x1 = x0 + 10.0

    for _ in range(12):
        p0, _, _, _ = price_frn(nominal, issue_spread, x0, start, end,
                                 proj_curve, disc_base_curve, settlement,
                                 day_count, calendar, index_type,
                                 zaronia_spread_bps, lookback, df_hist, df_zaronia,
                                 zaronia_dict, jibar_dict, return_df=False)
        p1, _, _, _ = price_frn(nominal, issue_spread, x1, start, end,
                                 proj_curve, disc_base_curve, settlement,
                                 day_count, calendar, index_type,
                                 zaronia_spread_bps, lookback, df_hist, df_zaronia,
                                 zaronia_dict, jibar_dict, return_df=False)
        y0 = p0 - target_all_in
        y1 = p1 - target_all_in
        if abs(y1) < 1e-4:
            return x1
        if abs(y1 - y0) < 1e-10:
            break
        x_new = x1 - y1 * (x1 - x0) / (y1 - y0)
        x0, x1 = x1, x_new

    return x1
""")

# Section 4: Portfolio Manager Functions
sections.append("""

# =============================================================================
# SECTION 4: PORTFOLIO MANAGER
# =============================================================================

def add_position_to_portfolio(instrument_id, instrument_data):
    \"\"\"Add or update a position in the portfolio.\"\"\"
    positions = load_portfolio()
    # Check if position already exists
    existing = [p for p in positions if p.get('id') == instrument_id]
    if existing:
        # Update existing
        for p in positions:
            if p.get('id') == instrument_id:
                p.update(instrument_data)
                p['id'] = instrument_id
                break
    else:
        # Add new
        instrument_data['id'] = instrument_id
        positions.append(instrument_data)
    save_portfolio(positions)
    return True


def remove_position_from_portfolio(instrument_id):
    \"\"\"Remove a position from the portfolio.\"\"\"
    positions = load_portfolio()
    positions = [p for p in positions if p.get('id') != instrument_id]
    save_portfolio(positions)
    return True


def get_portfolio_summary(positions, proj_curve, disc_curve, settlement, day_count, calendar,
                          zaronia_spread_bps, df_hist, df_zaronia, eval_date, rates_dict):
    \"\"\"Calculate portfolio-level aggregations and risk.\"\"\"
    summary_rows = []
    total_clean = 0.0
    total_dv01 = 0.0
    total_cs01 = 0.0
    kr_totals = {}

    zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
    jibar_dict = get_lookup_dict(df_hist, 'JIBAR3M')

    for pos in positions:
        try:
            idx_type = pos.get('index_type', 'JIBAR 3M')
            p_curve = build_zaronia_curve_daily(proj_curve, zaronia_spread_bps, settlement, day_count) if idx_type == 'ZARONIA' else proj_curve
            
            dirty, acc, clean, _ = price_frn(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                p_curve, disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict, return_df=False)

            dv01, cs01 = calculate_dv01_cs01(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                p_curve, disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict,
                eval_date, rates_dict)

            kr_dv01 = calculate_key_rate_dv01(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict,
                eval_date, rates_dict, clean)

            # Aggregate
            total_clean += clean
            total_dv01 += dv01
            total_cs01 += cs01
            for tenor, val in kr_dv01.items():
                kr_totals[tenor] = kr_totals.get(tenor, 0.0) + val

            summary_rows.append({
                'ID': pos['id'],
                'Name': pos.get('name', pos['id']),
                'Notional': pos['notional'],
                'Maturity': pos['maturity'],
                'Index': idx_type,
                'Issue Spread': pos['issue_spread'],
                'DM': pos['dm'],
                'Clean': clean,
                'Accrued': acc,
                'Dirty': dirty,
                'DV01': dv01,
                'CS01': cs01,
                **{f'KR_{t}': kr_dv01.get(t, 0.0) for t in ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y']},
                'Book': pos.get('book', ''),
                'Counterparty': pos.get('counterparty', ''),
                'Trader': pos.get('trader', ''),
            })
        except Exception as e:
            st.warning(f"Failed to price position {pos.get('id')}: {e}")

    return pd.DataFrame(summary_rows), total_clean, total_dv01, total_cs01, kr_totals


# =============================================================================
# SECTION 5: REPO TRADE MODULE
# =============================================================================

def calculate_repo_cashflows(repo_trade, frn_position, proj_curve, disc_curve, settlement,
                              day_count, calendar, zaronia_spread_bps, df_hist, df_zaronia):
    \"\"\"
    Calculate repo cashflows and valuation.
    Repo rate = JIBAR forward + repo_spread_bps.
    \"\"\"
    trade_date = to_ql_date(repo_trade['trade_date'])
    spot_date = to_ql_date(repo_trade['spot_date'])
    end_date = to_ql_date(repo_trade['end_date'])
    cash_amount = repo_trade['cash_amount']
    haircut = repo_trade.get('haircut', 0.0)
    repo_spread_bps = repo_trade['repo_spread_bps']
    direction = repo_trade['direction']  # 'borrow_cash' or 'lend_cash'

    cal = get_sa_calendar()
    
    # Repo rate = JIBAR forward over repo term + spread
    jibar_fwd = proj_curve.forwardRate(spot_date, end_date, day_count, ql.Simple).rate()
    repo_rate = jibar_fwd + repo_spread_bps / 10000.0
    
    t_repo = day_count.yearFraction(spot_date, end_date)
    interest = cash_amount * repo_rate * t_repo
    
    # Cashflows
    cf_rows = []
    
    # Initial leg
    initial_cf = cash_amount if direction == 'borrow_cash' else -cash_amount
    cf_rows.append({
        'Date': spot_date.ISO(),
        'Type': 'Initial Cash',
        'Amount': initial_cf,
        'Description': f'{"Receive" if direction == "borrow_cash" else "Pay"} cash',
    })
    
    # Final leg
    final_cf = -(cash_amount + interest) if direction == 'borrow_cash' else (cash_amount + interest)
    cf_rows.append({
        'Date': end_date.ISO(),
        'Type': 'Final Cash + Interest',
        'Amount': final_cf,
        'Description': f'{"Pay" if direction == "borrow_cash" else "Receive"} cash + interest',
    })
    
    # Collateral FRN coupons during repo term (if applicable)
    if frn_position and repo_trade.get('coupon_to_lender', False):
        # Get FRN schedule
        frn_start = to_ql_date(frn_position['start_date'])
        frn_end = to_ql_date(frn_position['maturity'])
        sched = ql.Schedule(frn_start, frn_end, ql.Period(3, ql.Months),
                           cal, ql.ModifiedFollowing, ql.ModifiedFollowing,
                           ql.DateGeneration.Forward, False)
        
        for i in range(1, len(sched)):
            cpn_date = sched[i]
            if spot_date < cpn_date <= end_date:
                # Coupon paid during repo term
                # Estimate coupon amount (simplified)
                d_s, d_e = sched[i-1], sched[i]
                fwd = proj_curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate()
                t_cpn = day_count.yearFraction(d_s, d_e)
                cpn_amt = frn_position['notional'] * (fwd + frn_position['issue_spread'] / 10000.0) * t_cpn
                
                # Coupon flows to cash lender
                cpn_cf = -cpn_amt if direction == 'borrow_cash' else cpn_amt
                cf_rows.append({
                    'Date': cpn_date.ISO(),
                    'Type': 'FRN Coupon (to lender)',
                    'Amount': cpn_cf,
                    'Description': f'Collateral coupon {"paid to" if direction == "borrow_cash" else "received from"} lender',
                })
    
    # PV of repo
    df_spot = disc_curve.discount(spot_date) / disc_curve.discount(settlement)
    df_end = disc_curve.discount(end_date) / disc_curve.discount(settlement)
    
    pv_initial = initial_cf * df_spot
    pv_final = final_cf * df_end
    pv_repo = pv_initial + pv_final
    
    return pd.DataFrame(cf_rows), pv_repo, repo_rate * 100, interest


# =============================================================================
# SECTION 6: MAIN CURVE BUILD & DATA INITIALIZATION
# =============================================================================

try:
    # Build base curves
    jibar_curve, settlement, day_count = build_jibar_curve(evaluation_date, rates)
    calendar = get_sa_calendar()
    zaronia_curve = build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count)
    
    # Build curve with diagnostics for Curve Diagnostics tab
    jibar_diag_curve, _, _, diagnostics = build_jibar_curve_with_diagnostics(evaluation_date, rates)
""")

# Section 7: Complete UI with all tabs
sections.append("""
    
    # =========================================================================
    # SECTION 7: UI LAYOUT - ALL TABS
    # =========================================================================
    
    tabs = st.tabs([
        "Market Data",
        "Curve Analysis", 
        "FRN Pricer & Risk",
        "ZARONIA Calculator",
        "Basis Analysis",
        "Portfolio Manager",
        "Repo Trades",
        "Curve Diagnostics"
    ])
    
    # -------------------------------------------------------------------------
    # TAB 1: Market Data
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Market Data Time Series")
        if df_historical is not None:
            fig_hist = px.line(df_historical, x='Date', y=['JIBAR3M', 'SASW5', 'SASW10'],
                              title="Historical JIBAR & Swaps")
            fig_hist.update_layout(template="plotly_dark")
            st.plotly_chart(fig_hist, use_container_width=True)
            st.dataframe(df_historical.tail(20), use_container_width=True)
        else:
            st.warning("Historical data file 'JIBAR_FRA_SWAPS.xlsx' not found.")
    
    # -------------------------------------------------------------------------
    # TAB 2: Curve Analysis
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Curve Visualizations")
        
        plot_dates = [settlement + ql.Period(i, ql.Months) for i in range(0, 120, 3)]
        j_zeros = [jibar_curve.zeroRate(d, day_count, ql.Compounded, ql.Annual).rate()*100 for d in plot_dates]
        z_zeros = [zaronia_curve.zeroRate(d, day_count, ql.Compounded, ql.Annual).rate()*100 for d in plot_dates]
        j_fwds = [jibar_curve.forwardRate(d, d+ql.Period(3, ql.Months), day_count, ql.Simple).rate()*100 for d in plot_dates]
        z_fwds = [zaronia_curve.forwardRate(d, d+ql.Period(3, ql.Months), day_count, ql.Simple).rate()*100 for d in plot_dates]
        
        df_plot = pd.DataFrame({
            "Date": [d.ISO() for d in plot_dates],
            "JIBAR Zero": j_zeros,
            "ZARONIA Zero": z_zeros,
            "JIBAR Fwd": j_fwds,
            "ZARONIA Fwd": z_fwds
        })
        
        col1, col2 = st.columns(2)
        with col1:
            fig_zero = px.line(df_plot, x="Date", y=["JIBAR Zero", "ZARONIA Zero"],
                              title="Zero Rates (Ann. Comp)", markers=True)
            fig_zero.update_layout(template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_zero, use_container_width=True)
        
        with col2:
            fig_fwd = px.line(df_plot, x="Date", y=["JIBAR Fwd", "ZARONIA Fwd"],
                             title="3M Forward Rates", markers=True)
            fig_fwd.update_layout(template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_fwd, use_container_width=True)
        
        df_plot["Spread (%)"] = df_plot["JIBAR Fwd"] - df_plot["ZARONIA Fwd"]
        fig_spread = px.area(df_plot, x="Date", y="Spread (%)",
                            title="Implied Spread (JIBAR - ZARONIA)", markers=True)
        fig_spread.update_layout(template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_spread, use_container_width=True)
        
        st.info(f"ZARONIA curve approximated using JIBAR - {zaronia_spread_bps}bps spread (Daily Bootstrapping).")
    
    # -------------------------------------------------------------------------
    # TAB 3: FRN Pricer & Risk
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.subheader("FRN Pricing & Risk Analysis")
        
        st.markdown("##### Instrument Selection")
        sel_inst = st.radio("Choose Instrument", ["Manual"] + list(INSTRUMENTS.keys()), horizontal=True, key="frn_inst_sel")
        
        if sel_inst != "Manual" and sel_inst in INSTRUMENTS:
            inst_data = INSTRUMENTS[sel_inst]
            st.session_state.frn_issue_spread = inst_data["spread"]
            st.session_state.frn_dm = inst_data["spread"]
            st.session_state.frn_start = inst_data["issue"]
            st.session_state.frn_end = inst_data["maturity"]
            st.session_state.frn_index = inst_data.get("index", "JIBAR 3M")
            st.session_state.frn_lookback = inst_data.get("lookback", 0)
        
        c1, c2, c3 = st.columns(3)
        nominal = c1.number_input("Nominal", value=1_000_000.0, step=10000.0, format="%.2f", key="frn_nom")
        issue_spread = c2.number_input("Issue Spread (bps)", value=st.session_state.get('frn_issue_spread', 90.0), key="frn_issue_spread")
        dm = c3.number_input("Market DM (bps)", value=st.session_state.get('frn_dm', 30.0), key="frn_dm")
        
        c4, c5 = st.columns(2)
        frn_start = c4.date_input("Issue Date", value=st.session_state.get('frn_start', evaluation_date), key="frn_start")
        frn_end = c5.date_input("Maturity", value=st.session_state.get('frn_end', evaluation_date + timedelta(days=365*3)), key="frn_end")
        
        c6, c7 = st.columns(2)
        trade_date = c6.date_input("Trade Date", value=evaluation_date, key="frn_trade")
        sett_date = c7.date_input("Settlement (T+3)", value=evaluation_date + timedelta(days=3), key="frn_sett")
        
        frn_index = st.radio("Reference Index", ["JIBAR 3M", "ZARONIA"],
                            index=0 if st.session_state.get('frn_index', 'JIBAR 3M') == 'JIBAR 3M' else 1,
                            key="frn_index")
        lookback = 0
        if frn_index == "ZARONIA":
            lookback = st.number_input("Lookback Days (p)", value=st.session_state.get('frn_lookback', 5), step=1, key="frn_lookback")
        
        if st.button("Price & Calculate Risk", type="primary", key="btn_price_frn"):
            proj = build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count) if frn_index == 'ZARONIA' else jibar_curve
            
            zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
            jibar_dict = get_lookup_dict(df_historical, 'JIBAR3M')
            
            dirty, acc, clean, df_cf = price_frn(
                nominal, issue_spread, dm, frn_start, frn_end,
                proj, jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict, return_df=True)
            
            dv01, cs01 = calculate_dv01_cs01(
                nominal, issue_spread, dm, frn_start, frn_end,
                proj, jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict,
                evaluation_date, rates)
            
            kr_dv01 = calculate_key_rate_dv01(
                nominal, issue_spread, dm, frn_start, frn_end,
                jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict,
                evaluation_date, rates, clean)
            
            st.markdown("### Valuation")
            m1, m2, m3 = st.columns(3)
            m1.metric("Dirty Price", f"{dirty:,.2f}", f"{(dirty/nominal)*100:.5f} per 100")
            m2.metric("Accrued", f"{acc:,.2f}", f"{(acc/nominal)*100:.5f} per 100")
            m3.metric("Clean Price", f"{clean:,.2f}", f"{(clean/nominal)*100:.5f} per 100")
            
            st.markdown("### Cash Flow Analysis")
            if df_cf is not None and not df_cf.empty:
                tab_cf_table, tab_cf_chart = st.tabs(["Detailed Table", "Cash Flow Profile"])
                
                with tab_cf_table:
                    st.dataframe(df_cf.style.format({
                        "Days": "{:.0f}",
                        "Index Rate (%)": "{:.4f}",
                        "Spread (bps)": "{:.2f}",
                        "Total Rate (%)": "{:.4f}",
                        "Period (yrs)": "{:.4f}",
                        "Coupon": "{:,.2f}",
                        "Principal": "{:,.2f}",
                        "Total Payment": "{:,.2f}",
                        "Disc Factor": "{:.6f}",
                        "PV": "{:,.2f}"
                    }), use_container_width=True, hide_index=True)
                
                with tab_cf_chart:
                    df_chart = df_cf.melt(id_vars=["End Date", "Type"],
                                         value_vars=["Total Payment", "PV"],
                                         var_name="Metric", value_name="Amount")
                    fig_cf = px.bar(df_chart, x="End Date", y="Amount", color="Metric",
                                   barmode="group", title=f"Projected Cash Flows: {frn_index}",
                                   hover_data=["Type"])
                    fig_cf.update_layout(template="plotly_dark", hovermode="x unified")
                    st.plotly_chart(fig_cf, use_container_width=True)
            
            st.markdown("### Risk Measures")
            r1, r2 = st.columns(2)
            r1.metric("DV01 (+1bp Rates ×10)", f"{dv01:,.2f}",
                     help="Change in Clean Price for 1bp parallel increase in rates, scaled by 10")
            r2.metric("CS01/DM01 (+1bp DM ×10)", f"{cs01:,.2f}",
                     help="Change in Clean Price for 1bp increase in DM, scaled by 10")
            
            st.markdown("#### Key-Rate DV01")
            kr_df = pd.DataFrame([{'Tenor': k, 'KR-DV01': v} for k, v in kr_dv01.items()])
            st.dataframe(kr_df.style.format({"KR-DV01": "{:,.2f}"}), use_container_width=True, hide_index=True)
    
    # -------------------------------------------------------------------------
    # TAB 4: ZARONIA Calculator
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Historical ZARONIA Compounding Calculator")
        
        col1, col2, col3 = st.columns(3)
        z_principal = col1.number_input("Principal", value=100_000_000.0, step=1_000_000.0, format="%.2f", key="z_prin")
        z_start = col2.date_input("Start Date", value=date(2026, 1, 1), key="z_start")
        z_end = col3.date_input("End Date", value=date.today() - timedelta(days=2), key="z_end")
        
        if st.button("Calculate Compounded ZARONIA", type="primary", key="btn_zar"):
            if df_zaronia is None:
                st.error("ZARONIA fixings file not found.")
            else:
                start_ql = calendar.adjust(to_ql_date(z_start))
                end_ql = calendar.adjust(to_ql_date(z_end))
                
                if start_ql >= end_ql:
                    st.error("Start Date must be before End Date.")
                else:
                    curr = start_ql
                    cum_idx = 1.0
                    results = []
                    
                    while curr < end_ql:
                        next_d = calendar.advance(curr, 1, ql.Days)
                        if next_d > end_ql:
                            next_d = end_ql
                        
                        ts = pd.Timestamp(curr.year(), curr.month(), curr.dayOfMonth())
                        rate = 0.0
                        source = "Missing"
                        
                        if ts in df_zaronia.index:
                            rate = df_zaronia.loc[ts, "ZARONIA"]
                            source = "ZARONIA"
                        else:
                            try:
                                idx_loc = df_zaronia.index.get_indexer([ts], method='ffill')[0]
                                if idx_loc != -1:
                                    rate = df_zaronia.iloc[idx_loc]["ZARONIA"]
                                    source = f"Filled ({df_zaronia.index[idx_loc].date()})"
                            except:
                                pass
                        
                        ndays = day_count.dayCount(curr, next_d)
                        dt = ndays / 365.0
                        interest_amt = (z_principal * cum_idx) * (rate / 100.0) * dt
                        cum_idx *= (1.0 + (rate / 100.0) * dt)
                        
                        results.append({
                            "Start Date": curr.ISO(),
                            "End Date": next_d.ISO(),
                            "Days": ndays,
                            "Rate (%)": rate,
                            "Source": source,
                            "Interest": interest_amt,
                            "Cumulative Index": cum_idx
                        })
                        curr = next_d
                    
                    df_res = pd.DataFrame(results)
                    if not df_res.empty:
                        total_interest = (z_principal * cum_idx) - z_principal
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Interest", f"{total_interest:,.2f}")
                        c2.metric("Final Amount", f"{z_principal * cum_idx:,.2f}")
                        c3.metric("Cumulative Index", f"{cum_idx:.8f}")
                        
                        st.dataframe(df_res.style.format({
                            "Rate (%)": "{:.4f}",
                            "Interest": "{:,.2f}",
                            "Cumulative Index": "{:.8f}"
                        }), use_container_width=True)
                        
                        fig_z = px.line(df_res, x="Start Date", y="Cumulative Index",
                                       title="ZARONIA Compounded Index")
                        fig_z.update_layout(template="plotly_dark")
                        st.plotly_chart(fig_z, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # TAB 5: Basis Analysis
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Basis Analysis: JIBAR vs ZARONIA")
        st.markdown(\"\"\"
        **Cross-Curve Basis Analysis**
        
        Calculates the implied spread differential between JIBAR and ZARONIA curves.
        For each tenor, we determine what spread must be added to ZARONIA to achieve
        the same present value as JIBAR Flat (zero spread).
        \"\"\")
        
        basis_cache = load_basis_cache()
        
        col1, col2, col3, col4 = st.columns(4)
        basis_sett = col1.date_input("Settlement", value=evaluation_date + timedelta(days=3), key="basis_sett")
        basis_nom = col2.number_input("Notional", value=100.0, step=10.0, format="%.2f", key="basis_nom")
        basis_lb = col3.number_input("ZARONIA Lookback", value=5, step=1, key="basis_lb")
        use_cache = col4.checkbox("Use Cache", value=True, key="use_cache")
        
        cache_key = get_cache_key(basis_sett, basis_nom, basis_lb, zaronia_spread_bps)
        cached = basis_cache.get(cache_key)
        
        if use_cache and cached:
            st.info(f"📁 Cached results from: {cached.get('timestamp', 'Unknown')}")
            df_basis = pd.DataFrame(cached['results'])
            st.dataframe(df_basis.style.format({
                "Term (Y)": "{:.2f}",
                "Basis (bps)": "{:.2f}"
            }), use_container_width=True, hide_index=True)
        
        if st.button("Calculate Basis", type="primary", key="btn_basis"):
            basis_terms = [0.25, 0.5, 1, 2, 3, 5, 7, 10]
            basis_results = []
            
            zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
            jibar_dict = get_lookup_dict(df_historical, 'JIBAR3M')
            
            with st.spinner("Calculating basis..."):
                for term in basis_terms:
                    mat = basis_sett + timedelta(days=int(term*365.25))
                    
                    # Price JIBAR Flat using ZARONIA discounting
                    pv_j_ois, _, clean_j, _ = price_frn(
                        basis_nom, 0.0, 0.0, basis_sett, mat,
                        jibar_curve, zaronia_curve, basis_sett,
                        day_count, calendar, 'JIBAR 3M',
                        zaronia_spread_bps, 0, df_historical, df_zaronia,
                        zaronia_dict, jibar_dict, return_df=False)
                    
                    # Solve for ZARONIA spread
                    try:
                        z_spread = solve_dm(
                            pv_j_ois, basis_nom, 0.0, basis_sett, mat,
                            build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count),
                            zaronia_curve, basis_sett,
                            day_count, calendar, 'ZARONIA',
                            zaronia_spread_bps, basis_lb, df_historical, df_zaronia,
                            zaronia_dict, jibar_dict)
                        
                        basis_results.append({
                            "Term (Y)": term,
                            "Basis (bps)": z_spread
                        })
                    except Exception as e:
                        st.warning(f"Failed for term {term}Y: {e}")
                
                df_basis = pd.DataFrame(basis_results)
                
                # Cache results
                cache_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'results': basis_results
                }
                basis_cache[cache_key] = cache_entry
                save_basis_cache(basis_cache)
                
                st.dataframe(df_basis.style.format({"Term (Y)": "{:.2f}", "Basis (bps)": "{:.2f}"}),
                           use_container_width=True, hide_index=True)
                
                fig_basis = px.line(df_basis, x="Term (Y)", y="Basis (bps)", markers=True,
                                   title="Implied Basis: JIBAR Flat = ZARONIA + Spread")
                fig_basis.update_layout(template="plotly_dark")
                st.plotly_chart(fig_basis, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # TAB 6: Portfolio Manager
    # -------------------------------------------------------------------------
    with tabs[5]:
        st.subheader("Portfolio Manager")
        
        portfolio_positions = load_portfolio()
        
        st.markdown("#### Add Position")
        with st.expander("➕ Add New Position", expanded=False):
            col1, col2, col3 = st.columns(3)
            new_id = col1.text_input("Position ID", value=f"POS_{uuid.uuid4().hex[:8]}", key="new_pos_id")
            new_name = col2.text_input("Name", value="", key="new_pos_name")
            new_notional = col3.number_input("Notional", value=1_000_000.0, step=10000.0, key="new_pos_not")
            
            col4, col5, col6 = st.columns(3)
            new_start = col4.date_input("Issue Date", value=evaluation_date, key="new_pos_start")
            new_mat = col5.date_input("Maturity", value=evaluation_date + timedelta(days=365*3), key="new_pos_mat")
            new_idx = col6.selectbox("Index", ["JIBAR 3M", "ZARONIA"], key="new_pos_idx")
            
            col7, col8, col9 = st.columns(3)
            new_iss_spr = col7.number_input("Issue Spread (bps)", value=100.0, key="new_pos_iss")
            new_dm = col8.number_input("Market DM (bps)", value=50.0, key="new_pos_dm")
            new_lb = col9.number_input("Lookback", value=5 if new_idx == "ZARONIA" else 0, key="new_pos_lb")
            
            col10, col11, col12 = st.columns(3)
            new_book = col10.text_input("Book", value="", key="new_pos_book")
            new_cpty = col11.text_input("Counterparty", value="", key="new_pos_cpty")
            new_trader = col12.text_input("Trader", value="", key="new_pos_trader")
            
            if st.button("Add to Portfolio", key="btn_add_pos"):
                pos_data = {
                    'name': new_name or new_id,
                    'notional': new_notional,
                    'start_date': new_start,
                    'maturity': new_mat,
                    'index_type': new_idx,
                    'issue_spread': new_iss_spr,
                    'dm': new_dm,
                    'lookback': new_lb,
                    'book': new_book,
                    'counterparty': new_cpty,
                    'trader': new_trader,
                }
                add_position_to_portfolio(new_id, pos_data)
                st.success(f"Added position {new_id}")
                st.rerun()
        
        st.markdown("#### Portfolio Positions")
        if portfolio_positions:
            df_summary, tot_clean, tot_dv01, tot_cs01, kr_tots = get_portfolio_summary(
                portfolio_positions, jibar_curve, jibar_curve, settlement,
                day_count, calendar, zaronia_spread_bps,
                df_historical, df_zaronia, evaluation_date, rates)
            
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
            
            st.markdown("#### Portfolio Totals")
            t1, t2, t3 = st.columns(3)
            t1.metric("Total Clean PV", f"{tot_clean:,.2f}")
            t2.metric("Total DV01", f"{tot_dv01:,.2f}")
            t3.metric("Total CS01", f"{tot_cs01:,.2f}")
            
            st.markdown("#### Key-Rate DV01 Totals")
            kr_df = pd.DataFrame([{'Tenor': k, 'Total KR-DV01': v} for k, v in kr_tots.items()])
            st.dataframe(kr_df.style.format({"Total KR-DV01": "{:,.2f}"}), use_container_width=True, hide_index=True)
            
            # Export
            if st.button("📥 Download Portfolio Report (CSV)", key="btn_export_port"):
                csv = df_summary.to_csv(index=False)
                st.download_button("Download CSV", csv, "portfolio_report.csv", "text/csv")
        else:
            st.info("No positions in portfolio. Add positions above.")
    
    # -------------------------------------------------------------------------
    # TAB 7: Repo Trades
    # -------------------------------------------------------------------------
    with tabs[6]:
        st.subheader("Repo Trade Module")
        
        repo_trades = load_repo_trades()
        
        st.markdown("#### Add Repo Trade")
        with st.expander("➕ Add New Repo Trade", expanded=False):
            col1, col2 = st.columns(2)
            repo_id = col1.text_input("Repo ID", value=f"REPO_{uuid.uuid4().hex[:8]}", key="repo_id")
            repo_dir = col2.selectbox("Direction", ["borrow_cash", "lend_cash"], key="repo_dir")
            
            col3, col4, col5 = st.columns(3)
            repo_trade_dt = col3.date_input("Trade Date", value=evaluation_date, key="repo_trade_dt")
            repo_spot = col4.date_input("Spot Date", value=evaluation_date + timedelta(days=3), key="repo_spot")
            repo_end = col5.date_input("End Date", value=evaluation_date + timedelta(days=90), key="repo_end")
            
            col6, col7, col8 = st.columns(3)
            repo_cash = col6.number_input("Cash Amount", value=10_000_000.0, step=100000.0, key="repo_cash")
            repo_spread = col7.number_input("Repo Spread (bps)", value=10.0, key="repo_spread")
            repo_haircut = col8.number_input("Haircut (%)", value=2.0, key="repo_haircut")
            
            repo_collat_id = st.selectbox("Collateral FRN (Portfolio ID)",
                                         ["None"] + [p.get('id', '') for p in load_portfolio()],
                                         key="repo_collat")
            repo_cpn_to_lender = st.checkbox("Coupon to Cash Lender", value=False, key="repo_cpn")
            
            if st.button("Add Repo Trade", key="btn_add_repo"):
                repo_data = {
                    'trade_date': repo_trade_dt,
                    'spot_date': repo_spot,
                    'end_date': repo_end,
                    'cash_amount': repo_cash,
                    'repo_spread_bps': repo_spread,
                    'haircut': repo_haircut,
                    'direction': repo_dir,
                    'collateral_id': repo_collat_id if repo_collat_id != "None" else None,
                    'coupon_to_lender': repo_cpn_to_lender,
                }
                trades = load_repo_trades()
                repo_data['id'] = repo_id
                trades.append(repo_data)
                save_repo_trades(trades)
                st.success(f"Added repo trade {repo_id}")
                st.rerun()
        
        st.markdown("#### Repo Trades")
        if repo_trades:
            for repo in repo_trades:
                with st.expander(f"Repo: {repo.get('id', 'Unknown')}"):
                    frn_pos = None
                    if repo.get('collateral_id'):
                        portfolio = load_portfolio()
                        frn_pos = next((p for p in portfolio if p.get('id') == repo['collateral_id']), None)
                    
                    df_cf, pv, repo_rate, interest = calculate_repo_cashflows(
                        repo, frn_pos, jibar_curve, jibar_curve, settlement,
                        day_count, calendar, zaronia_spread_bps, df_historical, df_zaronia)
                    
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Repo Rate (%)", f"{repo_rate:.4f}")
                    r2.metric("Interest", f"{interest:,.2f}")
                    r3.metric("PV", f"{pv:,.2f}")
                    
                    st.markdown("**Cashflows:**")
                    st.dataframe(df_cf, use_container_width=True, hide_index=True)
        else:
            st.info("No repo trades. Add trades above.")
    
    # -------------------------------------------------------------------------
    # TAB 8: Curve Diagnostics
    # -------------------------------------------------------------------------
    with tabs[7]:
        st.subheader("Curve Diagnostics")
        st.markdown("Par instrument repricing errors (Market vs Implied)")
        
        if diagnostics:
            df_diag = pd.DataFrame(diagnostics)
            st.dataframe(df_diag.style.format({
                "Market (%)": "{:.4f}",
                "Implied (%)": "{:.4f}",
                "Error (bps)": "{:.2f}"
            }), use_container_width=True, hide_index=True)
            
            fig_diag = px.bar(df_diag, x="Instrument", y="Error (bps)",
                             title="Par Instrument Repricing Errors")
            fig_diag.update_layout(template="plotly_dark")
            st.plotly_chart(fig_diag, use_container_width=True)
        else:
            st.info("No diagnostics available.")

except Exception as e:
    st.error(f"Application Error: {str(e)}\\n\\n{traceback.format_exc()}")
""")

# Write complete app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(header)
    for section in sections:
        f.write(section)

print(f"✓ Built complete app.py")
print(f"  Total: {len(header) + sum(len(s) for s in sections):,} chars")
print(f"  Header: {len(header):,} chars")
print(f"  Sections: {len(sections)}")
for i, s in enumerate(sections, 1):
    print(f"    Section {i}: {len(s):,} chars")

