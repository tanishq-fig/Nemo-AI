"""
Fetch Live ARGO Data from Public Sources

This script fetches real ARGO float data from public APIs:
- NOAA ERDDAP server
- IFREMER GDAC FTP
- Copernicus Marine Service

Usage:
    python fetch_live_data.py --source erddap --limit 100
"""
import os
import sys
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models import ArgoProfile, ArgoDocument
from config import settings


def fetch_from_erddap(limit: int = 100) -> pd.DataFrame:
    """
    Fetch ARGO data from NOAA ERDDAP server.
    
    Args:
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with ARGO data
    """
    print(f"Fetching live ARGO data from NOAA ERDDAP (limit: {limit})...")
    
    # ERDDAP API endpoint for ARGO data
    base_url = "https://www.ncei.noaa.gov/erddap/tabledap/ArgoFloats.json"
    
    # Get recent data (last 30 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Build query parameters
    params = {
        'time>=': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'time<=': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'latitude': '',
        'longitude': '',
        'temp': '',
        'psal': '',
        'pres': '',
        'platform_number': '',
    }
    
    try:
        # Make request
        print(f"  Requesting data from {base_url}")
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        if 'table' not in data:
            print("  Warning: Invalid response format")
            return pd.DataFrame()
        
        # Extract column names and rows
        columns = [col[0] for col in data['table']['columnNames']]
        rows = data['table']['rows']
        
        if not rows:
            print("  Warning: No data returned from ERDDAP")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=columns)
        
        # Rename columns to match our schema
        column_mapping = {
            'latitude': 'latitude',
            'longitude': 'longitude',
            'temp': 'temperature',
            'psal': 'salinity',
            'pres': 'pressure',
            'platform_number': 'float_id',
            'time': 'timestamp'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Convert types
        for col in ['latitude', 'longitude', 'temperature', 'salinity', 'pressure']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate depth from pressure
        if 'pressure' in df.columns:
            df['depth'] = df['pressure']
        
        # Limit results
        df = df.head(limit)
        
        print(f"  ✓ Fetched {len(df)} records from ERDDAP")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching from ERDDAP: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  Error processing ERDDAP data: {e}")
        return pd.DataFrame()


def fetch_from_ifremer_api(limit: int = 100) -> pd.DataFrame:
    """
    Fetch ARGO data from IFREMER Argo API.
    
    Args:
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with ARGO data
    """
    print(f"Fetching live ARGO data from IFREMER API (limit: {limit})...")
    
    # IFREMER Argo API endpoint
    base_url = "https://data-argo.ifremer.fr/api/profiles"
    
    try:
        # Get list of recent profiles
        print(f"  Requesting profile list from {base_url}")
        response = requests.get(f"{base_url}?limit={limit}", timeout=30)
        response.raise_for_status()
        
        profiles = response.json()
        
        if not profiles:
            print("  Warning: No profiles returned")
            return pd.DataFrame()
        
        # Fetch detailed data for each profile
        data_list = []
        for i, profile in enumerate(profiles[:limit]):
            try:
                profile_url = f"{base_url}/{profile['id']}"
                prof_response = requests.get(profile_url, timeout=10)
                prof_response.raise_for_status()
                prof_data = prof_response.json()
                
                # Extract measurements
                if 'measurements' in prof_data:
                    for meas in prof_data['measurements']:
                        data_list.append({
                            'latitude': prof_data.get('latitude'),
                            'longitude': prof_data.get('longitude'),
                            'temperature': meas.get('temperature'),
                            'salinity': meas.get('salinity'),
                            'pressure': meas.get('pressure'),
                            'depth': meas.get('pressure'),  # Approximation
                            'float_id': prof_data.get('platform_number'),
                            'timestamp': prof_data.get('date')
                        })
                
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(profiles[:limit])} profiles")
                    
            except Exception as e:
                print(f"  Error fetching profile {profile.get('id')}: {e}")
                continue
        
        if not data_list:
            print("  Warning: No measurements extracted")
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list)
        
        # Convert types
        for col in ['latitude', 'longitude', 'temperature', 'salinity', 'pressure', 'depth']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"  ✓ Fetched {len(df)} records from IFREMER")
        return df
        
    except Exception as e:
        print(f"  Error fetching from IFREMER: {e}")
        return pd.DataFrame()


def fetch_copernicus_data(limit: int = 100) -> pd.DataFrame:
    """
    Fetch ARGO data from Copernicus Marine Service.
    Note: Requires API key for full access.
    
    Args:
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with ARGO data
    """
    print(f"Fetching live ARGO data from Copernicus (limit: {limit})...")
    
    # Copernicus WMS/WCS endpoint (public subset)
    base_url = "https://nrt.cmems-du.eu/thredds/dodsC/INSITU_GLO_PHYBGCWAV_DISCRETE_MYNRT_013_030"
    
    try:
        # Note: This is a simplified example. Full implementation would use
        # the Copernicus Marine Toolbox or direct THREDDS access
        
        print("  Note: Copernicus requires authentication for full access")
        print("  Using public subset data...")
        
        # For now, return empty DataFrame
        # Full implementation would require copernicus_marine_client package
        return pd.DataFrame()
        
    except Exception as e:
        print(f"  Error fetching from Copernicus: {e}")
        return pd.DataFrame()


def clean_live_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate live ARGO data.
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    if df.empty:
        return df
    
    print(f"Cleaning live data ({len(df)} records)")
    
    # Remove rows with missing critical coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Validate ranges
    df = df[(df['latitude'] >= -90) & (df['latitude'] <= 90)]
    df = df[(df['longitude'] >= -180) & (df['longitude'] <= 180)]
    
    # Validate measurements
    if 'temperature' in df.columns:
        df.loc[(df['temperature'] < -2) | (df['temperature'] > 40), 'temperature'] = None
    
    if 'salinity' in df.columns:
        df.loc[(df['salinity'] < 0) | (df['salinity'] > 42), 'salinity'] = None
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['latitude', 'longitude', 'temperature', 'salinity'])
    
    print(f"  Cleaned to {len(df)} valid records")
    return df


def generate_semantic_text(row: pd.Series) -> str:
    """Generate semantic text for RAG."""
    parts = []
    parts.append(f"Real-time oceanographic measurement at latitude {row['latitude']:.2f}, longitude {row['longitude']:.2f}")
    
    if pd.notna(row.get('temperature')):
        parts.append(f"with water temperature of {row['temperature']:.2f}°C")
    
    if pd.notna(row.get('salinity')):
        parts.append(f"and salinity of {row['salinity']:.2f} PSU")
    
    if pd.notna(row.get('depth')):
        parts.append(f"at depth {row['depth']:.1f} meters")
    
    if pd.notna(row.get('float_id')):
        parts.append(f"recorded by ARGO float {row['float_id']}")
    
    return " ".join(parts) + "."


def ingest_live_data(df: pd.DataFrame, db: Session):
    """Store live data in database."""
    print(f"Ingesting {len(df)} live records to database...")
    
    profile_ids = []
    
    for idx, row in df.iterrows():
        try:
            profile = ArgoProfile(
                temperature=row.get('temperature'),
                salinity=row.get('salinity'),
                depth=row.get('depth'),
                pressure=row.get('pressure'),
                latitude=row['latitude'],
                longitude=row['longitude'],
                float_id=str(row.get('float_id', 'UNKNOWN')),
                timestamp=datetime.utcnow()
            )
            
            db.add(profile)
            db.flush()
            
            # PostGIS geometry (optional)
            try:
                db.execute(
                    text("""
                        UPDATE argo_profiles 
                        SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                        WHERE id = :id
                    """),
                    {"lon": row['longitude'], "lat": row['latitude'], "id": profile.id}
                )
            except:
                pass  # Skip if SQLite
            
            profile_ids.append(profile.id)
            
            # Generate semantic document
            semantic_text = generate_semantic_text(row)
            document = ArgoDocument(
                profile_id=profile.id,
                text=semantic_text,
                vector_id=profile.id
            )
            db.add(document)
            
        except Exception as e:
            print(f"  Error inserting record {idx}: {e}")
            continue
    
    db.commit()
    print(f"  ✓ Successfully ingested {len(profile_ids)} live profiles")
    
    return profile_ids


def main():
    """Main live data fetching pipeline."""
    print("=" * 60)
    print("Live ARGO Data Fetcher")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Try multiple sources
    print("\n2. Fetching live ARGO data...")
    
    all_data = []
    
    # Try ERDDAP first
    try:
        erddap_data = fetch_from_erddap(limit=50)
        if not erddap_data.empty:
            all_data.append(erddap_data)
            print(f"  ✓ Retrieved {len(erddap_data)} records from ERDDAP")
    except Exception as e:
        print(f"  × ERDDAP failed: {e}")
    
    # Try IFREMER
    try:
        ifremer_data = fetch_from_ifremer_api(limit=50)
        if not ifremer_data.empty:
            all_data.append(ifremer_data)
            print(f"  ✓ Retrieved {len(ifremer_data)} records from IFREMER")
    except Exception as e:
        print(f"  × IFREMER failed: {e}")
    
    if not all_data:
        print("\n  ❌ ERROR: Could not fetch live data from any source")
        print("\n  💡 To get real ARGO data:")
        print("     1. Download NetCDF files manually from:")
        print("        → https://data-argo.ifremer.fr/ (GDAC)")
        print("        → https://www.seanoe.org/data/00311/42182/")
        print("        → https://www.ncei.noaa.gov/products/argo-floats")
        print("     2. Place .nc files in: backend/data/raw/")
        print("     3. Run: python ingest.py")
        return
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Clean data
    print("\n3. Cleaning live data...")
    cleaned_df = clean_live_data(combined_df)
    
    if cleaned_df.empty:
        print("  ✗ No valid data after cleaning")
        return
    
    # Ingest to database
    print("\n4. Ingesting to database...")
    db = SessionLocal()
    try:
        profile_ids = ingest_live_data(cleaned_df, db)
        print(f"\n✓ Successfully ingested {len(profile_ids)} LIVE profiles")
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("Live Data Fetch Complete!")
    print("=" * 60)
    print(f"\nNext step: Run 'python build_index.py' to rebuild vector embeddings")


if __name__ == "__main__":
    main()
