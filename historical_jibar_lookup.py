"""
Historical JIBAR3M Lookup Utility
==================================

Provides accurate historical JIBAR3M rates for:
- Repo rate calculations (spot date lookup)
- Realized coupon calculations (reset date lookup)
- Any historical rate requirement

Uses actual historical data from JIBAR_FRA_SWAPS.xlsx
"""

import pandas as pd
from datetime import date, datetime, timedelta


def load_historical_jibar(filepath='JIBAR_FRA_SWAPS.xlsx'):
    """Load historical JIBAR data"""
    try:
        df = pd.read_excel(filepath)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        print(f"Warning: Could not load historical JIBAR data: {e}")
        return None


def get_jibar3m_on_date(target_date, df_historical=None, fallback_rate=6.63):
    """
    Get actual JIBAR3M rate on a specific date
    
    Args:
        target_date: date to lookup
        df_historical: DataFrame with historical JIBAR data
        fallback_rate: Rate to use if historical data not available
    
    Returns:
        JIBAR3M rate (as %, e.g., 6.63)
    """
    
    if df_historical is None or df_historical.empty:
        return fallback_rate
    
    # Convert target_date to datetime if needed
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()
    
    # Find closest date in historical data
    df_historical['Date_Only'] = df_historical['Date'].dt.date
    
    # Try exact match first
    exact_match = df_historical[df_historical['Date_Only'] == target_date]
    if not exact_match.empty and 'JIBAR3M' in exact_match.columns:
        return exact_match.iloc[0]['JIBAR3M']
    
    # Find closest date (within 5 business days)
    df_historical['Days_Diff'] = abs((df_historical['Date_Only'] - target_date).dt.days)
    closest = df_historical.nsmallest(1, 'Days_Diff')
    
    if not closest.empty and closest.iloc[0]['Days_Diff'] <= 5:
        if 'JIBAR3M' in closest.columns:
            return closest.iloc[0]['JIBAR3M']
    
    # Fallback
    return fallback_rate


def get_jibar3m_for_period(start_date, end_date, df_historical=None):
    """
    Get JIBAR3M rates for a period (for coupon calculations)
    
    Returns:
        List of (date, rate) tuples
    """
    
    if df_historical is None or df_historical.empty:
        return []
    
    # Convert dates
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    df_historical['Date_Only'] = df_historical['Date'].dt.date
    
    # Filter to period
    mask = (df_historical['Date_Only'] >= start_date) & (df_historical['Date_Only'] <= end_date)
    period_data = df_historical[mask]
    
    if period_data.empty or 'JIBAR3M' not in period_data.columns:
        return []
    
    return list(zip(period_data['Date_Only'], period_data['JIBAR3M']))


def calculate_repo_rate_accurate(spot_date, repo_spread_bps, df_historical=None, fallback_jibar=6.63):
    """
    Calculate accurate repo rate using historical JIBAR3M on spot date
    
    Args:
        spot_date: Repo spot date
        repo_spread_bps: Spread over JIBAR in bps
        df_historical: Historical data
        fallback_jibar: Fallback if no historical data
    
    Returns:
        Repo rate (as %, e.g., 6.73 for JIBAR 6.63% + 10bps)
    """
    
    # Get actual JIBAR3M on spot date
    jibar_on_spot = get_jibar3m_on_date(spot_date, df_historical, fallback_jibar)
    
    # Add spread (convert bps to %)
    repo_rate = jibar_on_spot + (repo_spread_bps / 100)
    
    return repo_rate


def calculate_realized_coupon_accurate(reset_date, payment_date, notional, spread_bps, 
                                       df_historical=None, fallback_jibar=6.63):
    """
    Calculate realized coupon using actual JIBAR3M on reset date
    
    Args:
        reset_date: Coupon reset date (typically start of period)
        payment_date: Coupon payment date
        notional: Position notional
        spread_bps: Issue spread in bps
        df_historical: Historical data
        fallback_jibar: Fallback if no historical data
    
    Returns:
        Coupon amount (in currency)
    """
    
    # Get actual JIBAR3M on reset date
    jibar_on_reset = get_jibar3m_on_date(reset_date, df_historical, fallback_jibar)
    
    # Calculate coupon rate
    coupon_rate = jibar_on_reset + (spread_bps / 100)  # Convert bps to %
    
    # Calculate day count fraction (ACT/365)
    if isinstance(reset_date, str):
        reset_date = datetime.strptime(reset_date, '%Y-%m-%d').date()
    if isinstance(payment_date, str):
        payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
    
    days = (payment_date - reset_date).days
    dcf = days / 365.0
    
    # Calculate coupon
    coupon_amount = notional * (coupon_rate / 100) * dcf
    
    return coupon_amount


def get_forward_jibar_projection(projection_date, df_historical=None, fallback_rate=6.63):
    """
    Project JIBAR3M for future dates using latest available rate
    
    For dates beyond historical data, uses the most recent rate as projection
    """
    
    if df_historical is None or df_historical.empty:
        return fallback_rate
    
    # Convert projection_date
    if isinstance(projection_date, str):
        projection_date = datetime.strptime(projection_date, '%Y-%m-%d').date()
    
    # Get latest available rate
    df_historical['Date_Only'] = df_historical['Date'].dt.date
    latest_data = df_historical.nlargest(1, 'Date')
    
    if not latest_data.empty and 'JIBAR3M' in latest_data.columns:
        latest_rate = latest_data.iloc[0]['JIBAR3M']
        latest_date = latest_data.iloc[0]['Date_Only']
        
        # If projection date is in the past or near-term, try to get actual
        if projection_date <= latest_date:
            return get_jibar3m_on_date(projection_date, df_historical, latest_rate)
        else:
            # Use latest rate as forward projection
            return latest_rate
    
    return fallback_rate


def validate_historical_data(df_historical):
    """
    Validate historical JIBAR data quality
    
    Returns:
        dict with validation results
    """
    
    if df_historical is None or df_historical.empty:
        return {
            'valid': False,
            'error': 'No historical data available',
            'warnings': []
        }
    
    warnings = []
    
    # Check for required columns
    if 'Date' not in df_historical.columns:
        return {'valid': False, 'error': 'Missing Date column', 'warnings': []}
    
    if 'JIBAR3M' not in df_historical.columns:
        return {'valid': False, 'error': 'Missing JIBAR3M column', 'warnings': []}
    
    # Check for missing values
    missing_jibar = df_historical['JIBAR3M'].isna().sum()
    if missing_jibar > 0:
        warnings.append(f'{missing_jibar} missing JIBAR3M values')
    
    # Check date range
    df_historical['Date_Only'] = df_historical['Date'].dt.date
    min_date = df_historical['Date_Only'].min()
    max_date = df_historical['Date_Only'].max()
    
    # Check if data is recent
    days_since_last = (date.today() - max_date).days
    if days_since_last > 7:
        warnings.append(f'Data is {days_since_last} days old (last: {max_date})')
    
    # Check for gaps
    date_diffs = df_historical.sort_values('Date')['Date'].diff()
    large_gaps = date_diffs[date_diffs > timedelta(days=7)]
    if len(large_gaps) > 0:
        warnings.append(f'{len(large_gaps)} gaps > 7 days in historical data')
    
    return {
        'valid': True,
        'date_range': (min_date, max_date),
        'num_records': len(df_historical),
        'warnings': warnings
    }


# Example usage
if __name__ == "__main__":
    # Load data
    df = load_historical_jibar()
    
    if df is not None:
        # Validate
        validation = validate_historical_data(df)
        print("Validation:", validation)
        
        # Test lookup
        test_date = date(2024, 1, 15)
        rate = get_jibar3m_on_date(test_date, df)
        print(f"JIBAR3M on {test_date}: {rate:.4f}%")
        
        # Test repo rate
        repo_rate = calculate_repo_rate_accurate(test_date, 10, df)
        print(f"Repo rate (JIBAR + 10bps): {repo_rate:.4f}%")
        
        # Test coupon
        coupon = calculate_realized_coupon_accurate(
            test_date, 
            test_date + timedelta(days=90),
            100_000_000,
            130,
            df
        )
        print(f"Realized coupon (R100M, 130bps spread): R{coupon:,.2f}")
