"""
Data Validators
===============

Validation functions for portfolio, repo, and market data quality.
"""

import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Tuple
import logging

from .schemas import Position, RepoTrade, MarketData, Portfolio, RepoBook

logger = logging.getLogger(__name__)


def validate_portfolio(positions: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate portfolio data quality.
    
    Args:
        positions: List of position dictionaries
    
    Returns:
        Tuple of (is_valid, list of warnings/errors)
    """
    warnings = []
    errors = []
    
    if not positions:
        warnings.append("Portfolio is empty")
        return True, warnings
    
    # Try to parse each position with Pydantic
    valid_positions = []
    for i, pos_dict in enumerate(positions):
        try:
            pos = Position(**pos_dict)
            valid_positions.append(pos)
        except Exception as e:
            errors.append(f"Position {i}: {str(e)}")
    
    if errors:
        return False, errors
    
    # Create Portfolio object for additional validation
    portfolio = Portfolio(positions=valid_positions)
    
    # Check for duplicate IDs
    ids = [p.id for p in valid_positions]
    if len(ids) != len(set(ids)):
        warnings.append("Duplicate position IDs found")
    
    # Check for concentration
    total_notional = portfolio.total_notional()
    counterparty_exposure = {}
    for pos in valid_positions:
        counterparty_exposure[pos.counterparty] = \
            counterparty_exposure.get(pos.counterparty, 0) + pos.notional
    
    for cpty, exposure in counterparty_exposure.items():
        pct = (exposure / total_notional) * 100 if total_notional > 0 else 0
        if cpty == "Republic of South Africa" and pct > 50:
            warnings.append(f"Sovereign exposure {pct:.1f}% exceeds 50% limit")
        elif pct > 20:
            warnings.append(f"{cpty} exposure {pct:.1f}% exceeds 20% limit")
    
    # Check for matured positions
    today = date.today()
    matured = [p for p in valid_positions if p.maturity < today]
    if matured:
        warnings.append(f"{len(matured)} positions have matured")
    
    # Check for positions starting in future
    future_start = [p for p in valid_positions if p.start_date > today]
    if future_start:
        warnings.append(f"{len(future_start)} positions start in the future")
    
    return True, warnings


def validate_repo_trades(repos: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate repo trades data quality.
    
    Args:
        repos: List of repo trade dictionaries
    
    Returns:
        Tuple of (is_valid, list of warnings/errors)
    """
    warnings = []
    errors = []
    
    if not repos:
        warnings.append("No repo trades")
        return True, warnings
    
    # Try to parse each repo with Pydantic
    valid_repos = []
    for i, repo_dict in enumerate(repos):
        try:
            repo = RepoTrade(**repo_dict)
            valid_repos.append(repo)
        except Exception as e:
            errors.append(f"Repo {i}: {str(e)}")
    
    if errors:
        return False, errors
    
    # Create RepoBook object
    repo_book = RepoBook(repos=valid_repos)
    
    # Check for duplicate IDs
    ids = [r.id for r in valid_repos]
    if len(ids) != len(set(ids)):
        warnings.append("Duplicate repo IDs found")
    
    # Check for matured repos
    today = date.today()
    matured = [r for r in valid_repos if r.end_date < today]
    if matured:
        warnings.append(f"{len(matured)} repos have matured")
    
    # Check for very short-dated repos (< 7 days)
    short_dated = [r for r in valid_repos 
                   if (r.end_date - r.spot_date).days < 7]
    if short_dated:
        warnings.append(f"{len(short_dated)} repos are very short-dated (< 7 days)")
    
    # Check for very long-dated repos (> 1 year)
    long_dated = [r for r in valid_repos 
                  if (r.end_date - r.spot_date).days > 365]
    if long_dated:
        warnings.append(f"{len(long_dated)} repos are very long-dated (> 1 year)")
    
    # Check repo spread reasonableness
    unusual_spreads = [r for r in valid_repos 
                       if r.repo_spread_bps < 0 or r.repo_spread_bps > 100]
    if unusual_spreads:
        warnings.append(f"{len(unusual_spreads)} repos have unusual spreads (< 0 or > 100 bps)")
    
    return True, warnings


def validate_market_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate market data quality.
    
    Args:
        df: DataFrame with market data
    
    Returns:
        Tuple of (is_valid, list of warnings/errors)
    """
    warnings = []
    errors = []
    
    if df is None or df.empty:
        errors.append("No market data available")
        return False, errors
    
    # Check for required columns
    if 'Date' not in df.columns:
        errors.append("Missing 'Date' column")
        return False, errors
    
    # Check for JIBAR3M (critical)
    if 'JIBAR3M' not in df.columns:
        errors.append("Missing 'JIBAR3M' column")
        return False, errors
    
    # Check date range
    df['Date'] = pd.to_datetime(df['Date'])
    min_date = df['Date'].min()
    max_date = df['Date'].max()
    
    days_of_data = (max_date - min_date).days
    if days_of_data < 365:
        warnings.append(f"Only {days_of_data} days of historical data (< 1 year)")
    
    # Check data freshness
    today = pd.Timestamp.now()
    days_since_last = (today - max_date).days
    if days_since_last > 7:
        warnings.append(f"Data is {days_since_last} days old (last: {max_date.date()})")
    
    # Check for missing values
    if 'JIBAR3M' in df.columns:
        missing_jibar = df['JIBAR3M'].isna().sum()
        if missing_jibar > 0:
            warnings.append(f"{missing_jibar} missing JIBAR3M values")
    
    # Check for gaps in dates
    df_sorted = df.sort_values('Date')
    date_diffs = df_sorted['Date'].diff()
    large_gaps = date_diffs[date_diffs > timedelta(days=7)]
    if len(large_gaps) > 0:
        warnings.append(f"{len(large_gaps)} gaps > 7 days in historical data")
    
    # Check rate reasonableness
    for col in ['JIBAR3M', 'SASW2', 'SASW5', 'SASW10']:
        if col in df.columns:
            min_rate = df[col].min()
            max_rate = df[col].max()
            if min_rate < 0 or max_rate > 30:
                warnings.append(f"{col} has unusual values (min: {min_rate:.2f}%, max: {max_rate:.2f}%)")
    
    return True, warnings


def validate_all_data(portfolio: List[Dict], repos: List[Dict], 
                     market_data: pd.DataFrame) -> Dict[str, Tuple[bool, List[str]]]:
    """
    Validate all data sources.
    
    Args:
        portfolio: Portfolio positions
        repos: Repo trades
        market_data: Market data DataFrame
    
    Returns:
        Dictionary with validation results for each data source
    """
    results = {
        'portfolio': validate_portfolio(portfolio),
        'repos': validate_repo_trades(repos),
        'market_data': validate_market_data(market_data)
    }
    
    # Log results
    for source, (is_valid, messages) in results.items():
        if not is_valid:
            logger.error(f"{source} validation failed: {messages}")
        elif messages:
            logger.warning(f"{source} validation warnings: {messages}")
        else:
            logger.info(f"{source} validation passed")
    
    return results
