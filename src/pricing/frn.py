"""
FRN Pricing Engine - CANONICAL
===============================

Single source of truth for FRN pricing.

This module provides the canonical implementation of FRN pricing with:
- Proper projection/discount curve separation
- Support for JIBAR 3M and ZARONIA indices
- Historical and forward rate handling
- Clean price, accrued interest, and PV calculations
"""

import pandas as pd
import QuantLib as ql
from datetime import date
from .helpers import to_ql_date, get_historical_rate
from .cashflows import calculate_compounded_zaronia


def price_frn(nominal, issue_spread_bps, dm_bps, start_date, end_date,
              proj_curve, disc_base_curve, settlement_date,
              day_count, calendar,
              index_type='JIBAR 3M',
              zaronia_spread_bps=0.0, lookback=0,
              df_hist=None, df_zaronia=None,
              zaronia_dict=None, jibar_dict=None,
              return_df=True):
    """
    Price FRN with proper projection/discount curve separation.
    
    **CANONICAL PRICING ENGINE - DO NOT DUPLICATE**
    
    Methodology:
    - Projection curve: Used to project forward JIBAR/ZARONIA rates
    - Discount curve: Base curve + DM spread for discounting cashflows
    - Discount curve = ZeroSpreadedTermStructure(disc_base_curve, dm_bps)
    
    Args:
        nominal: Position notional
        issue_spread_bps: Issue spread in bps (added to index rate)
        dm_bps: Discount margin in bps (added to discount curve)
        start_date: FRN start date
        end_date: FRN maturity date
        proj_curve: Projection curve for forward rates
        disc_base_curve: Base discount curve
        settlement_date: Settlement date for valuation
        day_count: Day count convention (ACT/365)
        calendar: Business day calendar (SA)
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread under JIBAR
        lookback: Lookback days for ZARONIA
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
        zaronia_dict: Pre-computed ZARONIA lookup
        jibar_dict: Pre-computed JIBAR lookup
        return_df: Return detailed cashflow DataFrame
    
    Returns:
        Tuple of (dirty_price, accrued, clean_price, cashflow_df)
        - dirty_price: Present value including accrued
        - accrued: Accrued interest
        - clean_price: PV excluding accrued
        - cashflow_df: DataFrame with cashflow details (if return_df=True)
    """
    # Convert dates to QuantLib
    start_ql = to_ql_date(start_date)
    end_ql = to_ql_date(end_date)
    sett_ql = to_ql_date(settlement_date)

    # Generate quarterly schedule
    schedule = ql.Schedule(
        start_ql, end_ql,
        ql.Period(3, ql.Months),
        calendar,
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Forward,
        False
    )
    dates = list(schedule)

    # Build discount curve with DM spread
    dm_spread = ql.SimpleQuote(dm_bps / 10000.0)
    disc_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(disc_base_curve),
        ql.QuoteHandle(dm_spread),
        ql.Compounded,
        ql.Annual,
        day_count
    )
    disc_curve.enableExtrapolation()

    ref_date = proj_curve.referenceDate()
    rows = []
    total_pv = 0.0
    accrued = 0.0

    # Calculate accrued interest
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        if d_s <= sett_ql < d_e:
            fwd = _get_coupon_rate(
                d_s, d_e, proj_curve, ref_date, index_type,
                zaronia_spread_bps, lookback, calendar, day_count,
                df_hist, df_zaronia, zaronia_dict, jibar_dict
            )
            t_acc = day_count.yearFraction(d_s, sett_ql)
            accrued = nominal * (fwd + issue_spread_bps / 10000.0) * t_acc
            break

    # Calculate cashflow PV
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        
        # Skip past cashflows
        if d_e <= sett_ql:
            continue

        # Get forward rate for this period
        fwd, rate_type = _get_coupon_rate(
            d_s, d_e, proj_curve, ref_date, index_type,
            zaronia_spread_bps, lookback, calendar, day_count,
            df_hist, df_zaronia, zaronia_dict, jibar_dict,
            return_type=True
        )

        # Calculate coupon
        t_period = day_count.yearFraction(d_s, d_e)
        coupon_rate = fwd + issue_spread_bps / 10000.0
        coupon_amt = nominal * coupon_rate * t_period

        # Discount factor
        df_val = disc_curve.discount(d_e) / disc_curve.discount(sett_ql)

        # Principal on final payment
        is_last = (i == len(dates) - 1)
        principal = nominal if is_last else 0.0
        total_pay = coupon_amt + principal
        pv = df_val * total_pay
        total_pv += pv

        # Store cashflow details
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


def calculate_accrued_interest(nominal, issue_spread_bps, start_date, settlement_date,
                               next_coupon_date, proj_curve, day_count, calendar,
                               index_type='JIBAR 3M', zaronia_spread_bps=0.0,
                               lookback=0, df_hist=None, df_zaronia=None,
                               zaronia_dict=None, jibar_dict=None):
    """
    Calculate accrued interest for an FRN.
    
    Args:
        nominal: Position notional
        issue_spread_bps: Issue spread in bps
        start_date: Coupon period start date
        settlement_date: Settlement date
        next_coupon_date: Next coupon payment date
        proj_curve: Projection curve
        day_count: Day count convention
        calendar: Business day calendar
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread
        lookback: Lookback days
        df_hist: Historical data
        df_zaronia: ZARONIA data
        zaronia_dict: ZARONIA lookup
        jibar_dict: JIBAR lookup
    
    Returns:
        Accrued interest amount
    """
    start_ql = to_ql_date(start_date)
    sett_ql = to_ql_date(settlement_date)
    next_ql = to_ql_date(next_coupon_date)
    
    ref_date = proj_curve.referenceDate()
    
    # Get forward rate for the period
    fwd = _get_coupon_rate(
        start_ql, next_ql, proj_curve, ref_date, index_type,
        zaronia_spread_bps, lookback, calendar, day_count,
        df_hist, df_zaronia, zaronia_dict, jibar_dict
    )
    
    # Calculate accrued
    t_acc = day_count.yearFraction(start_ql, sett_ql)
    accrued = nominal * (fwd + issue_spread_bps / 10000.0) * t_acc
    
    return accrued


def _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                     zaronia_spread_bps, lookback, calendar, day_count,
                     df_hist, df_zaronia, zaronia_dict, jibar_dict,
                     return_type=False):
    """
    Get forward coupon index rate for a period.
    
    Internal helper function for price_frn().
    
    Logic:
    1. If ZARONIA index: Use compounded ZARONIA
    2. If historical period (d_s < ref_date): Use historical JIBAR
    3. If future period: Use forward JIBAR from curve
    
    Args:
        d_s: Period start date (QuantLib.Date)
        d_e: Period end date (QuantLib.Date)
        proj_curve: Projection curve
        ref_date: Curve reference date
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread
        lookback: Lookback days
        calendar: Calendar
        day_count: Day count
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
        zaronia_dict: ZARONIA lookup
        jibar_dict: JIBAR lookup
        return_type: If True, return (rate, type_description)
    
    Returns:
        Forward rate as decimal, or (rate, description) if return_type=True
    """
    if index_type == 'ZARONIA':
        # Compounded ZARONIA
        fwd = calculate_compounded_zaronia(
            d_s, d_e, lookback, calendar, day_count,
            df_zaronia, proj_curve, df_jibar=df_hist,
            zaronia_spread_bps=zaronia_spread_bps,
            zaronia_dict=zaronia_dict, jibar_dict=jibar_dict
        )
        rtype = f'Comp. ZARONIA (lb={lookback}d)'
    
    elif d_s < ref_date:
        # Historical period - use actual JIBAR
        fwd = None
        py_ds = date(d_s.year(), d_s.month(), d_s.dayOfMonth())
        
        # Try jibar_dict first
        if jibar_dict:
            v = jibar_dict.get(py_ds)
            if v is not None:
                fwd = v / 100.0
        
        # Try historical DataFrame
        if fwd is None and df_hist is not None:
            fwd = get_historical_rate(pd.to_datetime(d_s.ISO()), df_hist, 'JIBAR3M')
        
        # Fallback to forward rate
        if fwd is None:
            fwd = proj_curve.forwardRate(ref_date, ref_date + (d_e - d_s), day_count, ql.Simple).rate()
        
        rtype = 'Historical JIBAR'
    
    else:
        # Future period - use forward rate
        fwd = proj_curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate()
        rtype = 'Forward JIBAR'

    return (fwd, rtype) if return_type else fwd
