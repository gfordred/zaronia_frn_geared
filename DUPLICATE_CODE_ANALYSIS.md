# Duplicate Code Analysis - app.py

**Analysis Date:** 2026-03-04  
**File:** app.py (3,301 lines)  
**Critical Finding:** SECTION 3 FRN PRICING ENGINE duplicated in full

---

## 🚨 CRITICAL: Complete Section Duplication

### Duplicate Block 1: Lines 783-1083 (300 lines)
**Section Header:** `# SECTION 3: FRN PRICING ENGINE (Proper Projection/Discount Separation)`

**Functions Included:**
1. `get_lookup_dict()` - Line 786
2. `get_historical_rate()` - Line 795
3. `calculate_compounded_zaronia()` - Line 816
4. `price_frn()` - Line 867
5. `calculate_dv01_cs01()` - Line 989
6. `calculate_key_rate_dv01()` - Line 1027

### Duplicate Block 2: Lines 1086-1386 (300 lines)
**Section Header:** `# SECTION 3: FRN PRICING ENGINE (Proper Projection/Discount Separation)`

**Functions Included (IDENTICAL):**
1. `get_lookup_dict()` - Line 1089
2. `get_historical_rate()` - Line 1098
3. `calculate_compounded_zaronia()` - Line 1119
4. `price_frn()` - Line 1170
5. `calculate_dv01_cs01()` - Line 1292
6. `calculate_key_rate_dv01()` - Line 1330

**Status:** ❌ EXACT DUPLICATES - 600 lines of duplicate code

---

## 📊 Curve Building Functions (NOT Duplicated)

### Single Instances (Good):
1. `build_jibar_curve()` - Line 579 ✅ Single instance
2. `build_jibar_curve_with_diagnostics()` - Line 625 ✅ Single instance
3. `build_zaronia_curve_daily()` - Line 680 ✅ Single instance

---

## 🎯 Migration Strategy

### Step 1: Extract to Canonical Modules

**Create:** `src/pricing/frn.py`
```python
# Canonical FRN pricing - SINGLE SOURCE OF TRUTH
def price_frn(...)
def calculate_accrued(...)
def calculate_clean_price(...)
```

**Create:** `src/pricing/risk.py`
```python
# Risk calculations
def calculate_dv01(...)
def calculate_cs01(...)
def calculate_key_rate_dv01(...)
```

**Create:** `src/pricing/cashflows.py`
```python
# Cashflow generation
def generate_frn_cashflows(...)
def calculate_compounded_zaronia(...)
```

**Create:** `src/curves/jibar_curve.py`
```python
# JIBAR curve building
def build_jibar_curve(...)
def build_jibar_curve_with_diagnostics(...)
```

**Create:** `src/curves/zaronia_curve.py`
```python
# ZARONIA curve building
def build_zaronia_curve_daily(...)
```

### Step 2: Delete Duplicates

**Delete:** Lines 1086-1386 (entire second copy)
**Keep:** Lines 783-1083 (first copy, then migrate to modules)

### Step 3: Update Imports Throughout app.py

**Replace:**
```python
# OLD (local functions)
price = price_frn(...)
dv01, cs01 = calculate_dv01_cs01(...)

# NEW (imported from modules)
from src.pricing import price_frn, calculate_dv01_cs01
price = price_frn(...)
dv01, cs01 = calculate_dv01_cs01(...)
```

---

## 📍 Usage Analysis

### Where are these functions called?

**Scanning for usage...**

```bash
# price_frn() usage
grep -n "price_frn(" app.py
# Result: Multiple tabs use this function

# calculate_dv01_cs01() usage  
grep -n "calculate_dv01_cs01(" app.py
# Result: Risk calculations in multiple tabs
```

**Tabs Using Pricing Functions:**
1. Tab 3: FRN Pricer & Risk
2. Tab 4: Portfolio Manager (valuation)
3. Tab 6: Time Travel (historical pricing)
4. Various analytics modules

---

## ⚠️ Risk Assessment

### High Risk:
- **Breaking existing functionality** if migration not done carefully
- **Inconsistent results** if tabs use different versions
- **Silent bugs** if one copy is fixed but not the other

### Mitigation:
1. ✅ Extract to canonical modules first
2. ✅ Add feature flag: `USE_NEW_PRICING = True/False`
3. ✅ Parallel run: Test new modules against old
4. ✅ Validate results match exactly
5. ✅ Migrate one tab at a time
6. ✅ Delete duplicates only after full validation

---

## 🔧 Implementation Plan

### Phase 2.2: Extract Canonical Pricing (Today)

**Priority 1: Core Pricing**
- [ ] Create `src/pricing/__init__.py`
- [ ] Create `src/pricing/frn.py` with `price_frn()`
- [ ] Create `src/pricing/risk.py` with `calculate_dv01_cs01()`, `calculate_key_rate_dv01()`
- [ ] Create `src/pricing/cashflows.py` with `calculate_compounded_zaronia()`
- [ ] Add unit tests for each function

**Priority 2: Curve Building**
- [ ] Create `src/curves/__init__.py`
- [ ] Create `src/curves/jibar_curve.py` with `build_jibar_curve()`
- [ ] Create `src/curves/zaronia_curve.py` with `build_zaronia_curve_daily()`
- [ ] Add curve validation tests

**Priority 3: Helper Functions**
- [ ] Create `src/pricing/helpers.py` with `get_lookup_dict()`, `get_historical_rate()`
- [ ] Add to pricing module exports

### Phase 2.3: Migration & Validation

**Week 2, Day 3-4:**
- [ ] Add feature flag to app.py: `USE_CANONICAL_PRICING = True`
- [ ] Update Tab 3 (FRN Pricer) to use new modules
- [ ] Validate: Compare old vs new results (should match exactly)
- [ ] Update Tab 4 (Portfolio Manager) to use new modules
- [ ] Validate: Portfolio valuations match
- [ ] Update remaining tabs
- [ ] Full regression test

### Phase 2.4: Cleanup

**Week 2, Day 5:**
- [ ] Delete lines 1086-1386 (second duplicate block)
- [ ] Delete lines 783-1083 (first block, now in modules)
- [ ] Update all imports to use `from src.pricing import ...`
- [ ] Remove feature flag (new modules are default)
- [ ] Final validation

---

## 📈 Expected Impact

### Before:
```
app.py: 3,301 lines
- 600 lines of duplicate pricing code
- Risk of inconsistency
- Hard to maintain
```

### After:
```
app.py: ~2,700 lines (-600 lines)
src/pricing/: ~400 lines (canonical)
src/curves/: ~200 lines (canonical)
- Zero duplicates
- Single source of truth
- Easy to test and maintain
```

---

## ✅ Success Criteria

- [ ] Zero duplicate pricing functions
- [ ] All tabs use canonical modules
- [ ] Results match exactly (validation passed)
- [ ] app.py reduced by 600+ lines
- [ ] Unit tests for all pricing functions
- [ ] No breaking changes to user experience

---

## 🎯 Next Action

**Immediate:** Create `src/pricing/frn.py` with canonical `price_frn()` function

**Command:**
```python
# Extract price_frn from lines 867-986
# Move to src/pricing/frn.py
# Add proper imports and documentation
```

---

**Analysis Complete:** Ready to proceed with extraction
**Estimated Time:** 2-3 hours for full migration
**Risk Level:** Medium (mitigated by parallel run strategy)
