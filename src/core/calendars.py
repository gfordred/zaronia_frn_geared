"""
South African Calendar and Business Day Logic
==============================================

Provides South African calendar for business day adjustments.
"""

import QuantLib as ql


def get_sa_calendar():
    """
    Get South African calendar for business day adjustments.
    
    Returns:
        QuantLib.Calendar: South Africa calendar
    """
    return ql.SouthAfrica()


def is_business_day(date, calendar=None):
    """
    Check if a date is a business day in South Africa.
    
    Args:
        date: Date to check (QuantLib.Date or datetime.date)
        calendar: Optional calendar (defaults to SA calendar)
    
    Returns:
        bool: True if business day
    """
    if calendar is None:
        calendar = get_sa_calendar()
    
    # Convert datetime.date to QuantLib.Date if needed
    if hasattr(date, 'day') and hasattr(date, 'month') and hasattr(date, 'year'):
        if not isinstance(date, ql.Date):
            date = ql.Date(date.day, date.month, date.year)
    
    return calendar.isBusinessDay(date)


def adjust_date(date, convention=ql.ModifiedFollowing, calendar=None):
    """
    Adjust date according to business day convention.
    
    Args:
        date: Date to adjust
        convention: Business day convention (default: Modified Following)
        calendar: Optional calendar (defaults to SA calendar)
    
    Returns:
        QuantLib.Date: Adjusted date
    """
    if calendar is None:
        calendar = get_sa_calendar()
    
    # Convert datetime.date to QuantLib.Date if needed
    if hasattr(date, 'day') and hasattr(date, 'month') and hasattr(date, 'year'):
        if not isinstance(date, ql.Date):
            date = ql.Date(date.day, date.month, date.year)
    
    return calendar.adjust(date, convention)


def business_days_between(start_date, end_date, calendar=None):
    """
    Calculate number of business days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        calendar: Optional calendar (defaults to SA calendar)
    
    Returns:
        int: Number of business days
    """
    if calendar is None:
        calendar = get_sa_calendar()
    
    # Convert datetime.date to QuantLib.Date if needed
    if hasattr(start_date, 'day'):
        if not isinstance(start_date, ql.Date):
            start_date = ql.Date(start_date.day, start_date.month, start_date.year)
    if hasattr(end_date, 'day'):
        if not isinstance(end_date, ql.Date):
            end_date = ql.Date(end_date.day, end_date.month, end_date.year)
    
    return calendar.businessDaysBetween(start_date, end_date)
