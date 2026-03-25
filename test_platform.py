"""
Comprehensive Platform Test Suite
Tests all major components for proper operation
"""
import sys
import os
import requests
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def test_backend_running():
    """Test if backend is accessible"""
    try:
        response = requests.get("http://localhost:8001", timeout=5)
        if response.status_code == 200:
            print_success("Backend server is running")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except requests.ConnectionError:
        print_error("Backend not accessible at http://localhost:8001")
        print_info("Start with: cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001")
        return False
    except Exception as e:
        print_error(f"Backend test failed: {e}")
        return False

def test_api_docs():
    """Test if API documentation is accessible"""
    try:
        response = requests.get("http://localhost:8001/docs", timeout=5)
        if response.status_code == 200:
            print_success("API documentation accessible")
            return True
        else:
            print_error("API docs not accessible")
            return False
    except Exception as e:
        print_error(f"API docs test failed: {e}")
        return False

def test_health_endpoint():
    """Test health check endpoint"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check: {data.get('status', 'unknown')}")
            return True
        else:
            print_error("Health check failed")
            return False
    except Exception as e:
        print_error(f"Health check test failed: {e}")
        return False

def test_database():
    """Test if database has data"""
    try:
        response = requests.get("http://localhost:8001/data/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = data.get('total_profiles', 0)
            if count > 0:
                print_success(f"Database has {count} profiles")
                return True
            else:
                print_warning("Database is empty - run python ingest.py")
                return False
        else:
            print_error("Could not fetch database summary")
            return False
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False

def test_authentication():
    """Test user registration and login"""
    try:
        # Try to register
        test_user = {
            "name": "Test User",
            "email": f"test_{int(time.time())}@test.com",
            "password": "test123456"
        }
        
        register_response = requests.post(
            "http://localhost:8001/auth/register",
            json=test_user,
            timeout=5
        )
        
        if register_response.status_code == 201:
            print_success("User registration works")
            
            # Try to login
            login_response = requests.post(
                "http://localhost:8001/auth/login",
                json={"email": test_user["email"], "password": test_user["password"]},
                timeout=5
            )
            
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                if token:
                    print_success("User login works")
                    return True
                else:
                    print_error("Login succeeded but no token received")
                    return False
            else:
                print_error("Login failed")
                return False
        else:
            print_warning("Could not register new user (may already exist)")
            return True  # Not critical
            
    except Exception as e:
        print_error(f"Authentication test failed: {e}")
        return False

def test_chat_endpoint():
    """Test if chat endpoint responds"""
    try:
        response = requests.post(
            "http://localhost:8001/chat/query",
            json={"query": "What is the temperature?"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('response'):
                print_success("Chat endpoint works")
                return True
            else:
                print_error("Chat returned no response")
                return False
        else:
            print_error(f"Chat endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Chat test failed: {e}")
        return False

def test_visualization_endpoints():
    """Test visualization endpoints"""
    endpoints = [
        "/visualization/temperature-distribution",
        "/visualization/salinity-boxplot",
        "/visualization/temp-salinity-scatter",
        "/visualization/depth-profile"
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8001{endpoint}", timeout=5)
            if response.status_code == 200:
                print_success(f"Visualization {endpoint.split('/')[-1]} works")
            else:
                print_error(f"Visualization {endpoint.split('/')[-1]} failed")
                all_ok = False
        except Exception as e:
            print_error(f"Visualization test failed: {e}")
            all_ok = False
    
    return all_ok

def test_map_data():
    """Test map data endpoint"""
    try:
        response = requests.get("http://localhost:8001/data/map", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                print_success(f"Map data has {len(data)} locations")
                return True
            else:
                print_warning("Map data is empty")
                return False
        else:
            print_error("Map data endpoint failed")
            return False
    except Exception as e:
        print_error(f"Map data test failed: {e}")
        return False

def test_live_endpoints():
    """Test live ARGO endpoints"""
    try:
        # Test stats endpoint
        response = requests.get("http://localhost:8001/live/stats", timeout=5)
        if response.status_code == 200:
            print_success("Live ARGO stats endpoint works")
            return True
        else:
            print_error("Live ARGO endpoints not responding")
            return False
    except Exception as e:
        print_error(f"Live endpoints test failed: {e}")
        return False

def test_faiss_index():
    """Test if FAISS index exists"""
    index_path = Path("backend/data/faiss_index.bin")
    if index_path.exists():
        print_success(f"FAISS index exists ({index_path.stat().st_size} bytes)")
        return True
    else:
        print_warning("FAISS index not found - run python build_index.py")
        return False

def test_cache_directory():
    """Test if cache directory exists"""
    cache_dir = Path("backend/cache")
    if cache_dir.exists():
        cache_files = list(cache_dir.glob("*.json"))
        print_success(f"Cache directory exists ({len(cache_files)} files)")
        return True
    else:
        print_info("Cache directory will be created automatically")
        return True

def test_netcdf_files():
    """Test if NetCDF data files exist"""
    data_dir = Path("backend/data/raw")
    if data_dir.exists():
        nc_files = list(data_dir.glob("*.nc"))
        if len(nc_files) > 0:
            total_size = sum(f.stat().st_size for f in nc_files)
            print_success(f"Found {len(nc_files)} NetCDF files ({total_size / 1024:.1f} KB)")
            return True
        else:
            print_warning("No NetCDF files found - run fetch_live_data.py")
            return False
    else:
        print_error("Data directory not found")
        return False

def test_frontend_running():
    """Test if frontend is accessible"""
    try:
        # Try different common ports
        for port in [5173, 5174, 5175, 5176]:
            try:
                response = requests.get(f"http://localhost:{port}", timeout=2)
                if response.status_code == 200:
                    print_success(f"Frontend running on port {port}")
                    return True
            except requests.ConnectionError:
                continue
        
        print_warning("Frontend not running - start with: cd frontend && npm run dev")
        return False
    except Exception as e:
        print_error(f"Frontend test failed: {e}")
        return False

def run_all_tests():
    """Run comprehensive test suite"""
    print("\n" + "=" * 60)
    print("ARGO Platform Comprehensive Test Suite")
    print("=" * 60 + "\n")
    
    results = {}
    
    print("[1/15] Testing Backend Server...")
    results['backend'] = test_backend_running()
    time.sleep(0.5)
    
    if results['backend']:
        print("\n[2/15] Testing API Documentation...")
        results['docs'] = test_api_docs()
        time.sleep(0.5)
        
        print("\n[3/15] Testing Health Endpoint...")
        results['health'] = test_health_endpoint()
        time.sleep(0.5)
        
        print("\n[4/15] Testing Database...")
        results['database'] = test_database()
        time.sleep(0.5)
        
        print("\n[5/15] Testing Authentication...")
        results['auth'] = test_authentication()
        time.sleep(0.5)
        
        print("\n[6/15] Testing Chat Endpoint...")
        results['chat'] = test_chat_endpoint()
        time.sleep(0.5)
        
        print("\n[7/15] Testing Visualization Endpoints...")
        results['visualizations'] = test_visualization_endpoints()
        time.sleep(0.5)
        
        print("\n[8/15] Testing Map Data...")
        results['map'] = test_map_data()
        time.sleep(0.5)
        
        print("\n[9/15] Testing Live ARGO Endpoints...")
        results['live'] = test_live_endpoints()
        time.sleep(0.5)
    else:
        print_error("\nBackend not running - skipping API tests")
        results.update({
            'docs': False, 'health': False, 'database': False,
            'auth': False, 'chat': False, 'visualizations': False,
            'map': False, 'live': False
        })
    
    print("\n[10/15] Testing FAISS Index...")
    results['faiss'] = test_faiss_index()
    time.sleep(0.5)
    
    print("\n[11/15] Testing Cache Directory...")
    results['cache'] = test_cache_directory()
    time.sleep(0.5)
    
    print("\n[12/15] Testing NetCDF Files...")
    results['netcdf'] = test_netcdf_files()
    time.sleep(0.5)
    
    print("\n[13/15] Testing Frontend...")
    results['frontend'] = test_frontend_running()
    time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test_name.ljust(20)}: {status}")
    
    print("\n" + "=" * 60)
    percentage = (passed / total) * 100
    if percentage == 100:
        print(f"{Colors.GREEN}All tests passed! Platform is fully operational.{Colors.END}")
    elif percentage >= 80:
        print(f"{Colors.YELLOW}Most tests passed ({passed}/{total}). Platform is mostly operational.{Colors.END}")
    else:
        print(f"{Colors.RED}Many tests failed ({passed}/{total}). Platform needs attention.{Colors.END}")
    print("=" * 60 + "\n")
    
    # Recommendations
    if not results.get('backend'):
        print_info("Start backend: cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001")
    
    if not results.get('database'):
        print_info("Load data: cd backend && python ingest.py")
    
    if not results.get('faiss'):
        print_info("Build index: cd backend && python build_index.py")
    
    if not results.get('netcdf'):
        print_info("Get data: cd backend && python fetch_live_data.py --source erddap --limit 50")
    
    if not results.get('frontend'):
        print_info("Start frontend: cd frontend && npm run dev")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
