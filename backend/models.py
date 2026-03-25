"""Database models for the ARGO oceanographic platform."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config import settings

# Only import and use PostGIS for PostgreSQL
HAS_POSTGIS = False
if "postgresql" in settings.DATABASE_URL.lower():
    try:
        from geoalchemy2 import Geometry
        HAS_POSTGIS = True
    except ImportError:
        pass

from database import Base
import datetime


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class ArgoProfile(Base):
    """ARGO float profile data model with PostGIS geometry."""
    __tablename__ = "argo_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=True)
    salinity = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # PostGIS geometry column for spatial queries (only if PostGIS available)
    if HAS_POSTGIS:
        geom = Column(Geometry('POINT', srid=4326), nullable=True)
    
    # Additional metadata
    float_id = Column(String(50), nullable=True, index=True)
    cycle_number = Column(Integer, nullable=True)
    pressure = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<ArgoProfile(id={self.id}, lat={self.latitude}, lon={self.longitude})>"


class ArgoDocument(Base):
    """Semantic text documents for RAG system."""
    __tablename__ = "argo_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey('argo_profiles.id'), nullable=True)
    text = Column(Text, nullable=False)
    vector_id = Column(Integer, nullable=False, index=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ArgoDocument(id={self.id}, vector_id={self.vector_id})>"


class ChatHistory(Base):
    """Chat conversation history."""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Context metadata
    retrieved_docs = Column(Text, nullable=True)  # JSON string of retrieved document IDs
    
    # Relationships
    user = relationship("User", back_populates="chat_history")
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, user_id={self.user_id})>"
