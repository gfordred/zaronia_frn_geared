"""
Risk Calculations - CANONICAL
==============================

Single source of truth for DV01, CS01, and key-rate risk calculations.
"""

try:
    import QuantLib as ql
    from .frn import price_frn
except ImportError:
    import QuantLib as ql
    from src.pricing.frn import price_frn


def calculate_dv01_cs01(nominal, issue_spread, dm, start, end,
                         proj_curve, disc_base_curve, settlement,
                         day_count, calendar, index_type,
                         zaronia_spread_bps, lookback,
                         df_hist, df_zaronia, zaronia_dict, jibar_dict,
                         eval_date, rates_dict, build_jibar_curve_func,
                         build_zaronia_curve_func):
    """
    Calculate DV01 and CS01 (DM01) for an FRN.
    
    **CANONICAL RISK ENGINE - DO NOT DUPLICATE**
    
    DV01 (Dollar Value of 01):
    - Sensitivity to 1bp parallel shift in JIBAR curve
    - Calculated by shifting entire JIBAR curve up 1bp and repricing
    
    CS01 (Credit Spread 01) / DM01 (Discount Margin 01):
    - Sensitivity to 1bp increase in discount margin
    - Calculated by increasing DM by 1bp and repricing
    
    Args:
        nominal: Position notional
        issue_spread: Issue spread in bps
        dm: Discount margin in bps
        start: FRN start date
        end: FRN maturity date
        proj_curve: Projection curve
        disc_base_curve: Base discount curve
        settlement: Settlement date
        day_count: Day count convention
        calendar: Business day calendar
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread
        lookback: Lookback days
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
        zaronia_dict: ZARONIA lookup
        jibar_dict: JIBAR lookup
        eval_date: Evaluation date
        rates_dict: Market rates dictionary
        build_jibar_curve_func: Function to build JIBAR curve
        build_zaronia_curve_func: Function to build ZARONIA curve
    
    Returns:
        Tuple of (dv01, cs01)
        - dv01: Change in value for 1bp parallel shift in JIBAR
        - cs01: Change in value for 1bp increase in DM
    """
    # Base case pricing
    _, _, base_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False
    )

    # DV01: Shift JIBAR curve up 1bp
    shifted_jibar, _, _ = build_jibar_curve_func(eval_date, rates_dict, shift_bps=1.0)
    
    # If ZARONIA, rebuild ZARONIA curve from shifted JIBAR
    shifted_proj = (build_zaronia_curve_func(shifted_jibar, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else shifted_jibar)
    
    _, _, shifted_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        shifted_proj, shifted_jibar, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False
    )
    
    # DV01 = (base - shifted) * 10 to convert 0.1bp to 1bp
    dv01 = (base_clean - shifted_clean) * 10.0

    # CS01/DM01: Increase DM by 1bp
    _, _, dm_clean, _ = price_frn(
        nominal, issue_spread, dm + 1.0, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False
    )
    
    # CS01 = (base - dm_shifted) * 10
    cs01 = (base_clean - dm_clean) * 10.0

    return dv01, cs01


def calculate_key_rate_dv01(nominal, issue_spread, dm, start, end,
                              disc_base_curve, settlement,
                              day_count, calendar, index_type,
                              zaronia_spread_bps, lookback,
                              df_hist, df_zaronia, zaronia_dict, jibar_dict,
                              eval_date, rates_dict, base_clean,
                              build_key_rate_curves_func,
                              build_zaronia_curve_func):
    """
    Calculate key-rate DV01 for standard tenors.
    
    Key-rate DV01 measures sensitivity to 1bp shift at specific tenor points
    while keeping other points unchanged.
    
    Args:
        nominal: Position notional
        issue_spread: Issue spread in bps
        dm: Discount margin in bps
        start: FRN start date
        end: FRN maturity date
        disc_base_curve: Base discount curve
        settlement: Settlement date
        day_count: Day count convention
        calendar: Business day calendar
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread
        lookback: Lookback days
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
        zaronia_dict: ZARONIA lookup
        jibar_dict: JIBAR lookup
        eval_date: Evaluation date
        rates_dict: Market rates dictionary
        base_clean: Base clean price (for efficiency)
        build_key_rate_curves_func: Function to build key-rate shifted curves
        build_zaronia_curve_func: Function to build ZARONIA curve
    
    Returns:
        Dictionary mapping tenor to key-rate DV01
        Example: {'3M': 150.0, '1Y': 450.0, '2Y': 300.0, ...}
    """
    tenors = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y']
    kr_curves = build_key_rate_curves_func(eval_date, rates_dict, day_count, tenors)
    
    results = {}
    for tenor, kr_proj in kr_curves.items():
        try:
            # If ZARONIA, rebuild from key-rate shifted curve
            proj = (build_zaronia_curve_func(kr_proj, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else kr_proj)
            
            _, _, kr_clean, _ = price_frn(
                nominal, issue_spread, dm, start, end,
                proj, kr_proj, settlement,
                day_count, calendar, index_type,
                zaronia_spread_bps, lookback, df_hist, df_zaronia,
                zaronia_dict, jibar_dict, return_df=False
            )
            
            # Key-rate DV01 for this tenor
            results[tenor] = (base_clean - kr_clean) * 10.0
        except Exception:
            # If curve building fails for this tenor, set to 0
            results[tenor] = 0.0
    
    return results


def solve_dm(target_all_in, nominal, issue_spread, start, end,
             proj_curve, disc_base_curve, settlement,
             day_count, calendar, index_type,
             zaronia_spread_bps, lookback,
             df_hist, df_zaronia, zaronia_dict, jibar_dict,
             initial_guess=None, max_iterations=12, tolerance=1e-4):
    """
    Solve for discount margin (DM) given target all-in price.
    
    Uses secant method to find DM that produces target price.
    
    Args:
        target_all_in: Target all-in (dirty) price
        nominal: Position notional
        issue_spread: Issue spread in bps
        start: FRN start date
        end: FRN maturity date
        proj_curve: Projection curve
        disc_base_curve: Base discount curve
        settlement: Settlement date
        day_count: Day count convention
        calendar: Business day calendar
        index_type: 'JIBAR 3M' or 'ZARONIA'
        zaronia_spread_bps: ZARONIA spread
        lookback: Lookback days
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
        zaronia_dict: ZARONIA lookup
        jibar_dict: JIBAR lookup
        initial_guess: Initial DM guess (default: issue_spread)
        max_iterations: Maximum iterations (default: 12)
        tolerance: Convergence tolerance (default: 1e-4)
    
    Returns:
        Solved discount margin in bps
    """
    x0 = initial_guess if initial_guess is not None else issue_spread
    x1 = x0 + 10.0

    for _ in range(max_iterations):
        # Price at x0
        p0, _, _, _ = price_frn(
            nominal, issue_spread, x0, start, end,
            proj_curve, disc_base_curve, settlement,
            day_count, calendar, index_type,
            zaronia_spread_bps, lookback, df_hist, df_zaronia,
            zaronia_dict, jibar_dict, return_df=False
        )
        
        # Price at x1
        p1, _, _, _ = price_frn(
            nominal, issue_spread, x1, start, end,
            proj_curve, disc_base_curve, settlement,
            day_count, calendar, index_type,
            zaronia_spread_bps, lookback, df_hist, df_zaronia,
            zaronia_dict, jibar_dict, return_df=False
        )
        
        # Check convergence
        y0 = p0 - target_all_in
        y1 = p1 - target_all_in
        
        if abs(y1) < tolerance:
            return x1
        
        # Check for numerical issues
        if abs(y1 - y0) < 1e-10:
            break
        
        # Secant method update
        x_new = x1 - y1 * (x1 - x0) / (y1 - y0)
        x0, x1 = x1, x_new

    return x1


def calculate_portfolio_risk(positions, proj_curve, disc_base_curve, settlement,
                             day_count, calendar, eval_date, rates_dict,
                             build_jibar_curve_func, build_zaronia_curve_func,
                             df_hist=None, df_zaronia=None):
    """
    Calculate aggregate portfolio risk metrics.
    
    Args:
        positions: List of position dictionaries
        proj_curve: Projection curve
        disc_base_curve: Base discount curve
        settlement: Settlement date
        day_count: Day count convention
        calendar: Business day calendar
        eval_date: Evaluation date
        rates_dict: Market rates dictionary
        build_jibar_curve_func: JIBAR curve builder
        build_zaronia_curve_func: ZARONIA curve builder
        df_hist: Historical JIBAR data
        df_zaronia: Historical ZARONIA data
    
    Returns:
        Dictionary with total_dv01, total_cs01, and per-position breakdown
    """
    total_dv01 = 0.0
    total_cs01 = 0.0
    position_risks = []
    
    for pos in positions:
        try:
            dv01, cs01 = calculate_dv01_cs01(
                pos.get('notional', 0),
                pos.get('issue_spread', 0),
                pos.get('dm', 0),
                pos.get('start_date'),
                pos.get('maturity'),
                proj_curve, disc_base_curve, settlement,
                day_count, calendar,
                pos.get('index', 'JIBAR 3M'),
                0.0, 0,  # zaronia_spread_bps, lookback
                df_hist, df_zaronia, None, None,
                eval_date, rates_dict,
                build_jibar_curve_func,
                build_zaronia_curve_func
            )
            
            total_dv01 += dv01
            total_cs01 += cs01
            
            position_risks.append({
                'id': pos.get('id'),
                'name': pos.get('name'),
                'dv01': dv01,
                'cs01': cs01
            })
        except Exception as e:
            # Skip positions that fail to price
            position_risks.append({
                'id': pos.get('id'),
                'name': pos.get('name'),
                'dv01': 0.0,
                'cs01': 0.0,
                'error': str(e)
            })
    
    return {
        'total_dv01': total_dv01,
        'total_cs01': total_cs01,
        'positions': position_risks
    }
