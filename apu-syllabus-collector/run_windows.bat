@echo off
setlocal
cd /d "%~dp0"

set "PYEXE="
for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE (
  echo Python 3 is required. Install Python 3.10 or newer and run this file again.
  pause
  exit /b 1
)

"%PYEXE%" -c "import openpyxl, selenium" >nul 2>nul
if errorlevel 1 (
  echo Installing required packages...
  "%PYEXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

"%PYEXE%" app.py
if errorlevel 1 pause
endlocal
