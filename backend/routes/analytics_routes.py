"""
Advanced Analytics Routes

Provides comprehensive ocean analytics data with geographic filtering support.
All data is returned in a single endpoint call to minimize frontend round-trips.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract
from typing import Optional
import numpy as np
from datetime import datetime

from database import get_db
from models import ArgoProfile
from dependencies import get_current_user
from global_floats import get_region_profiles

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _apply_geo_filter(query, min_lat, max_lat, min_lon, max_lon):
    """Apply geographic bounding box filters to a query."""
    if min_lat is not None:
        query = query.filter(ArgoProfile.latitude >= min_lat)
    if max_lat is not None:
        query = query.filter(ArgoProfile.latitude <= max_lat)
    if min_lon is not None:
        query = query.filter(ArgoProfile.longitude >= min_lon)
    if max_lon is not None:
        query = query.filter(ArgoProfile.longitude <= max_lon)
    return query


@router.get("/region-summary")
async def get_region_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
):
    """Get summary statistics for a geographic region."""
    base = db.query(ArgoProfile)
    base = _apply_geo_filter(base, min_lat, max_lat, min_lon, max_lon)

    total = base.count()
    if total == 0 and min_lat is not None:
        # No local data — fetch from Argovis
        return await _argovis_region_summary(min_lat, max_lat, min_lon, max_lon)

    floats = base.with_entities(func.count(func.distinct(ArgoProfile.float_id))).scalar()
    temp = base.with_entities(
        func.min(ArgoProfile.temperature),
        func.max(ArgoProfile.temperature),
        func.avg(ArgoProfile.temperature),
    ).filter(ArgoProfile.temperature.isnot(None)).first()
    sal = base.with_entities(
        func.min(ArgoProfile.salinity),
        func.max(ArgoProfile.salinity),
        func.avg(ArgoProfile.salinity),
    ).filter(ArgoProfile.salinity.isnot(None)).first()
    depth = base.with_entities(
        func.min(ArgoProfile.depth),
        func.max(ArgoProfile.depth),
        func.avg(ArgoProfile.depth),
    ).filter(ArgoProfile.depth.isnot(None)).first()
    geo = base.with_entities(
        func.min(ArgoProfile.latitude), func.max(ArgoProfile.latitude),
        func.min(ArgoProfile.longitude), func.max(ArgoProfile.longitude),
    ).first()

    return {
        "total_profiles": total,
        "total_floats": floats,
        "temperature": {"min": _f(temp[0]), "max": _f(temp[1]), "avg": _f(temp[2])} if temp[0] is not None else None,
        "salinity": {"min": _f(sal[0]), "max": _f(sal[1]), "avg": _f(sal[2])} if sal[0] is not None else None,
        "depth": {"min": _f(depth[0]), "max": _f(depth[1]), "avg": _f(depth[2])} if depth[0] is not None else None,
        "bounds": {
            "min_lat": _f(geo[0]), "max_lat": _f(geo[1]),
            "min_lon": _f(geo[2]), "max_lon": _f(geo[3]),
        } if geo[0] is not None else None,
    }


@router.get("/full")
async def get_full_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    limit: int = Query(2000, le=5000),
):
    """
    Return all data needed for the analytics dashboard in a single call.
    Supports geographic bounding-box filtering.
    Returns raw arrays for frontend Plotly charts plus pre-computed statistics.
    """
    base = db.query(ArgoProfile)
    base = _apply_geo_filter(base, min_lat, max_lat, min_lon, max_lon)

    rows = base.with_entities(
        ArgoProfile.temperature,
        ArgoProfile.salinity,
        ArgoProfile.depth,
        ArgoProfile.pressure,
        ArgoProfile.latitude,
        ArgoProfile.longitude,
        ArgoProfile.timestamp,
        ArgoProfile.float_id,
    ).limit(limit).all()

    if not rows and min_lat is not None:
        # No local data — fetch from Argovis
        return await _argovis_full_analytics(min_lat, max_lat, min_lon, max_lon, limit)

    if not rows:
        return {"count": 0}

    temps, sals, depths, pressures, lats, lons, timestamps, float_ids = [], [], [], [], [], [], [], []
    for r in rows:
        temps.append(r[0])
        sals.append(r[1])
        depths.append(r[2])
        pressures.append(r[3])
        lats.append(r[4])
        lons.append(r[5])
        timestamps.append(r[6].isoformat() if r[6] else None)
        float_ids.append(r[7])

    # Clean arrays for stats (remove None)
    t_clean = [v for v in temps if v is not None]
    s_clean = [v for v in sals if v is not None]
    d_clean = [v for v in depths if v is not None]

    result = {
        "count": len(rows),
        "temperature": temps,
        "salinity": sals,
        "depth": depths,
        "pressure": pressures,
        "latitude": lats,
        "longitude": lons,
        "timestamp": timestamps,
        "float_id": float_ids,
    }

    # Pre-computed stats
    if t_clean:
        ta = np.array(t_clean)
        result["temp_stats"] = {
            "mean": round(float(np.mean(ta)), 3),
            "median": round(float(np.median(ta)), 3),
            "std": round(float(np.std(ta)), 3),
            "min": round(float(np.min(ta)), 3),
            "max": round(float(np.max(ta)), 3),
            "q1": round(float(np.percentile(ta, 25)), 3),
            "q3": round(float(np.percentile(ta, 75)), 3),
        }
    if s_clean:
        sa = np.array(s_clean)
        result["sal_stats"] = {
            "mean": round(float(np.mean(sa)), 3),
            "median": round(float(np.median(sa)), 3),
            "std": round(float(np.std(sa)), 3),
            "min": round(float(np.min(sa)), 3),
            "max": round(float(np.max(sa)), 3),
            "q1": round(float(np.percentile(sa, 25)), 3),
            "q3": round(float(np.percentile(sa, 75)), 3),
        }
    if d_clean:
        da = np.array(d_clean)
        result["depth_stats"] = {
            "mean": round(float(np.mean(da)), 3),
            "median": round(float(np.median(da)), 3),
            "std": round(float(np.std(da)), 3),
            "min": round(float(np.min(da)), 3),
            "max": round(float(np.max(da)), 3),
        }

    # T-S correlation
    if t_clean and s_clean:
        n = min(len(t_clean), len(s_clean))
        if n > 2:
            corr = np.corrcoef(t_clean[:n], s_clean[:n])[0, 1]
            result["ts_correlation"] = round(float(corr), 4)

    # Unique floats
    result["unique_floats"] = list(set(f for f in float_ids if f))

    return result


@router.get("/map-points")
async def get_analytics_map_points(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(5000, le=10000),
):
    """Get map marker data for the analytics map selector — returns individual profile locations for maximum coverage."""
    rows = db.query(
        ArgoProfile.float_id,
        ArgoProfile.latitude,
        ArgoProfile.longitude,
        ArgoProfile.temperature,
        ArgoProfile.salinity,
        ArgoProfile.depth,
    ).filter(
        ArgoProfile.latitude.isnot(None),
        ArgoProfile.longitude.isnot(None),
    ).limit(limit).all()

    # Deduplicate by (lat, lon) rounded to 2 decimals to avoid stacking,
    # keeping first occurrence (which preserves variety).
    seen = set()
    points = []
    for r in rows:
        key = (round(r.latitude, 2), round(r.longitude, 2))
        if key in seen:
            continue
        seen.add(key)
        points.append({
            "lat": r.latitude,
            "lon": r.longitude,
            "temperature": round(r.temperature, 2) if r.temperature is not None else None,
            "salinity": round(r.salinity, 2) if r.salinity is not None else None,
            "float_id": r.float_id,
        })
    return {"count": len(points), "points": points}


@router.get("/global-floats")
async def get_global_float_positions(
    current_user: dict = Depends(get_current_user),
    refresh: bool = False,
):
    """
    Return latest position of every active ARGO float worldwide.
    Data is fetched from IFREMER ERDDAP and cached for 6 hours.
    Typically returns 3000–4000 floats.
    """
    from global_floats import get_global_floats
    return await get_global_floats(force_refresh=refresh)


def _f(v):
    """Safely convert to float."""
    return round(float(v), 4) if v is not None else None


# ── Argovis fallback helpers ─────────────────────────────────────

async def _argovis_region_summary(min_lat, max_lat, min_lon, max_lon):
    """Build region-summary response from Argovis profiles."""
    try:
        rows = await get_region_profiles(min_lat, max_lat, min_lon, max_lon)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Argovis region fetch failed: %s", e)
        return {"total_profiles": 0, "total_floats": 0}

    if not rows:
        return {"total_profiles": 0, "total_floats": 0}

    temps = [r["temperature"] for r in rows if r["temperature"] is not None]
    sals = [r["salinity"] for r in rows if r["salinity"] is not None]
    depths = [r["depth"] for r in rows if r["depth"] is not None]
    lats = [r["latitude"] for r in rows]
    lons = [r["longitude"] for r in rows]
    floats = list(set(r["float_id"] for r in rows if r["float_id"]))

    return {
        "total_profiles": len(rows),
        "total_floats": len(floats),
        "temperature": {
            "min": _f(min(temps)), "max": _f(max(temps)), "avg": _f(sum(temps) / len(temps))
        } if temps else None,
        "salinity": {
            "min": _f(min(sals)), "max": _f(max(sals)), "avg": _f(sum(sals) / len(sals))
        } if sals else None,
        "depth": {
            "min": _f(min(depths)), "max": _f(max(depths)), "avg": _f(sum(depths) / len(depths))
        } if depths else None,
        "bounds": {
            "min_lat": _f(min(lats)), "max_lat": _f(max(lats)),
            "min_lon": _f(min(lons)), "max_lon": _f(max(lons)),
        },
    }


async def _argovis_full_analytics(min_lat, max_lat, min_lon, max_lon, limit):
    """Build full analytics response from Argovis profiles."""
    try:
        rows = await get_region_profiles(min_lat, max_lat, min_lon, max_lon)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Argovis region fetch failed: %s", e)
        return {"count": 0}

    if not rows:
        return {"count": 0}

    rows = rows[:limit]

    temps = [r["temperature"] for r in rows]
    sals = [r["salinity"] for r in rows]
    depths = [r["depth"] for r in rows]
    pressures = [r["pressure"] for r in rows]
    lats = [r["latitude"] for r in rows]
    lons = [r["longitude"] for r in rows]
    timestamps = [r["timestamp"] for r in rows]
    float_ids = [r["float_id"] for r in rows]

    t_clean = [v for v in temps if v is not None]
    s_clean = [v for v in sals if v is not None]
    d_clean = [v for v in depths if v is not None]

    result = {
        "count": len(rows),
        "temperature": temps,
        "salinity": sals,
        "depth": depths,
        "pressure": pressures,
        "latitude": lats,
        "longitude": lons,
        "timestamp": timestamps,
        "float_id": float_ids,
    }

    if t_clean:
        ta = np.array(t_clean)
        result["temp_stats"] = {
            "mean": round(float(np.mean(ta)), 3),
            "median": round(float(np.median(ta)), 3),
            "std": round(float(np.std(ta)), 3),
            "min": round(float(np.min(ta)), 3),
            "max": round(float(np.max(ta)), 3),
            "q1": round(float(np.percentile(ta, 25)), 3),
            "q3": round(float(np.percentile(ta, 75)), 3),
        }
    if s_clean:
        sa = np.array(s_clean)
        result["sal_stats"] = {
            "mean": round(float(np.mean(sa)), 3),
            "median": round(float(np.median(sa)), 3),
            "std": round(float(np.std(sa)), 3),
            "min": round(float(np.min(sa)), 3),
            "max": round(float(np.max(sa)), 3),
            "q1": round(float(np.percentile(sa, 25)), 3),
            "q3": round(float(np.percentile(sa, 75)), 3),
        }
    if d_clean:
        da = np.array(d_clean)
        result["depth_stats"] = {
            "mean": round(float(np.mean(da)), 3),
            "median": round(float(np.median(da)), 3),
            "std": round(float(np.std(da)), 3),
            "min": round(float(np.min(da)), 3),
            "max": round(float(np.max(da)), 3),
        }

    if t_clean and s_clean:
        n = min(len(t_clean), len(s_clean))
        if n > 2:
            corr = np.corrcoef(t_clean[:n], s_clean[:n])[0, 1]
            result["ts_correlation"] = round(float(corr), 4)

    result["unique_floats"] = list(set(f for f in float_ids if f))
    return result
