"""Visualization and data API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from typing import List, Optional

from database import get_db
from models import ArgoProfile, User
from schemas import ArgoProfileResponse, MapDataPoint, DataSummary
from dependencies import get_current_user

router = APIRouter(tags=["data"])


@router.get("/visualization/profile/{profile_id}", response_model=ArgoProfileResponse)
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed ARGO profile by ID."""
    profile = db.query(ArgoProfile).filter(ArgoProfile.id == profile_id).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile


@router.get("/visualization/map")
async def get_map_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(500, le=1000),
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None
):
    """
    Get ARGO profile data for map visualization.
    Groups measurements by unique location to show float profiles.
    Supports geographic bounding box filtering.
    """
    from sqlalchemy import func, desc
    
    # Query to get unique profiles grouped by float_id, timestamp, and location
    # This gives us one point per profile, not one per depth measurement
    query = db.query(
        ArgoProfile.float_id,
        ArgoProfile.latitude,
        ArgoProfile.longitude,
        ArgoProfile.timestamp,
        func.avg(ArgoProfile.temperature).label('avg_temperature'),
        func.avg(ArgoProfile.salinity).label('avg_salinity'),
        func.max(ArgoProfile.depth).label('max_depth'),
        func.count(ArgoProfile.id).label('measurement_count')
    ).group_by(
        ArgoProfile.float_id,
        ArgoProfile.latitude,
        ArgoProfile.longitude,
        ArgoProfile.timestamp
    )
    
    # Apply geographic filters if provided
    if min_lat is not None:
        query = query.filter(ArgoProfile.latitude >= min_lat)
    if max_lat is not None:
        query = query.filter(ArgoProfile.latitude <= max_lat)
    if min_lon is not None:
        query = query.filter(ArgoProfile.longitude >= min_lon)
    if max_lon is not None:
        query = query.filter(ArgoProfile.longitude <= max_lon)
    
    # Order by timestamp descending to get most recent profiles first
    query = query.order_by(desc('timestamp'))
    
    # Get profiles
    profiles = query.limit(limit).all()
    
    # Format for map - one marker per unique profile location
    map_points = []
    for p in profiles:
        map_points.append({
            "lat": p.latitude,
            "lon": p.longitude,
            "temperature": round(p.avg_temperature, 2) if p.avg_temperature else None,
            "salinity": round(p.avg_salinity, 2) if p.avg_salinity else None,
            "depth": round(p.max_depth, 1) if p.max_depth else None,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "float_id": p.float_id,
            "measurements": p.measurement_count
        })
    
    return {
        "count": len(map_points),
        "points": map_points
    }


@router.get("/floats/trajectory")
async def get_float_trajectory(
    float_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trajectory path for a specific ARGO float."""
    profiles = db.query(ArgoProfile).filter(
        ArgoProfile.float_id == float_id
    ).order_by(ArgoProfile.timestamp).all()
    
    if not profiles:
        raise HTTPException(status_code=404, detail="Float not found")
    
    trajectory = []
    for p in profiles:
        trajectory.append({
            "lat": p.latitude,
            "lon": p.longitude,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "temperature": p.temperature,
            "salinity": p.salinity,
            "depth": p.depth
        })
    
    return {
        "float_id": float_id,
        "trajectory": trajectory,
        "total_points": len(trajectory)
    }


@router.get("/data/summary")
async def get_data_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    source: str = Query("local", description="Data source: live (ERDDAP) or local (SQLite)"),
    days: int = Query(30, ge=1, le=365),
):
    """Get summary statistics. Defaults to live ERDDAP, falls back to SQLite."""
    if source == "live":
        try:
            from erddap_service import get_erddap_service
            return get_erddap_service().summary(days=days)
        except Exception:
            pass  # fall through to SQLite

    # SQLite fallback
    total_profiles = db.query(func.count(ArgoProfile.id)).scalar()
    total_floats = db.query(func.count(func.distinct(ArgoProfile.float_id))).scalar()
    temp_stats = db.query(
        func.min(ArgoProfile.temperature),
        func.max(ArgoProfile.temperature),
        func.avg(ArgoProfile.temperature)
    ).filter(ArgoProfile.temperature.isnot(None)).first()
    sal_stats = db.query(
        func.min(ArgoProfile.salinity),
        func.max(ArgoProfile.salinity),
        func.avg(ArgoProfile.salinity)
    ).filter(ArgoProfile.salinity.isnot(None)).first()
    geo_stats = db.query(
        func.min(ArgoProfile.latitude),
        func.max(ArgoProfile.latitude),
        func.min(ArgoProfile.longitude),
        func.max(ArgoProfile.longitude)
    ).first()
    date_stats = db.query(
        func.min(ArgoProfile.timestamp),
        func.max(ArgoProfile.timestamp)
    ).filter(ArgoProfile.timestamp.isnot(None)).first()
    return {
        "total_profiles": total_profiles,
        "total_floats": total_floats,
        "date_range": {
            "start": date_stats[0].isoformat() if date_stats[0] else None,
            "end": date_stats[1].isoformat() if date_stats[1] else None
        },
        "temperature_range": {
            "min": float(temp_stats[0]) if temp_stats[0] else None,
            "max": float(temp_stats[1]) if temp_stats[1] else None,
            "avg": float(temp_stats[2]) if temp_stats[2] else None
        },
        "salinity_range": {
            "min": float(sal_stats[0]) if sal_stats[0] else None,
            "max": float(sal_stats[1]) if sal_stats[1] else None,
            "avg": float(sal_stats[2]) if sal_stats[2] else None
        },
        "geographic_bounds": {
            "min_lat": float(geo_stats[0]) if geo_stats[0] else None,
            "max_lat": float(geo_stats[1]) if geo_stats[1] else None,
            "min_lon": float(geo_stats[2]) if geo_stats[2] else None,
            "max_lon": float(geo_stats[3]) if geo_stats[3] else None
        },
        "source": "local"
    }


@router.get("/data/profiles")
async def get_profiles_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(50, le=500),
    source: str = Query("local", description="Data source: live (ERDDAP) or local (SQLite)"),
    days: int = Query(30, ge=1, le=365),
):
    """Get paginated list of ARGO profiles. Defaults to local SQLite."""
    if source == "live":
        try:
            from erddap_service import get_erddap_service
            return get_erddap_service().profiles_list(limit=limit, days=days)
        except Exception:
            pass  # fall through to SQLite

    # SQLite fallback
    profiles = db.query(ArgoProfile).offset(skip).limit(limit).all()
    total = db.query(func.count(ArgoProfile.id)).scalar()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "profiles": [
            {
                "id": p.id,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "temperature": p.temperature,
                "salinity": p.salinity,
                "depth": p.depth,
                "float_id": p.float_id,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None
            }
            for p in profiles
        ],
        "source": "local"
    }


@router.get("/data/floats")
async def get_floats_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of unique ARGO float IDs."""
    floats = db.query(
        ArgoProfile.float_id,
        func.count(ArgoProfile.id).label('profile_count')
    ).filter(
        ArgoProfile.float_id.isnot(None)
    ).group_by(
        ArgoProfile.float_id
    ).all()
    
    return {
        "floats": [
            {
                "float_id": f[0],
                "profile_count": f[1]
            }
            for f in floats
        ]
    }
