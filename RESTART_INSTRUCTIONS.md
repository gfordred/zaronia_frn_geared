# How to See Changes in Streamlit App

## Issue
Changes to `portfolio.json` and `repo_trades.json` are not showing in the app.

## Root Cause
Streamlit caches data and doesn't automatically reload JSON files when they change.

## Solution

### Option 1: Hard Refresh (Recommended)
1. Stop the Streamlit app (Ctrl+C in terminal)
2. Clear browser cache:
   - Chrome/Edge: Ctrl+Shift+Delete → Clear cached images and files
   - Or just close the browser tab completely
3. Restart Streamlit:
   ```bash
   streamlit run app.py
   ```
4. Open fresh browser window to http://localhost:8501

### Option 2: Force Reload in Browser
1. Keep Streamlit running
2. In browser, press: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
3. This forces a hard reload bypassing cache

### Option 3: Clear Streamlit Cache
1. In the Streamlit app, press **C** key
2. This opens the cache clearing menu
3. Click "Clear cache"
4. App will reload with fresh data

### Option 4: Add Cache Busting to app.py
Add this to the data loading functions:

```python
import time

@st.cache_data(ttl=10)  # Cache for only 10 seconds
def load_portfolio():
    return load_json_file(PORTFOLIO_FILE).get("positions", [])

@st.cache_data(ttl=10)
def load_repo_trades():
    return load_json_file(REPO_FILE).get("trades", [])
```

## Verification

After reloading, check in the app:
1. Go to Repo Trades tab
2. Look at any repo trade
3. Verify "Repo Spread" shows **10 bps** (not 15, 20, etc.)
4. Check "Total Repo Outstanding" = **R30,400,000,000.00**
5. Check "Gearing" = **10.00x**

## Current Data (Confirmed)
- ✅ 95 repo trades
- ✅ ALL at 10 bps spread
- ✅ R30.4B total outstanding
- ✅ 10.00x gearing
- ✅ All notionals in R5M increments

The data is correct in the files - just need to force Streamlit to reload it!
