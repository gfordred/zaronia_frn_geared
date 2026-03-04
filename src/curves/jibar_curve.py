"""
JIBAR Curve Building - CANONICAL
=================================

Single source of truth for JIBAR curve construction.

Builds JIBAR projection curve from market instruments:
- 3M Deposit
- FRAs (3x6, 6x9, 9x12, 18x21)
- Interest Rate Swaps (2Y, 3Y, 5Y, 10Y)

Conventions:
- Day count: ACT/365 Fixed
- Business day: Modified Following
- Calendar: South Africa
- Frequency: Quarterly
"""

import QuantLib as ql
from ..core.calendars import get_sa_calendar
from ..pricing.helpers import to_ql_date


def build_jibar_curve(eval_date, r, shift_bps=0.0):
    """
    Build JIBAR projection curve from Depo + FRAs + Swaps.
    
    **CANONICAL JIBAR CURVE BUILDER - DO NOT DUPLICATE**
    
    Uses piecewise log-cubic discount interpolation for smooth forward rates.
    
    Args:
        eval_date: Evaluation date (Python date or QuantLib Date)
        r: Dictionary of market rates with keys:
           - JIBAR3M: 3-month deposit rate (%)
           - FRA_3x6, FRA_6x9, FRA_9x12, FRA_18x21: FRA rates (%)
           - SASW2, SASW3, SASW5, SASW10: Swap rates (%)
        shift_bps: Parallel shift in bps (for DV01 calculation)
    
    Returns:
        Tuple of (curve, settlement_date, day_count)
        - curve: QuantLib.PiecewiseLogCubicDiscount curve
        - settlement_date: Settlement date (T+0)
        - day_count: QuantLib.Actual365Fixed
    
    Example:
        >>> rates = {
        ...     'JIBAR3M': 6.63,
        ...     'FRA_3x6': 6.70,
        ...     'SASW2': 7.20,
        ...     'SASW5': 7.80
        ... }
        >>> curve, settlement, dc = build_jibar_curve(date.today(), rates)
    """
    calendar = get_sa_calendar()
    settlement_days = 0
    ql_today = to_ql_date(eval_date)
    ql.Settings.instance().evaluationDate = ql_today
    settlement = calendar.advance(ql_today, settlement_days, ql.Days)

    helpers = []
    day_count = ql.Actual365Fixed()
    shift = shift_bps / 10000.0

    # 3M Deposit (spot, 0 settlement days)
    helpers.append(ql.DepositRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(r["JIBAR3M"] / 100 + shift)),
        ql.Period(3, ql.Months),
        settlement_days,
        calendar,
        ql.ModifiedFollowing,
        False,
        day_count
    ))

    # FRAs (start month × end month from settlement)
    for start_m, end_m, key in [(3, 6, "FRA_3x6"), (6, 9, "FRA_6x9"),
                                  (9, 12, "FRA_9x12"), (18, 21, "FRA_18x21")]:
        helpers.append(ql.FraRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(r[key] / 100 + shift)),
            start_m,
            end_m,
            settlement_days,
            calendar,
            ql.ModifiedFollowing,
            False,
            day_count
        ))

    # Interest Rate Swaps (quarterly JIBAR floating, ACT/365)
    jibar_index = ql.Jibar(ql.Period(3, ql.Months))
    for tenor, key in [(2, "SASW2"), (3, "SASW3"), (5, "SASW5"), (10, "SASW10")]:
        helpers.append(ql.SwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(r[key] / 100 + shift)),
            ql.Period(tenor, ql.Years),
            calendar,
            ql.Quarterly,
            ql.ModifiedFollowing,
            ql.Actual365Fixed(),
            jibar_index
        ))

    # Build piecewise log-cubic discount curve
    curve = ql.PiecewiseLogCubicDiscount(settlement, helpers, day_count)
    curve.enableExtrapolation()
    
    return curve, settlement, day_count


def build_jibar_curve_with_diagnostics(eval_date, r, shift_bps=0.0):
    """
    Build JIBAR curve and return par-instrument repricing errors for diagnostics.
    
    Useful for validating curve construction quality.
    
    Args:
        eval_date: Evaluation date
        r: Dictionary of market rates
        shift_bps: Parallel shift in bps
    
    Returns:
        Tuple of (curve, settlement, day_count, diagnostics_list)
        - diagnostics_list: List of dicts with repricing errors
    
    Example diagnostics entry:
        {
            'Instrument': 'JIBAR3M Depo',
            'Market (%)': 6.63,
            'Implied (%)': 6.6301,
            'Error (bps)': 0.01
        }
    """
    curve, settlement, day_count = build_jibar_curve(eval_date, r, shift_bps)
    calendar = get_sa_calendar()

    diag = []
    
    # Deposit repricing
    try:
        d_end = calendar.advance(settlement, ql.Period(3, ql.Months), ql.ModifiedFollowing)
        t = day_count.yearFraction(settlement, d_end)
        df_end = curve.discount(d_end)
        implied = (1.0 / df_end - 1.0) / t * 100
        diag.append({
            "Instrument": "JIBAR3M Depo",
            "Market (%)": r["JIBAR3M"],
            "Implied (%)": implied,
            "Error (bps)": (implied - r["JIBAR3M"]) * 100
        })
    except Exception:
        pass

    # FRA repricing
    for start_m, end_m, key in [(3, 6, "FRA_3x6"), (6, 9, "FRA_6x9"),
                                  (9, 12, "FRA_9x12"), (18, 21, "FRA_18x21")]:
        try:
            d_s = calendar.advance(settlement, ql.Period(start_m, ql.Months), ql.ModifiedFollowing)
            d_e = calendar.advance(settlement, ql.Period(end_m, ql.Months), ql.ModifiedFollowing)
            fwd = curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate() * 100
            diag.append({
                "Instrument": f"FRA {start_m}x{end_m}",
                "Market (%)": r[key],
                "Implied (%)": fwd,
                "Error (bps)": (fwd - r[key]) * 100
            })
        except Exception:
            pass

    # Swap repricing (par rate calculation)
    for tenor, key in [(2, "SASW2"), (3, "SASW3"), (5, "SASW5"), (10, "SASW10")]:
        try:
            sched = ql.Schedule(
                settlement,
                calendar.advance(settlement, ql.Period(tenor, ql.Years), ql.ModifiedFollowing),
                ql.Period(3, ql.Months),
                calendar,
                ql.ModifiedFollowing,
                ql.ModifiedFollowing,
                ql.DateGeneration.Forward,
                False
            )
            
            # Calculate annuity (sum of discount factors × accrual fractions)
            annuity = 0.0
            for i in range(1, len(sched)):
                t_i = day_count.yearFraction(sched[i - 1], sched[i])
                annuity += t_i * curve.discount(sched[i])
            
            # Floating leg PV = 1 - df(maturity)
            df_mat = curve.discount(sched[-1])
            par_rate = (1.0 - df_mat) / annuity * 100 if annuity > 0 else 0.0
            
            diag.append({
                "Instrument": f"SASW{tenor}Y",
                "Market (%)": r[key],
                "Implied (%)": par_rate,
                "Error (bps)": (par_rate - r[key]) * 100
            })
        except Exception:
            pass

    return curve, settlement, day_count, diag


def build_key_rate_curves(eval_date, r, day_count, tenors):
    """
    Build key-rate shifted JIBAR curves for key-rate DV01 calculation.
    
    Creates a separate curve for each tenor with a 1bp shift at that tenor only.
    
    Args:
        eval_date: Evaluation date
        r: Dictionary of market rates
        day_count: Day count convention
        tenors: List of tenors to shift (e.g., ['3M', '1Y', '2Y', '5Y'])
    
    Returns:
        Dictionary mapping tenor to shifted curve
        Example: {'3M': curve_3m_shifted, '1Y': curve_1y_shifted, ...}
    """
    tenor_map = {
        '3M': ('JIBAR3M', 'depo'),
        '6M': ('FRA_3x6', 'fra'),
        '1Y': ('FRA_9x12', 'fra'),
        '2Y': ('SASW2', 'swap'),
        '3Y': ('SASW3', 'swap'),
        '5Y': ('SASW5', 'swap'),
        '10Y': ('SASW10', 'swap')
    }
    
    kr_curves = {}
    
    for tenor in tenors:
        if tenor not in tenor_map:
            continue
        
        # Create shifted rates dictionary
        r_shifted = r.copy()
        key, inst_type = tenor_map[tenor]
        
        if key in r_shifted:
            # Shift this tenor by 1bp
            r_shifted[key] = r_shifted[key] + 0.01  # 1bp = 0.01%
            
            try:
                # Build curve with this tenor shifted
                curve, _, _ = build_jibar_curve(eval_date, r_shifted, shift_bps=0.0)
                kr_curves[tenor] = curve
            except Exception:
                # If curve building fails, skip this tenor
                pass
    
    return kr_curves
