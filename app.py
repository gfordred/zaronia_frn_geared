import streamlit as st
import QuantLib as ql
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import os
import sys
import traceback
import json
import uuid
import copy
from pathlib import Path

# Add project root to Python path for src imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Temporarily disable src imports until module structure is fixed
# TODO: Re-enable after fixing module imports on Streamlit Cloud
# from src.pricing import (
#     price_frn,
#     calculate_dv01_cs01,
#     calculate_key_rate_dv01,
#     solve_dm,
#     calculate_compounded_zaronia,
#     to_ql_date,
#     get_lookup_dict,
#     get_historical_rate
# )
# from src.curves import (
#     build_jibar_curve,
#     build_jibar_curve_with_diagnostics,
#     build_key_rate_curves,
#     build_zaronia_curve_daily
# )
# from src.core import get_sa_calendar

# Import ALL enhancement modules for Bloomberg-beating features
try:
    from easy_editors import render_easy_portfolio_editor, render_easy_repo_editor
    from nav_index_engine import render_nav_index, render_repo_master_table_and_summary
    from yield_attribution_engine import render_yield_attribution, render_composition_over_time
    from time_travel_portfolio import (
        render_complete_historical_settlement_account,
        render_3d_portfolio_surfaces,
        build_historical_curves_for_date
    )
    from zaronia_analytics import (
        render_zaronia_time_series,
        render_zaronia_3d_surface,
        render_zaronia_ois_curve_analysis
    )
    from historical_analytics import (
        render_repo_outstanding_chart,
        render_gearing_evolution_chart,
        render_cashflow_waterfall,
        render_portfolio_composition_over_time as render_historical_composition,
        render_yield_evolution
    )
    from inception_to_date_analytics import (
        render_inception_cashflows,
        render_risk_evolution
    )
    from settlement_account_proper import render_professional_settlement_account
    from counterparty_risk_manager import render_counterparty_risk_manager
    from daily_historical_analytics import render_daily_historical_analytics
    from asset_repo_visualization import render_asset_repo_visualization
    from tab_descriptions import render_tab_description
    from portfolio_time_series import render_portfolio_time_series
    from funding_risk_analysis import render_funding_risk_analysis
    
    MODULES_LOADED = True
    print("✓ ALL enhancement modules loaded successfully")
    print("  - Easy Editors (Portfolio & Repo)")
    print("  - NAV Index Engine")
    print("  - Yield Attribution Engine")
    print("  - Time Travel Portfolio")
    print("  - ZARONIA Analytics")
    print("  - Historical Analytics")
    print("  - Inception-to-Date Analytics")
    print("  - Tab Descriptions")
except ImportError as e:
    MODULES_LOADED = False
    print(f"⚠ Warning: Some enhancement modules not found: {e}")
    print("  App will run with basic features only")

# =============================================================================
# Configuration & Styling
# =============================================================================
st.set_page_config(page_title="ZAR FRN Trading Platform", page_icon="🇿🇦", layout="wide")

# VERSION MARKER - If you see this, new code is running
APP_VERSION = "v3.0 - Bloomberg-Beating Edition - 2026-03-03"

# Print to terminal to confirm new code is running
print("\n" + "="*70)
print(f"  ZAR FRN Trading Platform - {APP_VERSION}")
print("  Changes Applied:")
print("  ✓ Historical Time Series as default")
print("  ✓ All repos at 10 bps spread")
print("  ✓ QuantLib negative time error fixed")
print("="*70 + "\n")

st.markdown("""
<style>
    h1, h2, h3 { color: #FFB81C !important; }
    .stSlider > div > div > div > div { background-color: #007749; }
    div[data-testid="stMetricValue"] { color: #007749; }
    .stButton>button { background-color: #007749 !important; color: white !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 6px 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🇿🇦 ZAR FRN Trading Platform")
st.markdown("### JIBAR3M & ZARONIA Curves | FRN Pricer | Portfolio | Repo")

# =============================================================================
# SECTION 1: UTILITIES & CACHE
# =============================================================================

def load_json_file(path: str, default):
    """Generic safe JSON loader with utf-8 encoding."""
    p = Path(path)
    if p.exists():
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Failed to load {path}: {e}")
    return default

def save_json_file(path: str, data):
    """Generic safe JSON saver with utf-8 encoding."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        st.warning(f"Failed to save {path}: {e}")

def load_basis_cache():
    """Load cached basis analysis results."""
    return load_json_file("basis_cache.json", {})

def save_basis_cache(cache_data):
    """Save basis analysis results."""
    save_json_file("basis_cache.json", cache_data)

def get_cache_key(settlement_date, nominal, lookback, zaronia_spread):
    """Unique cache key for basis analysis params."""
    return f"{settlement_date.isoformat()}_{nominal}_{lookback}_{zaronia_spread:.2f}"

# -----------------------------------------------------------------------------
# Portfolio JSON helpers
# -----------------------------------------------------------------------------
PORTFOLIO_FILE = "portfolio.json"
REPO_FILE = "repo_trades.json"
CPTY_FILE = "counterparties.json"
NCD_PRICING_FILE = "ncd_pricing.json"

def load_portfolio():
    """Load portfolio positions from JSON."""
    data = load_json_file(PORTFOLIO_FILE, {"positions": []})
    positions = data.get("positions", [])
    # Deserialize date strings to date objects
    for pos in positions:
        if 'start_date' in pos and isinstance(pos['start_date'], str):
            pos['start_date'] = datetime.strptime(pos['start_date'], '%Y-%m-%d').date()
        if 'maturity' in pos and isinstance(pos['maturity'], str):
            pos['maturity'] = datetime.strptime(pos['maturity'], '%Y-%m-%d').date()
    return positions

def save_portfolio(positions: list):
    """Save portfolio positions to JSON."""
    save_json_file(PORTFOLIO_FILE, {"positions": positions})

def load_repo_trades():
    """Load repo trades from JSON."""
    data = load_json_file(REPO_FILE, {"trades": []})
    trades = data.get("trades", [])
    # Deserialize date strings to date objects
    for trade in trades:
        if 'trade_date' in trade and isinstance(trade['trade_date'], str):
            trade['trade_date'] = datetime.strptime(trade['trade_date'], '%Y-%m-%d').date()
        if 'spot_date' in trade and isinstance(trade['spot_date'], str):
            trade['spot_date'] = datetime.strptime(trade['spot_date'], '%Y-%m-%d').date()
        if 'end_date' in trade and isinstance(trade['end_date'], str):
            trade['end_date'] = datetime.strptime(trade['end_date'], '%Y-%m-%d').date()
    
    # DEBUG: Print to terminal to verify new code and data
    if trades:
        spreads = [t.get('repo_spread_bps', 0) for t in trades]
        unique_spreads = set(spreads)
        print(f"\n{'='*60}")
        print(f"DEBUG: Loaded {len(trades)} repo trades")
        print(f"DEBUG: Unique spreads: {unique_spreads}")
        print(f"DEBUG: All at 10 bps: {all(s == 10 for s in spreads)}")
        print(f"{'='*60}\n")
    
    return trades

def save_repo_trades(trades: list):
    """Save repo trades to JSON."""
    save_json_file(REPO_FILE, {"trades": trades})

def load_counterparties():
    """Load counterparty metadata from JSON."""
    data = load_json_file(CPTY_FILE, {"counterparties": []})
    return data.get("counterparties", [])

def save_counterparties(cptys: list):
    """Save counterparty metadata to JSON."""
    save_json_file(CPTY_FILE, {"counterparties": cptys})

def load_ncd_pricing():
    """Load NCD pricing data."""
    default = {
        "pricing_date": date.today().isoformat(),
        "banks": {}
    }
    return load_json_file(NCD_PRICING_FILE, default)

def save_ncd_pricing(pricing_data):
    """Save NCD pricing data."""
    save_json_file(NCD_PRICING_FILE, pricing_data)

def get_sa_calendar():
    """
    Get the South African calendar with public holidays.
    Ensures consistent holiday usage across the application.
    """
    cal = ql.SouthAfrica()
    
    # Custom/Observed Holidays 2023-2027
    custom_holidays = [
        # 2023
        ql.Date(2, 1, 2023),   # New Year observed
        ql.Date(21, 3, 2023),  # Human Rights
        ql.Date(7, 4, 2023),   # Good Friday
        ql.Date(10, 4, 2023),  # Family Day
        ql.Date(27, 4, 2023),  # Freedom Day
        ql.Date(1, 5, 2023),   # Workers
        ql.Date(16, 6, 2023),  # Youth
        ql.Date(9, 8, 2023),   # Womens
        ql.Date(24, 9, 2023),  # Heritage
        ql.Date(25, 9, 2023),  # Heritage observed
        ql.Date(16, 12, 2023), # Reconciliation
        ql.Date(25, 12, 2023), # Christmas
        ql.Date(26, 12, 2023), # Goodwill
        
        # 2024
        ql.Date(1, 1, 2024),
        ql.Date(21, 3, 2024),
        ql.Date(29, 3, 2024),
        ql.Date(1, 4, 2024),
        ql.Date(27, 4, 2024),
        ql.Date(1, 5, 2024),
        ql.Date(29, 5, 2024),  # Election Day
        ql.Date(17, 6, 2024),  # Youth observed
        ql.Date(9, 8, 2024),
        ql.Date(24, 9, 2024),
        ql.Date(16, 12, 2024),
        ql.Date(25, 12, 2024),
        ql.Date(26, 12, 2024),

        # 2025
        ql.Date(1, 1, 2025),
        ql.Date(21, 3, 2025),
        ql.Date(18, 4, 2025),
        ql.Date(21, 4, 2025),
        ql.Date(27, 4, 2025),
        ql.Date(28, 4, 2025), # Freedom observed
        ql.Date(1, 5, 2025),
        ql.Date(16, 6, 2025),
        ql.Date(9, 8, 2025),
        ql.Date(24, 9, 2025),
        ql.Date(16, 12, 2025),
        ql.Date(25, 12, 2025),
        ql.Date(26, 12, 2025),

        # 2026
        ql.Date(1, 1, 2026),
        ql.Date(21, 3, 2026),
        ql.Date(3, 4, 2026),
        ql.Date(6, 4, 2026),
        ql.Date(27, 4, 2026),
        ql.Date(1, 5, 2026),
        ql.Date(16, 6, 2026),
        ql.Date(9, 8, 2026),
        ql.Date(10, 8, 2026), # Womens observed
        ql.Date(24, 9, 2026),
        ql.Date(16, 12, 2026),
        ql.Date(25, 12, 2026),
        ql.Date(26, 12, 2026),

        # 2027
        ql.Date(1, 1, 2027),
        ql.Date(21, 3, 2027),
        ql.Date(22, 3, 2027), # Human Rights observed
        ql.Date(26, 3, 2027),
        ql.Date(29, 3, 2027),
        ql.Date(27, 4, 2027),
        ql.Date(1, 5, 2027),
        ql.Date(16, 6, 2027),
        ql.Date(9, 8, 2027),
        ql.Date(24, 9, 2027),
        ql.Date(16, 12, 2027),
        ql.Date(25, 12, 2027),
        ql.Date(26, 12, 2027),
        ql.Date(27, 12, 2027), # Christmas observed
    ]
    
    for h in custom_holidays:
        cal.addHoliday(h)
        
    return cal

TARGETS_FILE = "target_prices.json"
DEFAULT_TARGETS = {
    "RN2027": 102.6927,
    "RN2030": 100.5171,
    "RN2032": 104.6195,
    "RN2035": 103.9242,
    "ABFZ02": 101.45292
}

def load_targets():
    """Load targets from JSON or return defaults."""
    if os.path.exists(TARGETS_FILE):
        try:
            with open(TARGETS_FILE, "r") as f:
                saved = json.load(f)
                # Merge with defaults to ensure all keys exist
                # Prioritize saved values
                return {**DEFAULT_TARGETS, **saved}
        except Exception:
            pass
    return DEFAULT_TARGETS.copy()

def save_targets(targets):
    """Save targets to JSON."""
    try:
        with open(TARGETS_FILE, "w") as f:
            json.dump(targets, f, indent=4)
    except Exception as e:
        st.error(f"Error saving targets: {e}")

def to_ql_date(d):
    """Safely convert python date/datetime/Timestamp or ql.Date to ql.Date"""
    if isinstance(d, ql.Date):
        return d
    if hasattr(d, 'dayOfMonth'): 
        return d
    try:
        return ql.Date(d.day, d.month, d.year)
    except AttributeError:
        st.error(f"Date conversion error: Input type {type(d)} has no 'day' attribute. Value: {d}")
        raise

# -----------------------------------------------------------------------------
# Predefined Instruments
# -----------------------------------------------------------------------------
INSTRUMENTS = {
    "RN2027": {"spread": 130.0, "issue": date(2022, 7, 11), "maturity": date(2027, 7, 11)},
    "RN2030": {"spread": 96.0,  "issue": date(2023, 4, 17), "maturity": date(2030, 9, 17), "index": "JIBAR 3M"},
    "RN2032": {"spread": 147.0, "issue": date(2025, 4, 7),  "maturity": date(2032, 3, 31), "index": "JIBAR 3M"},
    "RN2035": {"spread": 130.0, "issue": date(2025, 8, 11), "maturity": date(2035, 9, 30), "index": "JIBAR 3M"},
    "ABFZ02": {"spread": 95.0, "issue": date(2025, 11, 28), "maturity": date(2028, 11, 28), "index": "ZARONIA", "lookback": 5}
}

# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------
@st.cache_data
def load_excel_data(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_excel(path)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df.sort_values('Date', inplace=True)
        df.set_index('Date', drop=False, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return None

excel_path = "JIBAR_FRA_SWAPS.xlsx"
df_historical = load_excel_data(excel_path)

zaronia_path = "ZARONIA_FIXINGS.csv"
@st.cache_data
def load_zaronia_data(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df.sort_values('Date', inplace=True)
        df.set_index('Date', drop=False, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading ZARONIA CSV: {e}")
        return None

df_zaronia = load_zaronia_data(zaronia_path)

def get_curve_rates_for_date(target_date, df_hist):
    """Get market rates (JIBAR, FRA, Swaps) for a specific date from history."""
    if df_hist is None:
        return None
        
    target_ts = pd.Timestamp(target_date)
    
    # Find row: Exact or Nearest Previous (using index)
    row = None
    if target_ts in df_hist.index:
        row = df_hist.loc[target_ts]
    else:
        # Nearest previous using index (already sorted)
        past_dates = df_hist.index[df_hist.index <= target_ts]
        if len(past_dates) > 0:
            last_avail_date = past_dates[-1]
            row = df_hist.loc[last_avail_date]
            
            # Check if this is the absolute last date in the file
            # If so, this is the "latest comprehensive curve" behavior requested
            latest_in_file = df_hist.index.max()
            if last_avail_date == latest_in_file:
                st.info(f"Trade Date {target_date} > Latest Data ({latest_in_file.date()}). Using curve data from {latest_in_file.date()}.")
            else:
                st.warning(f"No data for {target_date}. Using nearest previous: {last_avail_date.date()}")
        else:
            return None
            
    # Map rates
    r = {}
    
    # Store the actual date used for the data
    # row.name is the index (Timestamp) if found via loc/at
    if hasattr(row, 'name'):
        r["_source_date"] = row.name.date()
    elif "Date" in row:
        r["_source_date"] = row["Date"].date()
    else:
        # Fallback if somehow date is missing (unlikely given index)
        r["_source_date"] = target_date

    mapping = {
        "JIBAR3M": "JIBAR3M",
        "FRA 3x6": "FRA_3x6",
        "FRA 6x9": "FRA_6x9",
        "FRA 9x12": "FRA_9x12",
        "FRA 18x21": "FRA_18x21",
        "SASW2": "SASW2",
        "SASW3": "SASW3",
        "SASW5": "SASW5",
        "SASW10": "SASW10"
    }
    
    for xl_col, func_key in mapping.items():
        if xl_col in row:
            r[func_key] = row[xl_col]
            
    return r

def on_trade_date_change():
    """Update Settlement Date to T+3 when Trade Date changes."""
    if "trade_date" in st.session_state:
        t_date = st.session_state.trade_date
        cal = get_sa_calendar()
        try:
            ql_date = ql.Date(t_date.day, t_date.month, t_date.year)
            s_date = cal.advance(ql_date, 3, ql.Days)
            st.session_state.settlement_date = date(s_date.year(), s_date.month(), s_date.dayOfMonth())
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Sidebar: Inputs
# -----------------------------------------------------------------------------
st.sidebar.header("Configuration")

# Display version to confirm new code is running
st.sidebar.info(f"**App Version:** {APP_VERSION}")
st.sidebar.success("✅ **Changes Applied:**\n- Historical Time Series default\n- Repos at 10 bps\n- QuantLib error fixed")

# Mode Selection - Default to Historical Time Series
input_mode = st.sidebar.radio("Data Source", ["Manual Input", "Historical Time Series"], index=1)

historical_row = None

# Default to last business day if today is holiday/weekend
cal = get_sa_calendar()
today_ql = ql.Date(date.today().day, date.today().month, date.today().year)
if not cal.isBusinessDay(today_ql):
    today_ql = cal.adjust(today_ql, ql.Preceding)
    
selected_date_val = date(today_ql.year(), today_ql.month(), today_ql.dayOfMonth())

if input_mode == "Historical Time Series" and df_historical is not None:
    min_date = df_historical['Date'].min().date()
    max_date = df_historical['Date'].max().date()
    selected_date_val = st.sidebar.slider("Select Date", min_date, max_date, max_date)
    
    mask = df_historical['Date'].dt.date == selected_date_val
    if mask.any():
        historical_row = df_historical[mask].iloc[0]
        st.sidebar.success(f"Loaded data for {selected_date_val}")
    else:
        nearest_idx = (df_historical['Date'].dt.date - selected_date_val).abs().idxmin()
        historical_row = df_historical.loc[nearest_idx]
        selected_date_val = historical_row['Date'].date()
        st.sidebar.warning(f"No exact match. Using nearest: {selected_date_val}")

evaluation_date = st.sidebar.date_input("Evaluation Date", value=selected_date_val)

# Defaults
defaults = {
    "JIBAR3M": 6.78, "FRA 3x6": 6.68, "FRA 6x9": 6.51, "FRA 9x12": 6.42, "FRA 18x21": 6.28,
    "SASW2": 6.45, "SASW3": 6.46, "SASW5": 6.70, "SASW10": 7.52
}

if historical_row is not None:
    for k in defaults.keys():
        if k in historical_row:
            defaults[k] = historical_row[k]

rates = {}
with st.sidebar.expander("Market Rates (%)", expanded=True):
    rates["JIBAR3M"] = st.number_input("3M Jibar", value=float(defaults["JIBAR3M"]), format="%.3f")
    rates["FRA_3x6"] = st.number_input("FRA 3x6", value=float(defaults["FRA 3x6"]), format="%.3f")
    rates["FRA_6x9"] = st.number_input("FRA 6x9", value=float(defaults["FRA 6x9"]), format="%.3f")
    rates["FRA_9x12"] = st.number_input("FRA 9x12", value=float(defaults["FRA 9x12"]), format="%.3f")
    rates["FRA_18x21"] = st.number_input("FRA 18x21", value=float(defaults["FRA 18x21"]), format="%.3f")
    rates["SASW2"] = st.number_input("Swap 2Y", value=float(defaults["SASW2"]), format="%.3f")
    rates["SASW3"] = st.number_input("Swap 3Y", value=float(defaults["SASW3"]), format="%.3f")
    rates["SASW5"] = st.number_input("Swap 5Y", value=float(defaults["SASW5"]), format="%.3f")
    rates["SASW10"] = st.number_input("Swap 10Y", value=float(defaults["SASW10"]), format="%.3f")

with st.sidebar.expander("ZARONIA Settings", expanded=False):
    # Calculate default spread from history if available
    default_spread = 13.7
    
    # Check if we have JIBAR from history (loaded in historical_row)
    if historical_row is not None and "JIBAR3M" in historical_row:
        jibar_val = historical_row["JIBAR3M"]
        
        # Check ZARONIA - Use the same date as the JIBAR data source for consistency
        # This handles cases where Evaluation Date > Data Date (using last available)
        if df_zaronia is not None:
            # historical_row['Date'] is already a Timestamp from load_excel_data
            ts_ref = historical_row['Date']
            
            if ts_ref in df_zaronia.index:
                z_val = df_zaronia.loc[ts_ref, "ZARONIA"]
                if pd.notna(z_val):
                    default_spread = (jibar_val - z_val) * 100.0

    zaronia_spread_bps = st.number_input("JIBAR-ZARONIA Spread (bps)", value=float(default_spread), step=1.0, format="%.2f")

with st.sidebar.expander("Benchmark Target Prices", expanded=True):
    st.caption("Target All-in Price per 100 for Batch Calc")
    
    # Initialize session state for targets if not present
    if "benchmark_targets" not in st.session_state:
        st.session_state.benchmark_targets = load_targets()
        
    # Create DataFrame for Editor
    # Ensure all instruments are in the targets (merge with defaults if new instruments added)
    current_targets = st.session_state.benchmark_targets
    target_data = []
    for inst in INSTRUMENTS.keys():
        val = current_targets.get(inst, DEFAULT_TARGETS.get(inst, 100.0))
        target_data.append({"Instrument": inst, "Target Price": val})

    df_targets = pd.DataFrame(target_data)
    
    edited_targets = st.data_editor(
        df_targets,
        column_config={
            "Instrument": st.column_config.TextColumn(disabled=True),
            "Target Price": st.column_config.NumberColumn(min_value=0.0, max_value=200.0, step=0.00001, format="%.5f")
        },
        hide_index=True,
        key="target_editor"
    )
    
    # Update Session State from Editor & Save to Disk
    if not edited_targets.empty:
        updated_targets = {}
        for idx, row in edited_targets.iterrows():
            updated_targets[row["Instrument"]] = row["Target Price"]
        
        # Check if changed before saving to avoid redundant writes (optional but good)
        if updated_targets != st.session_state.benchmark_targets:
            st.session_state.benchmark_targets = updated_targets
            save_targets(updated_targets)
# SECTION 2: CURVE BUILDING (Projection + Discount, SA Conventions)
# =============================================================================

@st.cache_resource(ttl=300)  # Use cache_resource for QuantLib objects (not pickle-serializable)
def build_jibar_curve(eval_date, r, shift_bps=0.0):
    """
    Build JIBAR projection curve from Depo + FRAs + Swaps.
    ACT/365 Fixed, Modified Following, SA calendar.
    CACHED for performance - rebuilds every 5 minutes or when rates change.
    Returns (curve, settlement_date, day_count).
    Note: Uses cache_resource (not cache_data) because QuantLib objects cannot be pickled.
    """
    calendar = get_sa_calendar()
    settlement_days = 0
    ql_today = to_ql_date(eval_date)
    ql.Settings.instance().evaluationDate = ql_today
    settlement = calendar.advance(ql_today, settlement_days, ql.Days)

    helpers = []
    day_count = ql.Actual365Fixed()
    shift = shift_bps / 10000.0

    # 3M Depo (spot, 0 settlement days → deposits to settlement)
    helpers.append(ql.DepositRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(r["JIBAR3M"] / 100 + shift)),
        ql.Period(3, ql.Months), settlement_days,
        calendar, ql.ModifiedFollowing, False, day_count))

    # FRAs (start month × end month from settlement)
    for start_m, end_m, key in [(3, 6, "FRA_3x6"), (6, 9, "FRA_6x9"),
                                  (9, 12, "FRA_9x12"), (18, 21, "FRA_18x21")]:
        helpers.append(ql.FraRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(r[key] / 100 + shift)),
            start_m, end_m, settlement_days,
            calendar, ql.ModifiedFollowing, False, day_count))

    # IRS (quarterly JIBAR floating, ACT/365)
    jibar_index = ql.Jibar(ql.Period(3, ql.Months))
    for tenor, key in [(2, "SASW2"), (3, "SASW3"), (5, "SASW5"), (10, "SASW10")]:
        helpers.append(ql.SwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(r[key] / 100 + shift)),
            ql.Period(tenor, ql.Years),
            calendar, ql.Quarterly, ql.ModifiedFollowing,
            ql.Actual365Fixed(), jibar_index))

    curve = ql.PiecewiseLogCubicDiscount(settlement, helpers, day_count)
    curve.enableExtrapolation()
    return curve, settlement, day_count


def build_jibar_curve_with_diagnostics(eval_date, r, shift_bps=0.0):
    """
    Build JIBAR curve and return par-instrument repricing errors for diagnostics.
    Returns (curve, settlement, day_count, diagnostics_list).
    """
    curve, settlement, day_count = build_jibar_curve(eval_date, r, shift_bps)
    calendar = get_sa_calendar()

    diag = []
    # Depo repricing
    try:
        d_end = calendar.advance(settlement, ql.Period(3, ql.Months), ql.ModifiedFollowing)
        t = day_count.yearFraction(settlement, d_end)
        df_end = curve.discount(d_end)
        implied = (1.0 / df_end - 1.0) / t * 100
        diag.append({"Instrument": "JIBAR3M Depo", "Market (%)": r["JIBAR3M"], "Implied (%)": implied,
                      "Error (bps)": (implied - r["JIBAR3M"]) * 100})
    except Exception:
        pass

    # FRA repricing
    for start_m, end_m, key in [(3, 6, "FRA_3x6"), (6, 9, "FRA_6x9"),
                                  (9, 12, "FRA_9x12"), (18, 21, "FRA_18x21")]:
        try:
            d_s = calendar.advance(settlement, ql.Period(start_m, ql.Months), ql.ModifiedFollowing)
            d_e = calendar.advance(settlement, ql.Period(end_m, ql.Months), ql.ModifiedFollowing)
            fwd = curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate() * 100
            diag.append({"Instrument": f"FRA {start_m}x{end_m}", "Market (%)": r[key],
                          "Implied (%)": fwd, "Error (bps)": (fwd - r[key]) * 100})
        except Exception:
            pass

    # Swap repricing (par rate)
    for tenor, key in [(2, "SASW2"), (3, "SASW3"), (5, "SASW5"), (10, "SASW10")]:
        try:
            sched = ql.Schedule(settlement,
                                calendar.advance(settlement, ql.Period(tenor, ql.Years), ql.ModifiedFollowing),
                                ql.Period(3, ql.Months), calendar,
                                ql.ModifiedFollowing, ql.ModifiedFollowing,
                                ql.DateGeneration.Forward, False)
            annuity = 0.0
            for i in range(1, len(sched)):
                t_i = day_count.yearFraction(sched[i - 1], sched[i])
                annuity += t_i * curve.discount(sched[i])
            # Floating PV = 1 - df(maturity)
            df_mat = curve.discount(sched[-1])
            par_rate = (1.0 - df_mat) / annuity * 100 if annuity > 0 else 0.0
            diag.append({"Instrument": f"SASW{tenor}Y", "Market (%)": r[key],
                          "Implied (%)": par_rate, "Error (bps)": (par_rate - r[key]) * 100})
        except Exception:
            pass

    return curve, settlement, day_count, diag


def build_zaronia_curve_daily(jibar_curve, spread_bps, settlement, day_count):
    """
    Build ZARONIA OIS discount curve by daily bootstrapping from JIBAR curve.
    ZARONIA overnight rate = JIBAR overnight forward - spread.
    
    Fixed: Ensure we only calculate forward rates for dates >= settlement to avoid negative time errors
    """
    # Ensure settlement is a QuantLib Date
    if isinstance(settlement, date):
        settlement = ql.Date(settlement.day, settlement.month, settlement.year)
    
    dates = [settlement]
    dfs = [1.0]
    calendar = get_sa_calendar()

    current_date = settlement
    # Use direct date arithmetic with QuantLib Date and Period
    end_date = settlement + ql.Period(15, ql.Years)

    while current_date < end_date:
        next_date = current_date + ql.Period(1, ql.Days)
        
        # Skip if next_date is not after current_date (shouldn't happen but safety check)
        if next_date <= current_date:
            break
            
        dt = day_count.yearFraction(current_date, next_date)
        if dt < 1e-10:
            current_date = next_date
            continue
        
        # Ensure both dates are >= settlement to avoid negative time
        if current_date < settlement or next_date < settlement:
            current_date = next_date
            continue
            
        try:
            f_jibar = jibar_curve.forwardRate(current_date, next_date, day_count, ql.Simple).rate()
        except RuntimeError:
            # If forward rate calculation fails, use a fallback rate
            f_jibar = 0.08  # 8% fallback
            
        f_zaronia = max(f_jibar - spread_bps / 10000.0, 0.0)
        dfs.append(dfs[-1] / (1.0 + f_zaronia * dt))
        dates.append(next_date)
        current_date = next_date

    zaronia_curve = ql.DiscountCurve(dates, dfs, day_count)
    zaronia_curve.enableExtrapolation()
    return zaronia_curve


def build_discount_curve_with_dm(base_curve, dm_bps, day_count):
    """
    Build a discount curve = base_curve + DM spread using ZeroSpreadedTermStructure.
    This ensures discounting is truly 'swap curve + DM'.
    """
    spread_quote = ql.SimpleQuote(dm_bps / 10000.0)
    spread_handle = ql.QuoteHandle(spread_quote)
    base_handle = ql.YieldTermStructureHandle(base_curve)
    disc_curve = ql.ZeroSpreadedTermStructure(base_handle, spread_handle,
                                               ql.Compounded, ql.Annual, day_count)
    disc_curve.enableExtrapolation()
    return disc_curve


def build_key_rate_curves(eval_date, r, day_count, key_tenors=None):
    """
    Build a set of curves with single-tenor bumps for key-rate DV01.
    Returns dict: {tenor_label: bumped_curve}
    """
    if key_tenors is None:
        key_tenors = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y"]

    tenor_to_keys = {
        "3M":  ["JIBAR3M"],
        "6M":  ["FRA_3x6"],
        "1Y":  ["FRA_9x12"],
        "2Y":  ["SASW2"],
        "3Y":  ["SASW3"],
        "5Y":  ["SASW5"],
        "10Y": ["SASW10"],
    }

    kr_curves = {}
    bump = 1.0  # bps
    for tenor in key_tenors:
        keys_to_bump = tenor_to_keys.get(tenor, [])
        if not keys_to_bump:
            continue
        r_bumped = dict(r)
        for k in keys_to_bump:
            if k in r_bumped:
                r_bumped[k] = r_bumped[k] + bump
        try:
            kr_curve, _, _ = build_jibar_curve(eval_date, r_bumped)
            kr_curves[tenor] = kr_curve
        except Exception:
            pass
    return kr_curves


# =============================================================================
# SECTION 3: FRN PRICING ENGINE (Proper Projection/Discount Separation)
# =============================================================================
# NOTE: Temporarily restored local functions while fixing src module imports
# TODO: Remove once src.pricing imports are working on Streamlit Cloud

def get_lookup_dict(df, col_name):
    """Create {date: value} dict for O(1) lookup."""
    if df is None or col_name not in df.columns:
        return {}
    if not isinstance(df.index, pd.DatetimeIndex):
        return {}
    return {ts.date(): val for ts, val in zip(df.index, df[col_name]) if pd.notna(val)}


def get_historical_rate(date_lookup, df, col_name='JIBAR3M'):
    """Lookup historical rate with asof fallback."""
    if df is None:
        return None
    ts_lookup = pd.Timestamp(date_lookup)
    if isinstance(df.index, pd.DatetimeIndex):
        if ts_lookup in df.index:
            val = df.at[ts_lookup, col_name]
            if pd.notna(val):
                return val / 100.0
        try:
            prev_ts = df.index.asof(ts_lookup)
            if pd.notna(prev_ts):
                val = df.at[prev_ts, col_name]
                if pd.notna(val):
                    return val / 100.0
        except Exception:
            pass
    return None


def calculate_compounded_zaronia(start, end, lookback_days, calendar, day_count,
                                  df_zaronia, curve, df_jibar=None,
                                  zaronia_spread_bps=0.0,
                                  zaronia_dict=None, jibar_dict=None):
    """Calculate compounded daily ZARONIA with lookback."""
    d = start
    comp_factor = 1.0
    spread_adj = zaronia_spread_bps / 10000.0
    max_iter = 5000
    n = 0

    while d < end and n < max_iter:
        n += 1
        next_d = calendar.advance(d, 1, ql.Days)
        if next_d > end:
            next_d = end
        dt = day_count.yearFraction(d, next_d)
        obs_date = calendar.advance(d, -lookback_days, ql.Days)
        rate = None

        py_obs = date(obs_date.year(), obs_date.month(), obs_date.dayOfMonth())
        if zaronia_dict:
            v = zaronia_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0
        if rate is None and jibar_dict:
            v = jibar_dict.get(py_obs)
            if v is not None:
                rate = v / 100.0 - spread_adj
        if rate is None and df_zaronia is not None:
            rate = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_zaronia, 'ZARONIA')
        if rate is None and df_jibar is not None:
            j = get_historical_rate(pd.to_datetime(obs_date.ISO()), df_jibar, 'JIBAR3M')
            if j is not None:
                rate = j - spread_adj
        if rate is None:
            obs_next = calendar.advance(obs_date, 1, ql.Days)
            rate = curve.forwardRate(obs_date, obs_next, day_count, ql.Simple).rate()

        comp_factor *= (1.0 + rate * dt)
        d = next_d

    if n >= max_iter:
        return curve.forwardRate(start, end, day_count, ql.Simple).rate()

    total_dt = day_count.yearFraction(start, end)
    if total_dt < 1e-10:
        return 0.0
    return (comp_factor - 1.0) / total_dt


def price_frn(nominal, issue_spread_bps, dm_bps, start_date, end_date,
              proj_curve, disc_base_curve, settlement_date,
              day_count, calendar,
              index_type='JIBAR 3M',
              zaronia_spread_bps=0.0, lookback=0,
              df_hist=None, df_zaronia=None,
              zaronia_dict=None, jibar_dict=None,
              return_df=True):
    """
    Price FRN with proper projection/discount curve separation.
    Discount curve = ZeroSpreadedTermStructure(disc_base_curve, dm_bps).
    """
    start_ql = to_ql_date(start_date)
    end_ql = to_ql_date(end_date)
    sett_ql = to_ql_date(settlement_date)

    schedule = ql.Schedule(start_ql, end_ql,
                           ql.Period(3, ql.Months),
                           calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
                           ql.DateGeneration.Forward, False)
    dates = list(schedule)

    # Build discount curve with DM spread
    dm_spread = ql.SimpleQuote(dm_bps / 10000.0)
    disc_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(disc_base_curve),
        ql.QuoteHandle(dm_spread),
        ql.Compounded, ql.Annual, day_count)
    disc_curve.enableExtrapolation()

    ref_date = proj_curve.referenceDate()
    rows = []
    total_pv = 0.0
    accrued = 0.0

    # Accrued interest
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        if d_s <= sett_ql < d_e:
            fwd = _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                                   zaronia_spread_bps, lookback, calendar, day_count,
                                   df_hist, df_zaronia, zaronia_dict, jibar_dict)
            t_acc = day_count.yearFraction(d_s, sett_ql)
            accrued = nominal * (fwd + issue_spread_bps / 10000.0) * t_acc
            break

    # Cashflow PV
    for i in range(1, len(dates)):
        d_s, d_e = dates[i - 1], dates[i]
        if d_e <= sett_ql:
            continue

        fwd, rate_type = _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                                          zaronia_spread_bps, lookback, calendar, day_count,
                                          df_hist, df_zaronia, zaronia_dict, jibar_dict,
                                          return_type=True)

        t_period = day_count.yearFraction(d_s, d_e)
        coupon_rate = fwd + issue_spread_bps / 10000.0
        coupon_amt = nominal * coupon_rate * t_period

        df_val = disc_curve.discount(d_e) / disc_curve.discount(sett_ql)

        is_last = (i == len(dates) - 1)
        principal = nominal if is_last else 0.0
        total_pay = coupon_amt + principal
        pv = df_val * total_pay
        total_pv += pv

        if return_df:
            rows.append({
                'Start Date': d_s.ISO(),
                'End Date': d_e.ISO(),
                'Days': day_count.dayCount(d_s, d_e),
                'Rate Type': rate_type,
                'Index Rate (%)': fwd * 100,
                'Spread (bps)': issue_spread_bps,
                'Total Rate (%)': coupon_rate * 100,
                'Period (yrs)': t_period,
                'Coupon': coupon_amt,
                'Principal': principal,
                'Total Payment': total_pay,
                'Disc Factor': df_val,
                'PV': pv,
                'Type': 'Coupon+Principal' if is_last else 'Coupon',
            })

    clean = total_pv - accrued
    df_out = pd.DataFrame(rows) if return_df else None
    return total_pv, accrued, clean, df_out


def _get_coupon_rate(d_s, d_e, proj_curve, ref_date, index_type,
                     zaronia_spread_bps, lookback, calendar, day_count,
                     df_hist, df_zaronia, zaronia_dict, jibar_dict,
                     return_type=False):
    """Get forward coupon index rate for a period."""
    if index_type == 'ZARONIA':
        fwd = calculate_compounded_zaronia(d_s, d_e, lookback, calendar, day_count,
                                           df_zaronia, proj_curve, df_jibar=df_hist,
                                           zaronia_spread_bps=zaronia_spread_bps,
                                           zaronia_dict=zaronia_dict, jibar_dict=jibar_dict)
        rtype = f'Comp. ZARONIA (lb={lookback}d)'
    elif d_s < ref_date:
        fwd = None
        py_ds = date(d_s.year(), d_s.month(), d_s.dayOfMonth())
        if jibar_dict:
            v = jibar_dict.get(py_ds)
            if v is not None:
                fwd = v / 100.0
        if fwd is None and df_hist is not None:
            fwd = get_historical_rate(pd.to_datetime(d_s.ISO()), df_hist, 'JIBAR3M')
        if fwd is None:
            fwd = proj_curve.forwardRate(ref_date, ref_date + (d_e - d_s), day_count, ql.Simple).rate()
        rtype = 'Historical JIBAR'
    else:
        fwd = proj_curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate()
        rtype = 'Forward JIBAR'

    return (fwd, rtype) if return_type else fwd


def calculate_dv01_cs01(nominal, issue_spread, dm, start, end,
                         proj_curve, disc_base_curve, settlement,
                         day_count, calendar, index_type,
                         zaronia_spread_bps, lookback,
                         df_hist, df_zaronia, zaronia_dict, jibar_dict,
                         eval_date, rates_dict):
    """Calculate DV01 and CS01/DM01."""
    _, _, base_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)

    # DV01
    shifted_jibar, _, _ = build_jibar_curve(eval_date, rates_dict, shift_bps=1.0)
    shifted_proj = (build_zaronia_curve_daily(shifted_jibar, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else shifted_jibar)
    _, _, shifted_clean, _ = price_frn(
        nominal, issue_spread, dm, start, end,
        shifted_proj, shifted_jibar, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)
    dv01 = (base_clean - shifted_clean) * 10.0

    # CS01/DM01
    _, _, dm_clean, _ = price_frn(
        nominal, issue_spread, dm + 1.0, start, end,
        proj_curve, disc_base_curve, settlement,
        day_count, calendar, index_type,
        zaronia_spread_bps, lookback, df_hist, df_zaronia,
        zaronia_dict, jibar_dict, return_df=False)
    cs01 = (base_clean - dm_clean) * 10.0

    return dv01, cs01


def calculate_key_rate_dv01(nominal, issue_spread, dm, start, end,
                              disc_base_curve, settlement,
                              day_count, calendar, index_type,
                              zaronia_spread_bps, lookback,
                              df_hist, df_zaronia, zaronia_dict, jibar_dict,
                              eval_date, rates_dict, base_clean):
    """Calculate key-rate DV01 for standard tenors."""
    tenors = ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y']
    kr_curves = build_key_rate_curves(eval_date, rates_dict, day_count, tenors)
    results = {}
    for tenor, kr_proj in kr_curves.items():
        try:
            proj = (build_zaronia_curve_daily(kr_proj, zaronia_spread_bps, settlement, day_count)
                    if index_type == 'ZARONIA' else kr_proj)
            _, _, kr_clean, _ = price_frn(
                nominal, issue_spread, dm, start, end,
                proj, kr_proj, settlement,
                day_count, calendar, index_type,
                zaronia_spread_bps, lookback, df_hist, df_zaronia,
                zaronia_dict, jibar_dict, return_df=False)
            results[tenor] = (base_clean - kr_clean) * 10.0
        except Exception:
            results[tenor] = 0.0
    return results


def solve_dm(target_all_in, nominal, issue_spread, start, end,
             proj_curve, disc_base_curve, settlement,
             day_count, calendar, index_type,
             zaronia_spread_bps, lookback,
             df_hist, df_zaronia, zaronia_dict, jibar_dict,
             initial_guess=None):
    """Solve for DM given target all-in price."""
    x0 = initial_guess if initial_guess is not None else issue_spread
    x1 = x0 + 10.0

    for _ in range(12):
        p0, _, _, _ = price_frn(nominal, issue_spread, x0, start, end,
                                 proj_curve, disc_base_curve, settlement,
                                 day_count, calendar, index_type,
                                 zaronia_spread_bps, lookback, df_hist, df_zaronia,
                                 zaronia_dict, jibar_dict, return_df=False)
        p1, _, _, _ = price_frn(nominal, issue_spread, x1, start, end,
                                 proj_curve, disc_base_curve, settlement,
                                 day_count, calendar, index_type,
                                 zaronia_spread_bps, lookback, df_hist, df_zaronia,
                                 zaronia_dict, jibar_dict, return_df=False)
        y0 = p0 - target_all_in
        y1 = p1 - target_all_in
        if abs(y1) < 1e-4:
            return x1
        if abs(y1 - y0) < 1e-10:
            break
        x_new = x1 - y1 * (x1 - x0) / (y1 - y0)
        x0, x1 = x1, x_new

    return x1


# =============================================================================
# SECTION 4: PORTFOLIO MANAGER
# =============================================================================

def add_position_to_portfolio(instrument_id, instrument_data):
    """Add or update a position in the portfolio."""
    positions = load_portfolio()
    # Check if position already exists
    existing = [p for p in positions if p.get('id') == instrument_id]
    if existing:
        # Update existing
        for p in positions:
            if p.get('id') == instrument_id:
                p.update(instrument_data)
                p['id'] = instrument_id
                break
    else:
        # Add new
        instrument_data['id'] = instrument_id
        positions.append(instrument_data)
    save_portfolio(positions)
    return True


def remove_position_from_portfolio(instrument_id):
    """Remove a position from the portfolio."""
    positions = load_portfolio()
    positions = [p for p in positions if p.get('id') != instrument_id]
    save_portfolio(positions)
    return True


def get_portfolio_summary(positions, proj_curve, disc_curve, settlement, day_count, calendar,
                          zaronia_spread_bps, df_hist, df_zaronia, eval_date, rates_dict):
    """Calculate portfolio-level aggregations and risk."""
    summary_rows = []
    total_clean = 0.0
    total_dv01 = 0.0
    total_cs01 = 0.0
    kr_totals = {}

    zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
    jibar_dict = get_lookup_dict(df_hist, 'JIBAR3M')

    for pos in positions:
        try:
            idx_type = pos.get('index_type', 'JIBAR 3M')
            p_curve = build_zaronia_curve_daily(proj_curve, zaronia_spread_bps, settlement, day_count) if idx_type == 'ZARONIA' else proj_curve
            
            dirty, acc, clean, _ = price_frn(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                p_curve, disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict, return_df=False)

            dv01, cs01 = calculate_dv01_cs01(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                p_curve, disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict,
                eval_date, rates_dict)

            kr_dv01 = calculate_key_rate_dv01(
                pos['notional'], pos['issue_spread'], pos['dm'],
                pos['start_date'], pos['maturity'],
                disc_curve, settlement,
                day_count, calendar, idx_type,
                zaronia_spread_bps, pos.get('lookback', 0),
                df_hist, df_zaronia, zaronia_dict, jibar_dict,
                eval_date, rates_dict, clean)

            # Aggregate
            total_clean += clean
            total_dv01 += dv01
            total_cs01 += cs01
            for tenor, val in kr_dv01.items():
                kr_totals[tenor] = kr_totals.get(tenor, 0.0) + val

            summary_rows.append({
                'ID': pos['id'],
                'Name': pos.get('name', pos['id']),
                'Notional': pos['notional'],
                'Maturity': pos['maturity'],
                'Index': idx_type,
                'Issue Spread': pos['issue_spread'],
                'DM': pos['dm'],
                'Clean': clean,
                'Accrued': acc,
                'Dirty': dirty,
                'DV01': dv01,
                'CS01': cs01,
                **{f'KR_{t}': kr_dv01.get(t, 0.0) for t in ['3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y']},
                'Book': pos.get('book', ''),
                'Counterparty': pos.get('counterparty', ''),
                'Trader': pos.get('trader', ''),
            })
        except Exception as e:
            st.warning(f"Failed to price position {pos.get('id')}: {e}")

    return pd.DataFrame(summary_rows), total_clean, total_dv01, total_cs01, kr_totals


# =============================================================================
# SECTION 5: REPO TRADE MODULE
# =============================================================================

def calculate_repo_cashflows(repo_trade, frn_position, proj_curve, disc_curve, settlement,
                              day_count, calendar, zaronia_spread_bps, df_hist, df_zaronia):
    """
    Calculate repo cashflows and valuation with detailed interest calculations.
    Repo rate = JIBAR forward + repo_spread_bps.
    Ex-coupon dates: 5 business days for unlisted, 10 business days for RN bonds.
    """
    trade_date = to_ql_date(repo_trade['trade_date'])
    spot_date = to_ql_date(repo_trade['spot_date'])
    end_date = to_ql_date(repo_trade['end_date'])
    cash_amount = repo_trade['cash_amount']
    repo_spread_bps = repo_trade['repo_spread_bps']
    direction = repo_trade['direction']  # 'borrow_cash' or 'lend_cash'

    cal = get_sa_calendar()
    ref_date = proj_curve.referenceDate()
    
    # Determine ex-coupon days based on collateral type
    ex_coupon_days = 5  # Default for unlisted
    if frn_position and frn_position.get('name', '').startswith('RN'):
        ex_coupon_days = 10  # RN bonds have 10 day ex-coupon period
    
    # Repo rate = JIBAR forward over repo term + spread
    # Handle historical repos (both dates in the past)
    if end_date <= ref_date:
        # Historical repo - use historical JIBAR if available, else use spot rate
        hist_rate = None
        if df_hist is not None:
            hist_rate = get_historical_rate(pd.to_datetime(spot_date.ISO()), df_hist, 'JIBAR3M')
        
        if hist_rate is not None:
            jibar_fwd = hist_rate
        else:
            # Fallback to current spot rate
            jibar_fwd = proj_curve.forwardRate(ref_date, ref_date + ql.Period(3, ql.Months), 
                                               day_count, ql.Simple).rate()
    elif spot_date < ref_date < end_date:
        # Repo started in past, ends in future - use forward from ref_date to end_date
        jibar_fwd = proj_curve.forwardRate(ref_date, end_date, day_count, ql.Simple).rate()
    else:
        # Future repo - use forward rate
        jibar_fwd = proj_curve.forwardRate(spot_date, end_date, day_count, ql.Simple).rate()
    
    repo_rate = jibar_fwd + repo_spread_bps / 10000.0
    
    t_repo = day_count.yearFraction(spot_date, end_date)
    repo_days = day_count.dayCount(spot_date, end_date)
    interest = cash_amount * repo_rate * t_repo
    
    # Cashflows with detailed calculations
    # REPO LOGIC (from portfolio perspective):
    # borrow_cash = SELL asset (receive +cash), then BUY back (pay -cash-interest)
    # lend_cash = BUY asset (pay -cash), then SELL back (receive +cash+interest)
    
    cf_rows = []
    
    # Add repo rate breakdown row
    cf_rows.append({
        'Date': f'{spot_date.ISO()} to {end_date.ISO()}',
        'Type': 'Repo Rate Calculation',
        'Amount': 0.0,
        'Description': f'JIBAR fwd: {jibar_fwd*100:.4f}% + Spread: {repo_spread_bps:.1f}bps = {repo_rate*100:.4f}%',
        'Days': repo_days,
        'Year Fraction': t_repo,
        'Settlement Account': 0.0,
    })
    
    # Near leg (spot date)
    if direction == 'borrow_cash':
        # Portfolio SELLS asset, RECEIVES cash
        near_cf = cash_amount
        near_desc = f'SELL asset, RECEIVE cash R{cash_amount:,.0f}'
    else:
        # Portfolio BUYS asset, PAYS cash
        near_cf = -cash_amount
        near_desc = f'BUY asset, PAY cash R{cash_amount:,.0f}'
    
    cf_rows.append({
        'Date': spot_date.ISO(),
        'Type': 'Near Leg (Spot)',
        'Amount': near_cf,
        'Description': near_desc,
        'Days': 0,
        'Year Fraction': 0.0,
        'Settlement Account': near_cf,
    })
    
    # Interest calculation detail
    cf_rows.append({
        'Date': f'{spot_date.ISO()} to {end_date.ISO()}',
        'Type': 'Interest Accrual',
        'Amount': 0.0,
        'Description': f'R{cash_amount:,.0f} × {repo_rate*100:.4f}% × {t_repo:.6f} = R{interest:,.2f}',
        'Days': repo_days,
        'Year Fraction': t_repo,
        'Settlement Account': 0.0,
    })
    
    # Far leg (end date)
    if direction == 'borrow_cash':
        # Portfolio BUYS back asset, PAYS cash + interest
        far_cf = -(cash_amount + interest)
        far_desc = f'BUY back asset, PAY R{cash_amount:,.0f} + interest R{interest:,.2f} = R{cash_amount + interest:,.2f}'
    else:
        # Portfolio SELLS back asset, RECEIVES cash + interest
        far_cf = cash_amount + interest
        far_desc = f'SELL back asset, RECEIVE R{cash_amount:,.0f} + interest R{interest:,.2f} = R{cash_amount + interest:,.2f}'
    
    cf_rows.append({
        'Date': end_date.ISO(),
        'Type': 'Far Leg (Maturity)',
        'Amount': far_cf,
        'Description': far_desc,
        'Days': 0,
        'Year Fraction': 0.0,
        'Settlement Account': far_cf,
    })
    
    # Collateral FRN coupons during repo term (if applicable)
    if frn_position and repo_trade.get('coupon_to_lender', False):
        # Get FRN schedule
        frn_start = to_ql_date(frn_position['start_date'])
        frn_end = to_ql_date(frn_position['maturity'])
        sched = ql.Schedule(frn_start, frn_end, ql.Period(3, ql.Months),
                           cal, ql.ModifiedFollowing, ql.ModifiedFollowing,
                           ql.DateGeneration.Forward, False)
        
        for i in range(1, len(sched)):
            cpn_date = sched[i]
            if spot_date < cpn_date <= end_date:
                # Calculate ex-coupon date (business days before payment)
                ex_coupon_date = cal.advance(cpn_date, -ex_coupon_days, ql.Days)
                
                # Determine if repo holder is entitled to coupon
                # Entitled if holding the bond on ex-coupon date
                entitled = (spot_date <= ex_coupon_date)
                
                # Estimate coupon amount
                d_s, d_e = sched[i-1], sched[i]
                try:
                    if d_s < ref_date:
                        # Historical coupon - try to get historical rate
                        hist_rate = get_historical_rate(pd.to_datetime(d_s.ISO()), df_hist, 'JIBAR3M')
                        fwd = hist_rate if hist_rate else proj_curve.forwardRate(ref_date, ref_date + ql.Period(3, ql.Months), day_count, ql.Simple).rate()
                    else:
                        fwd = proj_curve.forwardRate(d_s, d_e, day_count, ql.Simple).rate()
                except:
                    fwd = 0.08  # Fallback rate
                
                t_cpn = day_count.yearFraction(d_s, d_e)
                cpn_days = day_count.dayCount(d_s, d_e)
                cpn_rate = fwd + frn_position['issue_spread'] / 10000.0
                cpn_amt = frn_position['notional'] * cpn_rate * t_cpn
                
                # Coupon flows to entitled party
                # If borrow_cash (sold asset), coupon goes to lender (cash out -)
                # If lend_cash (bought asset), coupon comes to us (cash in +)
                if entitled:
                    if direction == 'borrow_cash':
                        # We sold the asset, so coupon goes to lender (we pay)
                        cpn_cf = -cpn_amt
                        desc = f'FRN coupon R{cpn_amt:,.2f} PAID to lender (we sold asset) - Ex-date: {ex_coupon_date.ISO()}'
                    else:
                        # We bought the asset, so coupon comes to us (we receive)
                        cpn_cf = cpn_amt
                        desc = f'FRN coupon R{cpn_amt:,.2f} RECEIVED (we own asset) - Ex-date: {ex_coupon_date.ISO()}'
                else:
                    cpn_cf = 0.0
                    desc = f'FRN coupon R{cpn_amt:,.2f} NOT entitled (ex-date {ex_coupon_date.ISO()} after repo start)'
                
                cf_rows.append({
                    'Date': cpn_date.ISO(),
                    'Type': 'FRN Coupon' + (' ✓' if entitled else ' ✗'),
                    'Amount': cpn_cf,
                    'Description': desc,
                    'Days': cpn_days,
                    'Year Fraction': t_cpn,
                    'Settlement Account': cpn_cf,
                })
    
    # Calculate cumulative settlement account balance
    df_cf = pd.DataFrame(cf_rows)
    
    # Sort by date to ensure proper cumulative calculation
    df_cf['Date_Sort'] = pd.to_datetime(df_cf['Date'].str[:10], errors='coerce')
    df_cf = df_cf.sort_values('Date_Sort')
    
    # Calculate cumulative balance
    df_cf['Cumulative Balance'] = df_cf['Settlement Account'].cumsum()
    
    # Drop sort column
    df_cf = df_cf.drop('Date_Sort', axis=1)
    
    # PV of repo
    # Handle historical repos where dates may be before settlement
    try:
        if spot_date <= settlement:
            df_spot = 1.0  # Historical cashflow already occurred
        else:
            df_spot = disc_curve.discount(spot_date) / disc_curve.discount(settlement)
        
        if end_date <= settlement:
            df_end = 1.0  # Historical cashflow already occurred
        else:
            df_end = disc_curve.discount(end_date) / disc_curve.discount(settlement)
        
        pv_initial = near_cf * df_spot
        pv_final = far_cf * df_end
        pv_repo = pv_initial + pv_final
    except Exception as e:
        # Fallback for any discount curve issues with historical dates
        pv_repo = 0.0
        st.warning(f"Could not calculate PV for repo {repo_trade.get('id', 'Unknown')}: {e}")
    
    return df_cf, pv_repo, repo_rate * 100, interest


# =============================================================================
# SECTION 6: MAIN CURVE BUILD & DATA INITIALIZATION
# =============================================================================

try:
    # Build base curves
    jibar_curve, settlement, day_count = build_jibar_curve(evaluation_date, rates)
    calendar = get_sa_calendar()
    zaronia_curve = build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count)
    
    # Build curve with diagnostics for Curve Diagnostics tab
    jibar_diag_curve, _, _, diagnostics = build_jibar_curve_with_diagnostics(evaluation_date, rates)

    
    # =========================================================================
    # SECTION 7: UI LAYOUT - ALL TABS
    # =========================================================================
    
    tabs = st.tabs([
        "Market Data",
        "Curve Analysis", 
        "FRN Pricer & Risk",
        "ZARONIA Calculator",
        "Basis Analysis",
        "Portfolio Manager",
        "Repo Trades",
        "NCD Pricing",
        "Curve Diagnostics"
    ])
    
    # -------------------------------------------------------------------------
    # TAB 1: Market Data
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Market Data Time Series")
        
        # Merge JIBAR and ZARONIA data
        if df_historical is not None and df_zaronia is not None:
            df_merged = df_historical.copy()
            df_merged = df_merged.join(df_zaronia[['ZARONIA']], how='left')
            
            # Create comprehensive chart with ZARONIA
            fig_hist = go.Figure()
            
            fig_hist.add_trace(go.Scatter(
                x=df_merged.index,
                y=df_merged['JIBAR3M'],
                name='JIBAR 3M',
                line=dict(color='#00d4ff', width=2)
            ))
            
            fig_hist.add_trace(go.Scatter(
                x=df_merged.index,
                y=df_merged['ZARONIA'],
                name='ZARONIA',
                line=dict(color='#00ff88', width=2)
            ))
            
            fig_hist.add_trace(go.Scatter(
                x=df_merged.index,
                y=df_merged['SASW5'],
                name='5Y Swap',
                line=dict(color='#ffa500', width=2)
            ))
            
            fig_hist.add_trace(go.Scatter(
                x=df_merged.index,
                y=df_merged['SASW10'],
                name='10Y Swap',
                line=dict(color='#ff6b6b', width=2)
            ))
            
            fig_hist.update_layout(
                title="Historical JIBAR, ZARONIA & Swaps",
                xaxis_title="Date",
                yaxis_title="Rate (%)",
                template="plotly_dark",
                hovermode='x unified',
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Show recent data with ZARONIA
            st.markdown("##### Recent Market Data")
            recent_cols = ['JIBAR3M', 'ZARONIA', 'SASW2', 'SASW5', 'SASW10']
            available_cols = [col for col in recent_cols if col in df_merged.columns]
            st.dataframe(df_merged[available_cols].tail(20), use_container_width=True)
            
            # Swap Yield Curve Chart
            st.markdown("---")
            st.markdown("##### 📊 Complete Yield Curve (All Instruments)")
            
            # Get latest rates
            latest_data = df_merged.iloc[-1]
            
            # Calculate changes
            try:
                week_ago = df_merged.iloc[-6] if len(df_merged) >= 6 else df_merged.iloc[0]
                month_ago = df_merged.iloc[-22] if len(df_merged) >= 22 else df_merged.iloc[0]
                ytd_start = df_merged[df_merged.index.year == date.today().year].iloc[0] if len(df_merged[df_merged.index.year == date.today().year]) > 0 else df_merged.iloc[0]
            except:
                week_ago = month_ago = ytd_start = df_merged.iloc[0]
            
            # Build curve data
            curve_data = []
            
            # ZARONIA O/N
            if 'ZARONIA' in df_merged.columns:
                curve_data.append({
                    'Instrument': 'ZARONIA O/N',
                    'Type': 'OIS',
                    'Term': 0.003,  # ~1 day
                    'Rate': latest_data['ZARONIA'],
                    '1W Δ': latest_data['ZARONIA'] - week_ago.get('ZARONIA', latest_data['ZARONIA']),
                    '1M Δ': latest_data['ZARONIA'] - month_ago.get('ZARONIA', latest_data['ZARONIA']),
                    'YTD Δ': latest_data['ZARONIA'] - ytd_start.get('ZARONIA', latest_data['ZARONIA'])
                })
            
            # JIBAR 3M
            if 'JIBAR3M' in df_merged.columns:
                curve_data.append({
                    'Instrument': 'JIBAR 3M',
                    'Type': 'Deposit',
                    'Term': 0.25,
                    'Rate': latest_data['JIBAR3M'],
                    '1W Δ': latest_data['JIBAR3M'] - week_ago.get('JIBAR3M', latest_data['JIBAR3M']),
                    '1M Δ': latest_data['JIBAR3M'] - month_ago.get('JIBAR3M', latest_data['JIBAR3M']),
                    'YTD Δ': latest_data['JIBAR3M'] - ytd_start.get('JIBAR3M', latest_data['JIBAR3M'])
                })
            
            # FRAs
            fra_map = {
                'FRA3X6': (0.5, 'FRA'),
                'FRA6X9': (0.75, 'FRA'),
                'FRA9X12': (1.0, 'FRA'),
                'FRA18X21': (1.75, 'FRA')
            }
            for fra_name, (term, inst_type) in fra_map.items():
                if fra_name in df_merged.columns:
                    curve_data.append({
                        'Instrument': fra_name,
                        'Type': inst_type,
                        'Term': term,
                        'Rate': latest_data[fra_name],
                        '1W Δ': latest_data[fra_name] - week_ago.get(fra_name, latest_data[fra_name]),
                        '1M Δ': latest_data[fra_name] - month_ago.get(fra_name, latest_data[fra_name]),
                        'YTD Δ': latest_data[fra_name] - ytd_start.get(fra_name, latest_data[fra_name])
                    })
            
            # Swaps
            swap_map = {'SASW1': 1, 'SASW2': 2, 'SASW3': 3, 'SASW5': 5, 'SASW7': 7, 'SASW10': 10, 'SASW15': 15, 'SASW20': 20}
            for swap_name, term in swap_map.items():
                if swap_name in df_merged.columns:
                    curve_data.append({
                        'Instrument': swap_name,
                        'Type': 'Swap',
                        'Term': term,
                        'Rate': latest_data[swap_name],
                        '1W Δ': latest_data[swap_name] - week_ago.get(swap_name, latest_data[swap_name]),
                        '1M Δ': latest_data[swap_name] - month_ago.get(swap_name, latest_data[swap_name]),
                        'YTD Δ': latest_data[swap_name] - ytd_start.get(swap_name, latest_data[swap_name])
                    })
            
            df_curve = pd.DataFrame(curve_data)
            
            # Display table with changes
            st.dataframe(df_curve.style.format({
                'Term': '{:.2f}',
                'Rate': '{:.4f}',
                '1W Δ': '{:+.2f}',
                '1M Δ': '{:+.2f}',
                'YTD Δ': '{:+.2f}'
            }), use_container_width=True, hide_index=True)
            
            # Yield curve chart with period changes
            from plotly.subplots import make_subplots
            
            fig_curve = make_subplots(
                rows=2, cols=1,
                row_heights=[0.7, 0.3],
                subplot_titles=('Complete ZAR Yield Curve', 'Period Changes (1 Week)'),
                vertical_spacing=0.12,
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            # Color by type
            type_colors = {'OIS': '#9b59b6', 'Deposit': '#00d4ff', 'FRA': '#ffa500', 'Swap': '#00ff88'}
            
            # Top panel: Yield curve
            for inst_type in df_curve['Type'].unique():
                df_type = df_curve[df_curve['Type'] == inst_type]
                fig_curve.add_trace(go.Scatter(
                    x=df_type['Term'],
                    y=df_type['Rate'],
                    mode='lines+markers',
                    name=inst_type,
                    line=dict(color=type_colors.get(inst_type, '#ffffff'), width=3),
                    marker=dict(size=10),
                    hovertemplate='<b>%{text}</b><br>Term: %{x:.2f}Y<br>Rate: %{y:.4f}%<extra></extra>',
                    text=df_type['Instrument'],
                    showlegend=True
                ), row=1, col=1)
            
            # Bottom panel: Period changes as bars
            bar_colors = ['#00ff88' if x >= 0 else '#ff6b6b' for x in df_curve['1W Δ']]
            
            fig_curve.add_trace(go.Bar(
                x=df_curve['Term'],
                y=df_curve['1W Δ'],
                name='1W Change',
                marker=dict(color=bar_colors),
                hovertemplate='<b>%{text}</b><br>Term: %{x:.2f}Y<br>1W Δ: %{y:+.2f} bps<extra></extra>',
                text=df_curve['Instrument'],
                showlegend=False
            ), row=2, col=1)
            
            # Add zero line for reference
            fig_curve.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
            
            # Update axes
            fig_curve.update_xaxes(title_text="Term (Years)", row=1, col=1)
            fig_curve.update_xaxes(title_text="Term (Years)", row=2, col=1)
            fig_curve.update_yaxes(title_text="Rate (%)", row=1, col=1)
            fig_curve.update_yaxes(title_text="Change (bps)", row=2, col=1)
            
            fig_curve.update_layout(
                template='plotly_dark',
                height=800,
                hovermode='closest',
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1)
            )
            
            st.plotly_chart(fig_curve, use_container_width=True)
            
        elif df_historical is not None:
            # Fallback if ZARONIA not available
            fig_hist = px.line(df_historical, x='Date', y=['JIBAR3M', 'SASW5', 'SASW10'],
                              title="Historical JIBAR & Swaps")
            fig_hist.update_layout(template="plotly_dark")
            st.plotly_chart(fig_hist, use_container_width=True)
            st.dataframe(df_historical.tail(20), use_container_width=True)
        else:
            st.warning("Historical data file 'JIBAR_FRA_SWAPS.xlsx' not found.")
    
    # -------------------------------------------------------------------------
    # TAB 2: Curve Analysis
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.subheader("📈 Market Curves & Analytics")
        
        # Create sub-tabs for different curve views
        curve_tabs = st.tabs([
            "🎯 Live Market Rates",
            "📊 Zero Curves",
            "⚡ Forward Curves",
            "🔄 FRA Curve",
            "📉 Discount Factors"
        ])
        
        # TAB 2.1: Live Market Rates
        with curve_tabs[0]:
            st.markdown("##### Current Market Rates (Input Curve)")
            
            # Build market rates table
            market_rates_data = []
            
            # Depo
            market_rates_data.append({
                'Instrument': 'JIBAR 3M Depo',
                'Type': 'Deposit',
                'Tenor': '3M',
                'Rate (%)': rates['JIBAR3M'],
                'Maturity': calendar.advance(settlement, ql.Period(3, ql.Months), ql.ModifiedFollowing).ISO()
            })
            
            # FRAs
            fra_tenors = [('3x6', 3, 6), ('6x9', 6, 9), ('9x12', 9, 12), ('18x21', 18, 21)]
            for label, start_m, end_m in fra_tenors:
                market_rates_data.append({
                    'Instrument': f'FRA {label}',
                    'Type': 'FRA',
                    'Tenor': f'{start_m}x{end_m}',
                    'Rate (%)': rates[f'FRA_{label}'],
                    'Maturity': calendar.advance(settlement, ql.Period(end_m, ql.Months), ql.ModifiedFollowing).ISO()
                })
            
            # Swaps
            swap_tenors = [(2, 'SASW2'), (3, 'SASW3'), (5, 'SASW5'), (10, 'SASW10')]
            for years, key in swap_tenors:
                market_rates_data.append({
                    'Instrument': f'JIBAR Swap {years}Y',
                    'Type': 'IRS',
                    'Tenor': f'{years}Y',
                    'Rate (%)': rates[key],
                    'Maturity': calendar.advance(settlement, ql.Period(years, ql.Years), ql.ModifiedFollowing).ISO()
                })
            
            df_market = pd.DataFrame(market_rates_data)
            
            # Display with formatting
            st.dataframe(df_market.style.format({
                'Rate (%)': '{:.4f}'
            }),
            use_container_width=True, hide_index=True)
            
            # Market rate chart
            fig_market = go.Figure()
            
            # Add bars colored by type
            colors = {'Deposit': 'cyan', 'FRA': 'orange', 'IRS': 'magenta'}
            for inst_type in ['Deposit', 'FRA', 'IRS']:
                df_type = df_market[df_market['Type'] == inst_type]
                fig_market.add_trace(go.Bar(
                    x=df_type['Instrument'],
                    y=df_type['Rate (%)'],
                    name=inst_type,
                    marker_color=colors[inst_type],
                    text=df_type['Rate (%)'].round(4),
                    textposition='outside'
                ))
            
            fig_market.update_layout(
                title='Market Input Rates by Instrument Type',
                xaxis_title='Instrument',
                yaxis_title='Rate (%)',
                template='plotly_dark',
                barmode='group',
                height=500,
                showlegend=True
            )
            
            st.plotly_chart(fig_market, use_container_width=True)
            
            # Summary metrics
            st.markdown("##### Market Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("3M JIBAR", f"{rates['JIBAR3M']:.4f}%")
            m2.metric("2Y Swap", f"{rates['SASW2']:.4f}%")
            m3.metric("5Y Swap", f"{rates['SASW5']:.4f}%")
            m4.metric("2s5s Spread", f"{(rates['SASW5'] - rates['SASW2'])*100:.1f} bps")
        
        # TAB 2.2: Zero Curves
        with curve_tabs[1]:
            st.markdown("##### Zero Rate Curves (Continuously Compounded)")
            
            # Generate zero curve data
            zero_tenors = [ql.Period(i, ql.Months) for i in [1, 3, 6, 9, 12, 18, 24, 36, 48, 60, 84, 120]]
            zero_dates = [calendar.advance(settlement, tenor) for tenor in zero_tenors]
            
            zero_data = []
            for tenor, d in zip(zero_tenors, zero_dates):
                j_zero = jibar_curve.zeroRate(d, day_count, ql.Compounded, ql.Annual).rate() * 100
                z_zero = zaronia_curve.zeroRate(d, day_count, ql.Compounded, ql.Annual).rate() * 100
                
                # Calculate discount factors
                j_df = jibar_curve.discount(d)
                z_df = zaronia_curve.discount(d)
                
                years = day_count.yearFraction(settlement, d)
                
                zero_data.append({
                    'Tenor': str(tenor),
                    'Years': years,
                    'Date': d.ISO(),
                    'JIBAR Zero (%)': j_zero,
                    'ZARONIA Zero (%)': z_zero,
                    'Spread (bps)': (j_zero - z_zero) * 100,
                    'JIBAR DF': j_df,
                    'ZARONIA DF': z_df
                })
            
            df_zero = pd.DataFrame(zero_data)
            
            # Display table
            st.dataframe(df_zero.style.format({
                'Years': '{:.2f}',
                'JIBAR Zero (%)': '{:.4f}',
                'ZARONIA Zero (%)': '{:.4f}',
                'Spread (bps)': '{:.2f}',
                'JIBAR DF': '{:.6f}',
                'ZARONIA DF': '{:.6f}'
            }),
            use_container_width=True, hide_index=True)
            
            # Interactive zero curve chart
            fig_zero = go.Figure()
            
            fig_zero.add_trace(go.Scatter(
                x=df_zero['Years'],
                y=df_zero['JIBAR Zero (%)'],
                name='JIBAR Zero',
                mode='lines+markers',
                line=dict(color='cyan', width=3),
                marker=dict(size=8)
            ))
            
            fig_zero.add_trace(go.Scatter(
                x=df_zero['Years'],
                y=df_zero['ZARONIA Zero (%)'],
                name='ZARONIA Zero',
                mode='lines+markers',
                line=dict(color='magenta', width=3),
                marker=dict(size=8)
            ))
            
            fig_zero.update_layout(
                title='Zero Rate Curves (Continuously Compounded, Annual)',
                xaxis_title='Maturity (Years)',
                yaxis_title='Zero Rate (%)',
                template='plotly_dark',
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_zero, use_container_width=True)
            
            # Spread chart
            fig_spread = go.Figure()
            
            fig_spread.add_trace(go.Scatter(
                x=df_zero['Years'],
                y=df_zero['Spread (bps)'],
                name='JIBAR - ZARONIA',
                mode='lines+markers',
                fill='tozeroy',
                line=dict(color='orange', width=2),
                marker=dict(size=6)
            ))
            
            fig_spread.update_layout(
                title='Zero Rate Spread (JIBAR - ZARONIA)',
                xaxis_title='Maturity (Years)',
                yaxis_title='Spread (bps)',
                template='plotly_dark',
                height=400
            )
            
            st.plotly_chart(fig_spread, use_container_width=True)
        
        # TAB 2.3: Forward Curves
        with curve_tabs[2]:
            st.markdown("##### 3M Forward Rate Curves")
            
            # Generate forward curve data
            fwd_dates = [settlement + ql.Period(i, ql.Months) for i in range(0, 121, 3)]
            fwd_data = []
            
            for d in fwd_dates:
                if d >= settlement:
                    d_end = calendar.advance(d, ql.Period(3, ql.Months), ql.ModifiedFollowing)
                    j_fwd = jibar_curve.forwardRate(d, d_end, day_count, ql.Simple).rate() * 100
                    z_fwd = zaronia_curve.forwardRate(d, d_end, day_count, ql.Simple).rate() * 100
                    
                    years = day_count.yearFraction(settlement, d)
                    
                    fwd_data.append({
                        'Start Date': d.ISO(),
                        'End Date': d_end.ISO(),
                        'Years': years,
                        'JIBAR 3M Fwd (%)': j_fwd,
                        'ZARONIA 3M Fwd (%)': z_fwd,
                        'Spread (bps)': (j_fwd - z_fwd) * 100
                    })
            
            df_fwd = pd.DataFrame(fwd_data)
            
            # Display table (first 20 rows)
            st.dataframe(df_fwd.head(20).style.format({
                'Years': '{:.2f}',
                'JIBAR 3M Fwd (%)': '{:.4f}',
                'ZARONIA 3M Fwd (%)': '{:.4f}',
                'Spread (bps)': '{:.2f}'
            }), use_container_width=True, hide_index=True)
            
            # Forward curve chart
            fig_fwd = go.Figure()
            
            fig_fwd.add_trace(go.Scatter(
                x=df_fwd['Years'],
                y=df_fwd['JIBAR 3M Fwd (%)'],
                name='JIBAR 3M Forward',
                mode='lines',
                line=dict(color='cyan', width=2)
            ))
            
            fig_fwd.add_trace(go.Scatter(
                x=df_fwd['Years'],
                y=df_fwd['ZARONIA 3M Fwd (%)'],
                name='ZARONIA 3M Forward',
                mode='lines',
                line=dict(color='magenta', width=2)
            ))
            
            fig_fwd.update_layout(
                title='3-Month Forward Rate Curves',
                xaxis_title='Forward Start (Years)',
                yaxis_title='3M Forward Rate (%)',
                template='plotly_dark',
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_fwd, use_container_width=True)
        
        # TAB 2.4: FRA Curve
        with curve_tabs[3]:
            st.markdown("##### FRA Curve Analysis")
            
            # Build detailed FRA curve
            fra_curve_data = []
            
            # Actual FRAs from market
            fra_specs = [
                ('3x6', 3, 6, rates['FRA_3x6']),
                ('6x9', 6, 9, rates['FRA_6x9']),
                ('9x12', 9, 12, rates['FRA_9x12']),
                ('18x21', 18, 21, rates['FRA_18x21'])
            ]
            
            for label, start_m, end_m, market_rate in fra_specs:
                d_start = calendar.advance(settlement, ql.Period(start_m, ql.Months), ql.ModifiedFollowing)
                d_end = calendar.advance(settlement, ql.Period(end_m, ql.Months), ql.ModifiedFollowing)
                
                # Implied forward from curve
                implied_fwd = jibar_curve.forwardRate(d_start, d_end, day_count, ql.Simple).rate() * 100
                
                fra_curve_data.append({
                    'FRA': label,
                    'Start (M)': start_m,
                    'End (M)': end_m,
                    'Period (M)': end_m - start_m,
                    'Market Rate (%)': market_rate,
                    'Implied Fwd (%)': implied_fwd,
                    'Error (bps)': (implied_fwd - market_rate) * 100
                })
            
            df_fra = pd.DataFrame(fra_curve_data)
            
            st.dataframe(df_fra.style.format({
                'Market Rate (%)': '{:.4f}',
                'Implied Fwd (%)': '{:.4f}',
                'Error (bps)': '{:.2f}'
            }),
            use_container_width=True, hide_index=True)
            
            # FRA curve chart
            fig_fra = go.Figure()
            
            fig_fra.add_trace(go.Scatter(
                x=df_fra['FRA'],
                y=df_fra['Market Rate (%)'],
                name='Market FRA',
                mode='markers+lines',
                marker=dict(size=12, color='orange'),
                line=dict(width=2)
            ))
            
            fig_fra.add_trace(go.Scatter(
                x=df_fra['FRA'],
                y=df_fra['Implied Fwd (%)'],
                name='Curve Implied',
                mode='markers+lines',
                marker=dict(size=12, color='cyan'),
                line=dict(width=2, dash='dash')
            ))
            
            fig_fra.update_layout(
                title='FRA Market vs Curve Implied Forwards',
                xaxis_title='FRA',
                yaxis_title='Rate (%)',
                template='plotly_dark',
                height=400
            )
            
            st.plotly_chart(fig_fra, use_container_width=True)
            
            # Repricing errors
            st.markdown("##### FRA Repricing Quality")
            max_error = abs(df_fra['Error (bps)']).max()
            avg_error = abs(df_fra['Error (bps)']).mean()
            
            e1, e2, e3 = st.columns(3)
            e1.metric("Max Error", f"{max_error:.2f} bps")
            e2.metric("Avg Error", f"{avg_error:.2f} bps")
            e3.metric("Curve Quality", "Excellent" if max_error < 0.5 else "Good" if max_error < 1.0 else "Fair")
        
        # TAB 2.5: Discount Factors
        with curve_tabs[4]:
            st.markdown("##### Discount Factor Curves")
            
            # Use same tenors as zero curve
            df_disc = df_zero[['Tenor', 'Years', 'Date', 'JIBAR DF', 'ZARONIA DF']].copy()
            df_disc['DF Ratio'] = df_disc['ZARONIA DF'] / df_disc['JIBAR DF']
            
            st.dataframe(df_disc.style.format({
                'Years': '{:.2f}',
                'JIBAR DF': '{:.6f}',
                'ZARONIA DF': '{:.6f}',
                'DF Ratio': '{:.6f}'
            }), use_container_width=True, hide_index=True)
            
            # Discount factor chart
            fig_df = go.Figure()
            
            fig_df.add_trace(go.Scatter(
                x=df_disc['Years'],
                y=df_disc['JIBAR DF'],
                name='JIBAR DF',
                mode='lines+markers',
                line=dict(color='cyan', width=2)
            ))
            
            fig_df.add_trace(go.Scatter(
                x=df_disc['Years'],
                y=df_disc['ZARONIA DF'],
                name='ZARONIA DF',
                mode='lines+markers',
                line=dict(color='magenta', width=2)
            ))
            
            fig_df.update_layout(
                title='Discount Factor Curves',
                xaxis_title='Maturity (Years)',
                yaxis_title='Discount Factor',
                template='plotly_dark',
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_df, use_container_width=True)
            
            # DF Ratio chart
            fig_ratio = go.Figure()
            
            fig_ratio.add_trace(go.Scatter(
                x=df_disc['Years'],
                y=df_disc['DF Ratio'],
                name='ZARONIA DF / JIBAR DF',
                mode='lines+markers',
                fill='tozeroy',
                line=dict(color='orange', width=2)
            ))
            
            fig_ratio.add_hline(y=1.0, line_dash="dash", line_color="white", 
                               annotation_text="Parity")
            
            fig_ratio.update_layout(
                title='Discount Factor Ratio (ZARONIA / JIBAR)',
                xaxis_title='Maturity (Years)',
                yaxis_title='DF Ratio',
                template='plotly_dark',
                height=400
            )
            
            st.plotly_chart(fig_ratio, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # TAB 3: FRN Pricer & Risk
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.subheader("FRN Pricing & Risk Analysis")
        
        st.markdown("##### Instrument Selection")
        sel_inst = st.radio("Choose Instrument", ["Manual"] + list(INSTRUMENTS.keys()), horizontal=True, key="frn_inst_sel")
        
        if sel_inst != "Manual" and sel_inst in INSTRUMENTS:
            inst_data = INSTRUMENTS[sel_inst]
            st.session_state.frn_issue_spread = inst_data["spread"]
            st.session_state.frn_dm = inst_data["spread"]
            st.session_state.frn_start = inst_data["issue"]
            st.session_state.frn_end = inst_data["maturity"]
            st.session_state.frn_index = inst_data.get("index", "JIBAR 3M")
            st.session_state.frn_lookback = inst_data.get("lookback", 0)
        
        c1, c2, c3 = st.columns(3)
        nominal = c1.number_input("Nominal", value=1_000_000.0, step=10000.0, format="%.2f", key="frn_nom")
        issue_spread = c2.number_input("Issue Spread (bps)", value=st.session_state.get('frn_issue_spread', 90.0), key="frn_issue_spread")
        dm = c3.number_input("Market DM (bps)", value=st.session_state.get('frn_dm', 30.0), key="frn_dm")
        
        c4, c5 = st.columns(2)
        frn_start = c4.date_input("Issue Date", value=st.session_state.get('frn_start', evaluation_date), key="frn_start")
        frn_end = c5.date_input("Maturity", value=st.session_state.get('frn_end', evaluation_date + timedelta(days=365*3)), key="frn_end")
        
        c6, c7 = st.columns(2)
        trade_date = c6.date_input("Trade Date", value=evaluation_date, key="frn_trade")
        sett_date = c7.date_input("Settlement (T+3)", value=evaluation_date + timedelta(days=3), key="frn_sett")
        
        frn_index = st.radio("Reference Index", ["JIBAR 3M", "ZARONIA"],
                            index=0 if st.session_state.get('frn_index', 'JIBAR 3M') == 'JIBAR 3M' else 1,
                            key="frn_index")
        lookback = 0
        if frn_index == "ZARONIA":
            lookback = st.number_input("Lookback Days (p)", value=st.session_state.get('frn_lookback', 5), step=1, key="frn_lookback")
        
        if st.button("Price & Calculate Risk", type="primary", key="btn_price_frn"):
            proj = build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count) if frn_index == 'ZARONIA' else jibar_curve
            
            zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
            jibar_dict = get_lookup_dict(df_historical, 'JIBAR3M')
            
            dirty, acc, clean, df_cf = price_frn(
                nominal, issue_spread, dm, frn_start, frn_end,
                proj, jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict, return_df=True)
            
            dv01, cs01 = calculate_dv01_cs01(
                nominal, issue_spread, dm, frn_start, frn_end,
                proj, jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict,
                evaluation_date, rates)
            
            kr_dv01 = calculate_key_rate_dv01(
                nominal, issue_spread, dm, frn_start, frn_end,
                jibar_curve, sett_date,
                day_count, calendar, frn_index,
                zaronia_spread_bps, lookback,
                df_historical, df_zaronia, zaronia_dict, jibar_dict,
                evaluation_date, rates, clean)
            
            st.markdown("### Valuation")
            m1, m2, m3 = st.columns(3)
            m1.metric("Dirty Price", f"{dirty:,.2f}", f"{(dirty/nominal)*100:.5f} per 100")
            m2.metric("Accrued", f"{acc:,.2f}", f"{(acc/nominal)*100:.5f} per 100")
            m3.metric("Clean Price", f"{clean:,.2f}", f"{(clean/nominal)*100:.5f} per 100")
            
            st.markdown("### Cash Flow Analysis")
            if df_cf is not None and not df_cf.empty:
                tab_cf_table, tab_cf_chart = st.tabs(["Detailed Table", "Cash Flow Profile"])
                
                with tab_cf_table:
                    st.dataframe(df_cf.style.format({
                        "Days": "{:.0f}",
                        "Index Rate (%)": "{:.4f}",
                        "Spread (bps)": "{:.2f}",
                        "Total Rate (%)": "{:.4f}",
                        "Period (yrs)": "{:.4f}",
                        "Coupon": "{:,.2f}",
                        "Principal": "{:,.2f}",
                        "Total Payment": "{:,.2f}",
                        "Disc Factor": "{:.6f}",
                        "PV": "{:,.2f}"
                    }), use_container_width=True, hide_index=True)
                
                with tab_cf_chart:
                    df_chart = df_cf.melt(id_vars=["End Date", "Type"],
                                         value_vars=["Total Payment", "PV"],
                                         var_name="Metric", value_name="Amount")
                    fig_cf = px.bar(df_chart, x="End Date", y="Amount", color="Metric",
                                   barmode="group", title=f"Projected Cash Flows: {frn_index}",
                                   hover_data=["Type"])
                    fig_cf.update_layout(template="plotly_dark", hovermode="x unified")
                    st.plotly_chart(fig_cf, use_container_width=True)
            
            st.markdown("### Risk Measures")
            r1, r2 = st.columns(2)
            r1.metric("DV01 (+1bp Rates ×10)", f"{dv01:,.2f}",
                     help="Change in Clean Price for 1bp parallel increase in rates, scaled by 10")
            r2.metric("CS01/DM01 (+1bp DM ×10)", f"{cs01:,.2f}",
                     help="Change in Clean Price for 1bp increase in DM, scaled by 10")
            
            st.markdown("#### Key-Rate DV01")
            kr_df = pd.DataFrame([{'Tenor': k, 'KR-DV01': v} for k, v in kr_dv01.items()])
            st.dataframe(kr_df.style.format({"KR-DV01": "{:,.2f}"}), use_container_width=True, hide_index=True)
    
    # -------------------------------------------------------------------------
    # TAB 4: ZARONIA Calculator
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Historical ZARONIA Compounding Calculator")
        
        col1, col2, col3 = st.columns(3)
        z_principal = col1.number_input("Principal", value=100_000_000.0, step=1_000_000.0, format="%.2f", key="z_prin")
        z_start = col2.date_input("Start Date", value=date(2026, 1, 1), key="z_start")
        z_end = col3.date_input("End Date", value=date.today() - timedelta(days=2), key="z_end")
        
        if st.button("Calculate Compounded ZARONIA", type="primary", key="btn_zar"):
            if df_zaronia is None:
                st.error("ZARONIA fixings file not found.")
            else:
                start_ql = calendar.adjust(to_ql_date(z_start))
                end_ql = calendar.adjust(to_ql_date(z_end))
                
                if start_ql >= end_ql:
                    st.error("Start Date must be before End Date.")
                else:
                    curr = start_ql
                    cum_idx = 1.0
                    results = []
                    
                    while curr < end_ql:
                        next_d = calendar.advance(curr, 1, ql.Days)
                        if next_d > end_ql:
                            next_d = end_ql
                        
                        ts = pd.Timestamp(curr.year(), curr.month(), curr.dayOfMonth())
                        rate = 0.0
                        source = "Missing"
                        
                        if ts in df_zaronia.index:
                            rate = df_zaronia.loc[ts, "ZARONIA"]
                            source = "ZARONIA"
                        else:
                            try:
                                idx_loc = df_zaronia.index.get_indexer([ts], method='ffill')[0]
                                if idx_loc != -1:
                                    rate = df_zaronia.iloc[idx_loc]["ZARONIA"]
                                    source = f"Filled ({df_zaronia.index[idx_loc].date()})"
                            except:
                                pass
                        
                        ndays = day_count.dayCount(curr, next_d)
                        dt = ndays / 365.0
                        interest_amt = (z_principal * cum_idx) * (rate / 100.0) * dt
                        cum_idx *= (1.0 + (rate / 100.0) * dt)
                        
                        results.append({
                            "Start Date": curr.ISO(),
                            "End Date": next_d.ISO(),
                            "Days": ndays,
                            "Rate (%)": rate,
                            "Source": source,
                            "Interest": interest_amt,
                            "Cumulative Index": cum_idx
                        })
                        curr = next_d
                    
                    df_res = pd.DataFrame(results)
                    if not df_res.empty:
                        total_interest = (z_principal * cum_idx) - z_principal
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Interest", f"{total_interest:,.2f}")
                        c2.metric("Final Amount", f"{z_principal * cum_idx:,.2f}")
                        c3.metric("Cumulative Index", f"{cum_idx:.8f}")
                        
                        st.dataframe(df_res.style.format({
                            "Rate (%)": "{:.4f}",
                            "Interest": "{:,.2f}",
                            "Cumulative Index": "{:.8f}"
                        }), use_container_width=True)
                        
                        fig_z = px.line(df_res, x="Start Date", y="Cumulative Index",
                                       title="ZARONIA Compounded Index")
                        fig_z.update_layout(template="plotly_dark")
                        st.plotly_chart(fig_z, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # TAB 5: Basis Analysis
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Basis Analysis: JIBAR vs ZARONIA")
        st.markdown("""
        **Cross-Curve Basis Analysis**
        
        Calculates the implied spread differential between JIBAR and ZARONIA curves.
        For each tenor, we determine what spread must be added to ZARONIA to achieve
        the same present value as JIBAR Flat (zero spread).
        """)
        
        basis_cache = load_basis_cache()
        
        col1, col2, col3, col4 = st.columns(4)
        basis_sett = col1.date_input("Settlement", value=evaluation_date + timedelta(days=3), key="basis_sett")
        basis_nom = col2.number_input("Notional", value=100.0, step=10.0, format="%.2f", key="basis_nom")
        basis_lb = col3.number_input("ZARONIA Lookback", value=5, step=1, key="basis_lb")
        use_cache = col4.checkbox("Use Cache", value=True, key="use_cache")
        
        cache_key = get_cache_key(basis_sett, basis_nom, basis_lb, zaronia_spread_bps)
        cached = basis_cache.get(cache_key)
        
        if use_cache and cached:
            st.info(f"📁 Cached results from: {cached.get('timestamp', 'Unknown')}")
            df_basis = pd.DataFrame(cached['results'])
            st.dataframe(df_basis.style.format({
                "Term (Y)": "{:.2f}",
                "Basis (bps)": "{:.2f}"
            }), use_container_width=True, hide_index=True)
        
        if st.button("Calculate Basis", type="primary", key="btn_basis"):
            basis_terms = [0.25, 0.5, 1, 2, 3, 5, 7, 10]
            basis_results = []
            
            zaronia_dict = get_lookup_dict(df_zaronia, 'ZARONIA')
            jibar_dict = get_lookup_dict(df_historical, 'JIBAR3M')
            
            with st.spinner("Calculating basis..."):
                for term in basis_terms:
                    mat = basis_sett + timedelta(days=int(term*365.25))
                    
                    # Price JIBAR Flat using ZARONIA discounting
                    pv_j_ois, _, clean_j, _ = price_frn(
                        basis_nom, 0.0, 0.0, basis_sett, mat,
                        jibar_curve, zaronia_curve, basis_sett,
                        day_count, calendar, 'JIBAR 3M',
                        zaronia_spread_bps, 0, df_historical, df_zaronia,
                        zaronia_dict, jibar_dict, return_df=False)
                    
                    # Solve for ZARONIA spread
                    try:
                        z_spread = solve_dm(
                            pv_j_ois, basis_nom, 0.0, basis_sett, mat,
                            build_zaronia_curve_daily(jibar_curve, zaronia_spread_bps, settlement, day_count),
                            zaronia_curve, basis_sett,
                            day_count, calendar, 'ZARONIA',
                            zaronia_spread_bps, basis_lb, df_historical, df_zaronia,
                            zaronia_dict, jibar_dict)
                        
                        basis_results.append({
                            "Term (Y)": term,
                            "Basis (bps)": z_spread
                        })
                    except Exception as e:
                        st.warning(f"Failed for term {term}Y: {e}")
                
                df_basis = pd.DataFrame(basis_results)
                
                # Cache results
                cache_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'results': basis_results
                }
                basis_cache[cache_key] = cache_entry
                save_basis_cache(basis_cache)
                
                st.dataframe(df_basis.style.format({"Term (Y)": "{:.2f}", "Basis (bps)": "{:.2f}"}),
                           use_container_width=True, hide_index=True)
                
                fig_basis = px.line(df_basis, x="Term (Y)", y="Basis (bps)", markers=True,
                                   title="Implied Basis: JIBAR Flat = ZARONIA + Spread")
                fig_basis.update_layout(template="plotly_dark")
                st.plotly_chart(fig_basis, use_container_width=True)
    
    # -------------------------------------------------------------------------
    # TAB 6: Portfolio Manager
    # -------------------------------------------------------------------------
    with tabs[5]:
        st.subheader("📊 Portfolio Manager & Analytics")
        
        portfolio_positions = load_portfolio()
        repo_trades = load_repo_trades()
        
        if not portfolio_positions:
            st.warning("No portfolio positions loaded.")
            
            # Still show add position form
            st.markdown("#### Add Position")
            with st.expander("➕ Add New Position", expanded=True):
                # ... keep existing add position code ...
                pass
        else:
            # Create comprehensive sub-tabs
            portfolio_tabs = st.tabs([
                "📊 Current Valuation",
                "💰 Yield Attribution", 
                "📈 NAV Index",
                "🏦 Counterparty Risk",
                "📉 Time Series",
                "🕰️ Time Travel",
                "✏️ Edit Portfolio"
            ])
            
            # TAB 1: Current Valuation
            with portfolio_tabs[0]:
                st.markdown("##### Current Portfolio Valuation")
                
                st.info("""
                **Portfolio Valuation Logic:**
                
                - **Clean Price:** Present value of all future cashflows (coupons + principal) discounted using JIBAR curve
                - **DV01 (Dollar Value of 1bp):** Change in portfolio value for 1bp parallel shift in JIBAR curve
                - **CS01 (Credit Spread 01):** Change in portfolio value for 1bp parallel shift in credit spreads
                - **Gearing:** Ratio of repo debt to portfolio notional (leverage multiplier)
                
                FRNs are valued using QuantLib with South African market conventions (ACT/365, Modified Following, Quarterly resets).
                """)
                
                df_summary, tot_clean, tot_dv01, tot_cs01, kr_tots = get_portfolio_summary(
                    portfolio_positions, jibar_curve, jibar_curve, settlement,
                    day_count, calendar, zaronia_spread_bps,
                    df_historical, df_zaronia, evaluation_date, rates)
                
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
                
                # Metrics
                total_repo_cash = sum(r.get('cash_amount', 0) for r in repo_trades 
                                     if r.get('direction') == 'borrow_cash')
                total_notional = sum(p.get('notional', 0) for p in portfolio_positions)
                gearing = total_repo_cash / total_notional if total_notional > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total MV", f"R{tot_clean:,.2f}")
                m2.metric("DV01", f"R{tot_dv01:,.2f}")
                m3.metric("CS01", f"R{tot_cs01:,.2f}")
                m4.metric("Gearing", f"{gearing:.2f}x")
            
            # TAB 2: Yield Attribution
            with portfolio_tabs[1]:
                st.info("""
                **Yield Attribution Framework:**
                
                This analysis shows how gearing amplifies returns through the spread pickup between FRN coupons and repo financing costs.
                
                **Key Concepts:**
                - **Gross Yield:** FRN coupon income / Portfolio notional (JIBAR + avg FRN spread)
                - **Repo Cost Rate:** Repo interest / Repo outstanding (JIBAR + repo spread)
                - **Spread Pickup:** FRN spread - Repo spread (typically 100-120 bps for this portfolio)
                - **Gearing Benefit:** Spread pickup × Gearing ratio
                - **Net Yield:** Gross yield + Gearing benefit (return on equity)
                
                **Example:** With 9x gearing and 120 bps spread pickup:
                - Base yield: 7.93% (JIBAR 6.63% + 130 bps FRN spread)
                - Gearing benefit: 120 bps × 9 = 10.8%
                - **Total return on equity: ~18.7%**
                """)
                
                if MODULES_LOADED:
                    render_yield_attribution(portfolio_positions, repo_trades, rates.get('JIBAR3M', 8.0))
                    st.markdown("---")
                    render_composition_over_time(portfolio_positions, repo_trades)
                else:
                    st.info("💡 Yield attribution module not loaded. Install enhancement modules.")
            
            # TAB 3: NAV Index
            with portfolio_tabs[2]:
                st.info("""
                **NAV (Net Asset Value) Calculation:**
                
                NAV tracks the true economic value of the portfolio, accounting for all operating cashflows.
                
                **Formula:**
                ```
                NAV = Seed Capital + Cumulative Operating Cashflows
                ```
                
                **Operating Cashflows (impact NAV):**
                - ✅ FRN coupon income (received)
                - ✅ Repo interest expense (paid)
                
                **Financing Cashflows (balance sheet only, NOT in NAV):**
                - ❌ Repo principal borrowed/repaid (liability movements)
                
                **Why This Matters:**
                Repo borrowing is NOT income - it's a liability. Only the interest spread affects P&L.
                The NAV index shows true portfolio performance, similar to a hedge fund NAV.
                """)
                
                if MODULES_LOADED:
                    render_nav_index(portfolio_positions, repo_trades)
                    
                    # Add inception-to-date analytics
                    st.markdown("---")
                    st.markdown("### 📊 Complete History Since Inception")
                    
                    render_inception_cashflows(portfolio_positions, repo_trades, rates.get('JIBAR3M', 8.0))
                    
                    st.markdown("---")
                    st.markdown("### 💰 Professional Settlement Account (Proper Accounting)")
                    
                    render_professional_settlement_account(
                        portfolio_positions, 
                        repo_trades, 
                        seed_capital=100_000_000,  # R100M seed capital
                        jibar_rate=rates.get('JIBAR3M', 6.63)
                    )
                    
                    st.markdown("---")
                    st.markdown("### 📊 Daily Historical Analytics (Every Day Since Inception)")
                    
                    render_daily_historical_analytics(portfolio_positions, repo_trades, df_historical)
                    
                    st.markdown("---")
                    
                    render_risk_evolution(portfolio_positions)
                else:
                    st.info("💡 NAV index module not loaded. Install enhancement modules.")
            
            # TAB 4: Counterparty Risk
            with portfolio_tabs[3]:
                if MODULES_LOADED:
                    render_counterparty_risk_manager(portfolio_positions, evaluation_date)
                else:
                    st.info("💡 Counterparty risk module not loaded. Install enhancement modules.")
            
            # TAB 5: Time Series
            with portfolio_tabs[4]:
                st.info("""
                **Portfolio Time Series Analysis:**
                
                Track how the portfolio has evolved over time:
                
                - **Notional Evolution:** See portfolio growth from seed capital through gearing
                - **Gearing History:** Monitor leverage ratio over time (target: ~9x)
                - **Composition Changes:** Track counterparty exposure shifts
                - **Risk Metrics:** DV01/CS01 evolution as portfolio matures
                
                **Key Insight:** A well-managed geared portfolio maintains stable gearing while rotating positions
                to optimize spread pickup and manage concentration risk.
                """)
                
                if MODULES_LOADED:
                    render_portfolio_time_series(portfolio_positions, repo_trades)
                else:
                    st.info("💡 Portfolio time series module not loaded.")
            
            # TAB 6: Time Travel
            with portfolio_tabs[5]:
                st.markdown("##### 🕰️ Time Travel - Historical Portfolio Analysis")
                
                st.info("""
                **Time Travel Functionality:**
                
                Select any historical date to:
                - Value portfolio as of that date
                - See active positions on that date
                - View repo trades active on that date
                - Calculate gearing and metrics for that date
                """)
                
                # Get inception date
                all_dates = []
                for pos in portfolio_positions:
                    start = pos.get('start_date')
                    if isinstance(start, str):
                        start = datetime.strptime(start, '%Y-%m-%d').date()
                    all_dates.append(start)
                
                inception_date = min(all_dates) if all_dates else date.today() - timedelta(days=365)
                
                # Date selector
                col1, col2 = st.columns(2)
                with col1:
                    selected_date = st.date_input(
                        "Select Historical Date",
                        value=date.today() - timedelta(days=30),
                        min_value=inception_date,
                        max_value=date.today(),
                        key="time_travel_date"
                    )
                
                with col2:
                    st.metric("Days from Inception", (selected_date - inception_date).days)
                
                st.markdown("---")
                
                # Calculate portfolio state on selected date
                st.markdown(f"##### Portfolio State on {selected_date.strftime('%Y-%m-%d')}")
                
                # Active positions on this date
                active_positions = []
                for pos in portfolio_positions:
                    start = pos.get('start_date')
                    maturity = pos.get('maturity')
                    
                    if isinstance(start, str):
                        start = datetime.strptime(start, '%Y-%m-%d').date()
                    if isinstance(maturity, str):
                        maturity = datetime.strptime(maturity, '%Y-%m-%d').date()
                    
                    if start <= selected_date <= maturity:
                        active_positions.append(pos)
                
                # Active repos on this date
                active_repos = []
                for repo in repo_trades:
                    spot = repo['spot_date'] if isinstance(repo['spot_date'], date) else datetime.strptime(repo['spot_date'], '%Y-%m-%d').date()
                    end = repo['end_date'] if isinstance(repo['end_date'], date) else datetime.strptime(repo['end_date'], '%Y-%m-%d').date()
                    
                    if spot <= selected_date <= end:
                        active_repos.append(repo)
                
                # Metrics
                total_notional = sum(p.get('notional', 0) for p in active_positions)
                total_repo = sum(r.get('cash_amount', 0) for r in active_repos if r.get('direction') == 'borrow_cash')
                gearing = total_repo / total_notional if total_notional > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Active Positions", len(active_positions))
                m2.metric("Total Notional", f"R{total_notional/1e9:.2f}B")
                m3.metric("Active Repos", len(active_repos))
                m4.metric("Gearing", f"{gearing:.2f}x")
                
                # Show active positions
                if active_positions:
                    st.markdown("###### Active Positions")
                    pos_data = []
                    for pos in active_positions:
                        pos_data.append({
                            'Name': pos.get('name', 'Unknown'),
                            'Counterparty': pos.get('counterparty', 'Unknown'),
                            'Notional': f"R{pos.get('notional', 0):,.2f}",
                            'Spread (bps)': pos.get('issue_spread', 0),
                            'Maturity': pos.get('maturity')
                        })
                    st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)
                
                # Show active repos
                if active_repos:
                    st.markdown("###### Active Repos")
                    repo_data = []
                    for repo in active_repos:
                        repo_data.append({
                            'ID': repo.get('id', 'Unknown'),
                            'Cash': f"R{repo.get('cash_amount', 0):,.2f}",
                            'Spread (bps)': repo.get('repo_spread_bps', 0),
                            'End Date': repo.get('end_date')
                        })
                    st.dataframe(pd.DataFrame(repo_data), use_container_width=True, hide_index=True)
            
            
                
                # Advanced Time Travel Features
                if MODULES_LOADED:
                    st.markdown("---")
                    st.markdown("### 📊 Advanced Historical Analysis")
                    
                    # Complete settlement account
                    render_complete_historical_settlement_account(portfolio_positions, repo_trades)
                    
                    st.markdown("---")
                    
                    # 3D portfolio surfaces
                    render_3d_portfolio_surfaces(portfolio_positions, repo_trades, df_historical, df_zaronia)
            
            # TAB 7: Edit Portfolio
            with portfolio_tabs[6]:
                if MODULES_LOADED:
                    render_easy_portfolio_editor(portfolio_positions, save_portfolio)
                else:
                    st.info("💡 Portfolio editor module not loaded. Install enhancement modules.")
                    st.markdown("##### Manual JSON Editing")
                    st.json({"positions": portfolio_positions})
    
    # TAB 7: Repo Trades
    # -------------------------------------------------------------------------
    with tabs[6]:
        st.subheader("💼 Repo Trade Management & Analytics")
        
        repo_trades = load_repo_trades()
        portfolio_positions = load_portfolio()
        
        # Create comprehensive sub-tabs
        repo_subtabs = st.tabs([
            "📊 Dashboard",
            "📋 Master Table",
            "⚠️ Funding Risk",
            "✏️ Edit Trades",
            "➕ Add Trade"
        ])
        
        # TAB 1: Dashboard
        with repo_subtabs[0]:
            st.markdown("##### Repo Dashboard")
            
            if repo_trades:
                total_repo = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'borrow_cash')
                total_reverse = sum(r.get('cash_amount', 0) for r in repo_trades if r.get('direction') == 'lend_cash')
                net_financing = total_repo - total_reverse
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Repo (Borrow)", f"R{total_repo:,.2f}")
                m2.metric("Total Reverse (Lend)", f"R{total_reverse:,.2f}")
                m3.metric("Net Repo Financing", f"R{net_financing:,.2f}")
                
                # Add Asset/Repo Visualization
                st.markdown("---")
                if MODULES_LOADED:
                    render_asset_repo_visualization(portfolio_positions, repo_trades)
                
                st.markdown("---")
                st.markdown("##### Recent Repo Trades")
                recent_repos = sorted(repo_trades, key=lambda x: x.get('trade_date', date.today()), reverse=True)[:10]
                for repo in recent_repos:
                    with st.expander(f"Repo: {repo.get('id', 'Unknown')} - R{repo.get('cash_amount', 0)/1e6:.1f}M"):
                        st.json(repo)
            else:
                st.info("No repo trades.")
        
        
                
                # Historical Analytics
                if MODULES_LOADED:
                    st.markdown("---")
                    st.markdown("### 📈 Historical Repo Analytics")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        hist_start = st.date_input("From", value=date.today() - timedelta(days=180), key="repo_hist_start")
                    with col2:
                        hist_end = st.date_input("To", value=date.today(), key="repo_hist_end")
                    
                    render_repo_outstanding_chart(repo_trades, hist_start, hist_end)
                    
                    st.markdown("---")
                    
                    render_gearing_evolution_chart(portfolio_positions, repo_trades, hist_start, hist_end)
                    
                    st.markdown("---")
                    
                    render_cashflow_waterfall(portfolio_positions, repo_trades, hist_start, hist_end, rates.get('JIBAR3M', 8.0))
                    
                    st.markdown("---")
                    
                    render_yield_evolution(portfolio_positions, repo_trades, hist_start, hist_end, rates.get('JIBAR3M', 8.0))
            
            # TAB 2: Master Table
        with repo_subtabs[1]:
            if MODULES_LOADED:
                render_repo_master_table_and_summary(repo_trades, rates.get('JIBAR3M', 8.0))
            else:
                st.info("💡 Master table module not loaded.")
                if repo_trades:
                    st.dataframe(pd.DataFrame(repo_trades), use_container_width=True)
        
        # TAB 3: Funding Risk
        with repo_subtabs[2]:
            if MODULES_LOADED:
                render_funding_risk_analysis(portfolio_positions, repo_trades)
            else:
                st.info("💡 Funding risk analysis module not loaded.")
        
        # TAB 4: Edit Trades
        with repo_subtabs[3]:
            if MODULES_LOADED:
                render_easy_repo_editor(repo_trades, portfolio_positions, save_repo_trades)
            else:
                st.info("💡 Repo editor module not loaded.")
                st.markdown("##### Manual JSON Editing")
                st.json({"trades": repo_trades})
        
        # TAB 5: Add Trade
        with repo_subtabs[4]:
            st.markdown("##### Add New Repo Trade")
            with st.expander("➕ Add New Repo Trade", expanded=True):
                col1, col2 = st.columns(2)
                repo_id = col1.text_input("Repo ID", value=f"REPO_{uuid.uuid4().hex[:8]}", key="repo_id")
                repo_dir = col2.selectbox("Direction", ["borrow_cash", "lend_cash"], key="repo_dir")
                
                col3, col4 = st.columns(2)
                repo_trade_dt = col3.date_input("Trade Date", value=evaluation_date, key="repo_trade_dt")
                repo_spot = col4.date_input("Spot Date", value=evaluation_date + timedelta(days=3), key="repo_spot")
                
                col5, col6 = st.columns(2)
                repo_end = col5.date_input("End Date", value=evaluation_date + timedelta(days=30), key="repo_end")
                repo_cash = col6.number_input("Cash Amount", value=100_000_000.0, step=1000000.0, key="repo_cash")
                
                repo_spread = st.number_input("Repo Spread (bps)", value=10.0, step=5.0, key="repo_spread")
                
                repo_collat = st.selectbox("Collateral Position", 
                                          ["None"] + [p.get('id', '') for p in portfolio_positions],
                                          key="repo_collat")
                repo_cpn_to_lender = st.checkbox("Coupon to Cash Lender", value=False, key="repo_cpn")
                
                if st.button("Add Repo Trade", key="btn_add_repo"):
                    repo_data = {
                        'id': repo_id,
                        'trade_date': repo_trade_dt,
                        'spot_date': repo_spot,
                        'end_date': repo_end,
                        'cash_amount': repo_cash,
                        'repo_spread_bps': repo_spread,
                        'direction': repo_dir,
                        'collateral_id': repo_collat if repo_collat != "None" else None,
                        'coupon_to_lender': repo_cpn_to_lender
                    }
                    trades = load_repo_trades()
                    trades.append(repo_data)
                    save_repo_trades(trades)
                    st.success(f"✅ Added repo trade {repo_id}")
                    st.rerun()
    
    # TAB 8: NCD Pricing
    # -------------------------------------------------------------------------
    with tabs[7]:
        st.subheader("NCD Pricing Matrix")
        st.markdown("**Bank NCD Spreads over JIBAR3M (bps)**")
        
        ncd_data = load_ncd_pricing()
        
        # Get current date or latest available
        current_date_str = ncd_data.get('current_date', date.today().isoformat())
        
        # Display pricing date with date picker
        col1, col2 = st.columns([3, 1])
        with col1:
            # Date picker for historical pricing
            historical_pricing = ncd_data.get('historical_pricing', {})
            available_dates = sorted(historical_pricing.keys()) if historical_pricing else [current_date_str]
            
            if available_dates:
                selected_date_str = st.selectbox(
                    "Select Pricing Date",
                    options=available_dates,
                    index=len(available_dates) - 1,  # Default to latest
                    key="ncd_date_selector"
                )
            else:
                selected_date_str = current_date_str
                st.info(f"📅 Pricing Date: {selected_date_str}")
        
        with col2:
            st.metric("Historical Days", f"{len(available_dates)}")
        
        # Get pricing for selected date
        terms = ncd_data.get('terms', ["1Y", "1.5Y", "2Y", "3Y", "4Y", "5Y"])
        banks = ncd_data.get('banks', ["ABSA", "Standard Bank", "Nedbank", "FirstRand", "Investec", "Capitec"])
        
        # Get pricing for selected date
        if historical_pricing and selected_date_str in historical_pricing:
            date_pricing = historical_pricing[selected_date_str]
        else:
            # Fallback to default
            date_pricing = {bank: {term: 50 + i*10 for i, term in enumerate(terms)} for bank in banks}
        
        # Build DataFrame for editing
        pricing_df = pd.DataFrame({
            bank: [date_pricing.get(bank, {}).get(term, 0) for term in terms]
            for bank in banks
        }, index=terms)
        
        st.markdown("##### Edit NCD Spreads (bps)")
        edited_pricing = st.data_editor(
            pricing_df,
            use_container_width=True,
            num_rows="fixed",
            key="ncd_pricing_editor"
        )
        
        if st.button("💾 Save NCD Pricing for Selected Date", type="primary", key="btn_save_ncd"):
            # Update historical pricing for selected date
            if 'historical_pricing' not in ncd_data:
                ncd_data['historical_pricing'] = {}
            
            ncd_data['historical_pricing'][selected_date_str] = {
                bank: {term: float(edited_pricing.loc[term, bank]) for term in terms}
                for bank in banks
            }
            ncd_data['current_date'] = selected_date_str
            save_ncd_pricing(ncd_data)
            st.success(f"NCD pricing saved for {selected_date_str}!")
            st.rerun()
        
        # Visualizations
        st.markdown("---")
        st.markdown("##### NCD Spread Term Structure (Selected Date)")
        
        # Prepare data for plotting (selected date)
        plot_data = []
        for bank in banks:
            for term in terms:
                term_years = float(term.replace('Y', ''))
                spread = date_pricing.get(bank, {}).get(term, 0)
                plot_data.append({
                    'Bank': bank,
                    'Term (Years)': term_years,
                    'Spread (bps)': spread
                })
        
        df_plot = pd.DataFrame(plot_data)
        
        # Line chart of term structures
        fig_ncd = px.line(df_plot, x='Term (Years)', y='Spread (bps)', color='Bank',
                         title='NCD Spread Term Structure by Bank',
                         markers=True)
        fig_ncd.update_layout(template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_ncd, use_container_width=True)
        
        # Heatmap
        fig_heat = px.imshow(edited_pricing.T,
                            labels=dict(x="Term", y="Bank", color="Spread (bps)"),
                            x=terms,
                            y=banks,
                            title="NCD Pricing Heatmap",
                            color_continuous_scale="RdYlGn_r",
                            aspect="auto")
        fig_heat.update_layout(template="plotly_dark")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # Statistics
        st.markdown("##### Market Statistics (Selected Date)")
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        
        with stats_col1:
            avg_1y = df_plot[df_plot['Term (Years)'] == 1.0]['Spread (bps)'].mean()
            st.metric("Avg 1Y Spread", f"{avg_1y:.1f} bps")
        
        with stats_col2:
            avg_5y = df_plot[df_plot['Term (Years)'] == 5.0]['Spread (bps)'].mean()
            st.metric("Avg 5Y Spread", f"{avg_5y:.1f} bps")
        
        with stats_col3:
            curve_steepness = avg_5y - avg_1y
            st.metric("Curve Steepness (5Y-1Y)", f"{curve_steepness:.1f} bps")
        
        # Historical time-series analysis
        if historical_pricing and len(historical_pricing) > 1:
            st.markdown("---")
            st.markdown("##### Historical NCD Spread Evolution (2 Years)")
            
            # Select bank and term for time-series
            ts_col1, ts_col2 = st.columns(2)
            with ts_col1:
                selected_bank = st.selectbox("Select Bank", banks, key="ts_bank")
            with ts_col2:
                selected_term = st.selectbox("Select Term", terms, key="ts_term")
            
            # Build time-series data
            ts_data = []
            for date_str in sorted(historical_pricing.keys()):
                spread = historical_pricing[date_str].get(selected_bank, {}).get(selected_term, 0)
                ts_data.append({
                    'Date': date_str,
                    'Spread (bps)': spread
                })
            
            df_ts = pd.DataFrame(ts_data)
            df_ts['Date'] = pd.to_datetime(df_ts['Date'])
            
            # Time-series chart
            fig_ts = px.line(df_ts, x='Date', y='Spread (bps)',
                            title=f'{selected_bank} {selected_term} NCD Spread History',
                            markers=True)
            fig_ts.update_layout(template='plotly_dark', hovermode='x unified', height=400)
            st.plotly_chart(fig_ts, use_container_width=True)
            
            # All banks comparison for selected term
            st.markdown(f"##### All Banks - {selected_term} Spread History")
            
            ts_all_banks = []
            for date_str in sorted(historical_pricing.keys()):
                for bank in banks:
                    spread = historical_pricing[date_str].get(bank, {}).get(selected_term, 0)
                    ts_all_banks.append({
                        'Date': date_str,
                        'Bank': bank,
                        'Spread (bps)': spread
                    })
            
            df_ts_all = pd.DataFrame(ts_all_banks)
            df_ts_all['Date'] = pd.to_datetime(df_ts_all['Date'])
            
            fig_ts_all = px.line(df_ts_all, x='Date', y='Spread (bps)', color='Bank',
                                title=f'All Banks {selected_term} NCD Spreads (2 Year History)',
                                markers=False)
            fig_ts_all.update_layout(template='plotly_dark', hovermode='x unified', height=500)
            st.plotly_chart(fig_ts_all, use_container_width=True)
            
            # Summary statistics
            st.markdown("##### Historical Statistics")
            hist_col1, hist_col2, hist_col3, hist_col4 = st.columns(4)
            
            current_spread = df_ts['Spread (bps)'].iloc[-1] if not df_ts.empty else 0
            avg_spread = df_ts['Spread (bps)'].mean()
            max_spread = df_ts['Spread (bps)'].max()
            min_spread = df_ts['Spread (bps)'].min()
            
            hist_col1.metric("Current", f"{current_spread:.1f} bps")
            hist_col2.metric("2Y Average", f"{avg_spread:.1f} bps", 
                           delta=f"{current_spread - avg_spread:.1f} bps")
            hist_col3.metric("2Y High", f"{max_spread:.1f} bps")
            hist_col4.metric("2Y Low", f"{min_spread:.1f} bps")
    
    # -------------------------------------------------------------------------
    # TAB 9: Curve Diagnostics
    # -------------------------------------------------------------------------
    with tabs[8]:
        st.subheader("Curve Diagnostics")
        st.markdown("Par instrument repricing errors (Market vs Implied)")
        
        if diagnostics:
            df_diag = pd.DataFrame(diagnostics)
            st.dataframe(df_diag.style.format({
                "Market (%)": "{:.4f}",
                "Implied (%)": "{:.4f}",
                "Error (bps)": "{:.2f}"
            }), use_container_width=True, hide_index=True)
            
            fig_diag = px.bar(df_diag, x="Instrument", y="Error (bps)",
                             title="Par Instrument Repricing Errors")
            fig_diag.update_layout(template="plotly_dark")
            st.plotly_chart(fig_diag, use_container_width=True)
        else:
            st.info("No diagnostics available.")

except Exception as e:
    st.error(f"Application Error: {str(e)}\n\n{traceback.format_exc()}")
