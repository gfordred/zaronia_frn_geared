"""
Data Schemas with Pydantic Validation
======================================

Type-safe data models for positions, repos, and market data.
"""

from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional, Literal
from decimal import Decimal


class Position(BaseModel):
    """FRN Position schema with validation"""
    
    id: str = Field(..., description="Unique position identifier")
    name: str = Field(..., description="Position name/description")
    counterparty: str = Field(..., description="Issuer/counterparty name")
    notional: float = Field(..., gt=0, description="Position notional in ZAR")
    start_date: date = Field(..., description="Position start date")
    maturity: date = Field(..., description="Maturity date")
    issue_spread: float = Field(..., description="Issue spread in bps")
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
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class RepoTrade(BaseModel):
    """Repo trade schema with validation"""
    
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
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class MarketData(BaseModel):
    """Market data point schema"""
    
    date: date = Field(..., description="Market data date")
    jibar_3m: Optional[float] = Field(None, description="JIBAR 3M rate in %")
    zaronia: Optional[float] = Field(None, description="ZARONIA rate in %")
    fra_3x6: Optional[float] = Field(None, description="FRA 3x6 rate in %")
    fra_6x9: Optional[float] = Field(None, description="FRA 6x9 rate in %")
    fra_9x12: Optional[float] = Field(None, description="FRA 9x12 rate in %")
    fra_18x21: Optional[float] = Field(None, description="FRA 18x21 rate in %")
    sasw1: Optional[float] = Field(None, description="SASW 1Y rate in %")
    sasw2: Optional[float] = Field(None, description="SASW 2Y rate in %")
    sasw3: Optional[float] = Field(None, description="SASW 3Y rate in %")
    sasw5: Optional[float] = Field(None, description="SASW 5Y rate in %")
    sasw7: Optional[float] = Field(None, description="SASW 7Y rate in %")
    sasw10: Optional[float] = Field(None, description="SASW 10Y rate in %")
    sasw15: Optional[float] = Field(None, description="SASW 15Y rate in %")
    sasw20: Optional[float] = Field(None, description="SASW 20Y rate in %")
    
    @validator('jibar_3m', 'zaronia', 'fra_3x6', 'fra_6x9', 'fra_9x12', 'fra_18x21',
               'sasw1', 'sasw2', 'sasw3', 'sasw5', 'sasw7', 'sasw10', 'sasw15', 'sasw20')
    def rate_reasonable(cls, v):
        """Ensure rates are in reasonable range (0-30%)"""
        if v is not None and (v < 0 or v > 30):
            raise ValueError(f'Rate {v}% is outside reasonable range (0-30%)')
        return v
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class Portfolio(BaseModel):
    """Portfolio collection schema"""
    
    positions: list[Position] = Field(default_factory=list, description="List of positions")
    
    def total_notional(self) -> float:
        """Calculate total portfolio notional"""
        return sum(p.notional for p in self.positions)
    
    def active_positions(self, as_of_date: date) -> list[Position]:
        """Get positions active on a specific date"""
        return [p for p in self.positions 
                if p.start_date <= as_of_date <= p.maturity]
    
    def positions_by_counterparty(self, counterparty: str) -> list[Position]:
        """Get all positions for a specific counterparty"""
        return [p for p in self.positions if p.counterparty == counterparty]


class RepoBook(BaseModel):
    """Repo trades collection schema"""
    
    repos: list[RepoTrade] = Field(default_factory=list, description="List of repo trades")
    
    def total_outstanding(self, direction: str = "borrow_cash") -> float:
        """Calculate total repo outstanding for a direction"""
        return sum(r.cash_amount for r in self.repos if r.direction == direction)
    
    def active_repos(self, as_of_date: date) -> list[RepoTrade]:
        """Get repos active on a specific date"""
        return [r for r in self.repos 
                if r.spot_date <= as_of_date <= r.end_date]
