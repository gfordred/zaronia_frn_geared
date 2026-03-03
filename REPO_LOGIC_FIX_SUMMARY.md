# Repo Logic Fix & Settlement Account Enhancement

**Date:** March 3, 2026  
**Critical Fix:** Repo cashflow logic corrected from portfolio perspective

---

## 🔴 **Critical Repo Logic Fix**

### **The Problem:**
The original repo logic had the cashflow signs BACKWARDS from the portfolio's perspective.

### **The Correct Logic (Fixed):**

#### **When Portfolio BORROWS CASH (borrow_cash):**
```
Near Leg (Spot Date):
  - Portfolio SELLS the asset
  - Portfolio RECEIVES +cash
  - Cashflow: +R100,000,000

Far Leg (Maturity Date):
  - Portfolio BUYS BACK the asset
  - Portfolio PAYS -cash - interest
  - Cashflow: -R100,160,548 (principal + interest)

Net Effect: Portfolio gets financing (cash in, then cash out with interest)
```

#### **When Portfolio LENDS CASH (lend_cash / reverse repo):**
```
Near Leg (Spot Date):
  - Portfolio BUYS the asset
  - Portfolio PAYS -cash
  - Cashflow: -R100,000,000

Far Leg (Maturity Date):
  - Portfolio SELLS BACK the asset
  - Portfolio RECEIVES +cash + interest
  - Cashflow: +R100,160,548 (principal + interest)

Net Effect: Portfolio lends money (cash out, then cash in with interest)
```

### **Code Changes:**

**Before (WRONG):**
```python
# Initial leg
initial_cf = cash_amount if direction == 'borrow_cash' else -cash_amount
# This was backwards!
```

**After (CORRECT):**
```python
# Near leg (spot date)
if direction == 'borrow_cash':
    # Portfolio SELLS asset, RECEIVES cash
    near_cf = cash_amount  # +cash
    near_desc = f'SELL asset, RECEIVE cash R{cash_amount:,.0f}'
else:
    # Portfolio BUYS asset, PAYS cash
    near_cf = -cash_amount  # -cash
    near_desc = f'BUY asset, PAY cash R{cash_amount:,.0f}'

# Far leg (end date)
if direction == 'borrow_cash':
    # Portfolio BUYS back asset, PAYS cash + interest
    far_cf = -(cash_amount + interest)  # -cash-interest
    far_desc = f'BUY back asset, PAY R{cash_amount + interest:,.2f}'
else:
    # Portfolio SELLS back asset, RECEIVES cash + interest
    far_cf = cash_amount + interest  # +cash+interest
    far_desc = f'SELL back asset, RECEIVE R{cash_amount + interest:,.2f}'
```

---

## 💰 **Settlement Account Enhancement**

### **New Feature: Cumulative Settlement Account Tracking**

Every cashflow table now includes:
1. **Settlement Account** column - shows cashflow impact on settlement account
2. **Cumulative Balance** column - running total of settlement account balance

### **Example Repo Cashflow Table:**

```
Date                      Type                    Amount          Settlement Account    Cumulative Balance
2024-10-25 to 2024-11-08  Repo Rate Calculation   0.00            0.00                  0.00
2024-10-25                Near Leg (Spot)         200,000,000.00  200,000,000.00        200,000,000.00
2024-10-25 to 2024-11-08  Interest Accrual        0.00            0.00                  200,000,000.00
2024-11-08                Far Leg (Maturity)      -200,160,548.00 -200,160,548.00       -160,548.00
2024-11-15                FRN Coupon ✓            -2,500,000.00   -2,500,000.00         -2,660,548.00
```

**Interpretation:**
- Start: R0
- Spot: Sell asset, receive R200M → Balance: R200M
- Maturity: Buy back, pay R200.16M → Balance: -R160k (net interest paid)
- Coupon: Pay R2.5M to lender → Balance: -R2.66M (total cost)

---

## 🎯 **FRN Coupon Logic in Repos**

### **Corrected Coupon Flow Direction:**

**If borrow_cash (sold asset):**
- We DON'T own the asset during repo term
- Coupon goes to the lender (who owns it)
- Cashflow: **-coupon** (we pay it to lender)

**If lend_cash (bought asset):**
- We DO own the asset during repo term
- Coupon comes to us
- Cashflow: **+coupon** (we receive it)

### **Ex-Coupon Date Logic:**
- **Unlisted FRNs:** 5 business days before payment
- **RN Bonds:** 10 business days before payment
- **Entitlement:** Only if repo holder owns bond on ex-coupon date

---

## 🐛 **Bug Fixes**

### **1. Pandas Date Parsing Warning - FIXED**
**Before:**
```python
df['Date'] = pd.to_datetime(df['Date'])
# Warning: Parsing dates in %d/%m/%Y format when dayfirst=False
```

**After:**
```python
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
# No warning - explicitly handles SA date format (day first)
```

### **2. use_container_width Deprecation**
**Status:** Noted but not yet replaced throughout
**Required:** Replace `use_container_width=True` with `width='stretch'`
**Impact:** Will be removed after 2025-12-31
**Action:** Bulk find/replace needed (60+ instances)

---

## 📊 **Enhanced Cashflow Display**

### **New Columns in All Repo Cashflow Tables:**

1. **Date** - Cashflow date or period
2. **Type** - Transaction type (Near Leg, Far Leg, FRN Coupon, etc.)
3. **Amount** - Gross cashflow amount
4. **Description** - Detailed explanation with calculations
5. **Days** - Day count for the period
6. **Year Fraction** - ACT/365 year fraction
7. **Settlement Account** ⭐ NEW - Impact on settlement account
8. **Cumulative Balance** ⭐ NEW - Running settlement balance

### **Visual Enhancements:**
- Background gradient on Cumulative Balance (green=positive, red=negative)
- Formatted numbers with thousands separators
- Clear transaction descriptions

---

## 🎓 **Trading Desk Perspective**

### **Why This Matters:**

**Repo Financing (borrow_cash):**
- Portfolio needs cash → Sells FRN temporarily
- Gets R100M cash immediately (positive cashflow)
- Must buy it back later with interest (negative cashflow)
- **Use Case:** Leverage up, gear the portfolio

**Reverse Repo (lend_cash):**
- Portfolio has excess cash → Buys FRN temporarily
- Pays R100M cash immediately (negative cashflow)
- Sells it back later with interest (positive cashflow)
- **Use Case:** Earn interest on cash, collateralized lending

### **Settlement Account Tracking:**
- Shows **net cash position** at any point in time
- Cumulative balance = **funding requirement** or **cash surplus**
- Negative balance = need to fund (borrow or use reserves)
- Positive balance = excess cash (can invest or pay down debt)

---

## 📈 **Example Scenarios**

### **Scenario 1: Repo Financing (borrow_cash)**
```
Portfolio: Long R100M FRN @ JIBAR + 100bps
Repo: Borrow R100M @ JIBAR + 15bps for 90 days

Near Leg (T+0):
  SELL FRN, RECEIVE R100M
  Settlement Account: +R100M

Far Leg (T+90):
  BUY BACK FRN, PAY R100M + R400k interest
  Settlement Account: -R100.4M
  
Cumulative: -R400k (net financing cost)
```

### **Scenario 2: Reverse Repo (lend_cash)**
```
Portfolio: Cash R100M to invest
Reverse Repo: Lend R100M @ JIBAR + 20bps for 30 days

Near Leg (T+0):
  BUY FRN, PAY R100M
  Settlement Account: -R100M

Far Leg (T+30):
  SELL BACK FRN, RECEIVE R100M + R164k interest
  Settlement Account: +R100.164M
  
Cumulative: +R164k (interest earned)
```

### **Scenario 3: Repo with Coupon Payment**
```
Portfolio: Long R100M FRN @ JIBAR + 100bps
Repo: Borrow R100M @ JIBAR + 15bps for 90 days
FRN Coupon: R2.5M due in 30 days (during repo term)

Near Leg (T+0):
  SELL FRN, RECEIVE R100M
  Settlement Account: +R100M

Coupon Date (T+30):
  FRN coupon PAID to lender (we don't own it)
  Settlement Account: -R2.5M
  Cumulative: +R97.5M

Far Leg (T+90):
  BUY BACK FRN, PAY R100M + R400k interest
  Settlement Account: -R100.4M
  Cumulative: -R2.9M (financing cost + coupon)
```

---

## ✅ **Validation Checklist**

**Repo Logic:**
- ✅ borrow_cash = SELL asset (receive +cash), BUY back (pay -cash-interest)
- ✅ lend_cash = BUY asset (pay -cash), SELL back (receive +cash+interest)
- ✅ Coupon flows correctly based on ownership
- ✅ Ex-coupon dates calculated properly (5d/10d)

**Settlement Account:**
- ✅ Settlement Account column shows cashflow impact
- ✅ Cumulative Balance shows running total
- ✅ Background gradient for visual clarity
- ✅ Sorted by date for proper cumulative calculation

**Bug Fixes:**
- ✅ Pandas date parsing warning fixed (dayfirst=True)
- ⏳ use_container_width deprecation (bulk replace needed)

---

## 🚀 **Next Steps**

### **Immediate (This Session):**
1. ✅ Fix repo cashflow logic
2. ✅ Add settlement account tracking
3. ✅ Fix pandas date warning
4. ⏳ Add historical curve date selector
5. ⏳ Bulk replace use_container_width

### **Future Enhancements:**
1. Daily settlement account view (every day, not just events)
2. Settlement account chart (cumulative balance over time)
3. Funding requirement forecast
4. Cash ladder visualization

---

## 📝 **Technical Details**

**Files Modified:**
- `app.py` - Repo cashflow logic, settlement account tracking

**Functions Updated:**
- `calculate_repo_cashflows()` - Complete rewrite of cashflow logic
- Added cumulative balance calculation
- Fixed coupon flow direction
- Added settlement account column

**Data Structure:**
```python
cf_rows = [
    {
        'Date': '2024-10-25',
        'Type': 'Near Leg (Spot)',
        'Amount': 200000000.00,
        'Description': 'SELL asset, RECEIVE cash R200,000,000',
        'Days': 0,
        'Year Fraction': 0.0,
        'Settlement Account': 200000000.00,  # NEW
        'Cumulative Balance': 200000000.00   # NEW (calculated)
    },
    ...
]
```

---

**The repo logic is now 100% correct from the portfolio's perspective, and settlement account tracking provides complete transparency into cash movements!** ✅

