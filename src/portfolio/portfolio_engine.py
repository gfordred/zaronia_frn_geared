"""
Portfolio Aggregation Engine - CANONICAL
=========================================

Single source of truth for portfolio-level calculations and aggregations.
"""

from typing import List, Dict, Optional
from datetime import date
from .models import FRNPosition, RepoTrade, Portfolio, RepoBook, PortfolioSnapshot


class PortfolioAggregator:
    """
    Aggregates portfolio positions and calculates portfolio-level metrics.
    
    **CANONICAL PORTFOLIO ENGINE - DO NOT DUPLICATE**
    """
    
    def __init__(self, portfolio: Portfolio, repo_book: RepoBook):
        """
        Initialize portfolio aggregator.
        
        Args:
            portfolio: Portfolio object with positions
            repo_book: RepoBook object with repo trades
        """
        self.portfolio = portfolio
        self.repo_book = repo_book
    
    def calculate_gearing(self, as_of_date: Optional[date] = None) -> float:
        """
        Calculate gearing ratio.
        
        **CANONICAL GEARING CALCULATION**
        
        Gearing = Repo Outstanding / Portfolio Notional
        
        Args:
            as_of_date: Date for calculation (default: today)
        
        Returns:
            Gearing ratio (e.g., 9.0 for 9x gearing)
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get active positions and repos as of date
        active_positions = [p for p in self.portfolio.positions 
                          if p.start_date <= as_of_date <= p.maturity]
        active_repos = [r for r in self.repo_book.repos 
                       if r.spot_date <= as_of_date <= r.end_date 
                       and r.direction == "borrow_cash"]
        
        total_notional = sum(p.notional for p in active_positions)
        total_repo = sum(r.cash_amount for r in active_repos)
        
        if total_notional == 0:
            return 0.0
        
        return total_repo / total_notional
    
    def calculate_net_yield(self, jibar_rate: float, as_of_date: Optional[date] = None) -> Dict[str, float]:
        """
        Calculate portfolio net yield metrics.
        
        Args:
            jibar_rate: Current JIBAR 3M rate in %
            as_of_date: Date for calculation (default: today)
        
        Returns:
            Dictionary with yield metrics
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get active positions and repos
        active_positions = [p for p in self.portfolio.positions 
                          if p.start_date <= as_of_date <= p.maturity]
        active_repos = [r for r in self.repo_book.repos 
                       if r.spot_date <= as_of_date <= r.end_date 
                       and r.direction == "borrow_cash"]
        
        total_notional = sum(p.notional for p in active_positions)
        total_repo = sum(r.cash_amount for r in active_repos)
        
        if total_notional == 0:
            return {
                'gross_yield': 0.0,
                'repo_cost_rate': 0.0,
                'net_yield': 0.0,
                'gearing': 0.0
            }
        
        # Calculate average spreads
        avg_frn_spread = sum(p.issue_spread for p in active_positions) / len(active_positions) if active_positions else 0
        avg_repo_spread = sum(r.repo_spread_bps for r in active_repos) / len(active_repos) if active_repos else 0
        
        # Gross yield = JIBAR + avg FRN spread
        gross_yield = jibar_rate + (avg_frn_spread / 100)
        
        # Repo cost rate = JIBAR + avg repo spread
        repo_cost_rate = jibar_rate + (avg_repo_spread / 100)
        
        # Gearing - CORRECTED
        # Gearing = Repo Outstanding / Seed Capital (NOT Total Notional)
        SEED_CAPITAL = 100_000_000  # R100M
        gearing = total_repo / SEED_CAPITAL if SEED_CAPITAL > 0 else 0
        
        # Net yield = Gross yield + (Spread pickup × (Gearing - 1))
        spread_pickup = avg_frn_spread - avg_repo_spread
        net_yield = gross_yield + ((spread_pickup / 100) * (gearing - 1))
        
        return {
            'gross_yield': gross_yield,
            'repo_cost_rate': repo_cost_rate,
            'net_yield': net_yield,
            'gearing': gearing,
            'avg_frn_spread': avg_frn_spread,
            'avg_repo_spread': avg_repo_spread,
            'spread_pickup': spread_pickup
        }
    
    def get_counterparty_exposures(self, as_of_date: Optional[date] = None) -> Dict[str, float]:
        """
        Calculate exposure by counterparty.
        
        Args:
            as_of_date: Date for calculation (default: today)
        
        Returns:
            Dictionary mapping counterparty to exposure amount
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        active_positions = [p for p in self.portfolio.positions 
                          if p.start_date <= as_of_date <= p.maturity]
        
        exposures = {}
        for pos in active_positions:
            if pos.counterparty not in exposures:
                exposures[pos.counterparty] = 0.0
            exposures[pos.counterparty] += pos.notional
        
        return exposures
    
    def create_snapshot(self, as_of_date: Optional[date] = None) -> PortfolioSnapshot:
        """
        Create a point-in-time snapshot of the portfolio.
        
        Args:
            as_of_date: Date for snapshot (default: today)
        
        Returns:
            PortfolioSnapshot object
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Filter to active positions and repos
        active_positions = [p for p in self.portfolio.positions 
                          if p.start_date <= as_of_date <= p.maturity]
        active_repos = [r for r in self.repo_book.repos 
                       if r.spot_date <= as_of_date <= r.end_date]
        
        snapshot_portfolio = Portfolio(positions=active_positions)
        snapshot_repo_book = RepoBook(repos=active_repos)
        
        return PortfolioSnapshot(
            snapshot_date=as_of_date,
            portfolio=snapshot_portfolio,
            repo_book=snapshot_repo_book
        )


def calculate_portfolio_metrics(positions: List[Dict], repos: List[Dict], 
                                jibar_rate: float = 6.63) -> Dict[str, float]:
    """
    Calculate portfolio metrics from raw dictionaries.
    
    Convenience function for backward compatibility.
    
    Args:
        positions: List of position dictionaries
        repos: List of repo dictionaries
        jibar_rate: JIBAR 3M rate in %
    
    Returns:
        Dictionary with portfolio metrics
    """
    # Convert to Pydantic models
    try:
        frn_positions = [FRNPosition(**pos) for pos in positions]
        repo_trades = [RepoTrade(**repo) for repo in repos]
    except Exception as e:
        # If validation fails, return empty metrics
        return {
            'total_notional': 0.0,
            'total_repo': 0.0,
            'gearing': 0.0,
            'gross_yield': 0.0,
            'net_yield': 0.0,
            'error': str(e)
        }
    
    portfolio = Portfolio(positions=frn_positions)
    repo_book = RepoBook(repos=repo_trades)
    aggregator = PortfolioAggregator(portfolio, repo_book)
    
    yield_metrics = aggregator.calculate_net_yield(jibar_rate)
    
    return {
        'total_notional': portfolio.active_notional,
        'total_repo': repo_book.active_borrowed,
        **yield_metrics
    }


def calculate_gearing(positions: List[Dict], repos: List[Dict]) -> float:
    """
    Calculate gearing ratio from raw dictionaries.
    
    **CANONICAL GEARING CALCULATION**
    
    Args:
        positions: List of position dictionaries
        repos: List of repo dictionaries
    
    Returns:
        Gearing ratio
    """
    try:
        frn_positions = [FRNPosition(**pos) for pos in positions]
        repo_trades = [RepoTrade(**repo) for repo in repos]
        portfolio = Portfolio(positions=frn_positions)
        repo_book = RepoBook(repos=repo_trades)
        aggregator = PortfolioAggregator(portfolio, repo_book)
        return aggregator.calculate_gearing()
    except Exception:
        # Fallback to simple calculation
        total_notional = sum(p.get('notional', 0) for p in positions)
        total_repo = sum(r.get('cash_amount', 0) for r in repos 
                        if r.get('direction') == 'borrow_cash')
        return total_repo / total_notional if total_notional > 0 else 0.0


def calculate_net_yield(positions: List[Dict], repos: List[Dict], 
                       jibar_rate: float = 6.63) -> float:
    """
    Calculate net yield from raw dictionaries.
    
    Args:
        positions: List of position dictionaries
        repos: List of repo dictionaries
        jibar_rate: JIBAR 3M rate in %
    
    Returns:
        Net yield in %
    """
    metrics = calculate_portfolio_metrics(positions, repos, jibar_rate)
    return metrics.get('net_yield', 0.0)
