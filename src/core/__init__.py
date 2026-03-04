"""
Core Financial Conventions Module
==================================

South African market conventions for fixed income instruments.
"""

from .calendars import get_sa_calendar
from .daycount import ActualThreeSixtyFive
from .conventions import BusinessDayConvention, get_business_day_convention
from .config import (
    SEED_CAPITAL,
    TARGET_GEARING,
    DEFAULT_JIBAR_RATE,
    DEFAULT_REPO_SPREAD_BPS,
    GOVERNMENT_SPREAD_BPS,
    BANK_SPREADS
)

__all__ = [
    'get_sa_calendar',
    'ActualThreeSixtyFive',
    'BusinessDayConvention',
    'get_business_day_convention',
    'SEED_CAPITAL',
    'TARGET_GEARING',
    'DEFAULT_JIBAR_RATE',
    'DEFAULT_REPO_SPREAD_BPS',
    'GOVERNMENT_SPREAD_BPS',
    'BANK_SPREADS'
]
