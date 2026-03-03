# ZAR FRN Trading Platform - Expert Critique & Enhancement Roadmap

**Author:** Senior FRN Trader & Repo Specialist (South African Markets)  
**Date:** March 3, 2026  
**Platform Version:** 2.0 (Enhanced)

---

## Executive Summary

As a senior FRN trader specializing in South African rates markets with extensive repo desk experience, I've conducted a comprehensive review of the ZAR FRN Trading Platform. The platform demonstrates **strong fundamentals** in curve construction, FRN pricing mechanics, and SA market conventions. However, there are critical enhancements needed to transform this from a pricing tool into a **production-grade trading and risk management system**.

**Overall Grade: B+ (Strong Foundation, Production Enhancements Needed)**

---

## ✅ What's Working Well

### 1. **Market Conventions - Excellent** (A+)
- ✅ ACT/365 daycount correctly applied throughout
- ✅ Modified Following business day convention
- ✅ SA calendar with observed holidays (2023-2027)
- ✅ T+3 settlement logic
- ✅ Quarterly coupon frequency for JIBAR3M FRNs
- ✅ Proper handling of ZARONIA lookback periods

### 2. **Curve Construction - Very Good** (A)
- ✅ Proper separation of projection vs discount curves
- ✅ ZeroSpreadedTermStructure for DM discounting (critical!)
- ✅ Depo + FRA + Swap bootstrapping
- ✅ Curve diagnostics with par repricing errors
- ✅ Key-rate DV01 implementation

### 3. **FRN Pricing Engine - Strong** (A-)
- ✅ Correct forward rate estimation from FRAs
- ✅ Historical fixing lookups with fallbacks
- ✅ Accrued interest calculation
- ✅ Clean vs dirty price separation
- ✅ Cashflow decomposition (rate type identification)

### 4. **Repo Module - Good Foundation** (B+)
- ✅ Ex-coupon date logic (5d unlisted, 10d RN bonds)
- ✅ Detailed cashflow breakdown
- ✅ Repo rate = JIBAR forward + spread
- ✅ Historical repo handling
- ✅ Collateral linking to portfolio positions

---

## 🔴 Critical Issues & Fixes Required

### 1. **MISSING: Margin/Haircut Treatment in Repo Pricing** (CRITICAL)

**Issue:** While haircut field was removed from UI, the economic impact of haircuts on repo economics is not modeled.

**Fix Required:**
```python
# In repo valuation:
# 1. Collateral value = FRN Clean Price × (1 - Haircut%)
# 2. Max repo cash = Collateral value
# 3. Margin call triggers if FRN price drops

def calculate_margin_requirement(frn_clean_price, notional, haircut_pct, repo_cash):
    """
    Calculate margin call requirement.
    Margin = (Repo Cash / (FRN Value × (1 - Haircut))) - 1
    If Margin > 0, margin call triggered.
    """
    collateral_value = frn_clean_price * notional * (1 - haircut_pct/100)
    margin_ratio = repo_cash / collateral_value
    
    if margin_ratio > 1.0:
        margin_call = repo_cash - collateral_value
        return margin_call, "MARGIN CALL"
    else:
        excess_collateral = collateral_value - repo_cash
        return -excess_collateral, "OK"
```

**Impact:** Without this, traders cannot assess margin risk on geared positions.

---

### 2. **MISSING: Mark-to-Market P&L on Repo Positions** (HIGH PRIORITY)

**Issue:** Repo trades show initial cashflows but not MTM P&L as rates move.

**Fix Required:**
```python
def calculate_repo_mtm(repo_trade, current_repo_rate, frn_current_price):
    """
    MTM P&L on repo = Change in repo NPV + Change in collateral value
    
    For cash borrower (long FRN):
    - Gain if FRN price rises (collateral appreciation)
    - Loss if repo rates rise (higher funding cost on rollover)
    """
    # Original repo rate locked in
    original_rate = repo_trade['repo_rate']
    
    # MTM on funding leg (present value of rate differential)
    rate_diff = current_repo_rate - original_rate
    remaining_term = (repo_trade['end_date'] - date.today()).days / 365.25
    funding_mtm = -repo_trade['cash_amount'] * rate_diff * remaining_term
    
    # MTM on collateral (if linked FRN)
    if frn_current_price:
        original_price = repo_trade.get('initial_frn_price', 100.0)
        collateral_mtm = (frn_current_price - original_price) * notional / 100
    else:
        collateral_mtm = 0.0
    
    total_mtm = funding_mtm + collateral_mtm
    return total_mtm, funding_mtm, collateral_mtm
```

**Impact:** Traders cannot see daily P&L attribution between funding and collateral.

---

### 3. **MISSING: Carry & Rolldown Analysis** (HIGH PRIORITY)

**Issue:** No visibility into carry (coupon accrual) vs rolldown (price appreciation as bond approaches maturity).

**Fix Required:**
```python
def calculate_carry_rolldown(frn_position, proj_curve, disc_curve, horizon_days=30):
    """
    Carry = Coupon accrual over horizon
    Rolldown = Price change due to passage of time (curve unchanged)
    Total Return = Carry + Rolldown + Spread change
    """
    # Today's price
    price_t0 = price_frn(...)
    
    # Horizon date (e.g., 30 days forward)
    horizon_date = settlement + timedelta(days=horizon_days)
    
    # Carry: accrued interest over horizon
    carry = calculate_accrued(settlement, horizon_date, coupon_rate, notional)
    
    # Rolldown: reprice FRN at horizon with same curve (time decay)
    # Shift all dates forward by horizon_days
    price_t1 = price_frn(settlement=horizon_date, same_curve=True)
    rolldown = (price_t1 - price_t0) * notional / 100
    
    # Total return
    total_return = carry + rolldown
    return carry, rolldown, total_return
```

**Add to Portfolio Manager:**
- 30-day carry/rolldown projection
- Annualized carry yield
- Breakeven spread widening

---

### 4. **MISSING: Repo Strategy Optimizer** (MEDIUM PRIORITY)

**Issue:** No guidance on optimal gearing levels given funding costs and portfolio yields.

**Fix Required:**
```python
def calculate_optimal_gearing(portfolio_yield, repo_spread, target_net_yield):
    """
    Optimal Gearing maximizes Net Yield subject to risk constraints.
    
    Net Yield = Portfolio Yield + (Portfolio Yield - Funding Cost) × (Gearing - 1)
    
    Constraints:
    - Max gearing (regulatory/risk limits): typically 3-5x
    - Min net yield target
    - Max DV01 concentration
    """
    funding_cost = jibar_rate + repo_spread
    spread_pickup = portfolio_yield - funding_cost
    
    if spread_pickup <= 0:
        return 1.0, "NEGATIVE CARRY - DO NOT GEAR"
    
    # Optimal gearing (unconstrained)
    optimal_gearing = 1 + (target_net_yield - portfolio_yield) / spread_pickup
    
    # Apply constraints
    max_gearing = 3.0  # Example limit
    constrained_gearing = min(optimal_gearing, max_gearing)
    
    return constrained_gearing, f"Spread pickup: {spread_pickup:.2f}%"
```

---

### 5. **MISSING: Basis Trading Opportunities** (MEDIUM PRIORITY)

**Issue:** Basis Analysis tab shows JIBAR-ZARONIA basis but doesn't flag trading opportunities.

**Enhancement:**
```python
def identify_basis_opportunities(jibar_zaronia_basis, historical_avg, std_dev):
    """
    Flag when basis is rich/cheap vs historical average.
    
    Trading signals:
    - Basis > Avg + 2σ → RICH → Receive JIBAR, Pay ZARONIA
    - Basis < Avg - 2σ → CHEAP → Pay JIBAR, Receive ZARONIA
    """
    z_score = (jibar_zaronia_basis - historical_avg) / std_dev
    
    if z_score > 2.0:
        return "RICH", "Sell JIBAR FRN, Buy ZARONIA FRN", z_score
    elif z_score < -2.0:
        return "CHEAP", "Buy JIBAR FRN, Sell ZARONIA FRN", z_score
    else:
        return "FAIR", "No trade", z_score
```

---

## 📊 Enhanced Visualizations Needed

### 1. **Portfolio Attribution Chart**
```
Stacked bar chart showing P&L attribution:
- Carry (coupon accrual)
- Rolldown (time decay)
- Spread change (DM widening/tightening)
- Funding cost (repo interest)
- Net P&L
```

### 2. **Gearing Sensitivity Analysis**
```
Line chart: Net Yield vs Gearing Ratio
- Show breakeven gearing (where net yield = ungeared yield)
- Highlight current gearing level
- Show impact of +/- 10bps repo spread change
```

### 3. **Term Structure Evolution**
```
Animated line chart showing how FRN spreads have evolved:
- Historical spread levels (1M, 3M, 6M, 1Y ago)
- Current spreads
- Percentile ranking vs 1Y history
```

### 4. **Repo Funding Ladder**
```
Gantt chart showing repo maturity profile:
- X-axis: Time
- Y-axis: Cumulative repo cash
- Color-coded by counterparty
- Highlight rollover concentration risk
```

### 5. **Key-Rate DV01 Heatmap**
```
Heatmap showing portfolio sensitivity by tenor:
- Rows: Positions
- Columns: 3M, 6M, 1Y, 2Y, 3Y, 5Y, 10Y
- Color intensity: DV01 magnitude
- Identify concentration risk
```

---

## 🎯 Production Enhancements

### 1. **Add Trade Blotter**
```python
# Real-time trade capture with:
- Trade ID, timestamp
- Instrument, notional, price, spread
- Counterparty, trader, book
- Settlement date, trade date
- Status: Pending, Confirmed, Settled, Failed
```

### 2. **Add Position Reconciliation**
```python
# Daily position recon:
- Expected positions (from trade blotter)
- Actual positions (from portfolio.json)
- Breaks (differences)
- Aging of breaks
```

### 3. **Add Limit Monitoring**
```python
# Real-time limit checks:
- Counterparty exposure limits
- DV01 limits by book/desk
- Concentration limits (single issuer)
- Gearing limits
- VaR limits
```

### 4. **Add Historical P&L Tracking**
```python
# Store daily snapshots:
{
  "date": "2026-03-03",
  "portfolio_value": 2750000000,
  "total_dv01": 12500,
  "gearing_ratio": 2.04,
  "net_yield": 9.85,
  "daily_pnl": 1250000,
  "pnl_attribution": {
    "carry": 850000,
    "rolldown": 200000,
    "spread_change": 300000,
    "funding_cost": -100000
  }
}
```

### 5. **Add Stress Testing**
```python
def stress_test_portfolio(scenarios):
    """
    Stress scenarios:
    1. Parallel shift: +/- 50bps, 100bps, 200bps
    2. Steepening: 2s10s +50bps
    3. Flattening: 2s10s -50bps
    4. Credit spread widening: +25bps, +50bps, +100bps
    5. Repo spread widening: +10bps, +25bps, +50bps
    6. Combined: Rates +100bps AND Spreads +50bps
    """
    results = []
    for scenario in scenarios:
        shocked_pnl = reprice_portfolio(scenario)
        results.append({
            'scenario': scenario['name'],
            'pnl_impact': shocked_pnl - base_pnl,
            'pnl_pct': (shocked_pnl - base_pnl) / base_pnl * 100
        })
    return results
```

---

## 🏆 Best Practices from SA FRN Trading Desks

### 1. **Spread Quoting Convention**
- **Primary market:** Quote as "JIBAR + X bps" (issue spread)
- **Secondary market:** Quote as DM (discount margin) to reflect mark-to-market
- **Repo market:** Quote as "Repo rate = JIBAR + X bps" (repo spread)

### 2. **Settlement Conventions**
- **FRN trades:** T+3 settlement (already implemented ✅)
- **Repo trades:** Spot = T+0 or T+1 (overnight repo), T+3 (term repo)
- **Ex-dividend:** 10 business days for listed (RN bonds), 5 business days for unlisted ✅

### 3. **Repo Haircut Guidelines (SA Market)**
```
Government bonds (R-series):     0-2%
SOE bonds (Eskom, Transnet):     5-10%
Bank FRNs (Big 4):               2-5%
Bank FRNs (Tier 2):              5-10%
Corporate FRNs:                  10-20%
```

### 4. **Typical Repo Terms**
```
Overnight (O/N):    1 day
Tom-next (T/N):     1 day (settle tomorrow)
Spot-next (S/N):    1 day (settle spot)
1 week:             7 days
1 month:            30 days
3 months:           90 days
6 months:           180 days
```

### 5. **Gearing Strategy Rules of Thumb**
```
Conservative:  1.0x - 1.5x (minimal repo)
Moderate:      1.5x - 2.5x (typical for bank treasury)
Aggressive:    2.5x - 4.0x (hedge funds, prop desks)
Extreme:       4.0x+ (requires strong risk management)

Key constraint: Ensure positive carry after funding costs!
Net Yield = Gross Yield - (Funding Cost × (Gearing - 1)) > Target
```

---

## 📈 Recommended Workflow Enhancements

### Morning Routine (Pre-Market)
1. **Load overnight JIBAR fixings** → Update curves
2. **Review repo maturities** → Identify rollovers needed
3. **Check margin calls** → Calculate collateral requirements
4. **Run P&L attribution** → Understand yesterday's moves
5. **Review NCD pricing** → Update bank spread matrix

### Intraday (Trading Hours)
1. **Monitor live spreads** → Compare vs NCD pricing matrix
2. **Calculate gearing impact** → Before adding new positions
3. **Check limit utilization** → Counterparty, DV01, concentration
4. **Price new issues** → Use FRN Pricer with current curves
5. **Evaluate repo opportunities** → Optimize funding costs

### End of Day (Post-Market)
1. **Mark positions to market** → Update DM spreads
2. **Calculate daily P&L** → Attribute to carry/rolldown/spread
3. **Reconcile positions** → Trade blotter vs portfolio
4. **Update risk reports** → DV01, CS01, key-rate, VaR
5. **Plan next day rollovers** → Repo maturity ladder

---

## 🎓 Educational Insights for Junior Traders

### Why Gearing Works (When It Works)
```
Example:
Portfolio: R100M FRNs @ JIBAR + 100bps → Gross Yield = 9.0%
Repo: Borrow R100M @ JIBAR + 15bps → Funding Cost = 8.15%
Spread Pickup: 9.0% - 8.15% = 0.85% (85bps)

Ungeared: R100M × 9.0% = R9.0M annual income
Geared 2x: R200M × 9.0% - R100M × 8.15% = R18.0M - R8.15M = R9.85M
Net Yield: 9.85% on R100M equity (vs 9.0% ungeared)

Benefit: +85bps yield enhancement
Risk: If spreads widen 50bps, lose 2x on geared position
```

### When Gearing Fails
```
Scenario: Repo spread widens from 15bps to 50bps
New Funding Cost: 8.50%
Spread Pickup: 9.0% - 8.50% = 0.50% (down from 0.85%)

Geared 2x Net Yield: R200M × 9.0% - R100M × 8.50% = R9.5M
Net Yield: 9.5% (down from 9.85%)

If repo spread > 100bps → NEGATIVE CARRY → Forced unwind
```

### The Repo Trader's Golden Rule
**"Never gear into negative carry. Always stress test funding costs."**

---

## 🚀 Implementation Priority

### Phase 1 (Critical - Week 1)
- [ ] Add margin/haircut treatment to repo module
- [ ] Implement MTM P&L on repo positions
- [ ] Add carry & rolldown analysis
- [ ] Create portfolio attribution chart

### Phase 2 (High Priority - Week 2)
- [ ] Build repo strategy optimizer
- [ ] Add gearing sensitivity analysis
- [ ] Implement basis trading signals
- [ ] Create term structure evolution chart

### Phase 3 (Medium Priority - Week 3-4)
- [ ] Add trade blotter
- [ ] Implement position reconciliation
- [ ] Build limit monitoring system
- [ ] Add historical P&L tracking

### Phase 4 (Enhancement - Month 2)
- [ ] Stress testing framework
- [ ] VaR calculation
- [ ] Scenario analysis
- [ ] Automated reporting

---

## 📝 Final Assessment

### Strengths
✅ **Solid technical foundation** - Curve math is correct  
✅ **SA market conventions** - Properly implemented  
✅ **User-friendly interface** - Streamlit works well  
✅ **Modular design** - Easy to extend  

### Gaps
⚠️ **Production features** - Missing trade blotter, recon, limits  
⚠️ **Risk analytics** - Need stress testing, VaR, scenario analysis  
⚠️ **P&L attribution** - No carry/rolldown decomposition  
⚠️ **Repo economics** - Missing margin treatment, MTM P&L  

### Verdict
**This is an excellent pricing and analytics tool that needs production-grade risk management features to become a complete trading platform.**

With the enhancements outlined above, this platform can rival commercial systems like Bloomberg MARS, Murex, or Summit for FRN trading desks.

---

**Next Steps:** Implement Phase 1 critical features, then iterate based on trader feedback.

