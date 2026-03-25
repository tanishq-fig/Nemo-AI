#!/bin/bash
# ========================================
# Start ARGO Platform (Linux/Mac)
# ========================================

echo ""
echo "============================================"
echo "   Starting ARGO Intelligence Platform"
echo "============================================"
echo ""

# Kill existing processes
echo "[1/3] Stopping existing processes..."
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null

# Start backend
echo "[2/3] Starting backend server..."
cd backend
source venv/bin/activate
nohup python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd ..

# Wait a bit
sleep 3

# Start frontend
echo "[3/3] Starting frontend server..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
cd ..

echo ""
echo "============================================"
echo "   Platform Started!"
echo "============================================"
echo ""
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:5173 (or next available port)"
echo "API Docs: http://localhost:8001/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f logs/backend.log"
echo "  Frontend: tail -f logs/frontend.log"
echo ""
echo "To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  or: pkill -f 'uvicorn main:app' && pkill -f 'vite'"
echo ""

# Save PIDs for easy stopping
echo "$BACKEND_PID" > logs/backend.pid
echo "$FRONTEND_PID" > logs/frontend.pid
