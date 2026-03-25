# 🚀 QUICK START GUIDE

## First Time Setup

### Windows Users

1. **Run the setup script:**
   ```cmd
   setup.bat
   ```

2. **Wait for setup to complete** (may take 10-15 minutes)

3. **Start the application:**
   ```cmd
   start.bat
   ```

4. **Open your browser:**
   - Go to: http://localhost:5173
   - Login with demo account:
     - Email: `demo@argo.com`
     - Password: `demo123`

### macOS/Linux Users

1. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Start backend:**
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   ```

3. **Start frontend (new terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Open browser:**
   - Go to: http://localhost:5173

## Manual Setup (If Scripts Don't Work)

### 1. Start Database

**Using Docker:**
```bash
docker-compose up -d
```

**OR manually:**
- Ensure PostgreSQL is running
- Create database and user (see README.md)

### 2. Setup Backend

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python ingest.py
python build_index.py
python seed.py
python main.py
```

### 3. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### "Module not found" errors
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Database connection errors
- Check PostgreSQL is running: `docker ps` or check service
- Verify credentials in `.env` file
- Ensure PostGIS extension is installed

### Port already in use
- Backend (8000): Change `BACKEND_PORT` in `.env`
- Frontend (5173): Edit `vite.config.ts`

### Frontend not connecting to backend
- Ensure backend is running on http://localhost:8000
- Check browser console for CORS errors
- Verify `.env` CORS_ORIGINS includes frontend URL

## What to Try First

1. **Create an account** or use demo credentials
2. **Ask the AI:** "What's the average ocean temperature?"
3. **Explore the map** - click on data points
4. **View analytics** - check temperature distributions
5. **Try different queries:**
   - "Show me cold water measurements"
   - "What's the salinity in tropical regions?"
   - "Tell me about ARGO floats"

## Need Help?

Check the full [README.md](README.md) for:
- Detailed architecture
- API documentation
- Deployment guide
- Complete troubleshooting

---

**Enjoy exploring the ocean! 🌊**
