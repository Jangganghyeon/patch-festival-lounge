@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)

echo [2/3] Installing or checking packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Starting PATCH Festival Lounge...
".venv\Scripts\python.exe" launcher.py
goto :eof

:error
echo.
echo Start failed. Install Python 3.11 or newer and try again.
pause
exit /b 1
