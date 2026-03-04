"""
Day Count Conventions
=====================

ACT/365 day count convention for South African market.
"""

import QuantLib as ql
from datetime import date, datetime


class ActualThreeSixtyFive:
    """
    ACT/365 day count convention.
    
    Standard for South African floating rate notes.
    """
    
    def __init__(self):
        self.ql_daycount = ql.Actual365Fixed()
    
    def year_fraction(self, start_date, end_date):
        """
        Calculate year fraction between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            float: Year fraction (actual days / 365)
        """
        # Convert to QuantLib dates if needed
        if isinstance(start_date, (date, datetime)):
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            start_ql = ql.Date(start_date.day, start_date.month, start_date.year)
        else:
            start_ql = start_date
        
        if isinstance(end_date, (date, datetime)):
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            end_ql = ql.Date(end_date.day, end_date.month, end_date.year)
        else:
            end_ql = end_date
        
        return self.ql_daycount.yearFraction(start_ql, end_ql)
    
    def day_count(self, start_date, end_date):
        """
        Calculate actual number of days between dates.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            int: Number of days
        """
        # Convert to QuantLib dates if needed
        if isinstance(start_date, (date, datetime)):
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            start_ql = ql.Date(start_date.day, start_date.month, start_date.year)
        else:
            start_ql = start_date
        
        if isinstance(end_date, (date, datetime)):
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            end_ql = ql.Date(end_date.day, end_date.month, end_date.year)
        else:
            end_ql = end_date
        
        return self.ql_daycount.dayCount(start_ql, end_ql)
    
    def __repr__(self):
        return "ACT/365"


def get_day_count_convention(convention_name='ACT/365'):
    """
    Get day count convention by name.
    
    Args:
        convention_name: Name of convention (default: ACT/365)
    
    Returns:
        Day count convention object
    """
    if convention_name.upper() in ['ACT/365', 'ACTUAL/365', 'ACT365']:
        return ActualThreeSixtyFive()
    else:
        raise ValueError(f"Unknown day count convention: {convention_name}")
