"""
Cashflow Generation
===================

FRN cashflow generation including compounded ZARONIA.
"""

import pandas as pd
import QuantLib as ql
from datetime import date
from .helpers import get_historical_rate


def calculate_compounded_zaronia(start, end, lookback_days, calendar, day_count,
                                  df_zaronia, curve, df_jibar=None,
                                  zaronia_spread_bps=0.0,
                                  zaronia_dict=None, jibar_dict=None):
    """
    Calculate compounded daily ZARONIA with lookback.
    
    ZARONIA (South African Overnight Index Average) is compounded daily
    with an optional lookback period for operational ease.
    
    Args:
        start: Start date (QuantLib.Date)
        end: End date (QuantLib.Date)
        lookback_days: Lookback period in days
        calendar: QuantLib calendar
        day_count: Day count convention
        df_zaronia: DataFrame with historical ZARONIA rates
        curve: Projection curve for forward rates
        df_jibar: Optional DataFrame with JIBAR rates (fallback)
        zaronia_spread_bps: Spread adjustment in bps
        zaronia_dict: Optional pre-computed ZARONIA lookup dict
        jibar_dict: Optional pre-computed JIBAR lookup dict
    
    Returns:
        Compounded rate as decimal (e.g., 0.0650 for 6.50%)
    """
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

        # Try to get historical ZARONIA rate
        py_obs = date(obs_date.year(), obs_date.month(), obs_date.dayOfMonth())
        
        # 1. Try zaronia_dict (pre-computed)
        if zaronia_dict:
            v = zaronia_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0
        
        # 2. Try jibar_dict with spread adjustment
        if rate is None and jibar_dict:
            v = jibar_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0 - spread_adj
        
        # 3. Try historical ZARONIA from DataFrame
        if rate is None and df_zaronia is not None:
            rate = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_zaronia, 'ZARONIA')
        
        # 4. Try historical JIBAR with spread adjustment
        if rate is None and df_jibar is not None:
            j = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_jibar, 'JIBAR3M')
            if j is not None:
                rate = j - spread_adj
        
        # 5. Fallback to forward rate from curve
        if rate is None:
            obs_next = calendar.advance(obs_date, 1, ql.Days)
            rate = curve.forwardRate(obs_date, obs_next, day_count, ql.Simple).rate()

        # Compound
        comp_factor *= (1.0 + rate * dt)
        d = next_d

    # Safety check for infinite loop
    if n >= max_iter:
        return curve.forwardRate(start, end, day_count, ql.Simple).rate()

    # Convert compounded factor to rate
    total_dt = day_count.yearFraction(start, end)
    if total_dt < 1e-10:
        return 0.0
    
    return (comp_factor - 1.0) / total_dt


def generate_frn_cashflows(start_date, end_date, notional, issue_spread_bps,
                           calendar, day_count, frequency=ql.Quarterly):
    """
    Generate FRN cashflow schedule.
    
    Args:
        start_date: Start date (QuantLib.Date)
        end_date: Maturity date (QuantLib.Date)
        notional: Position notional
        issue_spread_bps: Issue spread in bps
        calendar: QuantLib calendar
        day_count: Day count convention
        frequency: Coupon frequency (default: Quarterly)
    
    Returns:
        List of cashflow dictionaries
    """
    # Create schedule
    schedule = ql.Schedule(
        start_date, end_date,
        ql.Period(frequency),
        calendar,
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Forward,
        False
    )
    
    dates = list(schedule)
    cashflows = []
    
    for i in range(1, len(dates)):
        d_start = dates[i - 1]
        d_end = dates[i]
        
        period_years = day_count.yearFraction(d_start, d_end)
        is_final = (i == len(dates) - 1)
        
        cashflows.append({
            'start_date': d_start,
            'end_date': d_end,
            'period_years': period_years,
            'notional': notional,
            'spread_bps': issue_spread_bps,
            'is_final': is_final
        })
    
    return cashflows
