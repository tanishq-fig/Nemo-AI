@echo off
REM ========================================
REM Start ARGO Platform (Windows)
REM ========================================

echo.
echo ============================================
echo    Starting ARGO Intelligence Platform
echo ============================================
echo.

REM Kill existing processes
echo [1/3] Stopping existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ARGO Backend*" >nul 2>&1
taskkill /F /IM node.exe /FI "WINDOWTITLE eq ARGO Frontend*" >nul 2>&1

REM Start backend
echo [2/3] Starting backend server...
start "ARGO Backend" cmd /k "cd backend && venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001"

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start frontend
echo [3/3] Starting frontend server...
start "ARGO Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo    Platform Started!
echo ============================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:5173 (or next available port)
echo API Docs: http://localhost:8001/docs
echo.
echo Press any key to stop all servers...
pause >nul

REM Stop everything
echo.
echo Stopping servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ARGO Backend*" >nul 2>&1
taskkill /F /IM node.exe /FI "WINDOWTITLE eq ARGO Frontend*" >nul 2>&1
echo Servers stopped.
