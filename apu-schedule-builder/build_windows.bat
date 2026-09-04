@echo off
setlocal
cd /d "%~dp0"

set "PYEXE="
for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if defined PYEXE goto :python_found

for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if defined PYEXE goto :python_found

echo Python is not installed or is not available.
echo Running the dependency installer...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if not defined PYEXE (
  echo Python installation finished, but Python could not be found.
  echo Close this window and run build_windows.bat again.
  pause
  exit /b 1
)

:python_found
"%PYEXE%" -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  "%PYEXE%" -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

"%PYEXE%" build_site.py --serve
if errorlevel 1 pause
endlocal
