@echo off
setlocal
cd /d "%~dp0"

set "PYEXE="
for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE (
  echo Python is not installed. Install Python 3 from https://www.python.org/downloads/ and run this again.
  pause
  exit /b 1
)

"%PYEXE%" -c "import sounddevice, soundfile, numpy" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  "%PYEXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

rem pythonw: no console window
set "PYW=%PYEXE:python.exe=pythonw.exe%"
if exist "%PYW%" (
  start "" "%PYW%" app.py
) else (
  "%PYEXE%" app.py
)
