# ARGO Intelligence Platform - Installation Guide

## System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 2GB free space
- **OS**: Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+)

### Required Software
1. **Python 3.11+**
   - Windows: https://www.python.org/downloads/
   - macOS: `brew install python@3.11`
   - Linux: `sudo apt install python3.11 python3.11-venv`

2. **Node.js 18+**
   - Windows/macOS: https://nodejs.org/
   - Linux: `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt install nodejs`

3. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

---

## Quick Installation

### Windows

1. **Download/Clone the project**
   ```cmd
   git clone <repository-url> jora
   cd jora
   ```

2. **Run automatic setup**
   ```cmd
   setup_complete.bat
   ```

3. **Start the platform**
   ```cmd
   start_all.bat
   ```

4. **Access the application**
   - Frontend: http://localhost:5173 (or displayed port)
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs

### Linux / macOS

1. **Download/Clone the project**
   ```bash
   git clone <repository-url> jora
   cd jora
   ```

2. **Make scripts executable**
   ```bash
   chmod +x *.sh
   ```

3. **Run automatic setup**
   ```bash
   ./setup_complete.sh
   ```

4. **Start the platform**
   ```bash
   ./start_all.sh
   ```

5. **Access the application**
   - Frontend: http://localhost:5173 (or displayed port)
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs

---

## Manual Installation

If automatic setup fails, follow these steps:

### Backend Setup

1. **Navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate.bat
   
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python -c "from database import init_db; init_db()"
   ```

5. **Download sample data (optional)**
   ```bash
   python fetch_live_data.py --source erddap --limit 50
   ```

6. **Build FAISS index**
   ```bash
   python build_index.py
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment (optional)**
   ```bash
   # Create .env file
   echo "VITE_API_URL=http://localhost:8001" > .env
   ```

---

## Configuration

### Backend Configuration (`.env`)

Create `backend/.env`:

```env
# Database
DATABASE_URL=sqlite:///./ocean_data.db

# Security
SECRET_KEY=your-secret-key-change-in-production

# AI APIs (optional)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
```

### Frontend Configuration (`.env`)

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8001
```

---

## Getting Real ARGO Data

The platform works with local historical data by default. To fetch real-time data:

### Method 1: Automated Fetch
```bash
cd backend
python fetch_live_data.py --source erddap --limit 100
```

### Method 2: Manual Download
1. Visit: https://data-argo.ifremer.fr/
2. Navigate to: dac/aoml/ or dac/coriolis/
3. Download NetCDF (.nc) files
4. Place in: `backend/data/raw/`

### Method 3: Live Streaming (in-app)
Use the live data endpoints from the dashboard:
- `/live/recent` - Fetch recent profiles
- `/live/region` - Fetch specific region

---

## Running the Platform

### Start Both Servers

**Windows:**
```cmd
start_all.bat
```

**Linux/macOS:**
```bash
./start_all.sh
```

### Start Individually

**Backend:**
```bash
cd backend
# Windows
venv\Scripts\activate.bat
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Linux/macOS
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## Stopping the Platform

### Windows
```cmd
stop_all.bat
```
Or press Ctrl+C in both terminal windows

### Linux/macOS
```bash
./stop_all.sh
```
Or:
```bash
pkill -f "uvicorn main:app"
pkill -f "vite"
```

---

## Troubleshooting

### Python not found
- Ensure Python 3.11+ is installed
- Add Python to PATH environment variable
- Try `python3` instead of `python`

### Node not found
- Install Node.js 18+
- Restart terminal after installation

### Port already in use
- Backend (8001): Change BACKEND_PORT in `backend/.env`
- Frontend (5173): Vite will automatically use next available port

### Database errors
```bash
cd backend
rm ocean_data.db argo_data.db
python -c "from database import init_db; init_db()"
```

### Missing NetCDF files
```bash
cd backend
python fetch_live_data.py --source erddap --limit 50
python build_index.py
```

### FAISS index errors
```bash
cd backend
rm data/faiss_index.*
python build_index.py
```

### Permission errors (Linux/macOS)
```bash
chmod +x *.sh
chmod +x backend/venv/bin/*
```

---

## Verification

After installation, verify everything works:

1. **Backend API**
   - Visit: http://localhost:8001
   - Should see: {"message": "ARGO Oceanographic Intelligence Platform API"}

2. **API Documentation**
   - Visit: http://localhost:8001/docs
   - Should see: Interactive API documentation

3. **Frontend**
   - Visit: http://localhost:5173
   - Should see: Landing page with login/register

4. **Database**
   ```bash
   cd backend
   python -c "from database import get_db; from models import OceanProfile; db = next(get_db()); print(f'Profiles: {db.query(OceanProfile).count()}')"
   ```

5. **FAISS Index**
   ```bash
   cd backend
   python -c "import os; print(f'Index exists: {os.path.exists(\"data/faiss_index.bin\")}')"
   ```

---

## Next Steps

After successful installation:

1. **Register an account** at http://localhost:5173/register
2. **Login** and explore the dashboard
3. **Chat with the AI** about ocean data
4. **View visualizations** - graphs and maps
5. **Fetch live data** using the live endpoints

For detailed usage, see: `DEMO_GUIDE.md`

---

## Getting Help

- **Issues**: Check `logs/` directory for error details
- **Documentation**: See `README.md`, `API_DOCUMENTATION.md`
- **Data Status**: See `DATA_STATUS.md`
- **API Setup**: See `GEMINI_API_SETUP.md` for AI configuration
