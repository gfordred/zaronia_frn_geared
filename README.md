# ZARONIA FRN Geared Portfolio Manager

Professional fixed-income portfolio management and analytics platform for South African FRN (Floating Rate Note) portfolios with repo financing.

## Overview

This application provides institutional-grade portfolio management, risk analytics, and performance attribution for geared FRN portfolios. Built with QuantLib for accurate pricing and Streamlit for interactive visualization.

## Key Features

### Portfolio Management
- **FRN Valuation**: Real-time pricing using QuantLib with JIBAR curves
- **Repo Financing**: Track repo borrowing and gearing ratios
- **Settlement Account**: Complete cash flow tracking
- **Balance Sheet**: Assets, liabilities, and NAV monitoring

### Analytics & Reporting
- **Yield Attribution**: Breakdown by counterparty, asset, and term bucket
- **NAV Index**: Daily NAV tracking with operating cashflows
- **Risk Metrics**: DV01, CS01, and key rate sensitivities
- **Time Series**: Portfolio composition and gearing evolution
- **Historical Analytics**: Inception-to-date performance

### Professional Features
- **Curve Building**: JIBAR swap curve construction from market data
- **Mark-to-Market**: Daily portfolio valuation
- **Cashflow Projection**: Future coupon and repo payments
- **Counterparty Risk**: Exposure monitoring and limits
- **Time Travel**: Historical portfolio snapshots

## Technical Stack

- **Python 3.12+**
- **QuantLib**: Fixed income pricing and curve building
- **Streamlit**: Interactive web interface
- **Pandas**: Data manipulation and analysis
- **Plotly**: Professional charting and visualization

## Installation

```bash
# Clone repository
git clone https://github.com/gfordred/zaronia_frn_geared.git
cd zaronia_frn_geared

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app.py
```

## Data Files

### Portfolio Positions (`portfolio_positions.json`)
```json
[
  {
    "id": "unique-id",
    "name": "Bond Name",
    "counterparty": "Issuer",
    "notional": 100000000,
    "start_date": "2024-01-01",
    "maturity": "2027-01-01",
    "issue_spread": 120,
    "dm": 120,
    "index": "JIBAR 3M"
  }
]
```

### Repo Trades (`repo_trades.json`)
```json
[
  {
    "id": "unique-id",
    "trade_date": "2024-01-01",
    "spot_date": "2024-01-03",
    "end_date": "2024-04-03",
    "cash_amount": 90000000,
    "repo_spread_bps": 10,
    "direction": "borrow_cash",
    "collateral_id": "bond-id",
    "collateral_name": "Bond Name"
  }
]
```

### Market Data (`JIBAR_FRA_SWAPS.xlsx`)
Historical JIBAR rates, FRAs, and swap rates for curve construction.

## Configuration

### Seed Capital
Default: R100,000,000 (R100M)
Set in `app.py`: `SEED_CAPITAL = 100_000_000`

### Inception Date
Automatically calculated from earliest portfolio/repo trade date.
Default fallback: 1 Jan 2024

### JIBAR Rate
Default: 6.6% (current market rate)
Loaded from `JIBAR_FRA_SWAPS.xlsx` when available

## Usage

### Starting Fresh
1. Empty `portfolio_positions.json`: `[]`
2. Empty `repo_trades.json`: `[]`
3. Settlement account shows R100M seed capital
4. Ready to book trades manually

### Booking Trades
Use the "Edit Portfolio" tab to add:
- FRN positions (bonds purchased)
- Repo trades (financing borrowed)

### Monitoring
- **Current Valuation**: Portfolio MV, settlement cash, balance sheet
- **Yield Attribution**: Income breakdown and gearing benefit
- **NAV Index**: Daily performance tracking
- **Risk**: DV01/CS01 exposure by tenor

## Key Concepts

### Gearing
```
Gearing = Repo Borrowed / Seed Capital
Example: R900M repo / R100M seed = 9x gearing
```

### NAV Calculation
```
NAV = Seed Capital + Operating Cashflows
Operating Cashflows:
  + FRN coupon income (received)
  - Repo interest expense (paid)
  
Excluded (financing):
  - Repo principal (balance sheet movement)
```

### Balance Sheet
```
Assets = Liabilities + Equity
Assets:
  - Portfolio MV (bonds at market value)
  - Settlement Cash (uninvested funds)
Liabilities:
  - Repo Outstanding (borrowed funds)
Equity:
  - NAV (seed capital + P&L)
```

## Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect repository to Streamlit Cloud
3. Deploy from `app.py`
4. Auto-deploys on git push

### Local Development
```bash
streamlit run app.py --server.port 8501
```

## Project Structure

```
zaronia_frn_geared/
├── app.py                          # Main application
├── portfolio_positions.json        # FRN holdings
├── repo_trades.json               # Repo financing
├── JIBAR_FRA_SWAPS.xlsx          # Market data
├── requirements.txt               # Dependencies
├── yield_attribution_engine.py    # Yield analytics
├── nav_index_engine.py           # NAV calculation
├── settlement_account_proper.py   # Cash tracking
├── settlement_account_tracker.py  # Settlement analytics
├── repo_cost_attribution.py      # Repo cost breakdown
├── inception_to_date_analytics.py # Historical analytics
├── portfolio_time_series.py      # Time series charts
├── daily_settlement_account.py   # Daily cash flows
└── src/                          # UI components
    ├── ui.py
    └── easy_editors.py
```

## Support

For issues or questions, contact: gordon@pv01.co.za

## License

Proprietary - PV01-MMAPP Ltd

---

**Version**: 2.0  
**Last Updated**: March 2026  
**Status**: Production Ready
