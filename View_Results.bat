@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run Run_Assignment.bat first to install dependencies and generate results.
    pause
    exit /b 1
)
echo Open the local address printed below in your browser. Ctrl+C stops the server.
".venv\Scripts\python.exe" assignment.py --serve
pause
