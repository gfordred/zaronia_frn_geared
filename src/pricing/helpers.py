"""
Pricing Helper Functions
=========================

Utility functions for pricing calculations.
"""

import pandas as pd
import QuantLib as ql
from datetime import date, datetime


def to_ql_date(d):
    """
    Convert Python date to QuantLib Date.
    
    Args:
        d: Python date, datetime, or QuantLib Date
    
    Returns:
        QuantLib.Date
    """
    if isinstance(d, ql.Date):
        return d
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return ql.Date(d.day, d.month, d.year)
    raise ValueError(f"Cannot convert {type(d)} to QuantLib Date")


def get_lookup_dict(df, col_name):
    """
    Create {date: value} dict for O(1) lookup.
    
    Args:
        df: DataFrame with DatetimeIndex
        col_name: Column name to extract
    
    Returns:
        Dictionary mapping date to value
    """
    if df is None or col_name not in df.columns:
        return {}
    if not isinstance(df.index, pd.DatetimeIndex):
        return {}
    return {ts.date(): val for ts, val in zip(df.index, df[col_name]) if pd.notna(val)}


def get_historical_rate(date_lookup, df, col_name='JIBAR3M'):
    """
    Lookup historical rate with asof fallback.
    
    Args:
        date_lookup: Date to lookup (datetime or date)
        df: DataFrame with DatetimeIndex and rate columns
        col_name: Column name (default: JIBAR3M)
    
    Returns:
        Rate as decimal (e.g., 0.0663 for 6.63%) or None
    """
    if df is None:
        return None
    
    ts_lookup = pd.Timestamp(date_lookup)
    
    if isinstance(df.index, pd.DatetimeIndex):
        # Try exact match first
        if ts_lookup in df.index:
            val = df.at[ts_lookup, col_name]
            if pd.notna(val):
                return val / 100.0
        
        # Try asof (most recent value before date)
        try:
            prev_ts = df.index.asof(ts_lookup)
            if pd.notna(prev_ts):
                val = df.at[prev_ts, col_name]
                if pd.notna(val):
                    return val / 100.0
        except Exception:
            pass
    
    return None
