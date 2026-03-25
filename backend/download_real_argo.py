"""
Download Real ARGO NetCDF Files from GDAC FTP Server

This script downloads actual ARGO float data files from the Global Data Assembly Center (GDAC).
Files are in NetCDF format and contain real oceanographic measurements.

GDAC FTP Mirrors:
- ftp://ftp.ifremer.fr/ifremer/argo/
- https://data-argo.ifremer.fr/
"""
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import List
import time


# GDAC HTTP mirror (easier than FTP)
GDAC_BASE_URL = "https://data-argo.ifremer.fr"


def download_file(url: str, output_path: Path, timeout: int = 30) -> bool:
    """
    Download a file from URL to local path.
    
    Args:
        url: Source URL
        output_path: Destination file path
        timeout: Request timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"  Downloading: {url}")
        
        # Create user agent to avoid blocking
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (ArgoResearchPlatform/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                # Download in chunks
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
        
        file_size = output_path.stat().st_size
        print(f"    ✓ Downloaded {file_size:,} bytes")
        return True
        
    except urllib.error.HTTPError as e:
        print(f"    × HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"    × URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"    × Error: {e}")
        return False


def get_sample_argo_files() -> List[tuple]:
    """
    Get a list of known ARGO float profile files from GDAC.
    
    Returns:
        List of (url, filename) tuples
    """
    # These are real ARGO float files from the GDAC archive
    # Format: dac/<institution>/<float_id>/profiles/<profile_file>
    
    files = [
        # MEDS Arctic floats (confirmed working)
        ("dac/meds/4902528/profiles/R4902528_001.nc", "arctic_float_4902528_001.nc"),
        ("dac/meds/4902528/profiles/R4902528_002.nc", "arctic_float_4902528_002.nc"),
        ("dac/meds/4902528/profiles/R4902528_003.nc", "arctic_float_4902528_003.nc"),
        ("dac/meds/4902528/profiles/R4902528_004.nc", "arctic_float_4902528_004.nc"),
        ("dac/meds/4902528/profiles/R4902528_005.nc", "arctic_float_4902528_005.nc"),
        ("dac/meds/4902528/profiles/R4902528_006.nc", "arctic_float_4902528_006.nc"),
        ("dac/meds/4902528/profiles/R4902528_007.nc", "arctic_float_4902528_007.nc"),
        ("dac/meds/4902528/profiles/R4902528_008.nc", "arctic_float_4902528_008.nc"),
        ("dac/meds/4902528/profiles/R4902528_009.nc", "arctic_float_4902528_009.nc"),
        ("dac/meds/4902528/profiles/R4902528_010.nc", "arctic_float_4902528_010.nc"),
        
        # More MEDS floats
        ("dac/meds/4902529/profiles/R4902529_001.nc", "float_4902529_001.nc"),
        ("dac/meds/4902529/profiles/R4902529_002.nc", "float_4902529_002.nc"),
        ("dac/meds/4902529/profiles/R4902529_003.nc", "float_4902529_003.nc"),
        ("dac/meds/4902529/profiles/R4902529_004.nc", "float_4902529_004.nc"),
        ("dac/meds/4902529/profiles/R4902529_005.nc", "float_4902529_005.nc"),
        
        ("dac/meds/4902530/profiles/R4902530_001.nc", "float_4902530_001.nc"),
        ("dac/meds/4902530/profiles/R4902530_002.nc", "float_4902530_002.nc"),
        ("dac/meds/4902530/profiles/R4902530_003.nc", "float_4902530_003.nc"),
        ("dac/meds/4902530/profiles/R4902530_004.nc", "float_4902530_004.nc"),
        ("dac/meds/4902530/profiles/R4902530_005.nc", "float_4902530_005.nc"),
    ]
    
    return files


def download_argo_data(output_dir: str = "data/raw", max_files: int = 20) -> List[Path]:
    """
    Download real ARGO NetCDF files from GDAC.
    
    Args:
        output_dir: Directory to save files
        max_files: Maximum number of files to download
        
    Returns:
        List of successfully downloaded file paths
    """
    print("=" * 70)
    print("Downloading REAL ARGO Data from GDAC")
    print("=" * 70)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    files_to_download = get_sample_argo_files()[:max_files]
    
    print(f"\nTarget: {len(files_to_download)} files from global ARGO float network")
    print(f"Output: {output_path.absolute()}\n")
    
    downloaded_files = []
    failed_files = []
    
    for i, (remote_path, local_filename) in enumerate(files_to_download, 1):
        print(f"[{i}/{len(files_to_download)}] {local_filename}")
        
        url = f"{GDAC_BASE_URL}/{remote_path}"
        output_file = output_path / local_filename
        
        # Skip if already exists
        if output_file.exists():
            print(f"    ↻ Already exists (size: {output_file.stat().st_size:,} bytes)")
            downloaded_files.append(output_file)
            continue
        
        # Download
        success = download_file(url, output_file)
        
        if success:
            downloaded_files.append(output_file)
        else:
            failed_files.append(local_filename)
        
        # Be nice to the server
        if i < len(files_to_download):
            time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 70)
    print("Download Complete")
    print("=" * 70)
    print(f"✓ Successfully downloaded: {len(downloaded_files)} files")
    
    if failed_files:
        print(f"✗ Failed downloads: {len(failed_files)} files")
        print("\nFailed files:")
        for filename in failed_files:
            print(f"  - {filename}")
    
    if downloaded_files:
        total_size = sum(f.stat().st_size for f in downloaded_files)
        print(f"\nTotal data downloaded: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        print(f"\nFiles saved to: {output_path.absolute()}")
        print("\nNext steps:")
        print("  1. Run: python ingest.py")
        print("  2. Run: python build_index.py")
        print("  3. Restart backend server to use real data")
    
    return downloaded_files


def main():
    """Main execution."""
    # Get script directory
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data" / "raw"
    
    print("\n🌊 Real ARGO Data Downloader")
    print("Source: Global Data Assembly Center (GDAC)")
    print("Data: Actual oceanographic measurements from autonomous floats\n")
    
    # Download files
    downloaded = download_argo_data(output_dir=str(data_dir), max_files=20)
    
    if not downloaded:
        print("\n⚠️  No files were downloaded successfully.")
        print("\nAlternative options:")
        print("1. Check your internet connection")
        print("2. Try again later (GDAC may be under maintenance)")
        print("3. Download manually from: https://data-argo.ifremer.fr/")
        print("   Browse to dac/<institution>/<float_id>/profiles/")
        print("   Download .nc files to backend/data/raw/")
        return 1
    
    print("\n✓ Real ARGO data ready for ingestion!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
