"""
Test FRN Pricing Function
==========================

Tests the price_frn function to verify it's working correctly.
With DM = Issue Spread, FRNs should price at ~100 (par).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import date, timedelta
import QuantLib as ql
import pandas as pd

# Import pricing function from app
from app import (
    price_frn, 
    build_jibar_curve,
    to_ql_date,
    load_json_file
)

def test_simple_frn_pricing():
    """
    Test FRN pricing with DM = Issue Spread
    Should get price ~100 (par)
    """
    
    print("=" * 70)
    print("FRN PRICING TEST")
    print("=" * 70)
    
    # Load rates
    rates = load_json_file("rates.json", {})
    print(f"\n1. Rates loaded: {rates}")
    
    # Build JIBAR curve
    eval_date = date.today()
    jibar_curve, settlement, day_count = build_jibar_curve(eval_date, rates)
    
    print(f"\n2. JIBAR Curve built:")
    print(f"   Reference date: {jibar_curve.referenceDate()}")
    print(f"   Settlement: {settlement}")
    
    # Test rates at various tenors
    print(f"\n3. JIBAR Curve Rates:")
    for tenor_years in [0.25, 0.5, 1, 2, 3, 5]:
        tenor_date = settlement + timedelta(days=int(tenor_years * 365))
        tenor_ql = to_ql_date(tenor_date)
        rate = jibar_curve.zeroRate(tenor_ql, day_count, ql.Compounded, ql.Annual).rate()
        print(f"   {tenor_years}Y: {rate*100:.4f}%")
    
    # Test simple FRN
    print(f"\n4. Test FRN Pricing:")
    print(f"   Notional: R100M")
    print(f"   Issue Spread: 120 bps")
    print(f"   DM: 120 bps (same as issue spread)")
    print(f"   Start: {settlement}")
    print(f"   Maturity: 2 years")
    
    notional = 100_000_000
    issue_spread = 120  # bps
    dm = 120  # bps - SAME as issue spread
    start = settlement
    maturity = settlement + timedelta(days=365*2)
    
    calendar = ql.SouthAfrica()
    
    # Load historical data
    df_hist = pd.read_csv("jibar_historical.csv", parse_dates=['Date'], index_col='Date')
    df_zaronia = pd.read_csv("zaronia_fixings.csv", parse_dates=['Date'], index_col='Date')
    
    # Price the FRN
    dirty, accrued, clean, df = price_frn(
        notional, issue_spread, dm,
        start, maturity,
        jibar_curve, jibar_curve, settlement,
        day_count, calendar, 'JIBAR 3M',
        0.0, 0,
        df_hist, df_zaronia, None, None,
        return_df=True
    )
    
    print(f"\n5. Pricing Results:")
    print(f"   Dirty Price: R{dirty:,.2f}")
    print(f"   Accrued: R{accrued:,.2f}")
    print(f"   Clean Price: R{clean:,.2f}")
    print(f"   Price as % of Notional: {clean/notional*100:.4f}%")
    
    print(f"\n6. Cashflow Schedule:")
    if df is not None and not df.empty:
        print(df.to_string())
    
    # Expected result
    expected_price_pct = 100.0
    actual_price_pct = clean / notional * 100
    difference = actual_price_pct - expected_price_pct
    
    print(f"\n7. Analysis:")
    print(f"   Expected price: ~{expected_price_pct:.2f}% (par)")
    print(f"   Actual price: {actual_price_pct:.4f}%")
    print(f"   Difference: {difference:+.4f}%")
    
    if abs(difference) < 1.0:
        print(f"   ✓ PASS - Price is within 1% of par")
    else:
        print(f"   ✗ FAIL - Price is {abs(difference):.2f}% away from par")
        print(f"   This suggests a pricing error!")
    
    print("\n" + "=" * 70)
    
    return actual_price_pct, difference


def test_portfolio_positions():
    """
    Test actual portfolio positions
    """
    
    print("\n" + "=" * 70)
    print("PORTFOLIO POSITIONS TEST")
    print("=" * 70)
    
    # Load portfolio
    import json
    with open('portfolio_positions.json', 'r') as f:
        positions = json.load(f)
    
    # Load rates
    rates = load_json_file("rates.json", {})
    
    # Build curve
    eval_date = date.today()
    jibar_curve, settlement, day_count = build_jibar_curve(eval_date, rates)
    calendar = ql.SouthAfrica()
    
    # Load historical data
    df_hist = pd.read_csv("jibar_historical.csv", parse_dates=['Date'], index_col='Date')
    df_zaronia = pd.read_csv("zaronia_fixings.csv", parse_dates=['Date'], index_col='Date')
    
    print(f"\nTesting {len(positions)} positions:")
    print(f"{'Position':<25} {'Notional':<15} {'Spread':<10} {'DM':<10} {'Price %':<12} {'Status'}")
    print("-" * 90)
    
    total_notional = 0
    total_mv = 0
    
    for pos in positions:
        notional = pos['notional']
        issue_spread = pos['issue_spread']
        dm = pos['dm']
        start = date.fromisoformat(pos['start_date'])
        maturity = date.fromisoformat(pos['maturity'])
        name = pos['name']
        
        try:
            dirty, accrued, clean, _ = price_frn(
                notional, issue_spread, dm,
                start, maturity,
                jibar_curve, jibar_curve, settlement,
                day_count, calendar, 'JIBAR 3M',
                0.0, 0,
                df_hist, df_zaronia, None, None,
                return_df=False
            )
            
            price_pct = clean / notional * 100
            status = "✓ OK" if price_pct > 95 else "✗ LOW"
            
            print(f"{name:<25} R{notional/1e6:>6.0f}M {issue_spread:>6} bps {dm:>6} bps {price_pct:>10.4f}% {status}")
            
            total_notional += notional
            total_mv += clean
            
        except Exception as e:
            print(f"{name:<25} R{notional/1e6:>6.0f}M {issue_spread:>6} bps {dm:>6} bps {'ERROR':<12} ✗ {str(e)[:30]}")
    
    print("-" * 90)
    print(f"{'TOTAL':<25} R{total_notional/1e6:>6.0f}M {'':<10} {'':<10} {total_mv/total_notional*100:>10.4f}%")
    
    mtm_loss = total_mv - total_notional
    mtm_pct = mtm_loss / total_notional * 100
    
    print(f"\nPortfolio Summary:")
    print(f"  Total Notional: R{total_notional/1e6:.1f}M")
    print(f"  Total MV: R{total_mv/1e6:.1f}M")
    print(f"  MTM P&L: R{mtm_loss/1e6:.1f}M ({mtm_pct:+.2f}%)")
    
    if mtm_pct < -5:
        print(f"  ⚠️  WARNING: Portfolio showing {abs(mtm_pct):.1f}% loss!")
        print(f"  This is unexpected if DM = Issue Spread")
    
    print("=" * 70)


if __name__ == "__main__":
    # Test 1: Simple FRN
    price_pct, diff = test_simple_frn_pricing()
    
    # Test 2: Actual portfolio
    test_portfolio_positions()
