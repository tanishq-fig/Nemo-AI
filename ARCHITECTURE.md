# 🏗️ SYSTEM ARCHITECTURE

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                    http://localhost:5173                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │ JWT Bearer Token
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      FRONTEND LAYER                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ React + TypeScript + Vite                                  │ │
│  │ • Landing Page (Hero, Features)                            │ │
│  │ • Login/Register Pages (Auth Forms)                        │ │
│  │ • Dashboard (Three-Panel Layout)                           │ │
│  │   - Chat Panel (Left)                                      │ │
│  │   - Ocean Map (Center)                                     │ │
│  │   - Analytics (Right)                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ UI Libraries                                               │ │
│  │ • Tailwind CSS (Styling)                                   │ │
│  │ • Framer Motion (Animations)                               │ │
│  │ • Plotly.js (Charts)                                       │ │
│  │ • Leaflet.js (Maps)                                        │ │
│  │ • Zustand (State)                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │ JSON Payloads
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                       BACKEND LAYER                              │
│                   http://localhost:8000                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FastAPI Application (main.py)                              │ │
│  │ • CORS Middleware                                          │ │
│  │ • OpenAPI/Swagger Docs                                     │ │
│  │ • Health Check Endpoint                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ API Routes                                                 │ │
│  │ • /auth/* (register, login, me, logout)                    │ │
│  │ • /chat/* (query, history, delete)                         │ │
│  │ • /data/* (summary, profiles, floats)                      │ │
│  │ • /visualization/* (map, profile, trajectory)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Authentication Layer                                       │ │
│  │ • JWT Token Generation (auth.py)                           │ │
│  │ • Bcrypt Password Hashing                                  │ │
│  │ • Bearer Token Validation (dependencies.py)                │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ RAG Pipeline (rag.py)                                      │ │
│  │ 1. Query → Embedding (SentenceTransformer)                 │ │
│  │ 2. Vector Search (FAISS)                                   │ │
│  │ 3. Context Retrieval (PostgreSQL)                          │ │
│  │ 4. LLM Generation (OpenAI or Fallback)                     │ │
│  │ 5. Response + History Save                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬───────────────┬────────────────────────┘
                         │               │
                    ┌────▼─────┐    ┌───▼────────┐
                    │ Database │    │   FAISS    │
                    │  Layer   │    │   Index    │
                    └──────────┘    └────────────┘
```

## Data Flow Diagrams

### 1. User Registration Flow

```
┌──────┐   POST /auth/register     ┌─────────┐
│ User │ ───────────────────────────▶│ FastAPI │
└──────┘   {name, email, password}  └────┬────┘
                                         │
                                    Validate
                                         │
                                    ┌────▼─────┐
                                    │ Check if │
                                    │ email    │
                                    │ exists   │
                                    └────┬─────┘
                                         │
                                    Hash Password
                                    (bcrypt)
                                         │
                                    ┌────▼─────┐
                                    │ Insert   │
                                    │ User Row │
                                    │ into DB  │
                                    └────┬─────┘
                                         │
┌──────┐   201 Created + User Data  ┌───▼────┐
│ User │ ◀───────────────────────────│ Return │
└──────┘                             └────────┘
```

### 2. Chat Query Flow (RAG Pipeline)

```
┌──────┐   POST /chat/query         ┌─────────┐
│ User │ ───────────────────────────▶│ FastAPI │
└──────┘   {"query": "..."}         └────┬────┘
                                          │
                                    Verify JWT
                                          │
                                    ┌─────▼──────┐
                                    │ RAG        │
                                    │ Pipeline   │
                                    └─────┬──────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        │                 │                 │
                   ┌────▼────┐      ┌────▼────┐      ┌────▼─────┐
                   │ Generate│      │ Search  │      │ Retrieve │
                   │Embedding│      │ FAISS   │      │ Docs     │
                   │(SentTrf)│      │ Index   │      │ from DB  │
                   └────┬────┘      └────┬────┘      └────┬─────┘
                        │                 │                 │
                        └─────────────────┼─────────────────┘
                                          │
                                    ┌─────▼──────┐
                                    │ Build      │
                                    │ Prompt     │
                                    │ with       │
                                    │ Context    │
                                    └─────┬──────┘
                                          │
                                    ┌─────▼──────┐
                                    │ Call LLM   │
                                    │ (OpenAI or │
                                    │  Fallback) │
                                    └─────┬──────┘
                                          │
                                    ┌─────▼──────┐
                                    │ Save to    │
                                    │ Chat       │
                                    │ History    │
                                    └─────┬──────┘
                                          │
┌──────┐   Response + Context       ┌────▼────┐
│ User │ ◀──────────────────────────│ Return  │
└──────┘                            └─────────┘
```

### 3. Data Ingestion Pipeline

```
┌─────────────┐
│ NetCDF File │
│   or        │
│ Synthetic   │
│   Data      │
└──────┬──────┘
       │
       │ python ingest.py
       │
┌──────▼───────┐
│ Read & Parse │
│ • xarray     │
│ • pandas     │
└──────┬───────┘
       │
┌──────▼───────┐
│ Clean & Val. │
│ • Lat/Lon    │
│ • Ranges     │
│ • NaN Check  │
└──────┬───────┘
       │
┌──────▼───────────────────────┐
│ Store in PostgreSQL          │
│ • argo_profiles table        │
│ • PostGIS geometry (geom)    │
└──────┬───────────────────────┘
       │
┌──────▼───────────────────────┐
│ Generate Semantic Text       │
│ "Oceanographic measurement   │
│  at lat X, lon Y with temp   │
│  Z°C and salinity W PSU..."  │
└──────┬───────────────────────┘
       │
┌──────▼───────────────────────┐
│ Store in argo_documents      │
│ • text field                 │
│ • vector_id (for FAISS)      │
└──────────────────────────────┘
```

### 4. Vector Index Building

```
┌─────────────────┐
│ argo_documents  │
│ table in DB     │
└────────┬────────┘
         │
         │ python build_index.py
         │
┌────────▼─────────┐
│ Load All Docs    │
│ (text field)     │
└────────┬─────────┘
         │
┌────────▼──────────────────┐
│ Generate Embeddings       │
│ • SentenceTransformers    │
│ • all-MiniLM-L6-v2        │
│ • 384-dim vectors         │
└────────┬──────────────────┘
         │
┌────────▼──────────────────┐
│ Build FAISS Index         │
│ • IndexFlatIP             │
│ • Cosine similarity       │
│ • Normalize L2            │
└────────┬──────────────────┘
         │
┌────────▼──────────────────┐
│ Save to Disk              │
│ • faiss_index.bin         │
│ • vector_id_mapping.npy   │
└───────────────────────────┘
```

## Technology Stack Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  React 18 • TypeScript • Tailwind CSS • Framer Motion       │
│  Plotly.js • Leaflet.js • React Router • Zustand            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  FastAPI • Pydantic • Python-Jose • Passlib                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                      BUSINESS LOGIC                          │
│  RAG Pipeline • Authentication • Data Processing             │
│  SentenceTransformers • FAISS • OpenAI Integration          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                       DATA LAYER                             │
│  SQLAlchemy ORM • GeoAlchemy2 • PostgreSQL • PostGIS        │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                          users                               │
├─────────────────────────────────────────────────────────────┤
│ id (PK)            │ INTEGER                                 │
│ name               │ VARCHAR(255)                            │
│ email              │ VARCHAR(255) UNIQUE                     │
│ password_hash      │ VARCHAR(255)                            │
│ created_at         │ TIMESTAMP                               │
└─────────────────────────────────────────────────────────────┘
                     │
                     │ 1:N
                     │
┌────────────────────▼────────────────────────────────────────┐
│                     chat_history                             │
├─────────────────────────────────────────────────────────────┤
│ id (PK)            │ INTEGER                                 │
│ user_id (FK)       │ INTEGER → users.id                      │
│ query              │ TEXT                                    │
│ response           │ TEXT                                    │
│ timestamp          │ TIMESTAMP                               │
│ retrieved_docs     │ TEXT (JSON)                             │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                     argo_profiles                            │
├─────────────────────────────────────────────────────────────┤
│ id (PK)            │ INTEGER                                 │
│ temperature        │ FLOAT                                   │
│ salinity           │ FLOAT                                   │
│ depth              │ FLOAT                                   │
│ latitude           │ FLOAT                                   │
│ longitude          │ FLOAT                                   │
│ timestamp          │ TIMESTAMP                               │
│ geom               │ GEOMETRY(POINT, 4326) ← PostGIS         │
│ float_id           │ VARCHAR(50)                             │
│ cycle_number       │ INTEGER                                 │
│ pressure           │ FLOAT                                   │
└─────────────────────────────────────────────────────────────┘
                     │
                     │ 1:1
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   argo_documents                             │
├─────────────────────────────────────────────────────────────┤
│ id (PK)            │ INTEGER                                 │
│ profile_id (FK)    │ INTEGER → argo_profiles.id              │
│ text               │ TEXT (semantic description)             │
│ vector_id          │ INTEGER (FAISS index reference)         │
│ created_at         │ TIMESTAMP                               │
└─────────────────────────────────────────────────────────────┘
```

## File System Layout

```
jora/
│
├── backend/                    # Python FastAPI Backend
│   ├── main.py                 # Application entry point
│   ├── config.py               # Environment configuration
│   ├── database.py             # DB connection & init
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # JWT & password utilities
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── rag.py                  # RAG pipeline implementation
│   ├── ingest.py               # Data ingestion script
│   ├── build_index.py          # FAISS index builder
│   ├── seed.py                 # Database seeding
│   ├── requirements.txt        # Python dependencies
│   └── routes/                 # API route modules
│       ├── __init__.py
│       ├── auth_routes.py      # /auth/* endpoints
│       ├── chat_routes.py      # /chat/* endpoints
│       └── data_routes.py      # /data/*, /visualization/* endpoints
│
├── frontend/                   # React TypeScript Frontend
│   ├── public/                 # Static assets
│   ├── src/
│   │   ├── components/         # Reusable React components
│   │   │   ├── BubbleBackground.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── OceanMap.tsx
│   │   │   ├── VisualizationPanel.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── pages/              # Page-level components
│   │   │   ├── LandingPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── store/              # State management (Zustand)
│   │   │   └── authStore.ts
│   │   ├── lib/                # Utilities
│   │   │   └── api.ts          # Axios HTTP client
│   │   ├── App.tsx             # Main app with routing
│   │   ├── main.tsx            # Entry point
│   │   ├── index.css           # Global styles
│   │   └── vite-env.d.ts       # TypeScript declarations
│   ├── index.html              # HTML template
│   ├── package.json            # Node.js dependencies
│   ├── vite.config.ts          # Vite configuration
│   ├── tailwind.config.js      # Tailwind CSS config
│   ├── postcss.config.js       # PostCSS config
│   └── tsconfig.json           # TypeScript config
│
├── data/                       # Data storage
│   ├── raw/                    # NetCDF input files
│   ├── faiss_index.bin         # FAISS vector index (generated)
│   └── faiss_index_mapping.npy # Vector ID mapping (generated)
│
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── docker-compose.yml          # PostgreSQL container definition
├── setup.bat                   # Windows automated setup
├── setup.sh                    # Unix/macOS automated setup
├── start.bat                   # Windows quick start
├── README.md                   # Comprehensive documentation
├── QUICKSTART.md               # Quick start guide
├── PROJECT_SUMMARY.md          # Project overview
└── VERIFICATION.md             # Testing checklist
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       PRODUCTION                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌─────────────┐                  │
│  │   Frontend   │         │   Backend   │                  │
│  │   (Nginx)    │◀───────▶│  (Gunicorn) │                  │
│  │   Port 80    │  Proxy  │  Port 8000  │                  │
│  └──────────────┘         └──────┬──────┘                  │
│                                   │                          │
│                          ┌────────▼────────┐                │
│                          │   PostgreSQL    │                │
│                          │   + PostGIS     │                │
│                          │   Port 5432     │                │
│                          └─────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

This architecture ensures:
✅ Separation of concerns
✅ Scalability
✅ Maintainability
✅ Security
✅ Performance
