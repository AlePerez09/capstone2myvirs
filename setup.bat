@echo off
REM MyVIRS Team A one-step setup for Windows (Command Prompt or PowerShell).
REM Creates a virtual environment in .venv, installs everything in
REM requirements.txt (spaCy's English model included), and runs the tests.
REM Usage: setup.bat
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install Python 3.10-3.13 from python.org and tick "Add python.exe to PATH".
    exit /b 1
)

echo == Creating .venv
python -m venv .venv || exit /b 1

echo == Installing packages (a few minutes the first time)
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\python -m pip install -r requirements.txt || exit /b 1

echo == Running the tests
.venv\Scripts\python -m pytest tests -q || exit /b 1

echo.
echo Setup done. Activate the environment before running anything:
echo     .venv\Scripts\activate
echo Then try: python priority_ranking.py --text-file data/samples/photosynthesis.txt --subject-aware
