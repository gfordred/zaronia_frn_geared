@echo off
echo ========================================
echo FORCE RELOAD - Clear All Caches
echo ========================================
echo.

echo Step 1: Stopping any running Streamlit processes...
taskkill /F /IM streamlit.exe 2>nul
timeout /t 2 >nul

echo Step 2: Clearing Python cache...
if exist __pycache__ rmdir /s /q __pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache

echo Step 3: Clearing Streamlit cache...
if exist "%USERPROFILE%\.streamlit" (
    echo Found Streamlit cache directory
    rmdir /s /q "%USERPROFILE%\.streamlit\cache" 2>nul
)

echo Step 4: Deleting any .pyc files...
del /s /q *.pyc 2>nul

echo.
echo ========================================
echo All caches cleared!
echo ========================================
echo.
echo Now run: streamlit run app.py
echo.
echo In browser: Press Ctrl+Shift+R for hard refresh
echo Or press C in Streamlit app to clear cache
echo.
pause
