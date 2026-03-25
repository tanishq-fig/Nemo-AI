@echo off
REM ARGO Ocean Intelligence Platform - One-Click Setup & Run
REM This script installs dependencies, sets up the database, and starts the application.

echo ===================================================
echo ARGO Ocean Intelligence Platform - Setup ^& Run
echo ===================================================

REM 1. Check Prerequisites
echo.
echo [1/5] Checking Prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
echo [OK] Prerequisites found.

REM 2. Backend Setup
echo.
echo [2/5] Setting up Backend...
cd backend

REM Create .env if missing
if not exist .env (
    copy .env.example .env >nul
    echo [OK] Created .env file (SQLite default)
)

REM Setup Virtual Environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Install Dependencies
echo Installing Python dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [X] Failed to install Python dependencies.
    pause
    exit /b 1
)

REM Initialize Database
echo Initializing database...
venv\Scripts\python.exe -c "from database import init_db; init_db()"

REM Ingest Data
echo Checking/Ingesting data...
venv\Scripts\python.exe ingest.py

REM Build Index (Fixed config required)
echo Building vector index...
venv\Scripts\python.exe build_index.py

REM Seed Database
echo Seeding database...
venv\Scripts\python.exe seed.py

cd ..

REM 3. Frontend Setup
echo.
echo [3/5] Setting up Frontend...
cd frontend
echo Installing Node.js dependencies...
call npm install --silent
cd ..

REM 4. Start Application
echo.
echo [4/5] Starting Application...
echo.
echo Backend will run on http://localhost:8001
echo Frontend will run on http://localhost:5173
echo.
echo Opening Backend in new window...
start "ARGO Backend" cmd /k "cd backend && venv\Scripts\python.exe main.py"

echo Opening Frontend in new window...
start "ARGO Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [5/5] Launching Browser...
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ===================================================
echo Setup & Start Complete!
echo Do not close the backend/frontend terminal windows.
echo ===================================================
pause
