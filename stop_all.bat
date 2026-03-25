@echo off
REM Stop all ARGO platform processes
echo Stopping ARGO platform...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ARGO Backend*" >nul 2>&1
taskkill /F /IM node.exe /FI "WINDOWTITLE eq ARGO Frontend*" >nul 2>&1
echo All servers stopped.
