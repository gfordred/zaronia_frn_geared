# Production Refactoring Plan - ZAR FRN Trading Platform

## Executive Summary

This document outlines the comprehensive refactoring plan to transform the current monolithic `app.py` into a production-ready, professional ZAR FRN trading platform.

**Current State:** 3,300+ line monolithic file mixing UI, pricing, data, and analytics  
**Target State:** Modular, testable, maintainable codebase with professional trader UX

---

## Critical Issues Identified

### 1. **Monolithic Architecture (HIGH RISK)**
- **Problem:** `app.py` does everything - 3,300+ lines mixing concerns
- **Risk:** Hard to trust, hard to maintain, easy to introduce silent bugs
- **Impact:** Any UI change can break valuation logic

### 2. **Duplicate Pricing Functions (CRITICAL)**
- **Problem:** "SECTION 3: FRN PRICING ENGINE" appears multiple times
- **Risk:** "I fixed it but it still uses the old function" bugs
- **Impact:** Inconsistent valuations across tabs

### 3. **Fragile Optional Imports (MEDIUM RISK)**
- **Problem:** `try/except` import pattern with print() indicators
- **Risk:** Features silently disappear in different environments
- **Impact:** Non-deterministic builds for trading tool

### 4. **Inconsistent Chart Layer (UX ISSUE)**
- **Problem:** Mix of plotly.express and graph_objects, inconsistent styling
- **Risk:** Confusing user experience, hard to maintain
- **Impact:** Unprofessional appearance

### 5. **Too Many Tabs, No Guided Journey (UX ISSUE)**
- **Problem:** 7+ main tabs with nested sub-tabs, overwhelming
- **Risk:** Traders can't find what they need quickly
- **Impact:** Slow trading workflow

### 6. **Missing Cashflow Truth Table (FUNCTIONAL GAP)**
- **Problem:** No canonical cashflow engine with proper tagging
- **Risk:** Reconciliation pain when scaling
- **Impact:** Can't trust settlement account

---

## Proposed Architecture

### New Folder Structure

```
zaronia_frn_geared/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── calendars.py          # SA calendar, business day logic
│   │   ├── daycount.py            # ACT/365 day count
│   │   ├── conventions.py         # Modified Following, etc.
│   │   └── config.py              # Constants, settings
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loaders.py             # Load JIBAR_FRA_SWAPS.xlsx, JSON files
│   │   ├── schemas.py             # Pydantic models for validation
│   │   └── validators.py          # Data quality checks
│   │
│   ├── curves/
│   │   ├── __init__.py
│   │   ├── jibar_curve.py         # JIBAR curve builder (depo+FRA+swap)
│   │   ├── zaronia_curve.py       # ZARONIA OIS curve
│   │   ├── spreaded_discount.py   # ZeroSpreadedTermStructure wrapper
│   │   └── curve_diagnostics.py   # Repricing, error analysis
│   │
│   ├── pricing/
│   │   ├── __init__.py
│   │   ├── frn.py                 # CANONICAL FRN pricing engine
│   │   ├── cashflows.py           # Cashflow generation, tagging
│   │   ├── risk.py                # DV01, CS01, KRDV01
│   │   └── accrual.py             # Accrued interest calculations
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── models.py              # Position, RepoTrade, Counterparty classes
│   │   ├── portfolio_engine.py    # Aggregation, netting
│   │   ├── settlement_account.py  # Canonical cashflow truth table
│   │   └── repo_economics.py      # Repo pricing, coupon entitlement
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── yield_attribution.py   # Gearing benefit analysis
│   │   ├── historical.py          # Daily historical analytics
│   │   ├── counterparty_risk.py   # Exposure limits, HHI
│   │   └── funding_risk.py        # Maturity ladder, liquidity
│   │
│   └── ui/
│       ├── __init__.py
│       ├── theme.py               # Chart factory, consistent styling
│       ├── components.py          # Reusable UI components
│       ├── trade_ticket.py        # Trade entry UI
│       ├── portfolio_view.py      # Portfolio dashboard
│       ├── repo_view.py           # Repo dashboard
│       └── diagnostics.py         # System health, logging
│
├── tests/
│   ├── __init__.py
│   ├── test_pricing.py            # FRN pricing unit tests
│   ├── test_curves.py             # Curve building tests
│   ├── test_risk.py               # DV01/CS01 tests
│   ├── test_cashflows.py          # Cashflow generation tests
│   └── test_repo.py               # Repo economics tests
│
├── app.py                         # THIN UI SHELL (< 500 lines)
├── requirements.txt               # Clean dependency list
├── README.md                      # How to run, architecture
└── .streamlit/
    └── config.toml                # Streamlit config
```

---

## Refactoring Steps

### Phase 1: Foundation (Week 1)

**Step 1.1: Create Core Modules**
- [ ] `src/core/calendars.py` - Extract `get_sa_calendar()`
- [ ] `src/core/daycount.py` - Extract day count logic
- [ ] `src/core/conventions.py` - Extract business day conventions
- [ ] `src/core/config.py` - Constants (SEED_CAPITAL, TARGET_GEARING, etc.)

**Step 1.2: Data Layer**
- [ ] `src/data/loaders.py` - Extract `load_jibar_fra_swaps()`, `load_portfolio()`, `load_repo_trades()`
- [ ] `src/data/schemas.py` - Pydantic models for Position, RepoTrade, MarketData
- [ ] `src/data/validators.py` - Data quality checks, missing data warnings

**Step 1.3: Scan for Duplicates**
- [ ] Identify all instances of FRN pricing functions
- [ ] Document which tabs use which version
- [ ] Create migration plan to single canonical version

### Phase 2: Pricing Engine (Week 2)

**Step 2.1: Consolidate FRN Pricing**
- [ ] Create `src/pricing/frn.py` with SINGLE canonical implementation
- [ ] Functions: `price_frn()`, `calculate_clean_price()`, `calculate_accrued()`
- [ ] Ensure all tabs import from this module ONLY
- [ ] Delete all duplicate implementations

**Step 2.2: Curve Building**
- [ ] Extract `src/curves/jibar_curve.py` - `build_jibar_curve()`
- [ ] Extract `src/curves/zaronia_curve.py` - `build_zaronia_curve_daily()`
- [ ] Extract `src/curves/spreaded_discount.py` - Spread handling
- [ ] Add curve diagnostics and repricing validation

**Step 2.3: Risk Calculations**
- [ ] Create `src/pricing/risk.py` - `calculate_dv01()`, `calculate_cs01()`, `calculate_krdv01()`
- [ ] Ensure consistent bump sizes (1bp for DV01, 1bp for CS01)
- [ ] Add sign and magnitude validation

**Step 2.4: Cashflow Engine**
- [ ] Create `src/pricing/cashflows.py` - Canonical cashflow generation
- [ ] Tag each cashflow: `asset_coupon`, `asset_principal`, `repo_interest`, `repo_principal`
- [ ] Implement proper ACT/365, Modified Following
- [ ] Add schedule generation with guards against negative time

### Phase 3: Portfolio & Repo (Week 3)

**Step 3.1: Portfolio Models**
- [ ] Create `src/portfolio/models.py` - Position, RepoTrade, Counterparty classes
- [ ] Add validation, serialization, deserialization
- [ ] Implement `__repr__` for debugging

**Step 3.2: Portfolio Engine**
- [ ] Create `src/portfolio/portfolio_engine.py`
- [ ] Functions: `aggregate_positions()`, `calculate_portfolio_metrics()`, `net_cashflows()`
- [ ] Implement proper netting rules

**Step 3.3: Settlement Account**
- [ ] Create `src/portfolio/settlement_account.py` - CANONICAL cashflow truth table
- [ ] Separate: Operating, Financing, Investment cashflows
- [ ] Daily ledger with proper accounting
- [ ] NAV calculation: Seed Capital + Cumulative Operating Cashflows

**Step 3.4: Repo Economics**
- [ ] Create `src/portfolio/repo_economics.py`
- [ ] Implement repo pricing with JIBAR projection
- [ ] Coupon entitlement logic (pass-through vs buyer keeps)
- [ ] Manufactured payment calculations
- [ ] Haircut and overcollateralization metrics

### Phase 4: UI Overhaul (Week 4)

**Step 4.1: Chart Factory**
- [ ] Create `src/ui/theme.py` - Single chart factory
- [ ] Consistent: fonts, colors, hover templates, axis labels
- [ ] Units: rates in %, spreads in bps
- [ ] Unified hover mode, sensible legends

**Step 4.2: Reusable Components**
- [ ] Create `src/ui/components.py`
- [ ] Metric cards, tables, editors, export buttons
- [ ] Validation helpers, date pickers

**Step 4.3: New Tab Structure**
- [ ] **Tab 1: Trade Ticket** (`src/ui/trade_ticket.py`)
  - Select index (JIBAR/ZARONIA)
  - Issue spread, market DM, dates, notional
  - Show clean/all-in/accrued
  - "Add to Portfolio" button
  - "Create Repo" button
  
- [ ] **Tab 2: Portfolio** (`src/ui/portfolio_view.py`)
  - Sticky portfolio strip (MV, DV01, CS01, carry, funding)
  - Position table with inline editing
  - Risk dashboard (DV01 by bucket, CS01 by issuer)
  - Cashflow ladder
  - Carry & roll-down chart
  
- [ ] **Tab 3: Repo / Funding** (`src/ui/repo_view.py`)
  - Repo table with inline editing
  - Outstanding repo over time
  - Weighted avg funding rate
  - Net carry vs haircut sensitivity
  - Asset/repo visualization (already created)
  
- [ ] **Tab 4: Curves & Diagnostics** (`src/ui/diagnostics.py`)
  - Curve build status, data dates
  - Module availability
  - Unit test status
  - Repricing errors
  - Missing data warnings

**Step 4.4: Sticky Portfolio Strip**
- [ ] Always visible at top of app
- [ ] Show: MV, DV01, CS01, KRDV01, Net Carry, Funding Gap
- [ ] Update in real-time as positions change

### Phase 5: Testing & Validation (Week 5)

**Step 5.1: Unit Tests**
- [ ] `tests/test_pricing.py` - FRN pricing, accrual
- [ ] `tests/test_curves.py` - Curve building, repricing
- [ ] `tests/test_risk.py` - DV01/CS01 sign and magnitude
- [ ] `tests/test_cashflows.py` - Schedule generation, cashflow amounts
- [ ] `tests/test_repo.py` - Repo pricing, coupon entitlement

**Step 5.2: Integration Tests**
- [ ] End-to-end: Load data → Build curves → Price FRN → Calculate risk
- [ ] Portfolio aggregation with multiple positions
- [ ] Settlement account reconciliation

**Step 5.3: Validation**
- [ ] Compare old vs new pricing (should match exactly)
- [ ] Validate all tabs still work
- [ ] Check no silent fallbacks

### Phase 6: Deployment (Week 6)

**Step 6.1: Clean Up**
- [ ] Remove dead code
- [ ] Remove unused imports
- [ ] Update `requirements.txt`
- [ ] Add logging (replace all `print()`)

**Step 6.2: Documentation**
- [ ] Update README with architecture
- [ ] Add "How to Run" section
- [ ] Document API for each module
- [ ] Create user guide

**Step 6.3: Deployment**
- [ ] Test locally
- [ ] Test on Streamlit Cloud
- [ ] Monitor for errors
- [ ] Gradual rollout

---

## Key Principles

### 1. **Correctness First**
- Do not change financial conventions (ACT/365, Modified Following, quarterly reset)
- Keep QuantLib as pricing backbone
- Every cashflow must be traceable

### 2. **No Silent Fallbacks**
- Any fallback must be shown in UI with warning
- Captured in Diagnostics tab
- Fail fast if critical data missing

### 3. **Single Source of Truth**
- ONE canonical pricing engine
- ONE canonical cashflow engine
- ONE canonical curve builder

### 4. **Testability**
- All core functions must be unit testable
- No UI dependencies in business logic
- Pure functions where possible

### 5. **Professional UX**
- Trader-first design
- Fast workflow (< 3 clicks to price)
- Clear visual hierarchy
- Consistent styling

---

## Migration Strategy

### Parallel Run Approach

1. **Build new modules alongside old code**
   - Don't break existing functionality
   - New modules in `src/` folder
   - Old code stays in `app.py` initially

2. **Gradual migration**
   - Migrate one tab at a time
   - Validate each migration
   - Compare old vs new results

3. **Feature flags**
   - Use `USE_NEW_PRICING = True/False` toggle
   - Allow switching between old and new
   - Remove old code only when confident

4. **Validation checkpoints**
   - After each phase, run full regression
   - Compare pricing, risk, cashflows
   - Document any differences

---

## Success Metrics

### Technical Metrics
- [ ] `app.py` reduced to < 500 lines
- [ ] Zero duplicate pricing functions
- [ ] 100% unit test coverage for pricing/risk
- [ ] All imports deterministic (no try/except)
- [ ] < 2 second load time

### UX Metrics
- [ ] 4 main tabs (down from 7+)
- [ ] < 3 clicks to price FRN
- [ ] Consistent chart styling across all tabs
- [ ] Sticky portfolio strip always visible
- [ ] Export buttons on all key views

### Business Metrics
- [ ] Traders can price FRN in < 30 seconds
- [ ] Portfolio risk visible at a glance
- [ ] Repo funding status clear
- [ ] No reconciliation errors

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation:**
- Parallel run with feature flags
- Extensive unit tests
- Validation against old code
- Gradual rollout

### Risk 2: Performance Degradation
**Mitigation:**
- Profile before and after
- Cache curve builds
- Lazy load heavy analytics
- Monitor load times

### Risk 3: User Confusion
**Mitigation:**
- User guide
- Tooltips and help text
- Gradual UI changes
- Training session

### Risk 4: Data Migration Issues
**Mitigation:**
- Pydantic validation
- Data quality checks
- Backward compatibility
- Migration scripts

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | Week 1 | Core modules, data layer, duplicate scan |
| Phase 2: Pricing Engine | Week 2 | Canonical pricing, curves, risk, cashflows |
| Phase 3: Portfolio & Repo | Week 3 | Models, engine, settlement, repo economics |
| Phase 4: UI Overhaul | Week 4 | Chart factory, new tabs, sticky strip |
| Phase 5: Testing | Week 5 | Unit tests, integration tests, validation |
| Phase 6: Deployment | Week 6 | Clean up, docs, deploy |

**Total: 6 weeks to production-ready platform**

---

## Next Steps

1. **Review and approve this plan**
2. **Set up development branch**
3. **Begin Phase 1: Foundation**
4. **Weekly progress reviews**
5. **Adjust plan as needed**

---

## Appendix: Code Removal Candidates

Files/sections to potentially remove:
- [ ] Duplicate FRN pricing functions (keep only canonical)
- [ ] Unused imports (pandas, numpy duplicates)
- [ ] Dead code in optional modules
- [ ] Commented-out code blocks
- [ ] Temporary debugging print statements
- [ ] Redundant chart generation code

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-04  
**Status:** DRAFT - Awaiting Approval
