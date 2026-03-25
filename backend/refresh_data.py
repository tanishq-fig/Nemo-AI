"""
Automatic Live ARGO Data Refresh Script

This script periodically downloads fresh ARGO data and updates the database.
Run this to keep your platform updated with the latest oceanographic measurements.

Usage:
    python refresh_data.py --floats 50 --profiles-per-float 10
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import argparse

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from download_real_argo import download_argo_data
from ingest import main as run_ingest
from build_index import main as run_build_index


def main():
    """
    Complete data refresh pipeline.
    
    Steps:
        1. Download fresh ARGO NetCDF files from GDAC
        2. Ingest new profiles into database
        3. Rebuild vector embeddings for RAG
    """
    parser = argparse.ArgumentParser(description="Refresh ARGO data")
    parser.add_argument('--limit', type=int, default=20, help='Number of files to download')
    parser.add_argument('--clean', action='store_true', help='Clean existing data before refresh')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 ARGO Data Refresh Pipeline")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: Download
    print("Step 1/3: Downloading fresh ARGO data...")
    print("-" * 70)
    try:
        data_dir = Path(__file__).parent / "data" / "raw"
        
        if args.clean:
            print("  Cleaning existing NetCDF files...")
            for nc_file in data_dir.glob("*.nc"):
                nc_file.unlink()
                print(f"    Removed: {nc_file.name}")
        
        downloaded = download_argo_data(output_dir=str(data_dir), max_files=args.limit)
        
        if not downloaded:
            print("  ⚠️ No new files downloaded")
            print("  Current data will be used")
        else:
            print(f"  ✓ Downloaded {len(downloaded)} files")
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return 1
    
    # Step 2: Ingest
    print("\nStep 2/3: Ingesting data to database...")
    print("-" * 70)
    try:
        run_ingest()
        print("  ✓ Data ingested successfully")
    except Exception as e:
        print(f"  ✗ Ingestion failed: {e}")
        return 1
    
    # Step 3: Build Index
    print("\nStep 3/3: Building vector index...")
    print("-" * 70)
    try:
        run_build_index()
        print("  ✓ Vector index rebuilt")
    except Exception as e:
        print(f"  ✗ Index building failed: {e}")
        return 1
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Data Refresh Complete!")
    print("=" * 70)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNext steps:")
    print("  - Restart the backend server to use fresh data")
    print("  - The RAG system now has updated vector embeddings")
    print("  - New profiles are available for visualization")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
