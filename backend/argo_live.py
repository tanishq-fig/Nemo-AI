"""Live ARGO data fetching with safe tiling and caching."""
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
import json
from pathlib import Path

class ARGOLiveFetcher:
    """Fetch live ARGO data with intelligent tiling and caching."""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.erddap_base_url = "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.json"
        # Columns to fetch
        self.columns = "?platform_number,latitude,longitude,time,pres,temp,psal"
        self.erddap_url = f"{self.erddap_base_url}{self.columns}"
        
        cache_path = Path(cache_dir)
        if not cache_path.is_absolute():
            cache_path = Path("/tmp") / cache_path.name
        self.cache_dir = cache_path
        self.cache_dir.mkdir(exist_ok=True)
        self.max_region_size = 20  # degrees
        self.timeout = 30
        self.max_retries = 3
        
    def _get_cache_key(self, params: Dict) -> str:
        """Generate cache key from query parameters."""
        key_parts = [
            f"lat_{params.get('lat_min')}_{params.get('lat_max')}",
            f"lon_{params.get('lon_min')}_{params.get('lon_max')}",
            f"time_{params.get('time_start')}_{params.get('time_end')}"
        ]
        return "_".join(key_parts) + ".json"
    
    def _load_cache(self, cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Load cached data if it exists and is fresh."""
        cache_file = self.cache_dir / cache_key
        
        if not cache_file.exists():
            return None
        
        # Check age
        file_age = time.time() - cache_file.stat().st_mtime
        if file_age > max_age_hours * 3600:
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
    
    def _save_cache(self, cache_key: str, data: Dict):
        """Save data to cache."""
        cache_file = self.cache_dir / cache_key
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def _tile_region(self, lat_min: float, lat_max: float, 
                     lon_min: float, lon_max: float) -> List[Tuple[float, float, float, float]]:
        """Split large region into safe tiles."""
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        
        # Calculate number of tiles needed
        lat_tiles = int(np.ceil(lat_range / self.max_region_size))
        lon_tiles = int(np.ceil(lon_range / self.max_region_size))
        
        tiles = []
        lat_step = lat_range / lat_tiles
        lon_step = lon_range / lon_tiles
        
        for i in range(lat_tiles):
            for j in range(lon_tiles):
                tile_lat_min = lat_min + i * lat_step
                tile_lat_max = min(lat_min + (i + 1) * lat_step, lat_max)
                tile_lon_min = lon_min + j * lon_step
                tile_lon_max = min(lon_min + (j + 1) * lon_step, lon_max)
                
                tiles.append((tile_lat_min, tile_lat_max, tile_lon_min, tile_lon_max))
        
        return tiles
    
    def _fetch_tile(self, lat_min: float, lat_max: float, 
                   lon_min: float, lon_max: float,
                   time_start: Optional[str] = None,
                   time_end: Optional[str] = None) -> Optional[Dict]:
        """Fetch single tile with retry logic."""
        
        # Build query
        params = {
            'latitude>=': lat_min,
            'latitude<=': lat_max,
            'longitude>=': lon_min,
            'longitude<=': lon_max,
        }
        
        if time_start:
            params['time>='] = time_start
        if time_end:
            params['time<='] = time_end
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.erddap_url,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data
                elif response.status_code == 404:
                    # No data in this tile
                    return {'table': {'rows': []}}
                else:
                    print(f"HTTP {response.status_code} for tile")
                    
            except requests.Timeout:
                print(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                print(f"Fetch error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def fetch_region(self, 
                    lat_min: float, 
                    lat_max: float,
                    lon_min: float, 
                    lon_max: float,
                    time_start: Optional[str] = None,
                    time_end: Optional[str] = None,
                    use_cache: bool = True) -> Dict:
        """
        Fetch ARGO data for region with safe tiling.
        
        Returns:
            {
                'profiles': List[Dict],
                'count': int,
                'region': Dict,
                'cached': bool
            }
        """
        
        # Check cache
        cache_params = {
            'lat_min': lat_min,
            'lat_max': lat_max,
            'lon_min': lon_min,
            'lon_max': lon_max,
            'time_start': time_start,
            'time_end': time_end
        }
        cache_key = self._get_cache_key(cache_params)
        
        if use_cache:
            cached = self._load_cache(cache_key)
            if cached:
                print(f"Cache hit: {cache_key}")
                cached['cached'] = True
                return cached
        
        print(f"Fetching region: lat[{lat_min},{lat_max}] lon[{lon_min},{lon_max}]")
        
        # Tile region if needed
        tiles = self._tile_region(lat_min, lat_max, lon_min, lon_max)
        print(f"Split into {len(tiles)} tiles")
        
        all_profiles = []
        
        for i, (tlat_min, tlat_max, tlon_min, tlon_max) in enumerate(tiles):
            print(f"Fetching tile {i+1}/{len(tiles)}...")
            
            tile_data = self._fetch_tile(
                tlat_min, tlat_max, tlon_min, tlon_max,
                time_start, time_end
            )
            
            if tile_data and 'table' in tile_data and 'rows' in tile_data['table']:
                rows = tile_data['table']['rows']
                all_profiles.extend(rows)
                print(f"  -> {len(rows)} profiles")
            
            # Rate limiting
            time.sleep(0.5)
        
        result = {
            'profiles': all_profiles,
            'count': len(all_profiles),
            'region': {
                'lat_min': lat_min,
                'lat_max': lat_max,
                'lon_min': lon_min,
                'lon_max': lon_max
            },
            'cached': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to cache
        self._save_cache(cache_key, result)
        
        return result
    
    def fetch_recent(self, days: int = 30, limit: int = 100) -> Dict:
        """Fetch recent ARGO data worldwide."""
        time_end = datetime.utcnow()
        time_start = time_end - timedelta(days=days)
        
        cache_key = f"recent_{days}days_{limit}.json"
        
        cached = self._load_cache(cache_key, max_age_hours=6)
        if cached:
            cached['cached'] = True
            return cached
        
        try:
            params = {
                'time>=': time_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'time<=': time_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
            
            response = requests.get(
                self.erddap_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get('table', {}).get('rows', [])
                
                # Limit results
                if len(rows) > limit:
                    rows = rows[:limit]
                
                result = {
                    'profiles': rows,
                    'count': len(rows),
                    'period_days': days,
                    'cached': False,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self._save_cache(cache_key, result)
                return result
            else:
                print(f"Fetch recent failed: HTTP {response.status_code}")
                # Log the response text to see the error message
                print(f"Response: {response.text[:200]}")
                return {
                    'profiles': [],
                    'count': 0,
                    'error': f"HTTP {response.status_code}: {response.text[:100]}",
                    'cached': False
                }
            
        except Exception as e:
            with open("live_debug.log", "a") as f:
                f.write(f"Fetch recent error: {e}\n")
            print(f"Fetch recent error: {e}")
        
        # Fallback
        return {
            'profiles': [],
            'count': 0,
            'error': 'Failed to fetch recent data',
            'cached': False
        }


# Global instance
live_fetcher = ARGOLiveFetcher()
