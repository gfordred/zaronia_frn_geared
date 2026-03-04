# Cashflow Accounting Fix & Portfolio Regeneration

## Problem Identified

The cumulative cashflow chart showed a massive spike because **repo principal proceeds were incorrectly treated as operating income**, inflating the NAV calculation.

### What Was Wrong

```python
# Old code - INCORRECT
if direction == 'borrow_cash':
    cf = cash_amount  # Repo proceeds treated as positive cashflow
    total_cashflow += cf  # Added to cumulative cashflow
```

**Issue:** When you borrow R1B via repos, this was shown as +R1B income, making it look like the portfolio was generating massive profits. This is fundamentally wrong.

## Accounting Best Practice

### Three Types of Cashflows

1. **OPERATING CASHFLOWS** (impact P&L and NAV):
   - ✅ FRN coupon income (received)
   - ✅ Repo interest expense (paid on borrowed funds)
   - ✅ Repo interest income (earned on lent funds)

2. **FINANCING CASHFLOWS** (balance sheet only, NOT in NAV):
   - ❌ Repo principal borrowed (liability increase)
   - ❌ Repo principal repaid (liability decrease)
   - ❌ Repo principal lent (asset increase)
   - ❌ Repo principal returned (asset decrease)

3. **INVESTMENT CASHFLOWS**:
   - Initial capital injection
   - FRN purchases/sales

### Correct NAV Formula

```
NAV = Seed Capital + Cumulative Operating Cashflows

NOT: NAV = Seed Capital + All Cashflows (including financing)
```

## Solution Implemented

### 1. New Settlement Account Module (`settlement_account_proper.py`)

Properly separates cashflows:

```python
# Near leg - Financing (NOT operating income)
if direction == 'borrow_cash':
    daily_ledger.append({
        'Type': 'Repo Near Leg',
        'Category': 'Financing',  # Balance sheet
        'Operating_CF': 0,        # NOT operating income
        'Financing_CF': cash_amount,
        'Total_CF': cash_amount
    })

# Far leg - Split into principal (financing) and interest (operating)
# Principal repayment
daily_ledger.append({
    'Type': 'Repo Far Leg - Principal',
    'Category': 'Financing',
    'Operating_CF': 0,
    'Financing_CF': -cash_amount,
    'Total_CF': -cash_amount
})

# Interest expense (THIS impacts NAV)
daily_ledger.append({
    'Type': 'Repo Interest Expense',
    'Category': 'Operating',
    'Operating_CF': -interest,  # Operating expense
    'Financing_CF': 0,
    'Total_CF': -interest
})
```

### 2. Portfolio Regeneration with Seed Capital

**New Structure:**
- **Seed Capital:** R100M (equity injection at inception)
- **Seed Positions:** 2 government bonds totaling R100M
- **Gearing Strategy:**
  1. Repo seed positions → raise ~R90M
  2. Buy more FRNs with repo proceeds
  3. Repo those FRNs → raise more cash
  4. Continue until 9x gearing achieved

**Final Portfolio:**
- Total Notional: R1,000,000,000
- Active Repo Debt: R894,724,995
- **Actual Gearing: 8.95x** ✅
- Equity: R100,000,000

### 3. Realistic Repo Structure

- 410 repo trades over time (rolling repos)
- 24 active repos at any given time
- Average repo term: 60-90 days
- Repos roll over to maintain ~R900M outstanding
- Spread: 10 bps over JIBAR

## Impact on Charts

### Before Fix
- Cumulative cashflow spiked to R35B+ (incorrect)
- Included all repo borrowings as "income"
- NAV calculation was meaningless

### After Fix
- **Operating Cashflow:** Only FRN coupons and repo interest
- **NAV Evolution:** Seed capital + operating cashflows
- **Cash Balance:** Separate view showing all cashflows (for liquidity tracking)

## Files Created

1. **`settlement_account_proper.py`** - Professional accounting module
2. **`regenerate_9x_gearing_final.py`** - Portfolio regeneration script
3. **`portfolio.json`** - New portfolio (24 positions, R1B notional)
4. **`repo_trades.json`** - New repos (410 trades, 8.95x gearing)

## How to Use

### Regenerate Portfolio
```bash
python regenerate_9x_gearing_final.py
```

### View Proper Settlement Account
The new module provides:
- Daily cashflows by category (Operating/Financing/Investment)
- NAV evolution (operating cashflows only)
- Cash balance (all cashflows for liquidity)
- Detailed transaction ledger
- Category breakdown

## Key Metrics (New Portfolio)

| Metric | Value |
|--------|-------|
| Seed Capital | R100,000,000 |
| Total Portfolio | R1,000,000,000 |
| Active Repos | R894,724,995 |
| Gearing | 8.95x |
| Positions | 24 |
| Active Repo Trades | 24 |

### Counterparty Breakdown
- Standard Bank: 24.4% (R243.8M)
- Nedbank: 21.7% (R217.5M)
- FirstRand: 16.1% (R160.8M)
- ABSA: 15.6% (R156.0M)
- Investec: 12.2% (R121.9M)
- Republic of SA: 10.0% (R100.0M)

## Expected NAV Evolution

With proper accounting:

**Year 1:**
- FRN Income: R1B × 7.93% = R79.3M
- Repo Interest: R900M × 6.73% = R60.6M
- Net Operating CF: R18.7M
- **NAV: R118.7M** (18.7% return on R100M equity)

This is realistic for a 9x geared portfolio with 120 bps spread pickup!

## Explanation of Spike (Old Chart)

The spike occurred because:
1. Multiple repos matured on same day
2. Repo proceeds (R1B+) were treated as income
3. Cumulative cashflow jumped from R10B to R35B
4. This was **completely wrong** - repo borrowing is not income!

**Correct view:** Only interest payments affect NAV, not principal movements.
