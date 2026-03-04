"""
Business Day Conventions
=========================

Standard business day conventions for South African market.
"""

import QuantLib as ql
from enum import Enum


class BusinessDayConvention(Enum):
    """Business day convention enumeration"""
    FOLLOWING = "Following"
    MODIFIED_FOLLOWING = "ModifiedFollowing"
    PRECEDING = "Preceding"
    MODIFIED_PRECEDING = "ModifiedPreceding"
    UNADJUSTED = "Unadjusted"


def get_business_day_convention(convention_name='ModifiedFollowing'):
    """
    Get QuantLib business day convention.
    
    Args:
        convention_name: Name of convention (default: ModifiedFollowing)
    
    Returns:
        QuantLib business day convention
    """
    convention_map = {
        'Following': ql.Following,
        'ModifiedFollowing': ql.ModifiedFollowing,
        'Preceding': ql.Preceding,
        'ModifiedPreceding': ql.ModifiedPreceding,
        'Unadjusted': ql.Unadjusted
    }
    
    if convention_name in convention_map:
        return convention_map[convention_name]
    else:
        # Default to Modified Following (SA market standard)
        return ql.ModifiedFollowing


# South African market standard
SA_BUSINESS_DAY_CONVENTION = ql.ModifiedFollowing
SA_COUPON_FREQUENCY = ql.Quarterly
SA_SETTLEMENT_DAYS = 0  # T+0 for most instruments
