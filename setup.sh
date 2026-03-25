#!/bin/bash

# ARGO Ocean Intelligence Platform - Setup Script
# This script automates the complete setup process

set -e  # Exit on error

echo "========================================"
echo "ARGO Ocean Intelligence Platform Setup"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found. Please install Python 3.9+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found${NC}"

# Check Docker (optional)
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker found${NC}"
    USE_DOCKER=true
else
    echo -e "${YELLOW}⚠ Docker not found. Will use manual PostgreSQL setup${NC}"
    USE_DOCKER=false
fi

# Setup .env file
echo -e "\n${YELLOW}Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${YELLOW}→ Please update .env with your credentials${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Start PostgreSQL
if [ "$USE_DOCKER" = true ]; then
    echo -e "\n${YELLOW}Starting PostgreSQL with Docker...${NC}"
    docker-compose up -d
    echo -e "${GREEN}✓ PostgreSQL started${NC}"
    echo -e "${YELLOW}→ Waiting 10 seconds for PostgreSQL to initialize...${NC}"
    sleep 10
else
    echo -e "\n${YELLOW}Please ensure PostgreSQL is running with PostGIS extension${NC}"
    echo -e "Run these commands in psql:"
    echo "  CREATE DATABASE argo_db;"
    echo "  CREATE USER argo_user WITH PASSWORD 'argo_pass';"
    echo "  GRANT ALL PRIVILEGES ON DATABASE argo_db TO argo_user;"
    echo "  \\c argo_db"
    echo "  CREATE EXTENSION postgis;"
    read -p "Press enter when ready to continue..."
fi

# Setup Backend
echo -e "\n${YELLOW}Setting up backend...${NC}"
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Initialize database
echo -e "\n${YELLOW}Initializing database...${NC}"
python -c "from database import init_db; init_db()"
echo -e "${GREEN}✓ Database initialized${NC}"

# Ingest data
echo -e "\n${YELLOW}Ingesting ARGO data...${NC}"
python ingest.py
echo -e "${GREEN}✓ Data ingested${NC}"

# Build vector index
echo -e "\n${YELLOW}Building vector index...${NC}"
python build_index.py
echo -e "${GREEN}✓ Vector index built${NC}"

# Seed database
echo -e "\n${YELLOW}Seeding database...${NC}"
python seed.py
echo -e "${GREEN}✓ Database seeded${NC}"

cd ..

# Setup Frontend
echo -e "\n${YELLOW}Setting up frontend...${NC}"
cd frontend

# Install dependencies
echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
npm install
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

cd ..

# Complete
echo -e "\n========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "========================================"
echo -e "\n${YELLOW}To start the application:${NC}"
echo -e "\n1. Start backend:"
echo -e "   cd backend"
echo -e "   source venv/bin/activate  # or venv\\Scripts\\activate on Windows"
echo -e "   python main.py"
echo -e "\n2. Start frontend (in new terminal):"
echo -e "   cd frontend"
echo -e "   npm run dev"
echo -e "\n3. Open browser:"
echo -e "   Frontend: ${GREEN}http://localhost:5173${NC}"
echo -e "   Backend API: ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "\n${YELLOW}Demo Account:${NC}"
echo -e "   Email: demo@argo.com"
echo -e "   Password: demo123"
echo -e "\n========================================"
