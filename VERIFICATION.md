# ✅ SYSTEM VERIFICATION CHECKLIST

Use this checklist to verify your ARGO Ocean Intelligence Platform is working correctly.

## Prerequisites Check

- [ ] Python 3.9+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] PostgreSQL running (Docker or local)
- [ ] Git installed (optional)

## Setup Verification

### Backend Setup
- [ ] Virtual environment created (`backend/venv/` exists)
- [ ] Dependencies installed (no errors in `pip install`)
- [ ] `.env` file exists in root directory
- [ ] Database initialized (no errors)
- [ ] Sample data ingested (100 profiles created)
- [ ] FAISS index built (`data/faiss_index.bin` exists)
- [ ] Demo user created (`demo@argo.com`)

### Frontend Setup
- [ ] Node modules installed (`frontend/node_modules/` exists)
- [ ] No TypeScript errors
- [ ] No Tailwind CSS errors
- [ ] Build completes successfully

## Functional Testing

### Backend API
Start backend: `cd backend && python main.py`

- [ ] Server starts on port 8000
- [ ] Visit http://localhost:8000 (shows welcome message)
- [ ] Visit http://localhost:8000/docs (Swagger UI loads)
- [ ] Health check: http://localhost:8000/health (returns healthy)

### Frontend App
Start frontend: `cd frontend && npm run dev`

- [ ] Server starts on port 5173
- [ ] Visit http://localhost:5173 (landing page loads)
- [ ] No console errors in browser DevTools
- [ ] Animations working (bubbles floating)

### Authentication Flow
- [ ] Click "Sign Up" button
- [ ] Register new account (form validation works)
- [ ] Redirected to dashboard after registration
- [ ] Logout button works
- [ ] Login with demo account: demo@argo.com / demo123
- [ ] Redirected to dashboard

### Dashboard Features
Logged in to dashboard:

#### Chat Panel (Left)
- [ ] Chat interface visible
- [ ] Can send message
- [ ] AI responds (may take 5-10 seconds)
- [ ] Message history persists
- [ ] Loading animation during query

Test queries:
- [ ] "What's the average ocean temperature?"
- [ ] "Tell me about salinity measurements"
- [ ] "Show me the data range"

#### Ocean Map (Center)
- [ ] Map loads (Leaflet.js)
- [ ] Data points visible (colored dots)
- [ ] Can zoom in/out
- [ ] Can pan map
- [ ] Click on point shows popup
- [ ] Legend visible at bottom
- [ ] Colors match temperature ranges

#### Visualization Panel (Right)
- [ ] Summary cards show numbers
- [ ] Total Profiles count > 0
- [ ] Active Floats count > 0
- [ ] Temperature histogram renders
- [ ] Salinity histogram renders
- [ ] Statistics table shows data
- [ ] Charts are interactive (hover works)

### API Endpoint Testing
Using http://localhost:8000/docs:

#### Auth Endpoints
- [ ] POST /auth/register (201 created)
- [ ] POST /auth/login (200 OK, returns token)
- [ ] GET /auth/me (200 OK with user data)

#### Chat Endpoints
- [ ] POST /chat/query (200 OK with response)
- [ ] GET /chat/history (200 OK with array)

#### Data Endpoints
- [ ] GET /data/summary (200 OK with stats)
- [ ] GET /data/profiles (200 OK with array)
- [ ] GET /visualization/map (200 OK with points)

## Database Verification

Connect to PostgreSQL:
```sql
-- Check tables exist
\dt

-- Check data counts
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM argo_profiles;
SELECT COUNT(*) FROM argo_documents;
SELECT COUNT(*) FROM chat_history;

-- Check PostGIS
SELECT PostGIS_Version();

-- Sample profile
SELECT * FROM argo_profiles LIMIT 1;
```

Expected results:
- [ ] 4 tables created
- [ ] At least 1 user
- [ ] 100 argo_profiles
- [ ] 100 argo_documents
- [ ] PostGIS version shown
- [ ] Profile has temperature, salinity, lat, lon, geom

## Performance Checks

- [ ] Backend starts in < 10 seconds
- [ ] Frontend builds in < 30 seconds
- [ ] Page loads in < 3 seconds
- [ ] Chat responses in < 10 seconds
- [ ] Map renders in < 5 seconds
- [ ] Charts render in < 3 seconds

## Error Handling

Test error scenarios:

- [ ] Login with wrong password (shows error)
- [ ] Register with existing email (shows error)
- [ ] Register with short password (shows validation error)
- [ ] Access /dashboard without login (redirects to /login)
- [ ] Backend stopped → frontend shows connection error

## Browser Compatibility

Test in browsers:
- [ ] Chrome/Edge (recommended)
- [ ] Firefox
- [ ] Safari

## Mobile Responsiveness

Test on mobile viewport:
- [ ] Landing page responsive
- [ ] Login page responsive
- [ ] Dashboard adjusts layout
- [ ] All text readable
- [ ] Buttons touchable

## File Structure Verification

Check these files exist:

### Root
- [ ] .env
- [ ] .gitignore
- [ ] docker-compose.yml
- [ ] README.md
- [ ] QUICKSTART.md
- [ ] PROJECT_SUMMARY.md
- [ ] setup.bat / setup.sh
- [ ] start.bat

### Backend
- [ ] backend/main.py
- [ ] backend/config.py
- [ ] backend/database.py
- [ ] backend/models.py
- [ ] backend/schemas.py
- [ ] backend/auth.py
- [ ] backend/rag.py
- [ ] backend/ingest.py
- [ ] backend/build_index.py
- [ ] backend/seed.py
- [ ] backend/requirements.txt
- [ ] backend/routes/*.py

### Frontend
- [ ] frontend/package.json
- [ ] frontend/vite.config.ts
- [ ] frontend/tailwind.config.js
- [ ] frontend/src/App.tsx
- [ ] frontend/src/main.tsx
- [ ] frontend/src/components/*.tsx
- [ ] frontend/src/pages/*.tsx
- [ ] frontend/src/store/authStore.ts

### Data
- [ ] data/raw/ directory
- [ ] data/faiss_index.bin (after build_index.py)

## Common Issues & Solutions

### Database connection failed
```bash
# Check PostgreSQL is running
docker ps
# or
psql -U argo_user -d argo_db
```

### Port already in use
```bash
# Find process using port 8000 (Windows)
netstat -ano | findstr :8000
# Kill process
taskkill /PID <process_id> /F
```

### Module not found errors
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend won't start
```bash
cd frontend
rm -rf node_modules
npm install
```

## Success Criteria

✅ **System is working if:**
1. Both servers start without errors
2. Can register and login
3. Dashboard loads with all 3 panels
4. Chat responds to queries
5. Map shows data points
6. Charts render correctly
7. No console errors
8. Database has 100 profiles

## Need Help?

If any check fails:
1. Read the error message carefully
2. Check the relevant section in README.md
3. Verify prerequisites are installed
4. Check .env configuration
5. Restart servers
6. Check database connectivity

---

**When all checks pass, your system is production-ready!** 🎉
