#!/bin/bash
# Stop all ARGO platform processes
echo "Stopping ARGO platform..."
pkill -f "uvicorn main:app"
pkill -f "vite"
rm -f logs/*.pid
echo "All servers stopped."
