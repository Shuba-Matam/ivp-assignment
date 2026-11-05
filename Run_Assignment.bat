@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -u assignment.py --all
if errorlevel 1 goto failed
echo.
echo All experiments finished. Open outputs or run View_Results.bat.
pause
exit /b 0
:failed
echo.
echo The assignment could not complete. Read the error above.
pause
exit /b 1
