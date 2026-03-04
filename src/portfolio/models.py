"""
Portfolio Models - CANONICAL
=============================

Type-safe models for FRN positions and repo trades with Pydantic validation.
"""

from pydantic import BaseModel, Field, validator, computed_field
from datetime import date, datetime
from typing import Optional, Literal, List
from decimal import Decimal


class FRNPosition(BaseModel):
    """
    Floating Rate Note Position with validation.
    
    Represents a single FRN holding in the portfolio.
    """
    
    id: str = Field(..., description="Unique position identifier")
    name: str = Field(..., description="Position name/description")
    counterparty: str = Field(..., description="Issuer name")
    notional: float = Field(..., gt=0, description="Position notional in ZAR")
    start_date: date = Field(..., description="Position start date")
    maturity: date = Field(..., description="Maturity date")
    issue_spread: float = Field(..., description="Issue spread in bps over JIBAR")
    dm: float = Field(..., description="Discount margin in bps")
    index: Literal["JIBAR 3M", "ZARONIA"] = Field(default="JIBAR 3M", description="Reference index")
    book: Optional[str] = Field(None, description="Trading book")
    strategy: Optional[str] = Field(None, description="Strategy tag")
    
    @validator('maturity')
    def maturity_after_start(cls, v, values):
        """Ensure maturity is after start date"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('Maturity must be after start date')
        return v
    
    @validator('notional')
    def notional_positive(cls, v):
        """Ensure notional is positive"""
        if v <= 0:
            raise ValueError('Notional must be positive')
        return v
    
    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if position is currently active"""
        today = date.today()
        return self.start_date <= today <= self.maturity
    
    @computed_field
    @property
    def days_to_maturity(self) -> int:
        """Calculate days to maturity"""
        return (self.maturity - date.today()).days
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class RepoTrade(BaseModel):
    """
    Repo Trade with validation and proper economics.
    
    Represents a repurchase agreement for funding or lending.
    """
    
    id: str = Field(..., description="Unique repo identifier")
    trade_date: date = Field(..., description="Trade date")
    spot_date: date = Field(..., description="Spot/near leg date")
    end_date: date = Field(..., description="Far leg/maturity date")
    cash_amount: float = Field(..., gt=0, description="Cash amount in ZAR")
    repo_spread_bps: float = Field(..., description="Repo spread over JIBAR in bps")
    direction: Literal["borrow_cash", "lend_cash"] = Field(..., description="Repo direction")
    collateral_id: Optional[str] = Field(None, description="Collateral position ID")
    coupon_to_lender: bool = Field(default=False, description="Coupon passes to lender")
    
    @validator('end_date')
    def end_after_spot(cls, v, values):
        """Ensure end date is after spot date"""
        if 'spot_date' in values and v <= values['spot_date']:
            raise ValueError('End date must be after spot date')
        return v
    
    @validator('spot_date')
    def spot_after_trade(cls, v, values):
        """Ensure spot date is on or after trade date"""
        if 'trade_date' in values and v < values['trade_date']:
            raise ValueError('Spot date must be on or after trade date')
        return v
    
    @validator('cash_amount')
    def cash_positive(cls, v):
        """Ensure cash amount is positive"""
        if v <= 0:
            raise ValueError('Cash amount must be positive')
        return v
    
    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if repo is currently active"""
        today = date.today()
        return self.spot_date <= today <= self.end_date
    
    @computed_field
    @property
    def days_to_maturity(self) -> int:
        """Calculate days to maturity"""
        return (self.end_date - date.today()).days
    
    @computed_field
    @property
    def term_days(self) -> int:
        """Calculate total term in days"""
        return (self.end_date - self.spot_date).days
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class Portfolio(BaseModel):
    """
    Portfolio collection with aggregation methods.
    """
    
    positions: List[FRNPosition] = Field(default_factory=list, description="List of FRN positions")
    
    @computed_field
    @property
    def total_notional(self) -> float:
        """Calculate total portfolio notional"""
        return sum(p.notional for p in self.positions)
    
    @computed_field
    @property
    def active_positions(self) -> List[FRNPosition]:
        """Get currently active positions"""
        return [p for p in self.positions if p.is_active]
    
    @computed_field
    @property
    def active_notional(self) -> float:
        """Calculate notional of active positions"""
        return sum(p.notional for p in self.active_positions)
    
    def positions_by_counterparty(self, counterparty: str) -> List[FRNPosition]:
        """Get all positions for a specific counterparty"""
        return [p for p in self.positions if p.counterparty == counterparty]
    
    def counterparty_exposure(self, counterparty: str) -> float:
        """Calculate total exposure to a counterparty"""
        return sum(p.notional for p in self.positions_by_counterparty(counterparty))
    
    def concentration_check(self, max_pct: float = 50.0) -> dict:
        """
        Check concentration limits.
        
        Args:
            max_pct: Maximum concentration percentage
        
        Returns:
            Dictionary with concentration warnings
        """
        warnings = []
        total = self.total_notional
        
        if total == 0:
            return {'warnings': warnings, 'compliant': True}
        
        # Check each counterparty
        counterparties = set(p.counterparty for p in self.positions)
        for cpty in counterparties:
            exposure = self.counterparty_exposure(cpty)
            pct = (exposure / total) * 100
            
            if cpty == "Republic of South Africa" and pct > 50:
                warnings.append(f"Sovereign exposure {pct:.1f}% exceeds 50% limit")
            elif pct > max_pct:
                warnings.append(f"{cpty} exposure {pct:.1f}% exceeds {max_pct}% limit")
        
        return {
            'warnings': warnings,
            'compliant': len(warnings) == 0
        }


class RepoBook(BaseModel):
    """
    Repo trades collection with aggregation methods.
    """
    
    repos: List[RepoTrade] = Field(default_factory=list, description="List of repo trades")
    
    @computed_field
    @property
    def total_borrowed(self) -> float:
        """Calculate total cash borrowed"""
        return sum(r.cash_amount for r in self.repos if r.direction == "borrow_cash")
    
    @computed_field
    @property
    def total_lent(self) -> float:
        """Calculate total cash lent"""
        return sum(r.cash_amount for r in self.repos if r.direction == "lend_cash")
    
    @computed_field
    @property
    def net_repo_position(self) -> float:
        """Calculate net repo position (borrowed - lent)"""
        return self.total_borrowed - self.total_lent
    
    @computed_field
    @property
    def active_repos(self) -> List[RepoTrade]:
        """Get currently active repos"""
        return [r for r in self.repos if r.is_active]
    
    @computed_field
    @property
    def active_borrowed(self) -> float:
        """Calculate active borrowed amount"""
        return sum(r.cash_amount for r in self.active_repos if r.direction == "borrow_cash")
    
    @computed_field
    @property
    def active_lent(self) -> float:
        """Calculate active lent amount"""
        return sum(r.cash_amount for r in self.active_repos if r.direction == "lend_cash")


class PortfolioSnapshot(BaseModel):
    """
    Point-in-time snapshot of portfolio and repo book.
    """
    
    snapshot_date: date = Field(..., description="Snapshot date")
    portfolio: Portfolio = Field(..., description="Portfolio at snapshot date")
    repo_book: RepoBook = Field(..., description="Repo book at snapshot date")
    
    @computed_field
    @property
    def gearing(self) -> float:
        """
        Calculate gearing ratio.
        
        Gearing = Repo Outstanding / Portfolio Notional
        """
        if self.portfolio.active_notional == 0:
            return 0.0
        return self.repo_book.active_borrowed / self.portfolio.active_notional
    
    @computed_field
    @property
    def net_asset_value(self) -> float:
        """
        Calculate net asset value (simplified).
        
        NAV = Portfolio Value - Repo Liability
        (This is a simplified calculation - actual NAV requires pricing)
        """
        return self.portfolio.active_notional - self.repo_book.net_repo_position
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }
