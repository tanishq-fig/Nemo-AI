import xarray as xr
import os

files = [f for f in os.listdir('data/raw') if f.endswith('.nc')]
print(f"Total files: {len(files)}\n")

unique_locations = set()
for f in files[:10]:  # Check first 10 files
    ds = xr.open_dataset(f'data/raw/{f}')
    lat = float(ds['LATITUDE'].values[0])
    lon = float(ds['LONGITUDE'].values[0])
    juld = ds['JULD'].values[0] if 'JULD' in ds else 'N/A'
    unique_locations.add((round(lat, 2), round(lon, 2)))
    print(f"{f}: Lat={lat:.2f}, Lon={lon:.2f}, Date={juld}")
    ds.close()

print(f"\nUnique locations in first 10 files: {len(unique_locations)}")
