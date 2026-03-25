# ARGO Intelligence — Complete Project Explanation

_Last updated for the current codebase state (March 2026)._  
This document explains how the entire project works end-to-end: architecture, backend, frontend, data sources, AI pipeline, APIs, and operational behavior.

---

## 1) What this project is

ARGO Intelligence is a full-stack ocean analytics platform that lets users:
- authenticate,
- explore global ARGO float positions on maps,
- run region analytics with charts,
- ask natural-language ocean data questions through AI chat.

It combines:
- **React + TypeScript + Vite** frontend,
- **FastAPI + SQLAlchemy** backend,
- **SQLite (or PostgreSQL/PostGIS optional)** data layer,
- **live ocean data providers (Argovis + ERDDAP)**,
- **LLM chat + optional RAG/vector components**.

---

## 2) High-level architecture

## Frontend (browser)
- Runs at `http://localhost:5173` during development.
- Handles login/register/dashboard UI.
- Calls backend REST APIs using Axios (`frontend/src/lib/api.ts`).
- Sends JWT automatically in Authorization header through interceptor.

## Backend (API server)
- Runs at `http://localhost:8001`.
- FastAPI app entrypoint: `backend/main.py`.
- Registers route modules:
  - `auth_routes`
  - `chat_routes`
  - `data_routes`
  - `visualization_routes`
  - `live_routes`
  - `api_routes`
  - `analytics_routes`
- Startup initializes database and tries to initialize RAG pipeline.

## Data + AI services
- Local persistence: `backend/argo.db` (via `DATABASE_URL=sqlite:///./argo.db`).
- Live float/global data: Argovis API (`backend/global_floats.py`).
- Live ERDDAP analytics source: IFREMER ERDDAP (`backend/erddap_service.py`).
- AI chat engine: Gemini-first, then local SQL-driven fallback (`backend/ai_chat_engine.py`).

---

## 3) Backend structure explained

## 3.1 Core platform files
- `backend/main.py`: FastAPI app setup, middleware, routers, startup/shutdown lifecycle.
- `backend/config.py`: environment-driven settings (`.env` support).
- `backend/database.py`: SQLAlchemy engine/session + DB initialization.
- `backend/models.py`: SQLAlchemy models.
- `backend/schemas.py`: Pydantic request/response schemas.
- `backend/dependencies.py`: auth dependency helpers (current user).
- `backend/error_handlers.py`: global HTTP/validation exception handlers.

## 3.2 Database models
Defined in `backend/models.py`:
- `User`
  - id, name, email, password_hash, created_at
- `ArgoProfile`
  - temperature, salinity, depth, latitude, longitude, timestamp,
  - float_id, cycle_number, pressure,
  - optional `geom` when PostGIS is available
- `ArgoDocument`
  - semantic text and vector_id used by RAG/indexing
- `ChatHistory`
  - user_id, query, response, timestamp, retrieved_docs

## 3.3 Auth and security
- JWT creation/validation in `backend/auth.py`.
- Password hashing with bcrypt/passlib.
- Protected routes use `get_current_user` dependency.
- Frontend stores token in `localStorage` and sends `Bearer <token>` automatically.

## 3.4 Route modules

### A) `backend/routes/auth_routes.py`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### B) `backend/routes/chat_routes.py`
- `POST /chat/query`: AI assistant query
- `GET /chat/history`
- `DELETE /chat/history/{chat_id}`

### C) `backend/routes/data_routes.py`
- Local/ERDDAP-backed summary and profile listing endpoints:
  - `/data/summary`
  - `/data/profiles`
  - `/data/floats`
- Map/profile/trajectory utilities:
  - `/visualization/map`
  - `/visualization/profile/{id}`
  - `/floats/trajectory`

### D) `backend/routes/visualization_routes.py`
- `GET /visualization/chart-data`
- Generates chart-ready payloads for:
  - histogram, scatter, depth_profile, heatmap,
  - 3d_scatter, correlation, line
- Uses ERDDAP when requested, then SQLite fallback.

### E) `backend/routes/api_routes.py`
- Live analytics endpoints from ERDDAP service:
  - `/api/temperature-distribution`
  - `/api/salinity-distribution`
  - `/api/temp-salinity`
  - `/api/temp-depth`
  - `/api/map-data`
  - `/api/time-trends`
  - `/api/summary`
  - `/api/cache-info`
  - `/api/cache`

### F) `backend/routes/live_routes.py`
- `/live/region` (safe regional live fetch)
- `/live/recent`
- `/live/stats`
- `/live/cache` (clear)

### G) `backend/routes/analytics_routes.py` (current dashboard-critical module)
- `/analytics/global-floats` → global float positions for maps
- `/analytics/map-points` → local DB points fallback
- `/analytics/full` → all chart arrays/stats for analytics panel
- `/analytics/region-summary` → summary cards for selected region
- Important behavior: when local DB has no rows for selected bbox, it falls back to Argovis regional fetch (`get_region_profiles`).

---

## 4) Data sources and how they are used

## 4.1 SQLite local store (primary persisted dataset)
- Configured by `.env`: `DATABASE_URL=sqlite:///./argo.db`.
- Used for:
  - user accounts,
  - chat history,
  - local ARGO profile analytics,
  - RAG document metadata.

## 4.2 Argovis API (global floats + region fallback)
- Integrated in `backend/global_floats.py`.
- `get_global_floats()`:
  - fetches recent profiles,
  - groups latest position per float,
  - returns thousands of active floats globally.
- `get_region_profiles()`:
  - fetches profile arrays inside selected map bbox,
  - powers analytics fallback when SQLite region has no data.
- Caching:
  - in-memory + disk cache (`backend/cache/global_floats.json`),
  - TTL is 6 hours.

## 4.3 IFREMER ERDDAP (live analytics service)
- Service implementation in `backend/erddap_service.py`.
- Uses streamed CSV requests with circuit-breaker behavior.
- Provides chart-ready transformed payloads and summary metrics.
- Cache TTL in this service defaults to 30 minutes.

---

## 5) AI system and query flow

There are two AI-related paths in this repo:

## 5.1 `AIChatEngine` (actively used by `/chat/query`)
File: `backend/ai_chat_engine.py`

Flow:
1. Receive user query.
2. Try special ERDDAP analytics shortcut for chart-oriented prompts.
3. If LLM available (Gemini key set), use model to plan SQL + chart type.
4. Validate and execute generated SQL (SELECT-only constraints).
5. Generate natural-language answer.
6. Include chart keywords (e.g., `temperature_histogram`) so frontend can auto-render charts.
7. Save result to `chat_history`.

Model behavior:
- Primary: Gemini (`gemini-2.0-flash` in current code).
- If unavailable/failing: local SQL-based fallback response path.

## 5.2 `RAGPipeline` (initialized on startup; optional runtime depending on paths)
File: `backend/rag.py`
- Loads sentence-transformers model for embeddings.
- Loads FAISS index and mapping from disk.
- Retrieves contextual docs + can generate responses with Gemini/OpenAI/fallback.
- In your current runtime logs, FAISS/SWIG warning may appear (DLL load warning), so fallback behavior can be active.

---

## 6) Frontend structure explained

## 6.1 App shell and routing
- `frontend/src/App.tsx` routes:
  - `/` Landing page
  - `/login`
  - `/register`
  - `/dashboard` (protected)
- `ProtectedRoute` guards private pages with auth state.

## 6.2 Global auth state
- `frontend/src/store/authStore.ts` (Zustand)
  - `login`, `register`, `logout`, `fetchUser`
  - stores JWT in `localStorage`
  - hydrates auth state on refresh

## 6.3 API client
- `frontend/src/lib/api.ts`
  - Axios instance
  - base URL: `VITE_API_URL` or `http://localhost:8001`
  - request interceptor injects bearer token
  - response interceptor handles 401 by clearing token and redirecting login

## 6.4 Dashboard tabs and core panels
File: `frontend/src/pages/DashboardPage.tsx`
- Tabs:
  - Explore
  - AI Chat
  - Analytics
- Keeps panel components mounted by tab visibility strategy.

### A) Explore tab → `OceanMap.tsx`
- Fetches `/analytics/global-floats` + `/data/summary`.
- Uses Leaflet + marker clustering.
- Displays global active floats on dark basemap with popups/legend.

### B) Analytics tab → `VisualizationPanel.tsx`
- Loads global floats (same endpoint) for selectable map.
- Supports shift+drag region selection.
- Calls:
  - `/analytics/full`
  - `/analytics/region-summary`
- Renders many Plotly charts and computed stats.

### C) AI Chat tab → `ChatPanel.tsx`
- Sends queries to `/chat/query`.
- Detects chart keywords from query/response.
- Calls `/visualization/chart-data` for chart payloads.
- Renders Plotly charts inline under messages.

---

## 7) End-to-end request flows

## 7.1 Login flow
1. User submits login form.
2. Frontend calls `POST /auth/login`.
3. Receives JWT token.
4. Stores token in localStorage.
5. Calls `GET /auth/me` to hydrate user profile.

## 7.2 Explore map flow
1. `OceanMap` requests `/analytics/global-floats`.
2. Backend fetches Argovis (or returns cached copy).
3. Frontend clusters markers and displays global floats.

## 7.3 Analytics region flow
1. User shift-drags bbox on analytics map.
2. Frontend requests `/analytics/full` + `/analytics/region-summary` with bbox params.
3. Backend queries local SQLite first.
4. If no local rows, backend fetches Argovis region profiles and builds fallback response.
5. Frontend updates summary cards and charts.

## 7.4 Chat flow
1. User asks question in Chat tab.
2. Frontend calls `POST /chat/query`.
3. Backend AI engine plans SQL + optional chart keyword.
4. SQL executes on local DB; answer generated.
5. Frontend optionally auto-loads chart data when chart keyword is present.

---

## 8) Runtime/developer operations

## 8.1 Common local URLs
- Frontend: `http://localhost:5173`
- Backend API root: `http://localhost:8001`
- Health: `http://localhost:8001/health`

## 8.2 Startup patterns
- Backend typically started with `uvicorn main:app --host 0.0.0.0 --port 8001`.
- Frontend with `npm run dev` in `frontend`.

## 8.3 Typical startup warning you may see
- RAG warning about `_swigfaiss` DLL import can appear.
- This usually impacts FAISS-dependent vector path, but app can still run using fallback logic.

---

## 9) Configuration and environment

Main backend env vars in `backend/.env`:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Frontend env:
- `VITE_API_URL` (optional override of backend URL)

---

## 10) Project strengths and current behavior notes

## Strengths
- Multiple data-source strategy (local + live fallback).
- Resilient API design with graceful fallbacks.
- Good user flow: auth → map → analytics → AI chat.
- Rich charting and geospatial UI.

## Current behavior notes
- Several older docs mention port 8000, but current runtime/config uses 8001.
- Legacy documentation still references OpenAI-first in places; active chat path is Gemini-first in current code.
- There are both ERDDAP and Argovis integrations; the map/global float path is currently Argovis-driven in analytics endpoints.

---

## 11) Where to look first (quick map)

If you want to understand/modify quickly:
1. API bootstrap: `backend/main.py`
2. Dashboard analytics: `backend/routes/analytics_routes.py` + `frontend/src/components/VisualizationPanel.tsx`
3. Global float map: `backend/global_floats.py` + `frontend/src/components/OceanMap.tsx`
4. AI chat: `backend/ai_chat_engine.py` + `backend/routes/chat_routes.py` + `frontend/src/components/ChatPanel.tsx`
5. Auth flow: `backend/routes/auth_routes.py` + `frontend/src/store/authStore.ts`

---

## 12) Short plain-English summary

This project is a modern ocean-data intelligence app: users log in, see global ARGO floats on an interactive map, select regions to run analytics, and ask an AI assistant questions that can trigger chart generation. The backend combines local SQL analytics with live-source fallbacks (Argovis/ERDDAP), while the frontend provides a smooth dashboard experience with Leaflet and Plotly.
