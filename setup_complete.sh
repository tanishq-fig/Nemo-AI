#!/bin/bash
# ========================================
# ARGO Platform Complete Setup (Linux/Mac)
# ========================================

echo ""
echo "============================================"
echo "   ARGO Intelligence Platform Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.11+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+"
    exit 1
fi

echo "[1/6] Setting up Python environment..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet
cd ..

echo "[2/6] Setting up frontend dependencies..."
cd frontend
npm install --silent
cd ..

echo "[3/6] Creating database tables..."
cd backend
./venv/bin/python -c "from database import init_db; init_db(); print('Database initialized')"

echo "[4/6] Checking data files..."
if [ -z "$(ls -A backend/data/raw/*.nc 2>/dev/null)" ]; then
    echo "WARNING: No NetCDF files found."
    echo "Run: python backend/fetch_live_data.py --source erddap --limit 50"
    echo "Or download manually from https://data-argo.ifremer.fr/"
fi

echo "[5/6] Building FAISS index..."
if [ -n "$(ls -A backend/data/raw/*.nc 2>/dev/null)" ]; then
    ./venv/bin/python build_index.py
else
    echo "SKIP: No data files to index"
fi

echo "[6/6] Creating cache directory..."
mkdir -p backend/cache
cd ..

echo ""
echo "============================================"
echo "   Setup Complete!"
echo "============================================"
echo ""
echo "To start the platform:"
echo "  Linux/Mac: ./start_all.sh"
echo "  Or manually:"
echo "    Backend:  cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8001"
echo "    Frontend: cd frontend && npm run dev"
echo ""
echo "Documentation:"
echo "  - README.md"
echo "  - QUICKSTART.md"
echo "  - API_DOCUMENTATION.md"
echo ""
