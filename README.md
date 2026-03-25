# ARGO Ocean Intelligence Platform

## 🌊 Overview

A production-grade, AI-driven conversational intelligence platform for analyzing ARGO oceanographic float data. This full-stack application combines React, FastAPI, SQLite/PostgreSQL with PostGIS, FAISS vector search, and retrieval-augmented generation (RAG) to provide an intuitive interface for exploring ocean temperature, salinity, and float trajectories.

**NEW**: Live ARGO data streaming with intelligent caching and safe region tiling!

## ✨ Features

### Core Capabilities
- ✅ **AI Chat Interface** - Natural language queries about ocean data
- ✅ **RAG Pipeline** - Contextual retrieval + LLM generation
- ✅ **Live Data Streaming** - Real-time ARGO GDAC integration
- ✅ **Interactive Visualizations** - Plotly.js charts and graphs
- ✅ **Geographic Maps** - Leaflet.js with float positions
- ✅ **Smart Caching** - 24-hour TTL for API responses
- ✅ **Error Resilience** - Graceful fallbacks and retry logic
- ✅ **Offline Mode** - Works with local dataset

### Backend
- **FastAPI** REST API with comprehensive endpoints
- **SQLite/PostgreSQL + PostGIS** for spatial data
- **SQLAlchemy ORM** with automatic table creation
- **JWT Authentication** with bcrypt password hashing
- **RAG Pipeline** using SentenceTransformers and FAISS
- **NetCDF Data Ingestion** for ARGO float data
- **Vector Embeddings** for semantic search (384-dim)
- **Live ARGO Integration** with safe tiling system
- **Intelligent Caching** with disk persistence
- **Error Handlers** for production reliability

### Frontend
- **React + TypeScript** with Vite
- **Tailwind CSS** with ocean-themed design
- **Framer Motion** animations
- **Plotly.js** for data visualization
- **Leaflet.js** for interactive maps
- **Glassmorphism** UI effects
- **Bubble animations** (ocean research aesthetic)
- **Responsive Layout** - Three-panel dashboard

### AI System
- **Three-Tier Fallback**: Google Gemini Pro → OpenAI GPT-4o → Intelligent Local
- **Free Tier Support**: Works without any API keys
- **Context-Aware**: RAG retrieves relevant data before generation
- **Scientific Accuracy**: Trained on oceanographic concepts

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- (Optional) PostgreSQL 14+ with PostGIS
- (Optional) Google Gemini or OpenAI API key

## 🚀 Quick Start

### Automatic Setup (Recommended)

**Windows:**
```cmd
setup_complete.bat
start_all.bat
```

**Linux/macOS:**
```bash
chmod +x *.sh
./setup_complete.sh
./start_all.sh
```

Then open: http://localhost:5173

### Manual Setup

See detailed instructions in `INSTALL.md`
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt

# 5. Initialize database and load data
python ingest.py
python build_index.py
python seed.py

# 6. Start backend server
python main.py

# 7. In a new terminal, set up frontend
cd ..\frontend
npm install
npm run dev
```

### Option 2: Manual PostgreSQL Setup

If you have PostgreSQL installed locally:

```bash
# 1. Create database
psql -U postgres
CREATE DATABASE argo_db;
CREATE USER argo_user WITH PASSWORD 'argo_pass';
GRANT ALL PRIVILEGES ON DATABASE argo_db TO argo_user;
\c argo_db
CREATE EXTENSION postgis;
\q

# 2. Update .env with your database credentials
# Then follow steps 4-7 from Option 1
```

## 📂 Project Structure

```
jora/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   ├── dependencies.py      # FastAPI dependencies
│   ├── rag.py               # RAG pipeline
│   ├── ingest.py            # Data ingestion script
│   ├── build_index.py       # Vector index builder
│   ├── seed.py              # Database seeding
│   ├── requirements.txt     # Python dependencies
│   └── routes/
│       ├── auth_routes.py   # Auth endpoints
│       ├── chat_routes.py   # Chat endpoints
│       └── data_routes.py   # Data endpoints
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── store/           # State management
│   │   ├── lib/             # Utilities
│   │   ├── App.tsx          # Main app component
│   │   └── main.tsx         # Entry point
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── data/
│   └── raw/                 # NetCDF files location
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Configuration

### Backend Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://argo_user:argo_pass@localhost:5432/argo_db

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI (Optional)
OPENAI_API_KEY=your-openai-api-key

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# CORS
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Vector Index
FAISS_INDEX_PATH=./data/faiss_index.bin
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Data
NETCDF_DATA_DIR=./data/raw
```

## 📊 Data Pipeline

### 1. Data Ingestion

```bash
cd backend
python ingest.py
```

This script:
- Reads NetCDF files from `data/raw/`
- Extracts temperature, salinity, depth, coordinates
- Cleans and validates data
- Stores in PostgreSQL with PostGIS geometry
- Generates semantic text descriptions
- If no NetCDF files found, generates 100 synthetic samples

### 2. Vector Index Building

```bash
python build_index.py
```

This script:
- Loads documents from database
- Generates embeddings using SentenceTransformers
- Builds FAISS index for fast similarity search
- Saves index to disk

### 3. Database Seeding

```bash
python seed.py
```

Creates demo user:
- Email: `demo@argo.com`
- Password: `demo123`

## 🎯 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout

### Chat
- `POST /chat/query` - Send query to RAG system
- `GET /chat/history` - Get chat history
- `DELETE /chat/history/{id}` - Delete chat message

### Data & Visualization
- `GET /visualization/profile/{id}` - Get profile details
- `GET /visualization/map` - Get map data points
- `GET /floats/trajectory` - Get float trajectory
- `GET /data/summary` - Get data statistics
- `GET /data/profiles` - List profiles (paginated)
- `GET /data/floats` - List unique floats

## 🎨 Frontend Features

### Pages
- **Landing Page** - Hero section with feature showcase
- **Login/Register** - Authentication with validation
- **Dashboard** - Main application interface

### Components
- **ChatPanel** - Conversational AI interface
- **OceanMap** - Interactive Leaflet map with temperature gradients
- **VisualizationPanel** - Plotly charts and statistics
- **BubbleBackground** - Animated ocean-themed background

### Theme
- Deep ocean gradient backgrounds
- Glassmorphism cards
- Coral accent colors
- Floating bubble animations
- Scientific dashboard aesthetic

## 🧪 Testing the System

1. **Start both servers**
   - Backend: `http://localhost:8000`
   - Frontend: `http://localhost:5173`

2. **Create an account**
   - Navigate to `http://localhost:5173`
   - Click "Get Started" or "Sign Up"
   - Register with your details

3. **Explore the dashboard**
   - Chat with AI about ocean data
   - View interactive map
   - Analyze temperature/salinity distributions

4. **Or use demo account**
   - Email: `demo@argo.com`
   - Password: `demo123`

## 📝 Sample Queries

Try asking the AI assistant:

- "What's the average ocean temperature in the dataset?"
- "Show me measurements from the Pacific Ocean"
- "What's the salinity range in tropical waters?"
- "Tell me about ARGO float trajectories"
- "What depths were measured?"

## 🛠️ Development

### Backend Development

```bash
cd backend
venv\Scripts\activate
python main.py
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend Development

```bash
cd frontend
npm run dev
# App available at http://localhost:5173
```

### Database Management

View PostgreSQL data:
```bash
psql -U argo_user -d argo_db
\dt  # List tables
SELECT COUNT(*) FROM argo_profiles;
SELECT COUNT(*) FROM argo_documents;
```

## 🔒 Security

- Passwords hashed with bcrypt
- JWT tokens for authentication
- CORS configured for frontend origin
- SQL injection protected by SQLAlchemy ORM
- Input validation with Pydantic schemas

## 🚀 Production Deployment

1. **Update environment variables**
   - Set strong `SECRET_KEY`
   - Use production database credentials
   - Configure proper CORS origins

2. **Backend deployment**
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Frontend deployment**
   ```bash
   npm run build
   # Deploy dist/ folder to hosting service
   ```

## 📦 API Endpoints

### Authentication (`/auth`)
- `POST /auth/register` - Create new account
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout

### Chat (`/chat`)
- `POST /chat/query` - Ask AI questions about ocean data

### Data (`/data`)
- `GET /data/summary` - Dataset statistics
- `GET /data/map` - Geographic float locations
- `GET /data/profiles` - Raw profile data

### Visualizations (`/visualization`)
- `GET /visualization/temperature-distribution` - Histogram
- `GET /visualization/salinity-boxplot` - Box plot
- `GET /visualization/temp-salinity-scatter` - Scatter plot
- `GET /visualization/depth-profile` - Depth chart

### Live ARGO (`/live`) ⭐ NEW
- `POST /live/region` - Fetch specific region with tiling
- `GET /live/recent` - Fetch recent worldwide data
- `GET /live/stats` - Cache statistics
- `DELETE /live/cache` - Clear cache

**Interactive Documentation**: http://localhost:8001/docs

---

## 📚 Documentation

- **[INSTALL.md](INSTALL.md)** - Detailed installation instructions
- **[DEMO_GUIDE.md](DEMO_GUIDE.md)** - Complete demo walkthrough
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Full API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[DATA_STATUS.md](DATA_STATUS.md)** - Current dataset information
- **[GEMINI_API_SETUP.md](GEMINI_API_SETUP.md)** - AI configuration guide

---

## 📦 Dependencies

### Backend
- fastapi - Web framework
- sqlalchemy - ORM
- psycopg2-binary - PostgreSQL adapter
- geoalchemy2 - PostGIS support
- python-jose - JWT handling
- passlib - Password hashing
- sentence-transformers - Embeddings
- faiss-cpu - Vector search
- xarray, netCDF4 - NetCDF processing
- openai - LLM integration (optional)

### Frontend
- react, react-dom - UI framework
- react-router-dom - Routing
- framer-motion - Animations
- plotly.js - Visualizations
- leaflet - Maps
- axios - HTTP client
- zustand - State management
- tailwindcss - Styling

## 🐛 Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check credentials in `.env`
- Verify PostGIS extension is installed

### FAISS Index Not Found
- Run `python build_index.py`
- Ensure data ingestion completed first

### Frontend API Errors
- Check backend is running on port 8000
- Verify CORS settings in backend config
- Check browser console for details

### No Data in Dashboard
- Run `python ingest.py` to load data
- Check database has profiles: `SELECT COUNT(*) FROM argo_profiles;`

## 📄 License

This project is for educational and research purposes.

## 🙏 Acknowledgments

- ARGO Float Program for oceanographic data
- Finding Nemo for ocean theme inspiration
- OpenAI for LLM capabilities

---

**Built with ❤️ for ocean research and data science**
