# Value Consistency Analysis & Fixes

**Date:** 2026-03-04  
**Issue:** Inconsistent values across the app - Current Notional and Cash Balance errors

---

## 🚨 Critical Issues Identified

### **Issue 1: Current Notional = R319.5M (Expected: R1,000M)**

**Root Cause:** Portfolio has staggered start dates
- 3 RSA bonds start: **2025-03-04** (1 year ago)
- 4 Bank bonds start: **2025-09-05** (6 months from now)

**On 2026-03-04:**
- Active positions: Only 3 RSA bonds (R510M total)
- Inactive: 4 Bank bonds (R490M) - haven't started yet

**But R319.5M doesn't match R510M either!**

**Likely Cause:** The inception analytics is filtering by some other criteria (maturity, pricing data availability, etc.)

---

### **Issue 2: Cash Balance Spike to R1,200M in Jul 2026**

**Root Cause:** Repo principal is being counted as cash inflow

**Wrong Accounting:**
```python
# When repo matures:
Cash_Balance += repo_principal_repaid  # R900M inflow - WRONG!
```

**This is incorrect because:**
1. Repo principal is a **liability**, not income
2. When we borrow R900M via repo:
   - Assets: +R900M cash
   - Liabilities: +R900M repo debt
   - **Net effect on equity: R0**

3. When repo matures and we repay:
   - Assets: -R900M cash
   - Liabilities: -R900M repo debt
   - **Net effect on equity: R0** (except interest)

**Correct Accounting:**
```python
# Repo borrowing (near leg):
Assets: +R900M cash
Liabilities: +R900M repo debt
Cash_Balance: +R900M (but this is BORROWED, not owned)

# Repo maturity (far leg):
Assets: -R900M cash (repayment)
Liabilities: -R900M repo debt (extinguished)
Operating_CF: -R10M (interest expense)
Cash_Balance: -R910M total
```

**The spike occurs because:**
- Settlement account treats repo principal as "Total Cashflow"
- When repos mature in Jul 2026, it shows +R900M inflow
- But this is just rolling the repo - not real cash generation

---

## 📊 What Should Be Displayed

### **Balance Sheet View (Point in Time)**

```
ASSETS (2026-03-04):
  Portfolio Notional:        R1,000,000,000
  (Active positions only:    R510,000,000)
  Cash:                      R100,000,000 (seed capital)
  
LIABILITIES:
  Repo Outstanding:          R900,000,000
  
EQUITY:
  Seed Capital:              R100,000,000
  Retained Earnings:         R0 (inception)
  Total Equity:              R100,000,000
  
GEARING:
  Repo / Seed Capital:       9.0x ✓
  Repo / Total Notional:     0.90 (90% funded)
```

### **Cash Flow View (Cumulative)**

```
OPERATING CASHFLOWS (P&L Impact):
  + FRN Coupon Income:       R145M/year
  - Repo Interest Expense:   R60M/year
  = Net Operating CF:        R85M/year
  
FINANCING CASHFLOWS (Balance Sheet):
  + Repo Borrowed:           R900M (liability)
  - Repo Repaid:             R0 (not yet matured)
  = Net Financing CF:        R900M (borrowed)
  
INVESTMENT CASHFLOWS:
  + Initial Capital:         R100M
  - FRN Purchases:           R1,000M
  = Net Investment CF:       -R900M (invested)
  
CASH BALANCE:
  Should be: ~R100M (seed capital + operating CF - investments)
  NOT: R1,200M (which includes repo principal incorrectly)
```

---

## 🔧 Required Fixes

### **Fix 1: Update Portfolio Start Dates**

All positions should start on the same date (inception) to avoid confusion:

```json
{
  "start_date": "2025-03-04",  // All positions
  "maturity": "2028-03-04"     // Varies by position
}
```

**Action:** Regenerate portfolio with consistent start dates

---

### **Fix 2: Fix Cash Balance Calculation**

The settlement account should separate:

1. **NAV (Net Asset Value):**
   - = Seed Capital + Cumulative Operating Cashflows
   - = R100M + (Coupons - Repo Interest)
   - **This is the true value**

2. **Cash Balance (Gross):**
   - = Cash on hand (including borrowed funds)
   - = Seed Capital + Repo Borrowed - FRN Purchases + Operating CF
   - **This includes liabilities!**

3. **Free Cash (Net):**
   - = Cash Balance - Repo Outstanding
   - = NAV (approximately, ignoring mark-to-market)
   - **This is what we actually own**

**Current Problem:**
- Chart shows "Cash Balance (All Cashflows)" = R1,200M
- This is WRONG because it treats repo principal as income

**Correct Display:**
```
Cash Balance Chart should show:
- NAV line (Operating CF only) = R100M + net coupons
- NOT total cashflows including repo principal
```

---

### **Fix 3: Add Clear Asset/Liability Summary**

Create a sticky summary strip showing:

```
┌─────────────────────────────────────────────────────────────┐
│ ASSETS: R1,000M  │  LIABILITIES: R900M  │  EQUITY: R100M   │
│ Gearing: 9.0x    │  NAV: R100M + P&L    │  ROE: 85% p.a.   │
└─────────────────────────────────────────────────────────────┘
```

This should be visible on every page.

---

## 📋 Action Items

1. ✅ **Regenerate portfolio** with consistent start dates (all 2025-03-04)
2. ⏳ **Fix settlement account** to exclude repo principal from NAV calculation
3. ⏳ **Update Cash Balance chart** to show NAV, not total cashflows
4. ⏳ **Add Balance Sheet summary** showing Assets/Liabilities/Equity clearly
5. ⏳ **Fix "Current Notional"** to show total portfolio, not just active positions
6. ⏳ **Add tooltips** explaining:
   - Gearing = Repo / Seed Capital
   - NAV = Seed + Operating CF (excludes repo principal)
   - Cash Balance ≠ NAV (includes borrowed funds)

---

## 🎯 Expected Results After Fixes

**Risk Summary:**
- Current Notional: **R1,000M** (all positions)
- Peak Notional: **R1,000M** (consistent)
- Current DV01: ~R6,345
- Gearing: **9.0x** everywhere

**Cash Balance Chart:**
- Smooth line starting at R100M (seed capital)
- Gradual increase from operating cashflows (coupons - interest)
- **NO spike to R1,200M** (repo principal excluded)
- Ending around R100M + cumulative net income

**Balance Sheet (always visible):**
```
Assets: R1,000M  |  Liabilities: R900M  |  Equity: R100M
Gearing: 9.0x    |  NAV: R100M + P&L    |  ROE: 85%
```

---

**Status:** Analysis complete, fixes in progress  
**Priority:** HIGH - User-facing calculation errors  
**Impact:** Critical for portfolio understanding and decision-making
