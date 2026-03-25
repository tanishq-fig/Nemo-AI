import requests
import json
import sys
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
DEMO_EMAIL = "demo@argo.com"
DEMO_PASS = "demo123"

# Force UTF-8 encoding for Windows console (to handle emojis like ✅)
sys.stdout.reconfigure(encoding='utf-8')

def print_section(title):
    print(f"\n{'='*60}")
    print(f"TESTING: {title}")
    print('='*60)

def print_result(name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"   Details: {details}")

class ArgoTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.headers = {"Content-Type": "application/json"}

    def test_health(self):
        print_section("System Health")
        try:
            resp = self.session.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print_result("Health Check", True, str(resp.json()))
                return True
            else:
                print_result("Health Check", False, f"Status: {resp.status_code}")
                return False
        except Exception as e:
            print_result("Health Check", False, f"Connection Refused: {e}")
            return False

    def test_auth(self):
        print_section("Authentication")
        
        # 1. Login
        login_data = {
            "username": DEMO_EMAIL,  # OAuth2 expects 'username' form field for email
            "password": DEMO_PASS
        }
        # Note: OAuth2PasswordRequestForm usually expects form data, not JSON
        try:
            resp = self.session.post(f"{BASE_URL}/auth/login", data=login_data)
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                self.headers["Authorization"] = f"Bearer {self.token}"
                print_result("Login (Demo User)", True, "Token received")
            else:
                print_result("Login (Demo User)", False, f"Status: {resp.status_code} - {resp.text}")
                return False

            # 2. Get Me
            resp = self.session.get(f"{BASE_URL}/auth/me", headers=self.headers)
            if resp.status_code == 200:
                user = resp.json()
                print_result("Get Current User", True, f"User: {user.get('email')}")
            else:
                print_result("Get Current User", False, f"Status: {resp.status_code}")
        
        except Exception as e:
            print_result("Auth Flow", False, str(e))
            return False
        return True

    def test_data_endpoints(self):
        print_section("Data Retrieval")
        if not self.token:
            print("Skipping Data tests (No Token)")
            return

        # 1. Summary
        try:
            resp = self.session.get(f"{BASE_URL}/data/summary", headers=self.headers)
            if resp.status_code == 200:
                print_result("Data Summary", True, str(resp.json()))
            else:
                print_result("Data Summary", False, f"Status: {resp.status_code}")
        except Exception as e: print_result("Data Summary", False, str(e))

        # 2. Map Data
        try:
            resp = self.session.get(f"{BASE_URL}/visualization/map", headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else 0
                print_result("Map Data Points", True, f"Received {count} coordinates")
            else:
                print_result("Map Data Points", False, f"Status: {resp.status_code}")
        except Exception as e: print_result("Map Data Points", False, str(e))
        
        # 3. Profiles
        try:
            resp = self.session.get(f"{BASE_URL}/data/profiles?limit=5", headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                print_result("List Profiles", True, f"Received {len(items)} profiles")
            else:
                print_result("List Profiles", False, f"Status: {resp.status_code}")
        except Exception as e: print_result("List Profiles", False, str(e))

    def test_chat_rag(self):
        print_section("Conversational AI (RAG)")
        if not self.token:
            return

        query = {
            "query": "What is the temperature range near India?"
        }
        
        try:
            start_time = time.time()
            resp = self.session.post(f"{BASE_URL}/chat/query", json=query, headers=self.headers)
            duration = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                has_response = bool(data.get('response'))
                has_sources = len(data.get('sources', [])) > 0
                print_result("RAG Query", True, f"Time: {duration:.2f}s | Has Answer: {has_response} | Sources: {len(data.get('sources', []))}")
                
                # Check for graph data
                if 'visualization' in data:
                    print_result("AI Visualization", True, f"Type: {data['visualization'].get('type')}")
                else:
                    print_result("AI Visualization", True, "No visualization suggested (acceptable)")
            else:
                print_result("RAG Query", False, f"Status: {resp.status_code} - {resp.text}")
        except Exception as e:
            print_result("RAG Query", False, str(e))

    def test_live_modules(self):
        print_section("Live Data Module")
        
        # 1. Stats
        try:
            resp = self.session.get(f"{BASE_URL}/live/stats", headers=self.headers)
            if resp.status_code == 200:
                print_result("Cache Stats", True, str(resp.json()))
            else:
                print_result("Cache Stats", False, f"Status: {resp.status_code}")
        except Exception as e: print_result("Cache Stats", False, str(e))

        # 2. Recent (use 1 day to ensure speed)
        try:
            resp = self.session.get(f"{BASE_URL}/live/recent?days=1&limit=10", headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                print_result("Fetch Recent Live Data", True, f"Fetched {data.get('count')} profiles")
            else:
                print_result("Fetch Recent Live Data", False, f"Status: {resp.status_code}")
        except Exception as e: print_result("Fetch Recent Live Data", False, str(e))

    def run_all(self):
        print("Starting Thorough Platform Test...")
        print(f"Target: {BASE_URL}")
        
        if self.test_health():
            self.test_auth()
            self.test_data_endpoints()
            self.test_chat_rag()
            self.test_live_modules()
        
        print("\nTest Suite Completed.")

if __name__ == "__main__":
    tester = ArgoTester()
    tester.run_all()
