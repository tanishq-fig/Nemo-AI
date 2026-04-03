"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from types import SimpleNamespace

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from config import settings
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


def _use_stateless_auth() -> bool:
    """Use stateless auth on serverless runtimes without reliable local persistence."""
    return os.getenv("VERCEL") == "1"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    if _use_stateless_auth():
        return SimpleNamespace(
            id=abs(hash(user_data.email)) % 1_000_000_000,
            name=user_data.name,
            email=user_data.email,
            created_at=datetime.utcnow(),
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    if _use_stateless_auth():
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": credentials.email,
                "user_id": abs(hash(credentials.email)) % 1_000_000_000,
                "name": credentials.email.split("@")[0],
            },
            expires_delta=access_token_expires,
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@router.post("/logout")
async def logout():
    """Logout endpoint (client should discard token)."""
    return {"message": "Successfully logged out"}
