"""
Global ARGO Float Fetcher

Fetches all active ARGO floats worldwide from the Argovis API,
groups by float ID to get the latest position per float,
and caches results server-side for performance.
"""
import httpx
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Cache ────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "global_floats.json"
CACHE_MAX_AGE_SECONDS = 6 * 3600  # 6 hours

_memory_cache: Optional[Dict] = None
_memory_cache_ts: float = 0.0


def _read_cache() -> Optional[Dict]:
    """Return cached data if fresh, else None."""
    global _memory_cache, _memory_cache_ts
    now = time.time()
    if _memory_cache and (now - _memory_cache_ts) < CACHE_MAX_AGE_SECONDS:
        return _memory_cache
    if CACHE_FILE.exists():
        age = now - CACHE_FILE.stat().st_mtime
        if age < CACHE_MAX_AGE_SECONDS:
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                _memory_cache = data
                _memory_cache_ts = CACHE_FILE.stat().st_mtime
                return data
            except Exception:
                pass
    return None


def _write_cache(data: Dict) -> None:
    global _memory_cache, _memory_cache_ts
    try:
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
        _memory_cache = data
        _memory_cache_ts = time.time()
    except Exception as e:
        logger.warning("Cache write failed: %s", e)


# ── Argovis API ──────────────────────────────────────────────────
ARGOVIS_BASE = "https://argovis-api.colorado.edu/argo"
LOOKBACK_DAYS = 10  # captures ~4000 unique active floats


async def _fetch_from_argovis() -> List[Dict]:
    """
    Fetch recent ARGO profiles from Argovis API (compression=minimal),
    then group by platform to keep only the latest position per float.

    Argovis minimal format per row:
    [profile_id, longitude, latitude, timestamp, sources, metadata_ids]
    """
    now = datetime.utcnow()
    t_start = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    t_end = now.strftime("%Y-%m-%dT23:59:59Z")

    url = (
        f"{ARGOVIS_BASE}"
        f"?startDate={t_start}"
        f"&endDate={t_end}"
        f"&compression=minimal"
    )

    logger.info("Fetching global floats from Argovis …")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        profiles = resp.json()

    if not profiles or not isinstance(profiles, list):
        return []

    # Group by platform_number (first part of profile_id before '_')
    # Keep only the most recent profile per platform
    latest: Dict[str, List] = {}
    for row in profiles:
        if not isinstance(row, list) or len(row) < 4:
            continue
        profile_id = row[0]  # e.g. "2902928_016"
        lon = row[1]
        lat = row[2]
        ts = row[3]  # ISO timestamp

        if lat is None or lon is None:
            continue

        platform = profile_id.split("_")[0]
        if platform not in latest or ts > latest[platform][3]:
            latest[platform] = row

    floats: List[Dict] = []
    for platform, row in latest.items():
        lon = row[1]
        lat = row[2]
        ts = row[3]
        sources = row[4] if len(row) > 4 else []
        floats.append({
            "float_id": platform,
            "lat": round(float(lat), 4),
            "lon": round(float(lon), 4),
            "temperature": None,
            "salinity": None,
            "pressure": None,
            "timestamp": ts,
            "sources": sources if isinstance(sources, list) else [],
        })

    logger.info("Argovis returned %d unique floats from %d profiles",
                len(floats), len(profiles))
    return floats


# ── Public API ───────────────────────────────────────────────────

async def get_global_floats(force_refresh: bool = False) -> Dict:
    """
    Return {count, floats, cached_at} with one entry per active ARGO float.
    Uses 6-hour disk+memory cache.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            return cached

    try:
        floats = await _fetch_from_argovis()
    except Exception as e:
        logger.error("Argovis fetch failed: %s", e)
        if CACHE_FILE.exists():
            try:
                return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        raise

    result = {
        "count": len(floats),
        "floats": floats,
        "cached_at": datetime.utcnow().isoformat() + "Z",
    }
    _write_cache(result)
    return result


# ── Region profile fetch ─────────────────────────────────────────

async def get_region_profiles(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    days_back: int = 30,
) -> List[Dict]:
    """
    Fetch detailed ARGO profiles from Argovis for a bounding box.
    Returns a list of flattened measurements suitable for analytics.
    Each profile contributes one row with surface-level measurements.
    """
    now = datetime.utcnow()
    t_start = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    t_end = now.strftime("%Y-%m-%dT23:59:59Z")

    # Argovis box format: [[minLon, minLat], [maxLon, maxLat]]
    box = f"[[{min_lon},{min_lat}],[{max_lon},{max_lat}]]"

    logger.info("Fetching Argovis profiles for box=%s", box)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(ARGOVIS_BASE, params={
            "startDate": t_start,
            "endDate": t_end,
            "box": box,
            "data": "temperature,salinity,pressure",
        })
        resp.raise_for_status()
        profiles = resp.json()

    if not profiles or not isinstance(profiles, list):
        return []

    rows: List[Dict] = []
    for p in profiles:
        geo = p.get("geolocation", {})
        coords = geo.get("coordinates", [None, None])
        lon, lat = coords[0], coords[1]
        if lat is None or lon is None:
            continue

        profile_id = p.get("_id", "")
        platform = profile_id.split("_")[0]
        ts = p.get("timestamp")

        # data is [[temps...], [sals...], [pressures...]]
        # data_info[0] tells us the order of variables
        data_info = p.get("data_info", [])
        data_arrays = p.get("data", [])

        var_names = data_info[0] if data_info else []
        var_idx = {name: i for i, name in enumerate(var_names)}

        temp_arr = data_arrays[var_idx["temperature"]] if "temperature" in var_idx and var_idx["temperature"] < len(data_arrays) else []
        sal_arr = data_arrays[var_idx["salinity"]] if "salinity" in var_idx and var_idx["salinity"] < len(data_arrays) else []
        pres_arr = data_arrays[var_idx["pressure"]] if "pressure" in var_idx and var_idx["pressure"] < len(data_arrays) else []

        # Take surface measurement (index 0) and also the deepest
        # For analytics charts we want one representative row per profile
        if not temp_arr and not sal_arr:
            continue

        # Surface values (shallowest measurement)
        temp_surface = temp_arr[0] if temp_arr else None
        sal_surface = sal_arr[0] if sal_arr else None
        pres_surface = pres_arr[0] if pres_arr else None

        # Max depth (deepest pressure)
        pres_max = max((v for v in pres_arr if v is not None), default=None) if pres_arr else None
        depth = round(pres_max * 1.019716, 1) if pres_max is not None else None

        rows.append({
            "float_id": platform,
            "latitude": round(float(lat), 4),
            "longitude": round(float(lon), 4),
            "temperature": round(float(temp_surface), 3) if temp_surface is not None else None,
            "salinity": round(float(sal_surface), 3) if sal_surface is not None else None,
            "pressure": round(float(pres_surface), 1) if pres_surface is not None else None,
            "depth": depth,
            "timestamp": ts,
        })

    logger.info("Argovis region query returned %d profiles", len(rows))
    return rows
