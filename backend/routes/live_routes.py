"""Live ARGO data API routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from argo_live import live_fetcher

router = APIRouter(prefix="/live", tags=["live-argo"])


class RegionQuery(BaseModel):
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    use_cache: bool = True


@router.post("/region")
async def fetch_region(query: RegionQuery):
    """
    Fetch ARGO data for a specific region with safe tiling.
    
    Example:
        {
            "lat_min": 40,
            "lat_max": 50,
            "lon_min": -50,
            "lon_max": -40,
            "time_start": "2024-01-01T00:00:00Z",
            "time_end": "2024-12-31T23:59:59Z"
        }
    """
    try:
        result = live_fetcher.fetch_region(
            lat_min=query.lat_min,
            lat_max=query.lat_max,
            lon_min=query.lon_min,
            lon_max=query.lon_max,
            time_start=query.time_start,
            time_end=query.time_end,
            use_cache=query.use_cache
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def fetch_recent(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    Fetch recent ARGO data worldwide.
    
    Parameters:
        - days: Number of days back to fetch (default: 30)
        - limit: Maximum number of profiles (default: 100)
    """
    try:
        result = live_fetcher.fetch_recent(days=days, limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get statistics about cached data."""
    import os
    from pathlib import Path
    
    cache_dir = Path("./cache")
    
    if not cache_dir.exists():
        return {
            "cache_enabled": False,
            "cached_files": 0,
            "total_size_mb": 0
        }
    
    files = list(cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    
    return {
        "cache_enabled": True,
        "cached_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "cache_dir": str(cache_dir.absolute())
    }


@router.delete("/cache")
async def clear_cache():
    """Clear all cached data."""
    import shutil
    from pathlib import Path
    
    cache_dir = Path("./cache")
    
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            cache_dir.mkdir()
            return {"message": "Cache cleared successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")
    
    return {"message": "No cache to clear"}
