# Gearing Calculation - Correction

**Issue:** Inconsistent gearing calculations throughout the app showing 0.89x instead of 9.0x

---

## ❌ WRONG Formula (Old)

```python
gearing = repo_outstanding / portfolio_notional
gearing = 900M / 1,000M = 0.90x  # WRONG!
```

**Problem:** This shows repo as a percentage of assets, not true leverage.

---

## ✅ CORRECT Formula (New)

```python
gearing = repo_outstanding / seed_capital
gearing = 900M / 100M = 9.0x  # CORRECT!
```

**Why:** Gearing measures how many times we've leveraged our equity capital.

---

## 📊 Example

**Scenario:**
- Seed Capital: R100M
- Portfolio Notional: R1,000M (bought with seed + borrowed funds)
- Repo Outstanding: R900M (borrowed)

**Correct Gearing:** 900M / 100M = **9.0x**
- We borrowed 9 times our equity
- For every R1 of equity, we borrowed R9
- Total assets = R1 equity + R9 borrowed = R10 (10x total exposure)

**Wrong Calculation:** 900M / 1,000M = **0.90x**
- This just shows repo as 90% of assets
- Doesn't reflect true leverage

---

## 🔧 Files to Update

### 1. **yield_attribution_engine.py** (Line 56)
```python
# OLD (WRONG):
gearing = total_repo_outstanding / total_notional

# NEW (CORRECT):
gearing = total_repo_outstanding / SEED_CAPITAL
```

### 2. **app.py** (Multiple locations)
```python
# OLD (WRONG):
gearing = total_repo_cash / total_notional

# NEW (CORRECT):
gearing = total_repo_cash / SEED_CAPITAL
```

### 3. **portfolio_time_series.py** (Line 55)
```python
# OLD (WRONG):
gearing = total_repo / total_notional

# NEW (CORRECT):
gearing = total_repo / SEED_CAPITAL
```

### 4. **All other modules** - Search for:
```python
gearing.*=.*total_notional
```

Replace with:
```python
gearing = repo_outstanding / SEED_CAPITAL
```

---

## 📋 Standard Definitions

**Gearing (Leverage Ratio):**
- Formula: `Repo Outstanding / Seed Capital`
- Interpretation: How many times equity is leveraged
- Example: 9.0x means R9 borrowed for every R1 of equity

**Asset Coverage:**
- Formula: `Repo Outstanding / Portfolio Notional`
- Interpretation: What % of assets are funded by borrowing
- Example: 0.90 means 90% of assets are repo-financed

**Net Equity:**
- Formula: `Portfolio Notional - Repo Outstanding`
- Should equal: `Seed Capital` (if no P&L)
- Example: R1,000M - R900M = R100M

---

## ✅ Verification

After fix, all gearing displays should show:
- **9.0x** (not 0.90x)
- Consistent across all tabs
- Clear that it's Repo / Seed Capital

---

**Status:** Fix in progress
**Priority:** HIGH - User-facing calculation error
