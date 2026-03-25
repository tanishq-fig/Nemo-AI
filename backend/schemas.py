"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Authentication Schemas
class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for user data response."""
    id: int
    name: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Chat Schemas
class ChatQuery(BaseModel):
    """Schema for chat query request."""
    query: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    """Schema for chat response."""
    query: str
    response: str
    timestamp: datetime
    retrieved_context: Optional[List[str]] = None


# ARGO Data Schemas
class ArgoProfileResponse(BaseModel):
    """Schema for ARGO profile data."""
    id: int
    temperature: Optional[float]
    salinity: Optional[float]
    depth: Optional[float]
    latitude: float
    longitude: float
    timestamp: Optional[datetime]
    float_id: Optional[str]
    
    class Config:
        from_attributes = True


class MapDataPoint(BaseModel):
    """Schema for map visualization points."""
    lat: float
    lon: float
    temperature: Optional[float]
    salinity: Optional[float]
    timestamp: Optional[str]


class DataSummary(BaseModel):
    """Schema for data summary statistics."""
    total_profiles: int
    total_floats: int
    date_range: dict
    temperature_range: dict
    salinity_range: dict
    geographic_bounds: dict
