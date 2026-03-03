@echo off
echo ======================================================================
echo Starting Streamlit with Debug Output
echo ======================================================================
echo.
echo Look for these messages in the terminal:
echo   1. "ZAR FRN Trading Platform - v2.0"
echo   2. "DEBUG: Loaded XX repo trades"
echo   3. "DEBUG: All at 10 bps: True"
echo.
echo If you see these messages, the new code IS running!
echo.
echo ======================================================================
echo.

streamlit run app.py

pause
