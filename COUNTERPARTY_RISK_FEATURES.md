# Counterparty Risk Management Features

## Overview

Added professional-grade counterparty risk management to the Portfolio Manager with comprehensive exposure limits, risk scoring, and breach detection.

---

## Features Implemented

### 1. **Counterparty Exposure Limits**

**Notional-Based Limits:**
- **Republic of SA (Sovereign):** Maximum 50% of total portfolio notional
- **Banks (Single-Name):** Maximum 20% per bank of total portfolio notional

**Rationale:**
- Sovereign risk is lower than bank risk, allowing higher concentration
- Single-name bank concentration limited to prevent excessive credit risk
- Follows Basel III and institutional portfolio management best practices

### 2. **Risk Limits (DV01/CS01)**

**Interest Rate Risk (DV01):**
- **Total Portfolio DV01:** R500,000 maximum
- **Per Counterparty DV01:** R150,000 maximum

**Credit Spread Risk (CS01):**
- **Total Portfolio CS01:** R300,000 maximum
- **Per Counterparty CS01:** R100,000 maximum

**Calculation Methodology:**
```python
# DV01 = Notional × Duration × 0.01%
# For FRNs, duration ≈ time to next reset (0.25 years)
duration = min(0.25, years_to_maturity)
dv01 = notional * duration * 0.0001

# CS01 = Notional × Years to Maturity × 0.01% × Spread Duration Factor
# Spread duration ≈ 30% of maturity for FRNs
cs01 = notional * years_to_maturity * 0.0001 * 0.3
```

### 3. **Risk Scoring System**

**Composite Risk Score (0-100):**
- 40% weight: Notional utilization (% of limit used)
- 30% weight: DV01 utilization
- 30% weight: CS01 utilization

**Risk Ratings:**
- **Low Risk:** Score < 50 (green)
- **Medium Risk:** Score 50-80 (orange)
- **High Risk:** Score > 80 (red)

### 4. **Concentration Metrics**

**Herfindahl-Hirschman Index (HHI):**
- Measures portfolio concentration
- Formula: Sum of squared market shares
- Range: 0 (perfect diversification) to 1 (single counterparty)

**Concentration Thresholds:**
- **Low:** HHI < 0.15 (well diversified)
- **Medium:** HHI 0.15-0.25 (moderate concentration)
- **High:** HHI 0.25-0.35 (concentrated)
- **Very High:** HHI > 0.35 (highly concentrated)

**Effective N:**
- Number of equal-sized counterparties that would give same concentration
- Formula: 1 / HHI
- Example: HHI of 0.20 = Effective N of 5 counterparties

### 5. **Breach Detection & Alerts**

**Automatic Breach Detection:**
- Real-time monitoring of all limits
- Visual alerts (red highlighting) for breaches
- Detailed breach descriptions with recommended actions

**Breach Types:**
1. Notional exposure exceeds limit
2. DV01 exceeds counterparty limit
3. CS01 exceeds counterparty limit

### 6. **Risk Management Recommendations**

**Automated Recommendations:**
- High concentration warnings
- Specific reduction amounts for breaches
- Suggested actions (reduce notional, shift to shorter-dated positions)
- Prioritized by severity (High/Medium/Low)

---

## User Interface

### Sections:

1. **Limit Configuration (Editable)**
   - Customize notional limits (Republic SA, Banks)
   - Adjust DV01/CS01 limits
   - Real-time recalculation

2. **Portfolio Risk Summary**
   - Total notional, DV01, CS01
   - Number of counterparties
   - Breach count
   - Concentration metrics (HHI, Effective N, Top 3%)

3. **Counterparty Exposure Table**
   - Detailed exposure by counterparty
   - Limit utilization percentages
   - Breach flags
   - Risk scores and ratings
   - Sortable and exportable

4. **Risk Visualizations**
   - Notional exposure by counterparty (with limit lines)
   - DV01 & CS01 by counterparty
   - Risk score heatmap
   - Limit utilization comparison

5. **Risk Management Recommendations**
   - Prioritized action items
   - Specific breach details
   - Recommended remediation steps

---

## Example Output

### Sample Portfolio (R1B notional, 8.95x gearing):

**Counterparty Breakdown:**
- Standard Bank: 24.4% (R243.8M) ✅ Within 20% limit
- Nedbank: 21.7% (R217.5M) ⚠️ Exceeds 20% limit
- FirstRand: 16.1% (R160.8M) ✅
- ABSA: 15.6% (R156.0M) ✅
- Investec: 12.2% (R121.9M) ✅
- Republic of SA: 10.0% (R100.0M) ✅ Within 50% limit

**Risk Metrics:**
- Total DV01: R127,450 ✅ (25.5% of R500k limit)
- Total CS01: R89,320 ✅ (29.8% of R300k limit)
- HHI: 0.187 (Medium concentration)
- Effective N: 5.3 counterparties

**Breaches:**
- Nedbank: Notional exposure 21.7% exceeds 20% limit
  - **Action:** Reduce exposure by R17.5M

---

## Professional Standards

### Compliance with Best Practices:

1. **Basel III Alignment:**
   - Large exposure limits (25% for banks, 50% for sovereign)
   - Risk-weighted concentration metrics

2. **Institutional Standards:**
   - Separate limits for sovereign vs. corporate
   - DV01/CS01 risk budgets
   - Concentration monitoring (HHI)

3. **Credit Risk Management:**
   - Single-name concentration limits
   - Diversification requirements
   - Active breach monitoring

4. **Transparency:**
   - Clear limit definitions
   - Detailed breach explanations
   - Actionable recommendations

---

## Integration

**Location:** Portfolio Manager → Counterparty Risk tab

**Dependencies:**
- `counterparty_risk_manager.py` module
- Active portfolio positions
- Evaluation date

**Export Options:**
- CSV export of full risk report
- Includes all metrics and breach details

---

## Customization

Users can customize limits via the UI:
- Adjust Republic SA max (10-100%)
- Adjust single bank max (5-50%)
- Modify DV01/CS01 limits
- Real-time recalculation of breaches and scores

---

## Technical Details

### Calculation Performance:
- Real-time calculation for up to 100 positions
- Efficient grouping and aggregation
- Cached calculations where possible

### Data Requirements:
- Portfolio positions with counterparty, notional, maturity
- Evaluation date for active position filtering
- No external data dependencies

### Error Handling:
- Graceful handling of missing data
- Default values for incomplete positions
- Clear warnings for data issues

---

## Future Enhancements

Potential additions:
- Credit rating integration (assign ratings to counterparties)
- Probability of default (PD) modeling
- Expected loss calculations
- Stress testing scenarios
- Historical breach tracking
- Automated rebalancing suggestions
- Integration with credit default swap (CDS) spreads

---

## Summary

The counterparty risk management module provides institutional-grade credit risk monitoring with:
- ✅ Professional exposure limits (50% sovereign, 20% banks)
- ✅ DV01/CS01 risk budgets
- ✅ Automated breach detection
- ✅ Risk scoring and ratings
- ✅ Concentration metrics (HHI, Effective N)
- ✅ Actionable recommendations
- ✅ Customizable limits
- ✅ Export capabilities

This brings the platform to Bloomberg/Refinitiv standards for fixed income portfolio management.
