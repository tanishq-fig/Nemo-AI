@echo off
REM ARGO Ocean Intelligence Platform - Windows Setup Script

echo ========================================
echo ARGO Ocean Intelligence Platform Setup
echo ========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found. Please install Python 3.9+
    exit /b 1
)
echo [OK] Python found

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js not found. Please install Node.js 18+
    exit /b 1
)
echo [OK] Node.js found

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [!] Docker not found. Will use manual PostgreSQL setup
    set USE_DOCKER=false
) else (
    echo [OK] Docker found
    set USE_DOCKER=true
)

REM Setup .env file
echo.
echo Setting up environment...
if not exist .env (
    copy .env.example .env
    echo [OK] Created .env file
    echo [!] Please update .env with your credentials
) else (
    echo [OK] .env file exists
)

REM Start PostgreSQL with Docker
if "%USE_DOCKER%"=="true" (
    echo.
    echo Starting PostgreSQL with Docker...
    docker-compose up -d
    echo [OK] PostgreSQL started
    echo [!] Waiting 10 seconds for PostgreSQL to initialize...
    timeout /t 10 /nobreak >nul
) else (
    echo.
    echo Please ensure PostgreSQL is running with PostGIS extension
    echo Run these commands in psql:
    echo   CREATE DATABASE argo_db;
    echo   CREATE USER argo_user WITH PASSWORD 'argo_pass';
    echo   GRANT ALL PRIVILEGES ON DATABASE argo_db TO argo_user;
    echo   \c argo_db
    echo   CREATE EXTENSION postgis;
    pause
)

REM Setup Backend
echo.
echo Setting up backend...
cd backend

REM Create virtual environment
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Python dependencies installed

REM Initialize database
echo.
echo Initializing database...
python -c "from database import init_db; init_db()"
echo [OK] Database initialized

REM Ingest data
echo.
echo Ingesting ARGO data...
python ingest.py
echo [OK] Data ingested

REM Build vector index
echo.
echo Building vector index...
python build_index.py
echo [OK] Vector index built

REM Seed database
echo.
echo Seeding database...
python seed.py
echo [OK] Database seeded

cd ..

REM Setup Frontend
echo.
echo Setting up frontend...
cd frontend

REM Install dependencies
echo Installing Node.js dependencies...
call npm install
echo [OK] Node.js dependencies installed

cd ..

REM Complete
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the application:
echo.
echo 1. Start backend:
echo    cd backend
echo    venv\Scripts\activate
echo    python main.py
echo.
echo 2. Start frontend (in new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo 3. Open browser:
echo    Frontend: http://localhost:5173
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo Demo Account:
echo    Email: demo@argo.com
echo    Password: demo123
echo.
echo ========================================

pause
