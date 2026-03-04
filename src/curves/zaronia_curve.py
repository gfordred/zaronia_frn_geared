"""
ZARONIA Curve Building - CANONICAL
===================================

Single source of truth for ZARONIA OIS discount curve construction.

ZARONIA (South African Overnight Index Average) is built by daily bootstrapping
from the JIBAR curve with a spread adjustment.

Methodology:
- ZARONIA overnight rate = JIBAR overnight forward - spread
- Daily compounding to build discount factors
- 15-year horizon for extrapolation
"""

import QuantLib as ql
from datetime import date
from ..core.calendars import get_sa_calendar


def build_zaronia_curve_daily(jibar_curve, spread_bps, settlement, day_count):
    """
    Build ZARONIA OIS discount curve by daily bootstrapping from JIBAR curve.
    
    **CANONICAL ZARONIA CURVE BUILDER - DO NOT DUPLICATE**
    
    ZARONIA is typically 10-20 bps below JIBAR 3M due to term premium.
    
    Args:
        jibar_curve: JIBAR projection curve (QuantLib curve)
        spread_bps: ZARONIA spread under JIBAR in bps (typically 10-20)
        settlement: Settlement date (QuantLib.Date or Python date)
        day_count: Day count convention (ACT/365)
    
    Returns:
        QuantLib.DiscountCurve for ZARONIA
    
    Example:
        >>> jibar_curve, settlement, dc = build_jibar_curve(date.today(), rates)
        >>> zaronia_curve = build_zaronia_curve_daily(jibar_curve, 15, settlement, dc)
    """
    # Ensure settlement is a QuantLib Date
    if isinstance(settlement, date):
        settlement = ql.Date(settlement.day, settlement.month, settlement.year)
    
    dates = [settlement]
    dfs = [1.0]
    calendar = get_sa_calendar()

    current_date = settlement
    # Build curve out to 15 years
    end_date = settlement + ql.Period(15, ql.Years)

    while current_date < end_date:
        next_date = current_date + ql.Period(1, ql.Days)
        
        # Safety check for date progression
        if next_date <= current_date:
            break
            
        dt = day_count.yearFraction(current_date, next_date)
        
        # Skip zero-length periods
        if dt < 1e-10:
            current_date = next_date
            continue
        
        # Ensure both dates are >= settlement to avoid negative time errors
        if current_date < settlement or next_date < settlement:
            current_date = next_date
            continue
            
        try:
            # Get JIBAR overnight forward rate
            f_jibar = jibar_curve.forwardRate(current_date, next_date, day_count, ql.Simple).rate()
        except RuntimeError:
            # Fallback if forward rate calculation fails
            f_jibar = 0.08  # 8% fallback
            
        # ZARONIA = JIBAR - spread (floored at 0)
        f_zaronia = max(f_jibar - spread_bps / 10000.0, 0.0)
        
        # Compound discount factor
        dfs.append(dfs[-1] / (1.0 + f_zaronia * dt))
        dates.append(next_date)
        current_date = next_date

    # Build discount curve from dates and discount factors
    zaronia_curve = ql.DiscountCurve(dates, dfs, day_count)
    zaronia_curve.enableExtrapolation()
    
    return zaronia_curve


def get_zaronia_spread_from_market(jibar_3m_rate, zaronia_on_rate):
    """
    Calculate implied ZARONIA spread from market rates.
    
    Useful for calibrating the spread parameter.
    
    Args:
        jibar_3m_rate: JIBAR 3M rate in % (e.g., 6.63)
        zaronia_on_rate: ZARONIA overnight rate in % (e.g., 6.48)
    
    Returns:
        Implied spread in bps
    
    Example:
        >>> spread = get_zaronia_spread_from_market(6.63, 6.48)
        >>> print(f"Implied spread: {spread:.1f} bps")
        Implied spread: 15.0 bps
    """
    spread_pct = jibar_3m_rate - zaronia_on_rate
    spread_bps = spread_pct * 100
    return spread_bps
