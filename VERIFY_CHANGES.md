# Verification Guide - Confirm Changes Are Active

## 🎯 How to Verify New Code is Running

After restarting Streamlit, you should see these **IMMEDIATE VISUAL CONFIRMATIONS** in the sidebar:

### 1. Version Display (Top of Sidebar)
```
ℹ️ App Version: v2.0 - Updated 2026-03-03 13:30
```

### 2. Changes Applied Box (Below Version)
```
✅ Changes Applied:
- Historical Time Series default
- Repos at 10 bps
- QuantLib error fixed
```

### 3. Data Source Radio Buttons
```
○ Manual Input
● Historical Time Series  ← Should be SELECTED by default
```

**If you see these 3 things, the new code IS running!**

---

## 🔍 If You DON'T See These

The old code is still running. Try:

### Step 1: Complete Process Kill
```powershell
# Kill ALL Python processes
Get-Process python | Stop-Process -Force

# Wait 5 seconds
Start-Sleep -Seconds 5

# Verify nothing running
Get-Process python
# Should show: "Cannot find a process with the name 'python'"
```

### Step 2: Clear ALL Caches
```powershell
# Python cache
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Streamlit cache
Remove-Item -Recurse -Force "$env:USERPROFILE\.streamlit\cache" -ErrorAction SilentlyContinue
```

### Step 3: Fresh Start
```powershell
# Start Streamlit
streamlit run app.py

# In browser: Hard refresh
# Ctrl+Shift+R (Windows)
# Cmd+Shift+R (Mac)
```

---

## 📊 Verify Repo Data

After confirming new code is running, check repo data:

1. Go to **Repo Trades** tab
2. Click on any repo
3. Check **"Repo Spread (bps)"** field
4. Should show: **10** (not 15, 20, 25, etc.)

---

## 🚨 If STILL Not Working

### Check File Locations
```powershell
# Verify you're in the right directory
Get-Location
# Should show: ...\zaronia_frn

# Check app.py exists and is recent
Get-Item app.py | Select-Object Name, LastWriteTime

# Check for multiple app.py files
Get-ChildItem -Recurse -Filter "app.py"
```

### Check Streamlit Process
```powershell
# See what Streamlit is actually running
Get-Process streamlit | Select-Object Path, StartTime

# Check command line
Get-WmiObject Win32_Process -Filter "name = 'python.exe'" | Select-Object CommandLine
```

### Nuclear Option
```powershell
# 1. Stop everything
taskkill /F /IM python.exe /T
taskkill /F /IM streamlit.exe /T

# 2. Delete ALL Python cache everywhere
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force

# 3. Close browser completely

# 4. Restart computer

# 5. After restart:
cd "C:\Users\GordonFordred\OneDrive - PV01-MMAPP Ltd\Projects\zaronia_frn"
streamlit run app.py
```

---

## ✅ Success Criteria

You'll know it's working when you see:

1. **Sidebar shows:**
   - Version: v2.0 - Updated 2026-03-03 13:30
   - Green box with changes applied
   - Historical Time Series selected by default

2. **No errors:**
   - No QuantLib "negative time" errors
   - App loads without crashes

3. **Repo data:**
   - All repos: 10 bps spread
   - Total outstanding: R30,400,000,000.00
   - 95 repos total

4. **Historical mode works:**
   - Can select different dates
   - Loads market data for that date
   - No errors when changing dates

---

**If you see the version number and green box, the new code IS running!**
