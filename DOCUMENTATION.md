# ZARONIA FRN Geared Portfolio - Complete Documentation

**Version**: 2.0  
**Last Updated**: March 10, 2026  
**Status**: Production Ready  
**Investigation**: Gallium Fund Infrastructure

---

## Table of Contents
1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Key Features](#key-features)
4. [Data Files & Structure](#data-files--structure)
5. [Balance Sheet & Accounting](#balance-sheet--accounting)
6. [Usage Guide](#usage-guide)
7. [Investigation Infrastructure](#investigation-infrastructure)
8. [Technical Architecture](#technical-architecture)
9. [Deployment](#deployment)
10. [Forensic Audit Summary](#forensic-audit-summary)

---

## Overview

Professional fixed-income portfolio management and analytics platform for South African FRN (Floating Rate Note) portfolios with repo financing. Built as investigation infrastructure for the Gallium Fund case, emphasizing data lineage, reproducibility, and auditability.

### Purpose
- **Portfolio Management**: Track FRN holdings and repo financing
- **Risk Analytics**: Monitor DV01, CS01, and counterparty exposure
- **Performance Attribution**: Yield breakdown and NAV tracking
- **Investigation Support**: Evidence-grade data tracking and calculation versioning

### Technical Stack
- **Python 3.12+**
- **QuantLib**: Fixed income pricing and curve building
- **Streamlit**: Interactive web interface
- **Pandas**: Data manipulation and analysis
- **Plotly**: Professional charting and visualization

---

## Installation & Setup

### Quick Start
```bash
# Clone repository
git clone https://github.com/gfordred/zaronia_frn_geared.git
cd zaronia_frn_geared

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app.py
```

### Dependencies
```
pandas>=2.0.0
numpy>=1.24.0
QuantLib>=1.32
plotly>=5.18.0
streamlit>=1.30.0
matplotlib>=3.7.0
python-dateutil>=2.8.2
openpyxl>=3.1.0
```

### Starting Fresh
1. Empty `portfolio_positions.json`: `[]`
2. Empty `repo_trades.json`: `[]`
3. Settlement account shows R100M seed capital
4. Ready to book trades

---

## Key Features

### Portfolio Management
- **FRN Valuation**: Real-time pricing using QuantLib with JIBAR curves
- **Repo Financing**: Track repo borrowing and gearing ratios
- **Settlement Account**: Complete cash flow tracking
- **Balance Sheet**: Assets, liabilities, and NAV monitoring
- **Position Editor**: Add/edit FRN positions and repo trades

### Analytics & Reporting
- **Yield Attribution**: Breakdown by counterparty, asset, and term bucket
- **NAV Index**: Daily NAV tracking with operating cashflows
- **Risk Metrics**: DV01, CS01, and key rate sensitivities
- **Time Series**: Portfolio composition and gearing evolution
- **Historical Analytics**: Inception-to-date performance
- **Time Travel**: Historical portfolio snapshots

### Professional Features
- **Curve Building**: JIBAR swap curve construction from market data
- **Mark-to-Market**: Daily portfolio valuation
- **Cashflow Projection**: Future coupon and repo payments
- **Counterparty Risk**: Exposure monitoring and concentration limits
- **Basis Analysis**: JIBAR vs ZARONIA spread analysis
- **NCD Pricing**: Bank NCD spread matrix

---

## Data Files & Structure

### Portfolio Positions (`portfolio_positions.json`)
```json
[
  {
    "id": "POS_unique123",
    "name": "Bond Name",
    "counterparty": "ABSA",
    "book": "Standard Bank",
    "notional": 100000000,
    "start_date": "2024-01-01",
    "maturity": "2027-01-01",
    "issue_spread": 120,
    "dm": 120,
    "index": "JIBAR 3M",
    "lookback": 0,
    "strategy": "Core"
  }
]
```

**Fields:**
- `id`: Unique position identifier
- `name`: Bond name/description
- `counterparty`: Issuer/counterparty
- `book`: Trading book
- `notional`: Face value (ZAR)
- `start_date`: Issue date
- `maturity`: Maturity date
- `issue_spread`: Issue spread over index (bps)
- `dm`: Discount margin / market spread (bps)
- `index`: Reference rate ("JIBAR 3M" or "ZARONIA")
- `lookback`: Lookback days (for ZARONIA)
- `strategy`: Investment strategy

### Repo Trades (`repo_trades.json`)
```json
[
  {
    "id": "REPO_unique123",
    "trade_date": "2024-01-01",
    "spot_date": "2024-01-03",
    "end_date": "2024-04-03",
    "cash_amount": 90000000,
    "repo_spread_bps": 10,
    "direction": "borrow_cash",
    "collateral_id": "POS_unique123",
    "collateral_name": "Bond Name",
    "coupon_to_lender": true
  }
]
```

**Fields:**
- `id`: Unique repo identifier
- `trade_date`: Trade execution date
- `spot_date`: Settlement date (T+3)
- `end_date`: Repo maturity date
- `cash_amount`: Borrowed amount (ZAR)
- `repo_spread_bps`: Repo spread over JIBAR (bps)
- `direction`: "borrow_cash" or "lend_cash"
- `collateral_id`: Position ID used as collateral
- `collateral_name`: Bond name
- `coupon_to_lender`: Whether coupons go to lender

### Market Data (`JIBAR_FRA_SWAPS.xlsx`)
Historical JIBAR rates, FRAs, and swap rates for curve construction.

**Columns:**
- Date
- JIBAR3M (3-month JIBAR rate)
- SASW2, SASW5, SASW10 (Swap rates)
- FRA rates (forward rate agreements)

### ZARONIA Fixings (`ZARONIA_FIXINGS.csv`)
Daily ZARONIA (ZAR Overnight Index Average) fixings.

---

## Balance Sheet & Accounting

### Balance Sheet Equation
```
Assets = Liabilities + Equity
```

### Components

**ASSETS:**
- **Portfolio Market Value**: FRN bonds at current market value
- **Settlement Cash**: Uninvested/undeployed cash

**LIABILITIES:**
- **Repo Outstanding**: Borrowed funds via repo financing

**EQUITY (NAV):**
- **Net Asset Value**: Seed capital + cumulative P&L

### Calculation Logic

**Settlement Cash:**
```
Settlement Cash = Seed Capital + Repo Borrowed - Portfolio Purchases (at notional)
```

**Examples:**
1. **No repo, R100M portfolio:**
   - Cash = R100M + R0 - R100M = **R0**
   - Assets = R99.9M (MV) + R0 = **R99.9M**
   - Liabilities = **R0**
   - Equity = **R99.9M** (seed R100M - R0.1M MTM loss)

2. **R900M repo, R1000M portfolio:**
   - Cash = R100M + R900M - R1000M = **R0**
   - Assets = R999M (MV) + R0 = **R999M**
   - Liabilities = **R900M**
   - Equity = **R99M** (seed R100M - R1M MTM loss)

3. **R900M repo, R632M portfolio:**
   - Cash = R100M + R900M - R632M = **R368M**
   - Assets = R632M (MV) + R368M = **R1000M**
   - Liabilities = **R900M**
   - Equity = **R100M**

### Gearing
```
Gearing = Repo Borrowed / Seed Capital
Example: R900M repo / R100M seed = 9x gearing
```

### NAV Calculation
```
NAV = Seed Capital + Operating Cashflows + MTM P&L

Operating Cashflows:
  + FRN coupon income (received)
  - Repo interest expense (paid)
  
MTM P&L:
  = Portfolio Market Value - Portfolio Notional

Excluded (financing):
  - Repo principal (balance sheet movement, not P&L)
```

---

## Usage Guide

### Booking a Position

1. Navigate to **Portfolio Manager** tab
2. Click **"➕ Add New Position"** expander
3. Fill in position details:
   - Name (optional - auto-generated if blank)
   - Counterparty (issuer)
   - Notional (in millions)
   - Start Date & Maturity
   - Issue Spread (bps)
   - DM (discount margin, bps)
   - Index (JIBAR 3M or ZARONIA)
   - Book (trading book)
4. Click **"➕ Add Position"**
5. App stays on Portfolio Manager tab (no reload to Market Data)

### Booking a Repo Trade

1. Navigate to **Repo Trades** tab
2. Click **"➕ Add New Repo Trade"** expander
3. Fill in repo details:
   - Trade Date
   - Spot Date (auto T+3)
   - End Date (repo maturity)
   - Cash Amount (borrowed)
   - Repo Spread (bps over JIBAR)
   - Direction (borrow_cash / lend_cash)
   - Collateral (select position)
4. Click **"Add Repo Trade"**

### Monitoring Portfolio

**Current Valuation Tab:**
- Portfolio summary table (all positions)
- Balance sheet (assets, liabilities, equity)
- Risk metrics (DV01, CS01)

**Yield Attribution Tab:**
- Income breakdown by counterparty
- Asset vs repo cost comparison
- Gearing benefit analysis

**NAV Index Tab:**
- Daily NAV performance
- Operating cashflows
- Cumulative P&L

**Time Series Tab:**
- Portfolio composition over time
- Gearing evolution
- Settlement cash history

**Time Travel Tab:**
- Historical portfolio snapshots
- Point-in-time valuations

---

## Investigation Infrastructure

### Data Lineage

**Primary Sources:**
1. `JIBAR_FRA_SWAPS.xlsx` - Market rates (PRIMARY EVIDENCE)
2. `ZARONIA_FIXINGS.csv` - ZARONIA rates (PRIMARY EVIDENCE)
3. `portfolio_positions.json` - Holdings (EVIDENCE)
4. `repo_trades.json` - Financing (EVIDENCE)

**Data Flow:**
```
Market Data (XLSX/CSV)
    ↓
Rate Extraction (historical_jibar_lookup.py)
    ↓
Curve Building (enhanced_swap_curves.py)
    ↓
Pricing (portfolio_valuation_engine.py)
    ↓
Analytics (yield_attribution_engine.py, nav_index_engine.py)
    ↓
Visualization (app.py)
```

### Reproducibility

**Deterministic Calculations:**
- ✅ FRN pricing (QuantLib)
- ✅ NAV calculation
- ✅ Yield attribution
- ✅ Rate lookups

**Non-Deterministic (Requires Versioning):**
- ⚠️ Cache files (basis_cache.json, ncd_pricing.json)
- ⚠️ Historical calculations (no versioning yet)

### Audit Trail Requirements

**Current Status:**
- ❌ No calculation versioning
- ❌ No audit logging
- ❌ No data provenance tracking
- ⚠️ Limited input validation

**Recommended Improvements:**
1. Add calculation version constants
2. Implement audit logging
3. Add data provenance headers to cache files
4. Create unit tests for calculation engines
5. Add input validation on all data loaders

---

## Technical Architecture

### Project Structure
```
zaronia_frn_geared/
├── app.py                          # Main Streamlit application (3,200 lines)
├── portfolio_positions.json        # FRN holdings (EVIDENCE)
├── repo_trades.json               # Repo financing (EVIDENCE)
├── JIBAR_FRA_SWAPS.xlsx          # Market data (PRIMARY SOURCE)
├── ZARONIA_FIXINGS.csv           # ZARONIA rates (PRIMARY SOURCE)
├── requirements.txt               # Python dependencies
│
├── Core Engines/
│   ├── portfolio_valuation_engine.py    # FRN pricing (QuantLib)
│   ├── nav_index_engine.py             # NAV calculation
│   ├── yield_attribution_engine.py     # Yield breakdown
│   └── repo_cost_attribution.py        # Repo cost analysis
│
├── Analytics Modules/
│   ├── historical_analytics.py         # Historical views
│   ├── inception_to_date_analytics.py  # ITD analytics
│   ├── daily_historical_analytics.py   # Daily metrics
│   ├── counterparty_risk_manager.py    # Risk analysis
│   ├── funding_risk_analysis.py        # Funding risk
│   └── time_travel_portfolio.py        # Historical snapshots
│
├── Settlement Account/ (NEEDS CONSOLIDATION)
│   ├── settlement_account_proper.py    # Settlement tracking (19KB)
│   ├── settlement_account_tracker.py   # Settlement analytics (9KB)
│   └── daily_settlement_account.py     # Daily cashflows (12KB)
│
├── Editors/ (NEEDS CONSOLIDATION)
│   ├── easy_editors.py                 # Portfolio editing (16KB)
│   └── editable_portfolio.py           # Portfolio editing (12KB)
│
├── Visualization/
│   ├── portfolio_time_series.py        # Time series charts
│   ├── asset_repo_visualization.py     # Asset/liability charts
│   ├── enhanced_repo_trades.py         # Repo trade UI
│   ├── enhanced_swap_curves.py         # Curve visualization
│   └── zaronia_analytics.py            # ZARONIA analysis
│
├── Data Processing/
│   ├── historical_jibar_lookup.py      # Rate extraction
│   └── ncd_interpolation.py            # NCD pricing
│
├── Support/
│   ├── tab_descriptions.py             # UI descriptions
│   └── src/                           # Core utilities
│       ├── core/                      # Calendars, day count, config
│       ├── curves/                    # Curve building
│       ├── instruments/               # FRN pricing
│       └── data/                      # Data loaders
│
├── Documentation/
│   ├── README.md                       # User guide
│   ├── FORENSIC_AUDIT_REPORT.md       # Audit findings
│   └── DOCUMENTATION.md               # This file
│
└── Archive/
    └── scripts_archive/               # One-time regenerate scripts
```

### Module Dependencies

**Core Dependencies:**
- `app.py` → All modules (main orchestrator)
- Calculation engines → `src/` utilities
- Analytics → Calculation engines
- Visualization → Analytics + Calculation engines

**No Circular Dependencies Detected**

---

## Deployment

### Streamlit Cloud
1. Push to GitHub: `git push origin main`
2. Connect repository to Streamlit Cloud
3. Deploy from `app.py`
4. Auto-deploys on every git push

### Local Development
```bash
# Standard mode
streamlit run app.py

# Debug mode with port
streamlit run app.py --server.port 8501

# With logging
streamlit run app.py --logger.level=debug
```

### Environment Variables
None currently required. All configuration in `app.py` and `src/core/config.py`.

---

## Forensic Audit Summary

### Investigation Readiness Score: **58.5% (D+)**

### Critical Findings

**1. Data Lineage Gaps (HIGH RISK)**
- Cache files lack provenance: `basis_cache.json`, `ncd_pricing.json`
- Cannot trace how cached data was generated
- No source attribution or timestamps

**2. Duplicate Calculation Logic (HIGH RISK)**
- 3 settlement account modules (which is authoritative?)
- 2 portfolio editor modules
- Risk of inconsistent outputs

**3. No Calculation Versioning (HIGH RISK)**
- Cannot reproduce historical calculations
- No way to prove calculations haven't drifted
- No checksums to validate outputs

**4. Insufficient Audit Trail (HIGH RISK)**
- No logging of data transformations
- No logging of user actions
- No logging of calculation inputs/outputs

**5. No Validation Tests (HIGH RISK)**
- Core calculation engines untested
- Cannot prove calculations are correct
- Silent errors possible

### Immediate Actions Required

**Phase 1: Consolidate Duplicates (1-2 days)**
1. Merge 3 settlement account modules → 1
2. Merge 2 portfolio editor modules → 1
3. Remove unused functions

**Phase 2: Add Investigation Infrastructure (3-5 days)**
1. Calculation versioning
2. Data provenance tracking
3. Audit logging

**Phase 3: Validation (1 week)**
1. Unit tests for calculation engines
2. Input validation
3. Output checksums

**Estimated Time to Investigation-Ready: 2-3 weeks**

### Files Cleaned Up (Session: March 10, 2026)

**Removed (21 files):**
- Backup files: `app.py.backup`, `app.py.backup2`
- Legacy app: `build_app.py`
- Duplicate integration: `COMPLETE_BLOOMBERG_INTEGRATION.py`, `COMPLETE_INTEGRATION.py`
- Orphaned files: `portfolio.json`, `index.html`, `counterparties.json`
- Batch scripts: `FORCE_RELOAD.bat`, `START_APP_DEBUG.bat`
- One-time scripts: 9 regenerate scripts → `scripts_archive/`
- Utility: `uncomment_section3.py`

**Added:**
- `.gitignore` (cache files, Python bytecode, IDE files)

**Codebase now ~200KB leaner**

---

## Configuration

### Seed Capital
```python
SEED_CAPITAL = 100_000_000  # R100M
```
Set in `app.py` line 2475

### Inception Date
Automatically calculated from earliest portfolio/repo trade date.
Default fallback: 1 Jan 2024

### JIBAR Rate
Default: 6.6% (current market rate)
Loaded from `JIBAR_FRA_SWAPS.xlsx` when available

### File Paths
```python
PORTFOLIO_FILE = "portfolio_positions.json"
REPO_FILE = "repo_trades.json"
NCD_PRICING_FILE = "ncd_pricing.json"
```

---

## Support & Contact

**Developer**: Gordon Fordred  
**Email**: gordon@pv01.co.za  
**Organization**: PV01-MMAPP Ltd  
**Repository**: https://github.com/gfordred/zaronia_frn_geared

---

## License

Proprietary - PV01-MMAPP Ltd

---

## Version History

**v2.0** (March 10, 2026)
- Fixed balance sheet calculation for unfunded portfolios
- Fixed tab navigation (stays on active tab after adding positions)
- Fixed date input validation error
- Removed 21 unnecessary files
- Added .gitignore
- Comprehensive forensic audit completed
- Investigation infrastructure documented

**v1.0** (January 2024)
- Initial release
- Core FRN pricing and portfolio management
- Repo financing tracking
- Basic analytics

---

**End of Documentation**
