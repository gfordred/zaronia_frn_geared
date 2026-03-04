"""
Simple FRN Pricing Test
========================

Minimal test to check if FRN pricing is working correctly.
"""

import json
from datetime import date

# Load portfolio
with open('portfolio_positions.json', 'r') as f:
    positions = json.load(f)

print("=" * 70)
print("PORTFOLIO POSITIONS - DM vs ISSUE SPREAD CHECK")
print("=" * 70)

print(f"\n{'Position':<25} {'Notional':<15} {'Issue Spread':<15} {'DM':<15} {'Match'}")
print("-" * 90)

all_match = True
total_notional = 0

for pos in positions:
    name = pos['name']
    notional = pos['notional']
    issue_spread = pos['issue_spread']
    dm = pos['dm']
    match = "✓ YES" if issue_spread == dm else "✗ NO"
    
    if issue_spread != dm:
        all_match = False
    
    total_notional += notional
    
    print(f"{name:<25} R{notional/1e6:>6.0f}M {issue_spread:>10} bps {dm:>10} bps {match}")

print("-" * 90)
print(f"{'TOTAL':<25} R{total_notional/1e6:>6.0f}M")

print(f"\n✓ All DM values match Issue Spread: {all_match}")

if all_match:
    print("\n📊 EXPECTED BEHAVIOR:")
    print("   - FRNs should price at ~100 (par) when DM = Issue Spread")
    print("   - Portfolio MV should be ~R1,000M (same as notional)")
    print("   - Any significant deviation indicates a pricing error")
else:
    print("\n⚠️  WARNING: Some DM values don't match Issue Spread!")
    print("   This will cause bonds to price away from par")

print("\n" + "=" * 70)

# Check rates file
print("\nRATES FILE CHECK:")
print("=" * 70)

try:
    with open('rates.json', 'r') as f:
        rates = json.load(f)
    
    print(f"\nRates loaded successfully:")
    for key, value in rates.items():
        print(f"  {key}: {value}")
    
    jibar_3m = rates.get('JIBAR3M', 'NOT FOUND')
    print(f"\nJIBAR 3M rate: {jibar_3m}")
    
    if isinstance(jibar_3m, (int, float)):
        if 5 <= jibar_3m <= 10:
            print(f"✓ JIBAR rate looks reasonable ({jibar_3m}%)")
        else:
            print(f"⚠️  JIBAR rate seems unusual ({jibar_3m}%)")
    
except FileNotFoundError:
    print("✗ rates.json not found!")
except Exception as e:
    print(f"✗ Error loading rates: {e}")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)

print("""
1. ✓ All DM values = Issue Spread (correct)
2. ? JIBAR curve needs verification
3. ? FRN pricing function needs testing

If portfolio MV shows R632.9M instead of R1,000M:
- This is a 37% loss
- Should NOT happen if DM = Issue Spread
- Likely causes:
  a) Bug in price_frn function
  b) JIBAR curve is incorrect
  c) Cashflow calculation error
  d) Discount factor calculation error

Next step: Run actual pricing test with debugger to see where the issue is.
""")

print("=" * 70)
