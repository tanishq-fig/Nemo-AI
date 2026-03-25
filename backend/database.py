"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create SQLAlchemy engine
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and PostGIS extension."""
    from sqlalchemy import text
    
    # Check if using PostgreSQL
    if "postgresql" in settings.DATABASE_URL:
        # Enable PostGIS extension
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
                print("✓ PostGIS extension enabled")
            except Exception as e:
                print(f"PostGIS extension may already exist: {e}")
    else:
        print("[OK] Using SQLite (PostGIS features disabled)")
    
    # Import all models to ensure they're registered
    from models import User, ArgoProfile, ArgoDocument, ChatHistory
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
print("[OK] Database tables created successfully")
