@echo off
REM Quick Start Script - Starts both backend and frontend

echo ========================================
echo Starting ARGO Ocean Intelligence Platform
echo ========================================

REM Start backend in new window
echo Starting backend server...
start "ARGO Backend" cmd /k "cd backend && venv\Scripts\activate && python main.py"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "ARGO Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Servers Starting...
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop servers
echo ========================================

pause
