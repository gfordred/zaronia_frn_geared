"""
Tab Descriptions Module
Provides detailed descriptions and logic writeups for each tab in the application
"""

import streamlit as st


TAB_DESCRIPTIONS = {
    "Batch Calculator": {
        "title": "🧮 Batch Calculator",
        "description": """
        **Purpose:** Rapid batch pricing of predefined FRN instruments (RN bonds and bank FRNs)
        
        **Logic:**
        1. Select instrument from dropdown (RN2027, RN2030, RN2032, RN2035, ABFZ02)
        2. Input desired all-in price per 100
        3. System calculates required discount margin (DM) to achieve target price
        4. Uses QuantLib FRN pricing engine with:
           - Projection curve: JIBAR 3M for coupon forecasting
           - Discount curve: JIBAR + DM for present value calculation
           - Day count: ACT/365 Fixed
           - Calendar: South African business days
        
        **Output:**
        - Required DM (basis points)
        - Clean price, Dirty price, Accrued interest
        - DV01 (price sensitivity to 1bp parallel shift)
        - CS01 (price sensitivity to 1bp credit spread change)
        
        **Use Case:** Quick "what DM do I need to hit 102.50?" calculations
        """,
        "key_formulas": [
            "Dirty Price = Clean Price + Accrued Interest",
            "DV01 = -∂Price/∂Rate × 0.0001",
            "CS01 = -∂Price/∂DM × 0.0001"
        ]
    },
    
    "Curve Analysis": {
        "title": "📊 Curve Analysis",
        "description": """
        **Purpose:** Comprehensive interest rate curve analysis and visualization
        
        **Logic:**
        1. **Curve Building (QuantLib):**
           - Bootstrap JIBAR curve from: 3M Depo + 4 FRAs + 4 Swaps
           - Method: PiecewiseLogCubicDiscount
           - Interpolation: Log-cubic on discount factors
           - Extrapolation: Flat forward rates
        
        2. **ZARONIA Curve:**
           - Daily bootstrapping from JIBAR forwards
           - ZARONIA(t) = JIBAR_forward(t) - spread
           - Compounded overnight rates for discount factors
        
        3. **Curve Analytics:**
           - Zero rates (continuously compounded, annual)
           - Forward rates (simple, 3M tenor)
           - Discount factors
           - FRA repricing quality (market vs implied)
        
        **Sub-Tabs:**
        - **Live Market Rates:** Input instruments with color-coded bars
        - **Zero Curves:** JIBAR vs ZARONIA zero rates and spreads
        - **Forward Curves:** 3M forward rate projections (40 points)
        - **FRA Curve:** Repricing quality metrics (errors in bps)
        - **Discount Factors:** DF curves and ratios
        - **Curve Evolution:** Historical time-series of swap rates
        - **Steepness Analysis:** 2s5s, 5s10s, 2s10s spreads over time
        - **3D Surface:** Interactive 3D visualization of curve evolution
        
        **Use Case:** Market analysis, curve positioning, relative value
        """,
        "key_formulas": [
            "Zero Rate: r(t) = -ln(DF(t))/t",
            "Forward Rate: f(t1,t2) = (DF(t1)/DF(t2) - 1)/(t2-t1)",
            "DF(t) = exp(-r(t) × t)"
        ]
    },
    
    "Single FRN Pricer": {
        "title": "💎 Single FRN Pricer",
        "description": """
        **Purpose:** Detailed pricing of individual FRN with full cashflow breakdown
        
        **Logic:**
        1. **Input Parameters:**
           - Notional, Start date, Maturity
           - Issue spread (coupon = JIBAR + spread)
           - Discount margin (DM for valuation)
           - Index: JIBAR 3M or ZARONIA
        
        2. **Cashflow Generation (QuantLib):**
           - Quarterly schedule (3M frequency)
           - Modified Following business day convention
           - SA calendar with public holidays
           - Coupon = Notional × (Index_forward + Spread) × DCF
        
        3. **Valuation:**
           - Project coupons using JIBAR projection curve
           - Discount using JIBAR + DM discount curve
           - Clean Price = PV of all cashflows
           - Accrued = Pro-rata coupon from last payment to settlement
        
        4. **Risk Metrics:**
           - DV01: Bump JIBAR curve +1bp, reprice
           - CS01: Bump DM +1bp, reprice
           - Key Rate DV01: Bump individual tenors
        
        **Output:**
        - Full cashflow table (dates, coupons, discount factors, PVs)
        - Price metrics (clean, dirty, accrued, yield)
        - Risk metrics (DV01, CS01, key rate sensitivities)
        
        **Use Case:** Detailed analysis of specific FRN, understanding cashflows
        """,
        "key_formulas": [
            "Coupon = Notional × (Forward_Rate + Spread) × Day_Count_Fraction",
            "PV = Σ(Cashflow_i × DF_i)",
            "Clean Price = (PV / Notional) × 100"
        ]
    },
    
    "ZARONIA Pricer": {
        "title": "🌙 ZARONIA Pricer",
        "description": """
        **Purpose:** Specialized pricing for ZARONIA-linked FRNs (e.g., ABFZ02)
        
        **Logic:**
        1. **ZARONIA Compounding:**
           - Lookback period (e.g., 5 business days)
           - Compounded overnight rates over coupon period
           - Formula: (1 + r1×d1)(1 + r2×d2)...(1 + rn×dn) - 1
        
        2. **Historical Fixings:**
           - Load ZARONIA fixings from CSV
           - For historical periods: use actual fixings
           - For future periods: use forward rates from ZARONIA curve
        
        3. **Coupon Calculation:**
           - Compounded ZARONIA rate + spread
           - Applied to notional with day count fraction
           - Quarterly payments
        
        4. **Discounting:**
           - Use ZARONIA OIS curve (risk-free)
           - No credit spread adjustment
        
        **Output:**
        - Compounded ZARONIA rates per period
        - Detailed coupon breakdown
        - Price and risk metrics
        
        **Use Case:** Pricing government ZARONIA FRNs, OIS-linked instruments
        """,
        "key_formulas": [
            "Compounded Rate = Π(1 + ZARONIA_i × DCF_i) - 1",
            "Coupon = Notional × (Compounded_Rate + Spread) × Period_DCF"
        ]
    },
    
    "NCD Pricing": {
        "title": "💳 NCD Pricing",
        "description": """
        **Purpose:** Bank NCD (Negotiable Certificate of Deposit) spread matrix
        
        **Logic:**
        1. **NCD Market:**
           - Short-term bank funding instruments
           - Spreads over JIBAR 3M
           - Reflect bank credit quality and liquidity
        
        2. **Pricing Matrix:**
           - Banks: ABSA, Standard Bank, Nedbank, FirstRand, Investec, Capitec
           - Tenors: 1Y, 1.5Y, 2Y, 3Y, 4Y, 5Y
           - Spreads in basis points
        
        3. **Historical Pricing:**
           - 2 years of daily NCD pricing (499 business days)
           - Time-series visualization
           - Statistics: 2Y average, high, low
        
        4. **FRN Valuation Use:**
           - Interpolate NCD spreads for FRN valuation
           - Use as market-based DM for fair value
           - Linear interpolation between tenors
        
        **Output:**
        - Editable spread matrix
        - Historical spread evolution charts
        - Summary statistics
        
        **Use Case:** Market-based FRN valuation, credit spread analysis
        """,
        "key_formulas": [
            "Interpolated Spread = S1 + (S2-S1) × (T-T1)/(T2-T1)",
            "Fair Value DM = NCD_Spread(Maturity, Bank)"
        ]
    },
    
    "Portfolio Manager": {
        "title": "📊 Portfolio Manager",
        "description": """
        **Purpose:** Comprehensive portfolio analytics and management
        
        **Logic:**
        1. **Portfolio Valuation:**
           - Price each FRN using QuantLib engine
           - Aggregate: Total MV, DV01, CS01, Net Yield
           - Gearing = Repo Outstanding / Portfolio Notional
        
        2. **Historical Valuation:**
           - Value portfolio on any historical date
           - Build curves from JIBAR_FRA_SWAPS.xlsx
           - Interpolate NCD spreads for that date
           - Compare P&L vs different dates
        
        3. **Composition Analysis:**
           - By counterparty (concentration risk)
           - By maturity bucket (0-1Y, 1-2Y, etc.)
           - Weighted average metrics
        
        4. **Cashflow Analysis:**
           - Project all FRN coupons (quarterly)
           - Repo cashflows (near/far legs)
           - Waterfall chart by type
           - Cumulative balance
        
        5. **Editable Portfolio:**
           - Inline editing with st.data_editor
           - Add/delete positions
           - Bulk operations (spread adjustments)
        
        **Sub-Tabs:**
        - Current Valuation
        - Historical Valuation (any date)
        - Complete History (inception to date)
        - Composition & Yields
        - Cashflows
        - Edit Portfolio
        
        **Use Case:** Portfolio monitoring, P&L attribution, risk management
        """,
        "key_formulas": [
            "Portfolio MV = Σ(Position_MV_i)",
            "Gearing = Repo_Outstanding / Portfolio_Notional",
            "Net Yield = (Gross_Yield × Notional - Repo_Cost) / Notional"
        ]
    },
    
    "Repo Trades": {
        "title": "💼 Repo Trades",
        "description": """
        **Purpose:** Repo financing management and analytics
        
        **Logic:**
        1. **Repo Mechanics:**
           - Near Leg: SELL asset, RECEIVE cash (+)
           - Far Leg: BUY back asset, PAY cash + interest (-)
           - Repo Rate = JIBAR forward + repo spread
           - Interest = Cash × Rate × (Days/365)
        
        2. **Coupon Alignment:**
           - Each repo linked to specific collateral
           - Repo expires BEFORE next coupon date
           - Avoids coupon entitlement complications
           - Maximum term: 90 days (3 months)
        
        3. **Settlement Account:**
           - Track daily cash balance
           - Near leg: +cash (borrow) or -cash (lend)
           - Far leg: -cash-interest (borrow) or +cash+interest (lend)
           - Cumulative balance shows funding needs
        
        4. **Analytics:**
           - Outstanding balance over time
           - Gearing ratio evolution
           - Maturity ladder
           - P&L by repo
        
        **Sub-Tabs:**
        - Dashboard (metrics, charts)
        - Historical Analytics (balance, gearing)
        - Settlement Account (daily)
        - Master Table (all repos)
        - P&L Analytics
        - Add Trade
        - Trade Details
        
        **Use Case:** Funding management, gearing optimization, cash planning
        """,
        "key_formulas": [
            "Repo Rate = JIBAR_Forward + Repo_Spread",
            "Interest = Cash × Repo_Rate × (Days/365)",
            "Net Cashflow = Near_Leg + Far_Leg = -Interest"
        ]
    }
}


def render_tab_description(tab_name):
    """Render description for a specific tab"""
    if tab_name in TAB_DESCRIPTIONS:
        desc = TAB_DESCRIPTIONS[tab_name]
        
        with st.expander(f"ℹ️ About {desc['title']}", expanded=False):
            st.markdown(desc['description'])
            
            if 'key_formulas' in desc:
                st.markdown("**Key Formulas:**")
                for formula in desc['key_formulas']:
                    st.code(formula, language="")


def render_all_tab_descriptions():
    """Render descriptions for all tabs"""
    st.markdown("### 📚 Application Guide")
    
    for tab_name, desc in TAB_DESCRIPTIONS.items():
        with st.expander(f"{desc['title']}", expanded=False):
            st.markdown(desc['description'])
            
            if 'key_formulas' in desc:
                st.markdown("**Key Formulas:**")
                for formula in desc['key_formulas']:
                    st.code(formula, language="")
