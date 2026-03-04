"""
Repo Economics - CANONICAL
===========================

Proper repo economics including coupon entitlement and interest calculations.
"""

from datetime import date, timedelta
from typing import Optional, Tuple
from ..core.daycount import ActualThreeSixtyFive


def calculate_repo_interest(cash_amount: float, repo_rate: float, 
                           start_date: date, end_date: date,
                           day_count: Optional[ActualThreeSixtyFive] = None) -> float:
    """
    Calculate repo interest for a repo trade.
    
    **CANONICAL REPO INTEREST CALCULATION**
    
    Interest = Cash × Rate × (Days / 365)
    
    Args:
        cash_amount: Repo cash amount
        repo_rate: Repo rate in % (e.g., 6.73 for 6.73%)
        start_date: Repo start date (spot date)
        end_date: Repo end date (maturity)
        day_count: Day count convention (default: ACT/365)
    
    Returns:
        Interest amount in ZAR
    """
    if day_count is None:
        day_count = ActualThreeSixtyFive()
    
    year_fraction = day_count.year_fraction(start_date, end_date)
    interest = cash_amount * (repo_rate / 100) * year_fraction
    
    return interest


def determine_coupon_ownership(repo_trade: dict, coupon_date: date) -> str:
    """
    Determine who owns the coupon for a repo'd position.
    
    **CANONICAL COUPON ENTITLEMENT LOGIC**
    
    Rules:
    1. If coupon_to_lender = True: Lender gets coupon
    2. If coupon_to_lender = False: Borrower keeps coupon
    3. Default: Borrower keeps coupon (standard repo convention)
    
    Args:
        repo_trade: Repo trade dictionary
        coupon_date: Coupon payment date
    
    Returns:
        'lender' or 'borrower'
    """
    spot_date = repo_trade.get('spot_date')
    end_date = repo_trade.get('end_date')
    
    # Convert string dates if needed
    if isinstance(spot_date, str):
        from datetime import datetime
        spot_date = datetime.strptime(spot_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        from datetime import datetime
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Check if coupon falls within repo period
    if not (spot_date <= coupon_date <= end_date):
        return 'borrower'  # Repo not active, borrower owns
    
    # Check coupon entitlement flag
    coupon_to_lender = repo_trade.get('coupon_to_lender', False)
    
    if coupon_to_lender:
        return 'lender'
    else:
        return 'borrower'


def calculate_coupon_entitlement(position_notional: float, coupon_rate: float,
                                 coupon_start: date, coupon_end: date,
                                 repo_trade: Optional[dict] = None,
                                 day_count: Optional[ActualThreeSixtyFive] = None) -> Tuple[float, str]:
    """
    Calculate coupon amount and determine ownership.
    
    Args:
        position_notional: Position notional
        coupon_rate: Coupon rate in % (e.g., 7.93 for 7.93%)
        coupon_start: Coupon period start date
        coupon_end: Coupon period end date (payment date)
        repo_trade: Optional repo trade dict (if position is repo'd)
        day_count: Day count convention (default: ACT/365)
    
    Returns:
        Tuple of (coupon_amount, owner)
        - coupon_amount: Coupon in ZAR
        - owner: 'borrower' or 'lender'
    """
    if day_count is None:
        day_count = ActualThreeSixtyFive()
    
    # Calculate coupon amount
    year_fraction = day_count.year_fraction(coupon_start, coupon_end)
    coupon_amount = position_notional * (coupon_rate / 100) * year_fraction
    
    # Determine ownership
    if repo_trade is None:
        owner = 'borrower'  # No repo, borrower (portfolio) owns
    else:
        owner = determine_coupon_ownership(repo_trade, coupon_end)
    
    return coupon_amount, owner


def calculate_repo_economics(repo_trade: dict, jibar_rate: float,
                            collateral_coupons: Optional[list] = None) -> dict:
    """
    Calculate complete repo economics including interest and coupon adjustments.
    
    Args:
        repo_trade: Repo trade dictionary
        jibar_rate: JIBAR 3M rate in %
        collateral_coupons: List of coupon payments during repo period
    
    Returns:
        Dictionary with repo economics
    """
    cash_amount = repo_trade.get('cash_amount', 0)
    repo_spread_bps = repo_trade.get('repo_spread_bps', 0)
    spot_date = repo_trade.get('spot_date')
    end_date = repo_trade.get('end_date')
    direction = repo_trade.get('direction', 'borrow_cash')
    
    # Convert dates if needed
    if isinstance(spot_date, str):
        from datetime import datetime
        spot_date = datetime.strptime(spot_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        from datetime import datetime
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Calculate repo rate
    repo_rate = jibar_rate + (repo_spread_bps / 100)
    
    # Calculate repo interest
    repo_interest = calculate_repo_interest(cash_amount, repo_rate, spot_date, end_date)
    
    # Adjust for direction
    if direction == 'borrow_cash':
        # We pay interest
        interest_cashflow = -repo_interest
    else:
        # We receive interest
        interest_cashflow = repo_interest
    
    # Calculate coupon adjustments
    coupon_adjustment = 0.0
    if collateral_coupons:
        for coupon in collateral_coupons:
            coupon_amount = coupon.get('amount', 0)
            coupon_date = coupon.get('date')
            
            owner = determine_coupon_ownership(repo_trade, coupon_date)
            
            if direction == 'borrow_cash' and owner == 'lender':
                # We borrowed cash, lender gets coupon, we pay it
                coupon_adjustment -= coupon_amount
            elif direction == 'lend_cash' and owner == 'lender':
                # We lent cash, we get coupon
                coupon_adjustment += coupon_amount
    
    return {
        'repo_rate': repo_rate,
        'repo_interest': repo_interest,
        'interest_cashflow': interest_cashflow,
        'coupon_adjustment': coupon_adjustment,
        'net_cashflow': interest_cashflow + coupon_adjustment,
        'term_days': (end_date - spot_date).days
    }
