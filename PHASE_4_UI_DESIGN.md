# Phase 4: UI Overhaul - Design Document

**Status:** In Progress  
**Started:** 2026-03-04 1:07 PM

---

## 🎯 Objectives

Transform the current 7-tab structure into a streamlined 4-tab professional trading platform with:
- Unified chart theming
- Sticky portfolio strip
- Reusable UI components
- Trader-first UX

---

## 📊 Current Structure (Before)

**7 Tabs:**
1. Current Valuation
2. Yield Attribution
3. NAV Index
4. Counterparty Risk
5. Time Series
6. Time Travel
7. Edit Portfolio

**Issues:**
- Too many tabs (cognitive overload)
- Inconsistent chart styling
- No persistent portfolio summary
- Duplicate functionality across tabs

---

## 🎨 New Structure (After)

### **4-Tab Design:**

#### **Tab 1: 📊 Trade Ticket**
**Purpose:** Price FRNs, execute trades, manage positions

**Sections:**
- FRN Pricer (with live pricing)
- Quick Trade Entry
- Position Editor
- Recent Trades

**Key Features:**
- Real-time pricing with DV01/CS01
- One-click trade execution
- Position modification
- Trade history

---

#### **Tab 2: 💼 Portfolio**
**Purpose:** Portfolio analysis, performance, attribution

**Sections:**
- Current Valuation (with breakdown)
- Yield Attribution
- Performance Analytics
- Counterparty Exposure
- Risk Metrics (DV01, CS01, KRDV01)

**Key Features:**
- Comprehensive portfolio view
- Yield decomposition
- Counterparty concentration
- Risk attribution

---

#### **Tab 3: 🏦 Repo & Funding**
**Purpose:** Repo management, funding analysis, gearing

**Sections:**
- Repo Dashboard
- Funding Risk Analysis
- Asset/Repo Visualization
- Repo Master Table
- Gearing Evolution

**Key Features:**
- Repo outstanding tracking
- Funding capacity analysis
- Asset encumbrance visualization
- Maturity ladder

---

#### **Tab 4: 🔧 Diagnostics**
**Purpose:** Historical analysis, time travel, system diagnostics

**Sections:**
- Time Travel (historical valuation)
- NAV Index (inception to date)
- Settlement Account
- Daily Analytics
- Curve Diagnostics
- System Health

**Key Features:**
- Historical portfolio valuation
- NAV evolution
- Cashflow analysis
- Curve repricing errors
- Data quality checks

---

## 🎨 Unified Chart Theme

**Color Scheme:**
- Primary: `#00D9FF` (Cyan) - Main charts, positive values
- Secondary: `#FF6B9D` (Pink) - Secondary series
- Success: `#00E676` (Green) - Gains, positive metrics
- Warning: `#FFD600` (Yellow) - Warnings, moderate risk
- Danger: `#FF5252` (Red) - Losses, high risk
- Neutral: `#B0BEC5` (Gray) - Neutral data

**Typography:**
- Font: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto
- Title: 16px
- Body: 12px
- Axis: 11px

**Layout:**
- Dark theme (plotly_dark)
- Consistent margins: L:60, R:40, T:60, B:60
- Default height: 500px
- Hover mode: x unified

---

## 📌 Sticky Portfolio Strip

**Always Visible at Top:**
```
┌─────────────────────────────────────────────────────────────┐
│ Total MV    │ DV01      │ CS01      │ Gearing │ Net Yield │ Positions │
│ R632.9M     │ R74.3k    │ R667.6k   │ 15.29x  │ 7.56%     │ 24        │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Sticky positioning (stays at top on scroll)
- Real-time updates
- Click to expand for details
- Color-coded risk indicators

---

## 🧩 Reusable Components

### **Created Components:**

1. **`render_metric_card()`** - Consistent metric display
2. **`render_portfolio_strip()`** - Sticky portfolio summary
3. **`render_risk_gauge()`** - Risk utilization gauges
4. **`render_data_table()`** - Styled data tables
5. **`render_section_header()`** - Section headers with icons
6. **`render_alert()`** - Alert messages
7. **`render_key_value_pairs()`** - Key-value grid layout
8. **`render_tabs_with_counts()`** - Tabs with counts
9. **`render_filter_panel()`** - Dynamic filter panel
10. **`render_download_button()`** - Data export

### **Chart Factory Methods:**

1. **`create_line_chart()`** - Time series, trends
2. **`create_bar_chart()`** - Comparisons, breakdowns
3. **`create_waterfall_chart()`** - Cashflow analysis
4. **`create_gauge_chart()`** - Risk metrics
5. **`create_heatmap()`** - Correlation, risk matrices

---

## 📋 Migration Plan

### **Phase 4.1: Foundation** ✅ COMPLETE
- [x] Create unified chart factory
- [x] Create reusable UI components
- [x] Define color scheme and theming

### **Phase 4.2: Sticky Strip** (Next)
- [ ] Implement sticky portfolio strip
- [ ] Add real-time metric updates
- [ ] Add expand/collapse functionality

### **Phase 4.3: Tab Restructuring**
- [ ] Create Tab 1: Trade Ticket
- [ ] Create Tab 2: Portfolio
- [ ] Create Tab 3: Repo & Funding
- [ ] Create Tab 4: Diagnostics

### **Phase 4.4: Content Migration**
- [ ] Migrate FRN Pricer to Trade Ticket
- [ ] Migrate valuation/attribution to Portfolio
- [ ] Migrate repo content to Repo & Funding
- [ ] Migrate time travel/analytics to Diagnostics

### **Phase 4.5: Polish**
- [ ] Update all charts to use ChartFactory
- [ ] Add loading states
- [ ] Add error boundaries
- [ ] Performance optimization

---

## 🎯 Success Criteria

- [x] Unified chart theming across all visualizations
- [x] Reusable component library created
- [ ] 4-tab structure implemented
- [ ] Sticky portfolio strip functional
- [ ] All existing functionality preserved
- [ ] Improved navigation and UX
- [ ] Reduced cognitive load
- [ ] Professional trader-first interface

---

## 📊 Before/After Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Number of tabs | 7 | 4 | -43% |
| Chart themes | Inconsistent | Unified | ✅ |
| Portfolio summary | Hidden | Always visible | ✅ |
| Component reuse | None | 10+ components | ✅ |
| Navigation depth | 2-3 clicks | 1-2 clicks | -33% |

---

## 🚀 Next Steps

1. Implement sticky portfolio strip
2. Create 4-tab structure skeleton
3. Migrate content to new tabs
4. Update all charts to use ChartFactory
5. User testing and refinement

---

**Status:** Phase 4.1 Complete (Chart Factory + Components)  
**Next:** Phase 4.2 (Sticky Portfolio Strip)  
**ETA:** 2-3 hours for full Phase 4 completion
