"""
Live ERDDAP Analytics API Routes

Provides chart-ready JSON endpoints powered by real-time ARGO data
from the IFREMER ERDDAP service.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from erddap_service import get_erddap_service

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/temperature-distribution")
async def temperature_distribution(
    limit: int = Query(5000, ge=100, le=50000),
    days: int = Query(1, ge=1, le=365),
    time_min: Optional[str] = Query(None, description="ISO datetime, e.g. 2025-01-01T00:00:00Z"),
    time_max: Optional[str] = Query(None, description="ISO datetime"),
):
    """Temperature distribution histogram from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.temperature_distribution(limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/salinity-distribution")
async def salinity_distribution(
    limit: int = Query(5000, ge=100, le=50000),
    days: int = Query(1, ge=1, le=365),
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """Salinity distribution histogram from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.salinity_distribution(limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/temp-salinity")
async def temp_salinity(
    limit: int = Query(5000, ge=100, le=50000),
    days: int = Query(1, ge=1, le=365),
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """Temperature vs Salinity scatter plot from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.temp_salinity(limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/temp-depth")
async def temp_depth(
    limit: int = Query(5000, ge=100, le=50000),
    days: int = Query(1, ge=1, le=365),
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """Temperature vs Depth profile from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.temp_depth(limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/map-data")
async def map_data(
    limit: int = Query(2000, ge=100, le=20000),
    days: int = Query(1, ge=1, le=365),
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """Float location map data from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.map_data(limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/time-trends")
async def time_trends(
    variable: str = Query("temp", description="Variable: temp or psal"),
    limit: int = Query(5000, ge=100, le=50000),
    days: int = Query(7, ge=1, le=365),
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
):
    """Time trends (daily averages) from live ERDDAP ARGO data."""
    if variable not in ("temp", "psal"):
        raise HTTPException(status_code=400, detail="variable must be 'temp' or 'psal'")
    try:
        svc = get_erddap_service()
        return svc.time_trends(variable=variable, limit=limit, days=days, time_min=time_min, time_max=time_max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/summary")
async def summary(
    days: int = Query(1, ge=1, le=365),
    limit: int = Query(5000, ge=100, le=50000),
):
    """Summary statistics from live ERDDAP ARGO data."""
    try:
        svc = get_erddap_service()
        return svc.summary(limit=limit, days=days)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ERDDAP fetch failed: {e}")


@router.get("/cache-info")
async def cache_info():
    """Get ERDDAP cache statistics."""
    svc = get_erddap_service()
    return svc.cache_info()


@router.delete("/cache")
async def clear_cache():
    """Clear the ERDDAP data cache."""
    svc = get_erddap_service()
    svc.clear_cache()
    return {"message": "ERDDAP cache cleared"}
