"""
ARGO NetCDF Data Ingestion Pipeline

This script:
1. Reads ARGO NetCDF files from data directory
2. Extracts oceanographic measurements
3. Cleans and validates data
4. Stores records in PostgreSQL with PostGIS geometry
5. Generates semantic text descriptions for RAG
"""
import os
import sys
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db, engine
from models import ArgoProfile, ArgoDocument
from config import settings


def read_netcdf_file(file_path: str) -> pd.DataFrame:
    """
    Read ARGO NetCDF file and convert to DataFrame.
    
    Args:
        file_path: Path to NetCDF file
        
    Returns:
        DataFrame with extracted ARGO profile data
    """
    print(f"Reading NetCDF file: {file_path}")
    
    try:
        # Open NetCDF file with xarray
        ds = xr.open_dataset(file_path)
        
        # Extract float ID - try multiple sources
        float_id = 'UNKNOWN'
        if 'PLATFORM_NUMBER' in ds:
            float_id_raw = ds['PLATFORM_NUMBER'].values
            if hasattr(float_id_raw, '__len__'):
                float_id_raw = float_id_raw[0]
            if isinstance(float_id_raw, bytes):
                float_id = float_id_raw.decode('utf-8').strip()
            else:
                float_id = str(float_id_raw).strip()
        elif 'platform_number' in ds.attrs:
            float_id = str(ds.attrs['platform_number']).strip()
        else:
            # Try to extract from filename
            filename = Path(file_path).stem
            parts = filename.split('_')
            for part in parts:
                if part.isdigit() and len(part) >= 7:
                    float_id = part
                    break
        
        # Get dimensions
        n_prof = ds.dims.get('N_PROF', 1)
        n_levels = ds.dims.get('N_LEVELS', 0)
        
        if n_levels == 0:
            print(f"  Warning: No depth levels found in {file_path}")
            return pd.DataFrame()
        
        # Extract variables - handle multi-dimensional data
        temp = ds['TEMP'].values if 'TEMP' in ds else None
        psal = ds['PSAL'].values if 'PSAL' in ds else None
        pres = ds['PRES'].values if 'PRES' in ds else None
        lat = ds['LATITUDE'].values if 'LATITUDE' in ds else None
        lon = ds['LONGITUDE'].values if 'LONGITUDE' in ds else None
        
        # Convert 2D arrays to 1D by taking first profile
        if temp is not None and len(temp.shape) > 1:
            temp = temp[0, :]  # Take first profile
        if psal is not None and len(psal.shape) > 1:
            psal = psal[0, :]
        if pres is not None and len(pres.shape) > 1:
            pres = pres[0, :]
        
        # Latitude/Longitude are usually per-profile
        if lat is not None:
            lat = float(lat[0]) if hasattr(lat, '__len__') else float(lat)
        if lon is not None:
            lon = float(lon[0]) if hasattr(lon, '__len__') else float(lon)
        
        # Extract timestamp if available
        timestamp = None
        if 'JULD' in ds:
            juld = ds['JULD'].values
            if hasattr(juld, '__len__'):
                juld = juld[0]
            try:
                timestamp = pd.to_datetime(juld).to_pydatetime()
            except:
                timestamp = None
        
        # Create DataFrame with one row per depth level
        # Each depth level becomes a separate "measurement" with same location
        df_list = []
        for i in range(len(temp) if temp is not None else n_levels):
            row = {
                'float_id': float_id,
                'latitude': lat,
                'longitude': lon,
                'timestamp': timestamp,
            }
            
            # Extract depth - important for profile visualization
            if pres is not None and i < len(pres):
                val = float(pres[i])
                # Convert pressure to depth (rough approximation: 1 dbar ≈ 1 meter)
                row['depth'] = val if not np.isnan(val) else None
            else:
                row['depth'] = float(i * 10)  # Fallback: assume 10m intervals
            
            # Extract values and handle NaN
            if temp is not None and i < len(temp):
                val = float(temp[i])
                row['temperature'] = val if not np.isnan(val) else None
            else:
                row['temperature'] = None
                
            if psal is not None and i < len(psal):
                val = float(psal[i])
                row['salinity'] = val if not np.isnan(val) else None
            else:
                row['salinity'] = None
                
            if pres is not None and i < len(pres):
                val = float(pres[i])
                row['pressure'] = val if not np.isnan(val) else None
            else:
                row['pressure'] = None
            
            # Only add row if it has at least one measurement
            if any([row.get('temperature'), row.get('salinity'), row.get('pressure')]):
                df_list.append(row)
        
        df = pd.DataFrame(df_list)
        ds.close()
        
        print(f"  Extracted {len(df)} depth measurements from float {float_id} at ({lat:.2f}, {lon:.2f})")
        return df
        
    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate ARGO data.
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    print(f"Cleaning data ({len(df)} records)")
    
    # Remove rows with missing critical coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    
    # Validate latitude/longitude ranges
    df = df[(df['latitude'] >= -90) & (df['latitude'] <= 90)]
    df = df[(df['longitude'] >= -180) & (df['longitude'] <= 180)]
    
    # Calculate depth from pressure (approximation: 1 dbar ≈ 1 meter)
    if 'pressure' in df.columns:
        df['depth'] = df['pressure'].apply(lambda x: x if x is not None else None)
    
    # Validate temperature and salinity ranges
    if 'temperature' in df.columns:
        df.loc[(df['temperature'] < -2) | (df['temperature'] > 40), 'temperature'] = None
    
    if 'salinity' in df.columns:
        df.loc[(df['salinity'] < 0) | (df['salinity'] > 42), 'salinity'] = None
    
    print(f"  Cleaned to {len(df)} valid records")
    return df


def generate_semantic_text(row: pd.Series) -> str:
    """
    Generate semantic text description for a profile record.
    Used for embedding and RAG retrieval.
    
    Args:
        row: DataFrame row with profile data
        
    Returns:
        Semantic text description
    """
    parts = []
    
    # Location
    parts.append(f"Oceanographic measurement at latitude {row['latitude']:.2f}, longitude {row['longitude']:.2f}")
    
    # Temperature
    if pd.notna(row.get('temperature')):
        parts.append(f"with water temperature of {row['temperature']:.2f}°C")
    
    # Salinity
    if pd.notna(row.get('salinity')):
        parts.append(f"and salinity of {row['salinity']:.2f} PSU")
    
    # Depth
    if pd.notna(row.get('depth')):
        parts.append(f"at depth {row['depth']:.1f} meters")
    
    # Float ID
    if pd.notna(row.get('float_id')):
        parts.append(f"recorded by ARGO float {row['float_id']}")
    
    return " ".join(parts) + "."


def ingest_to_database(df: pd.DataFrame, db: Session) -> List[int]:
    """
    Store cleaned data in PostgreSQL database with PostGIS geometry.
    
    Args:
        df: Cleaned DataFrame
        db: Database session
        
    Returns:
        List of created profile IDs
    """
    print(f"Ingesting {len(df)} records to database...")
    
    profile_ids = []
    
    for idx, row in df.iterrows():
        try:
            # Create ArgoProfile record
            profile = ArgoProfile(
                temperature=row.get('temperature'),
                salinity=row.get('salinity'),
                depth=row.get('depth'),
                pressure=row.get('pressure'),
                latitude=row['latitude'],
                longitude=row['longitude'],
                float_id=row.get('float_id'),
                timestamp=row.get('timestamp') if pd.notna(row.get('timestamp')) else datetime.utcnow()
            )
            
            db.add(profile)
            db.flush()  # Get ID before commit
            
            # Update PostGIS geometry using SQL (only if PostgreSQL)
            try:
                db.execute(
                    text("""
                        UPDATE argo_profiles 
                        SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                        WHERE id = :id
                    """),
                    {"lon": row['longitude'], "lat": row['latitude'], "id": profile.id}
                )
            except Exception as e:
                # Skip PostGIS if not available (SQLite)
                pass
            
            profile_ids.append(profile.id)
            
            # Generate and store semantic document
            semantic_text = generate_semantic_text(row)
            document = ArgoDocument(
                profile_id=profile.id,
                text=semantic_text,
                vector_id=profile.id  # Will be used as index in FAISS
            )
            db.add(document)
            
        except Exception as e:
            print(f"  Error inserting record {idx}: {e}")
            continue
    
    db.commit()
    print(f"  Successfully ingested {len(profile_ids)} profiles")
    
    return profile_ids


def main():
    """Main ingestion pipeline - REAL ARGO DATA ONLY."""
    print("=" * 60)
    print("ARGO Data Ingestion Pipeline")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create data directory if needed
    data_dir = Path(settings.NETCDF_DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for NetCDF files
    netcdf_files = list(data_dir.glob("*.nc"))
    
    print(f"\n2. Scanning for NetCDF files in {data_dir}")
    print(f"   Found {len(netcdf_files)} NetCDF files")
    
    if len(netcdf_files) == 0:
        print("\n❌ ERROR: No NetCDF files found!")
        print("   Please download real ARGO data first using:")
        print("   python fetch_live_data.py --source gdac --limit 20")
        return
    
    # Process ONLY real NetCDF files
    all_data = []
    for nc_file in netcdf_files:
        df = read_netcdf_file(str(nc_file))
        if not df.empty:
            all_data.append(df)
    
    if not all_data:
        print("\n❌ ERROR: No valid data extracted from NetCDF files!")
        print("   Check that your .nc files contain valid ARGO data.")
        return
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Clean data
    print("\n3. Cleaning data...")
    cleaned_df = clean_data(combined_df)
    
    # Ingest to database
    print("\n4. Ingesting to database...")
    db = SessionLocal()
    try:
        profile_ids = ingest_to_database(cleaned_df, db)
        print(f"\n✓ Successfully ingested {len(profile_ids)} REAL ARGO profiles")
        print(f"✓ Profile IDs: {profile_ids[:10]}..." if len(profile_ids) > 10 else f"✓ Profile IDs: {profile_ids}")
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("Ingestion Complete!")
    print("=" * 60)
    print(f"\nNext step: Run 'python build_index.py' to create vector embeddings")


if __name__ == "__main__":
    main()
