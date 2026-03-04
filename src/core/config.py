"""
Configuration Constants
========================

Central configuration for the ZAR FRN trading platform.
"""

from datetime import date

# Portfolio Configuration
SEED_CAPITAL = 100_000_000  # R100M initial equity
TARGET_GEARING = 9.0  # 9x leverage target
INCEPTION_DATE = date(2022, 7, 11)  # Portfolio inception

# Market Rates (Fallback values)
DEFAULT_JIBAR_RATE = 6.63  # JIBAR 3M in %
DEFAULT_REPO_SPREAD_BPS = 10  # Repo spread over JIBAR in bps
ZARONIA_SPREAD_BPS = 15  # ZARONIA spread under JIBAR in bps

# Issuer Spreads (in bps)
GOVERNMENT_SPREAD_BPS = 130  # Republic of South Africa

BANK_SPREADS = {
    'Standard Bank': 75,
    'ABSA': 95,
    'Nedbank': 110,
    'FirstRand': 125,
    'Investec': 130
}

# Risk Limits
MAX_SOVEREIGN_EXPOSURE_PCT = 50.0  # Max 50% to Republic of SA
MAX_BANK_EXPOSURE_PCT = 20.0  # Max 20% to any single bank

TOTAL_DV01_LIMIT = 500_000  # R500k total DV01
COUNTERPARTY_DV01_LIMIT = 150_000  # R150k per counterparty

TOTAL_CS01_LIMIT = 300_000  # R300k total CS01
COUNTERPARTY_CS01_LIMIT = 100_000  # R100k per counterparty

# Pricing Configuration
BUMP_SIZE_BPS = 1  # 1bp for DV01/CS01 calculations
VALUATION_TOLERANCE = 1e-6  # Convergence tolerance

# Data Files
HISTORICAL_DATA_FILE = 'JIBAR_FRA_SWAPS.xlsx'
PORTFOLIO_FILE = 'portfolio.json'
REPO_TRADES_FILE = 'repo_trades.json'

# UI Configuration
CHART_THEME = 'plotly_dark'
CHART_HEIGHT_DEFAULT = 600
CHART_HEIGHT_LARGE = 800

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
