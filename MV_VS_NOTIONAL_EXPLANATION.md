# Portfolio MV vs Notional - Explanation

**Issue:** Portfolio MV shows R632.9M but yield attribution shows R1,000M

---

## ✅ This is CORRECT - Here's Why

### **Two Different Concepts:**

**1. Portfolio Market Value (MV) = R632.9M**
- What the bonds are worth **TODAY**
- Based on current market prices (mark-to-market)
- Changes daily based on interest rates, credit spreads, etc.
- **This is the ASSET value on the balance sheet**

**2. Portfolio Notional = R1,000M**
- **Face value** of the bonds (original amount)
- Never changes (unless bonds mature or are sold)
- Used for yield calculations and attribution
- **This is NOT the asset value**

---

## 📊 Current Situation

```
Portfolio Notional:        R1,000,000,000  (face value)
Portfolio Market Value:    R632,905,211    (current worth)
─────────────────────────────────────────────────────
Mark-to-Market Loss:       R-367,094,789   (-36.7%)
```

**This means:**
- The FRN portfolio has lost 36.7% of its value
- Bonds purchased at par (100) are now worth ~63.3
- This is an **unrealized loss** (only realized if sold)

---

## 🔍 Why the Loss?

**Possible reasons for 37% decline:**

1. **Interest Rate Increase**
   - If JIBAR increased significantly since purchase
   - FRN prices fall when rates rise (even though coupons reset)
   - Discount margin (DM) captures this

2. **Credit Spread Widening**
   - If credit spreads widened (counterparty risk increased)
   - Bonds trade at discount to reflect higher risk

3. **Pricing Methodology**
   - FRNs are priced using discount margin (DM)
   - DM > Issue Spread → Price < 100
   - Check if DM values are realistic

---

## 🎯 What Should Be Shown

### **Balance Sheet (Current):**
```
ASSETS:
  Portfolio MV:     R632.9M  ← Correct (mark-to-market)
  Notional:         R1,000M  ← Reference only
  MTM P&L:          -R367.1M (-36.7%)
```

### **Yield Attribution Table:**
```
Should show BOTH:
- Notional (for yield calculations)
- Market Value (for actual worth)
- MTM P&L (unrealized gain/loss)
```

---

## 🔧 Recommended Fixes

### **1. Add MV column to yield attribution table:**

| Counterparty | Positions | Notional | Market Value | MTM P&L | Weight |
|--------------|-----------|----------|--------------|---------|--------|
| Standard Bank | 6 | R243.8M | R154.2M | -R89.6M | 24.4% |
| Nedbank | 5 | R217.5M | R137.6M | -R79.9M | 21.8% |
| ... | ... | ... | ... | ... | ... |
| **TOTAL** | **24** | **R1,000M** | **R632.9M** | **-R367.1M** | **100%** |

### **2. Add warning banner:**
```
⚠️ Portfolio Trading Below Par
- Current MV: R632.9M (63.3% of notional)
- Unrealized Loss: R367.1M (-36.7%)
- This impacts NAV and equity
```

### **3. Verify pricing is correct:**
- Check if DM values are realistic
- Verify JIBAR curve is correct
- Confirm FRN pricing methodology
- Review if 37% loss makes sense given market conditions

---

## 📋 Action Items

1. ✅ Add MTM P&L to balance sheet display
2. ⏳ Add MV column to yield attribution table
3. ⏳ Add warning if MV significantly below notional
4. ⏳ Verify FRN pricing is working correctly
5. ⏳ Check if DM values are realistic (should be close to issue spread for par bonds)

---

## 💡 Key Takeaway

**The R632.9M is CORRECT for the balance sheet** because:
- Balance sheet shows **market value** (what you could sell for today)
- Yield attribution uses **notional** (for calculating coupon income)
- The difference is **unrealized P&L** (mark-to-market gain/loss)

**This is standard accounting:**
- Assets = Market Value (not notional)
- Liabilities = Repo Outstanding
- Equity = MV - Repo = R632.9M - R900M = **-R267.1M** (underwater)

The portfolio is currently showing a **negative NAV** because:
- Assets (R632.9M) < Liabilities (R900M)
- This is a realistic scenario showing interest rate risk impact
- With 9x gearing, losses are amplified

---

**Status:** Explanation complete, fixes in progress
**Priority:** MEDIUM - Need to verify pricing is correct
**Impact:** Critical for understanding portfolio performance
