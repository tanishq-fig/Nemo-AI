"""
ERDDAP Live Data Service

Fetches, caches, and processes live ARGO ocean data from the IFREMER ERDDAP API.
Provides analytics-ready methods for all chart types the frontend expects.
"""

import csv
import io
import logging
import math
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

ERDDAP_BASE = "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats"
COLUMNS = ["platform_number", "time", "latitude", "longitude", "temp", "psal", "pres"]
FLOAT_COLS = {"latitude", "longitude", "temp", "psal", "pres"}


class ERDDAPService:
    """Fetches and caches live ARGO data from IFREMER ERDDAP."""

    def __init__(self, cache_ttl: int = 1800):
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.cache_ttl = cache_ttl  # 30 min default
        self.connect_timeout = 10   # fail fast if server is unreachable
        self.read_timeout = 90      # allow time for large CSV streams
        self._server_down_until: float = 0  # circuit breaker timestamp

    # ------------------------------------------------------------------ cache
    def _cache_get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                if time.time() - self._cache_ts.get(key, 0) < self.cache_ttl:
                    return self._cache[key]
                del self._cache[key]
                del self._cache_ts[key]
        return None

    def _cache_set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = value
            self._cache_ts[key] = time.time()

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
            self._cache_ts.clear()

    def cache_info(self) -> Dict:
        with self._lock:
            now = time.time()
            breaker_remaining = max(0, self._server_down_until - now)
            return {
                "keys": len(self._cache),
                "active": sum(
                    1 for k in self._cache_ts if now - self._cache_ts[k] < self.cache_ttl
                ),
                "ttl_seconds": self.cache_ttl,
                "server_reachable": breaker_remaining == 0,
                "circuit_breaker_seconds": round(breaker_remaining, 1),
            }

    # ------------------------------------------------------------------ fetch
    @staticmethod
    def _build_url(
        variables: List[str], constraints: List[str], fmt: str = "csv"
    ) -> str:
        url = f"{ERDDAP_BASE}.{fmt}?{','.join(variables)}"
        for c in constraints:
            url += f"&{c}"
        return url

    def fetch_profiles(
        self,
        limit: int = 5000,
        days: int = 1,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> List[Dict]:
        """Fetch ARGO profiles from ERDDAP.  Returns list of dicts.
        
        Uses streaming to cap rows without downloading the full response
        (ArgoFloats can return 300k+ rows/day). 
        Always fetches a standard batch (max of limit and 5000) and caches
        by time window so all analytics methods share one fetch.
        """
        fetch_size = max(limit, 5000)  # always fetch at least 5000 to share cache

        # Circuit breaker: skip fetch if server was recently unreachable
        if time.time() < self._server_down_until:
            logger.info("ERDDAP circuit breaker active — skipping fetch")
            return []

        constraints: List[str] = []
        if time_min:
            constraints.append(f"time>={time_min}")
        else:
            start = (datetime.utcnow() - timedelta(days=days)).strftime(
                "%Y-%m-%dT00:00:00Z"
            )
            constraints.append(f"time>={start}")
        if time_max:
            constraints.append(f"time<={time_max}")
        else:
            constraints.append(
                f"time<={datetime.utcnow().strftime('%Y-%m-%dT23:59:59Z')}"
            )

        # Cache by time window only (not limit) so all analytics share one fetch
        cache_key = f"profiles_{'_'.join(constraints)}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info("ERDDAP cache hit (%d records)", len(cached))
            return cached[:limit]

        url = self._build_url(COLUMNS, constraints + ['orderBy("time")'])
        try:
            records = self._stream_fetch(url, fetch_size)
        except (requests.ConnectionError, requests.Timeout):
            self._server_down_until = time.time() + 60  # pause 60s
            logger.error("ERDDAP server unreachable — circuit breaker set for 60s")
            return []
        if records is not None:
            self._server_down_until = 0  # server is responding, reset breaker
            self._cache_set(cache_key, records)
            return records[:limit]

        # Fallback: shrink to 1-day window (only if server responded but query failed)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
        fb_constraints = [
            f"time>={yesterday}",
            f"time<={datetime.utcnow().strftime('%Y-%m-%dT23:59:59Z')}",
        ]
        url2 = self._build_url(COLUMNS, fb_constraints + ['orderBy("time")'])
        try:
            records = self._stream_fetch(url2, fetch_size)
        except (requests.ConnectionError, requests.Timeout):
            self._server_down_until = time.time() + 60
            logger.error("ERDDAP server unreachable on fallback — circuit breaker set")
            return []
        if records is not None:
            self._cache_set(cache_key, records)
            return records[:limit]

        logger.error("ERDDAP fetch failed entirely")
        return []

    def _stream_fetch(self, url: str, limit: int) -> Optional[List[Dict]]:
        """Stream CSV from ERDDAP line-by-line, stopping after `limit` data rows.
        
        Returns:
            list of records on success, empty list on 404/no data, None on error.
        Raises:
            requests.ConnectionError on connectivity failure (so caller can skip fallback).
        """
        try:
            resp = requests.get(url, timeout=(self.connect_timeout, self.read_timeout), stream=True)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200:
                logger.warning("ERDDAP HTTP %d", resp.status_code)
                return None

            records: List[Dict] = []
            header: Optional[List[str]] = None
            skip_units = True  # second line is units row

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.strip()
                if not line:
                    continue

                if header is None:
                    header = [c.strip() for c in line.split(",")]
                    continue
                if skip_units:
                    skip_units = False
                    continue

                parts = line.split(",")
                rec: Dict[str, Any] = {}
                for col, val in zip(header, parts):
                    val = val.strip()
                    if col in FLOAT_COLS:
                        try:
                            rec[col] = float(val) if val and val != "NaN" else None
                        except ValueError:
                            rec[col] = None
                    else:
                        rec[col] = val if val and val != "NaN" else None
                records.append(rec)

                if len(records) >= limit:
                    break

            resp.close()
            logger.info("ERDDAP streamed %d records from %s", len(records), url[:80])
            return records

        except (requests.ConnectionError, requests.Timeout) as exc:
            logger.warning("ERDDAP unreachable: %s", exc)
            raise  # let caller know server is down — don't bother retrying
        except Exception as exc:
            logger.warning("ERDDAP stream error: %s", exc)
        return None

    @staticmethod
    def _parse_csv(text: str) -> List[Dict]:
        """Parse ERDDAP CSV (header + units row + data rows)."""
        lines = text.strip().split("\n")
        if len(lines) < 3:
            return []
        # line 0 = column names, line 1 = units, line 2+ = data
        cleaned = lines[0] + "\n" + "\n".join(lines[2:])
        reader = csv.DictReader(io.StringIO(cleaned))
        records: List[Dict] = []
        for row in reader:
            rec: Dict[str, Any] = {}
            for col, val in row.items():
                if not col:
                    continue
                val = (val or "").strip()
                if col in FLOAT_COLS:
                    try:
                        rec[col] = float(val) if val and val != "NaN" else None
                    except ValueError:
                        rec[col] = None
                else:
                    rec[col] = val if val and val != "NaN" else None
            records.append(rec)
        return records

    # ----------------------------------------------------------- analytics

    def temperature_distribution(self, **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        values = [r["temp"] for r in records if r.get("temp") is not None]
        return {
            "type": "histogram",
            "title": "Temperature Distribution",
            "data": values,
            "stats": _stats(values),
            "metadata": {
                "xlabel": "Temperature (\u00b0C)",
                "ylabel": "Frequency",
                "variable": "temperature",
            },
        }

    def salinity_distribution(self, **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        values = [r["psal"] for r in records if r.get("psal") is not None]
        return {
            "type": "histogram",
            "title": "Salinity Distribution",
            "data": values,
            "stats": _stats(values),
            "metadata": {
                "xlabel": "Salinity (PSU)",
                "ylabel": "Frequency",
                "variable": "salinity",
            },
        }

    def temp_salinity(self, **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        pairs = [
            (r["temp"], r["psal"])
            for r in records
            if r.get("temp") is not None and r.get("psal") is not None
        ]
        if not pairs:
            return {
                "type": "scatter",
                "title": "Temperature vs Salinity",
                "data": {"x": [], "y": []},
                "correlation": 0,
                "metadata": {
                    "xlabel": "Temperature (\u00b0C)",
                    "ylabel": "Salinity (PSU)",
                },
            }
        x, y = zip(*pairs)
        return {
            "type": "scatter",
            "title": "Temperature vs Salinity",
            "data": {"x": list(x), "y": list(y)},
            "correlation": _pearson(list(x), list(y)),
            "metadata": {
                "xlabel": "Temperature (\u00b0C)",
                "ylabel": "Salinity (PSU)",
            },
        }

    def temp_depth(self, **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        pairs = [
            (r["temp"], r["pres"])
            for r in records
            if r.get("temp") is not None and r.get("pres") is not None
        ]
        if not pairs:
            return {
                "type": "depth_profile",
                "title": "Temperature vs Depth",
                "data": {"temperature": [], "depth": []},
                "metadata": {
                    "xlabel": "Temperature (\u00b0C)",
                    "ylabel": "Pressure / Depth (dbar)",
                },
            }
        temps, depths = zip(*pairs)
        return {
            "type": "depth_profile",
            "title": "Temperature vs Depth",
            "data": {"temperature": list(temps), "depth": list(depths)},
            "metadata": {
                "xlabel": "Temperature (\u00b0C)",
                "ylabel": "Pressure / Depth (dbar)",
            },
        }

    def map_data(self, **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        points: List[Dict] = []
        for r in records:
            if r.get("latitude") is not None and r.get("longitude") is not None:
                points.append(
                    {
                        "lat": r["latitude"],
                        "lon": r["longitude"],
                        "temperature": r.get("temp"),
                        "salinity": r.get("psal"),
                        "depth": r.get("pres"),
                        "time": r.get("time"),
                        "float_id": r.get("platform_number"),
                    }
                )
        return {
            "type": "map",
            "title": "Float Locations",
            "data": points,
            "count": len(points),
        }

    def time_trends(self, variable: str = "temp", **kw) -> Dict:
        records = self.fetch_profiles(**kw)
        daily: Dict[str, List[float]] = {}
        for r in records:
            t = r.get("time")
            v = r.get(variable)
            if t and v is not None:
                day = t[:10]
                daily.setdefault(day, []).append(v)
        days_sorted = sorted(daily.keys())
        avgs = [round(sum(daily[d]) / len(daily[d]), 3) for d in days_sorted]
        label = {"temp": "Temperature (\u00b0C)", "psal": "Salinity (PSU)"}.get(
            variable, variable
        )
        return {
            "type": "line",
            "title": f"{label} Over Time",
            "data": {"dates": days_sorted, "values": avgs},
            "metadata": {"xlabel": "Date", "ylabel": label},
        }

    # ---- format-compatible methods for existing frontend endpoints ----

    def summary(self, **kw) -> Dict:
        """Return summary in the same shape as /data/summary."""
        records = self.fetch_profiles(**kw)
        temps = [r["temp"] for r in records if r.get("temp") is not None]
        sals = [r["psal"] for r in records if r.get("psal") is not None]
        floats = {r.get("platform_number") for r in records if r.get("platform_number")}
        times = [r["time"] for r in records if r.get("time")]
        lats = [r["latitude"] for r in records if r.get("latitude") is not None]
        lons = [r["longitude"] for r in records if r.get("longitude") is not None]
        return {
            "total_profiles": len(records),
            "total_floats": len(floats),
            "date_range": {
                "start": min(times) if times else None,
                "end": max(times) if times else None,
            },
            "temperature_range": {
                "min": round(min(temps), 2) if temps else None,
                "max": round(max(temps), 2) if temps else None,
                "avg": round(sum(temps) / len(temps), 2) if temps else None,
            },
            "salinity_range": {
                "min": round(min(sals), 2) if sals else None,
                "max": round(max(sals), 2) if sals else None,
                "avg": round(sum(sals) / len(sals), 2) if sals else None,
            },
            "geographic_bounds": {
                "min_lat": round(min(lats), 2) if lats else None,
                "max_lat": round(max(lats), 2) if lats else None,
                "min_lon": round(min(lons), 2) if lons else None,
                "max_lon": round(max(lons), 2) if lons else None,
            },
            "source": "ERDDAP Live",
        }

    def profiles_list(self, limit: int = 500, **kw) -> Dict:
        """Return profiles in the same shape as /data/profiles."""
        records = self.fetch_profiles(limit=limit, **kw)
        profiles = []
        for i, r in enumerate(records):
            profiles.append(
                {
                    "id": i + 1,
                    "latitude": r.get("latitude"),
                    "longitude": r.get("longitude"),
                    "temperature": r.get("temp"),
                    "salinity": r.get("psal"),
                    "depth": r.get("pres"),
                    "float_id": r.get("platform_number"),
                    "timestamp": r.get("time"),
                }
            )
        return {
            "total": len(profiles),
            "skip": 0,
            "limit": limit,
            "profiles": profiles,
            "source": "ERDDAP Live",
        }

    def chart_data_histogram(self, variable: str, limit: int = 1000) -> Dict:
        """Return histogram in the format /visualization/chart-data expects."""
        if variable == "temperature":
            result = self.temperature_distribution(limit=limit)
        elif variable == "salinity":
            result = self.salinity_distribution(limit=limit)
        elif variable == "depth":
            records = self.fetch_profiles(limit=limit)
            values = [r["pres"] for r in records if r.get("pres") is not None]
            result = {
                "data": values,
                "stats": _stats(values),
                "metadata": {
                    "title": "Depth Distribution",
                    "xlabel": "Pressure (dbar)",
                    "ylabel": "Frequency",
                    "variable": "depth",
                },
            }
        else:
            return {"error": f"Unknown variable: {variable}"}

        return {
            "chart_type": "histogram",
            "variable": variable,
            "values": result["data"],
            "stats": result.get("stats", {}),
            "metadata": result.get("metadata", {}),
        }

    def chart_data_scatter(
        self, var_x: str, var_y: str, limit: int = 1000
    ) -> Dict:
        """Return scatter in the format /visualization/chart-data expects."""
        var_map = {
            "temperature": "temp",
            "salinity": "psal",
            "depth": "pres",
            "pressure": "pres",
            "latitude": "latitude",
            "longitude": "longitude",
        }
        kx = var_map.get(var_x, var_x)
        ky = var_map.get(var_y, var_y)
        records = self.fetch_profiles(limit=limit)
        pairs = [
            (r[kx], r[ky])
            for r in records
            if r.get(kx) is not None and r.get(ky) is not None
        ]
        if not pairs:
            return {"error": "No data available"}
        x_vals, y_vals = zip(*pairs)
        return {
            "chart_type": "scatter",
            "x_variable": var_x,
            "y_variable": var_y,
            "x_values": list(x_vals),
            "y_values": list(y_vals),
            "correlation": _pearson(list(x_vals), list(y_vals)),
            "metadata": {
                "title": f"{var_y.capitalize()} vs {var_x.capitalize()}",
                "xlabel": var_x.capitalize(),
                "ylabel": var_y.capitalize(),
            },
        }

    def chart_data_depth_profile(self, variable: str, limit: int = 1000) -> Dict:
        """Return depth profile in the format /visualization/chart-data expects."""
        var_map = {"temperature": "temp", "salinity": "psal", "pressure": "pres"}
        key = var_map.get(variable, variable)
        records = self.fetch_profiles(limit=limit)
        pairs = [
            (r["pres"], r[key])
            for r in records
            if r.get("pres") is not None and r.get(key) is not None
        ]
        if not pairs:
            return {"error": "No data available"}
        pairs.sort(key=lambda p: p[0])
        depths, values = zip(*pairs)
        unit = {
            "temperature": "\u00b0C",
            "salinity": "PSU",
            "pressure": "dbar",
        }.get(variable, "")
        return {
            "chart_type": "depth_profile",
            "variable": variable,
            "depths": list(depths),
            "values": list(values),
            "metadata": {
                "title": f"Depth Profile: {variable.capitalize()}",
                "xlabel": f"{variable.capitalize()} ({unit})",
                "ylabel": "Depth (dbar)",
            },
        }

    def chart_data_heatmap(self, variable: str, limit: int = 1000) -> Dict:
        """Return heatmap in the format /visualization/chart-data expects."""
        var_map = {"temperature": "temp", "salinity": "psal", "depth": "pres"}
        key = var_map.get(variable, variable)
        records = self.fetch_profiles(limit=limit)
        lats, lons, vals = [], [], []
        for r in records:
            if (
                r.get("latitude") is not None
                and r.get("longitude") is not None
                and r.get(key) is not None
            ):
                lats.append(r["latitude"])
                lons.append(r["longitude"])
                vals.append(r[key])
        if not lats:
            return {"error": "No data available"}
        return {
            "chart_type": "heatmap",
            "variable": variable,
            "latitudes": lats,
            "longitudes": lons,
            "values": vals,
            "metadata": {
                "title": f"Spatial Distribution: {variable.capitalize()}",
                "xlabel": "Longitude",
                "ylabel": "Latitude",
            },
        }

    def chart_data_3d_scatter(self, limit: int = 1000) -> Dict:
        """Return 3D scatter in the format /visualization/chart-data expects."""
        records = self.fetch_profiles(limit=limit)
        temps, sals, depths = [], [], []
        for r in records:
            if (
                r.get("temp") is not None
                and r.get("psal") is not None
                and r.get("pres") is not None
            ):
                temps.append(r["temp"])
                sals.append(r["psal"])
                depths.append(r["pres"])
        if not temps:
            return {"error": "No data available"}
        return {
            "chart_type": "3d_scatter",
            "temperature": temps,
            "salinity": sals,
            "depth": depths,
            "metadata": {
                "title": "3D Ocean Properties",
                "xlabel": "Temperature (\u00b0C)",
                "ylabel": "Salinity (PSU)",
                "zlabel": "Depth (dbar)",
            },
        }

    def chart_data_correlation(self, limit: int = 1000) -> Dict:
        """Return correlation matrix in the format /visualization/chart-data expects."""
        records = self.fetch_profiles(limit=limit)
        rows = []
        for r in records:
            if (
                r.get("temp") is not None
                and r.get("psal") is not None
                and r.get("pres") is not None
            ):
                rows.append(
                    [r["temp"], r["psal"], r["pres"], r.get("pres") or 0]
                )
        if not rows:
            return {"error": "No data available"}
        variables_list = ["Temperature", "Salinity", "Depth", "Pressure"]
        n_vars = len(variables_list)
        cols = list(zip(*rows))  # transpose
        matrix = []
        for i in range(n_vars):
            row = []
            for j in range(n_vars):
                row.append(_pearson(list(cols[i]), list(cols[j])))
            matrix.append(row)
        return {
            "chart_type": "correlation",
            "variables": variables_list,
            "correlation_matrix": matrix,
            "metadata": {"title": "Variable Correlation Matrix"},
        }

    def chart_data_line(self, variable: str, limit: int = 1000) -> Dict:
        """Return line chart in the format /visualization/chart-data expects."""
        var_map = {"temperature": "temp", "salinity": "psal", "depth": "pres"}
        key = var_map.get(variable, variable)
        records = self.fetch_profiles(limit=limit)
        indices, values = [], []
        for i, r in enumerate(records):
            if r.get(key) is not None:
                indices.append(i + 1)
                values.append(r[key])
        if not indices:
            return {"error": "No data available"}
        return {
            "chart_type": "line",
            "variable": variable,
            "indices": indices,
            "values": values,
            "metadata": {
                "title": f"{variable.capitalize()} Sequence",
                "xlabel": "Measurement Index",
                "ylabel": variable.capitalize(),
            },
        }


# ---------------------------------------------------------------------- helpers

def _stats(values: List[float]) -> Dict:
    if not values:
        return {}
    n = len(values)
    mean = sum(values) / n
    sorted_v = sorted(values)
    median = sorted_v[n // 2]
    variance = sum((v - mean) ** 2 for v in values) / n
    return {
        "count": n,
        "mean": round(mean, 3),
        "median": round(median, 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "std": round(variance ** 0.5, 3),
    }


def _pearson(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    dy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return round(num / (dx * dy), 4) if dx and dy else 0.0


# ---------------------------------------------------------------------- singleton

_instance: Optional[ERDDAPService] = None


def get_erddap_service() -> ERDDAPService:
    global _instance
    if _instance is None:
        _instance = ERDDAPService()
    return _instance
