"""
Portfolio Module
================

Portfolio and repo models with Pydantic validation and proper economics.
"""

from .models import (
    FRNPosition,
    RepoTrade,
    Portfolio,
    RepoBook,
    PortfolioSnapshot
)
from .portfolio_engine import (
    PortfolioAggregator,
    calculate_portfolio_metrics,
    calculate_gearing,
    calculate_net_yield
)
from .repo_economics import (
    calculate_repo_interest,
    calculate_coupon_entitlement,
    determine_coupon_ownership
)

__all__ = [
    'FRNPosition',
    'RepoTrade',
    'Portfolio',
    'RepoBook',
    'PortfolioSnapshot',
    'PortfolioAggregator',
    'calculate_portfolio_metrics',
    'calculate_gearing',
    'calculate_net_yield',
    'calculate_repo_interest',
    'calculate_coupon_entitlement',
    'determine_coupon_ownership'
]
