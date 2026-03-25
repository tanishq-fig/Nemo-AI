@echo off
REM ========================================
REM ARGO Platform Complete Setup (Windows)
REM ========================================

echo.
echo ============================================
echo    ARGO Intelligence Platform Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    exit /b 1
)

echo [1/6] Setting up Python environment...
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
cd ..

echo [2/6] Setting up frontend dependencies...
cd frontend
call npm install --silent
cd ..

echo [3/6] Creating database tables...
cd backend
call venv\Scripts\python.exe -c "from database import init_db; init_db(); print('Database initialized')"

echo [4/6] Checking data files...
if not exist backend\data\raw\*.nc (
    echo WARNING: No NetCDF files found.
    echo Run: python backend\fetch_live_data.py --source erddap --limit 50
    echo Or download manually from https://data-argo.ifremer.fr/
)

echo [5/6] Building FAISS index...
if exist backend\data\raw\*.nc (
    call venv\Scripts\python.exe build_index.py
) else (
    echo SKIP: No data files to index
)

echo [6/6] Creating cache directory...
if not exist backend\cache (
    mkdir backend\cache
)
cd ..

echo.
echo ============================================
echo    Setup Complete!
echo ============================================
echo.
echo To start the platform:
echo   Windows: start_all.bat
echo   Or manually:
echo     Backend:  cd backend ^&^& venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
echo     Frontend: cd frontend ^&^& npm run dev
echo.
echo Documentation:
echo   - README.md
echo   - QUICKSTART.md
echo   - API_DOCUMENTATION.md
echo.

pause
