import requests
import json
import os
from datetime import datetime

BASE_URL = "http://localhost:8001"
EMAIL = "demo@argo.com"
PASSWORD = "demo123"

def get_token():
    try:
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code == 200:
            return r.json()["access_token"]
        return None
    except:
        return None

def run_mega_test():
    token = get_token()
    if not token:
        print("Mega Test Failed: Could not login.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    report = []
    report.append("# 🧪 ARGO Platform Mega-Test Report")
    report.append(f"Generated at: {datetime.now().isoformat()}\n")

    # 1. Map Check
    report.append("## 1. Map Data Integrity")
    try:
        r = requests.get(f"{BASE_URL}/visualization/map?limit=100", headers=headers)
        if r.status_code == 200:
            data = r.json()
            count = data.get('count', 0)
            report.append(f"- Map points found: {count}")
            if count > 0:
                sample = data['points'][0]
                report.append(f"- Sample Location: Lat {sample['lat']}, Lon {sample['lon']}")
                report.append(f"- Temperature: {sample['temperature']}°C")
        else:
            report.append(f"- Map Error: {r.status_code}")
    except Exception as e:
        report.append(f"- Map Exception: {str(e)}")

    # 2. Chatbot Deep Test
    report.append("\n## 2. Scientific Chatbot Verification")
    questions = [
        "What is the average temperature across all current float measurements?",
        "Can you compare the salinity of floats in the Arctic versus the Indian Ocean?",
        "Show me a T-S diagram analysis for the deepest measurements (>500m).",
        "Identify any unusual temperature spikes in the recent data for float GLB_8649429.",
        "How do the measurements from the Southern Ocean compare to the Global average?"
    ]

    for q in questions:
        report.append(f"\n### 🔍 Query: {q}")
        try:
            r = requests.post(f"{BASE_URL}/chat/query", json={"query": q}, headers=headers)
            if r.status_code == 200:
                resp = r.json()
                report.append(f"**AI Response:**\n\n{resp['response']}\n")
                if "retrieved_context" in resp and resp["retrieved_context"]:
                    report.append("**Context Sources Used:**")
                    for ctx in resp["retrieved_context"][:2]:
                        report.append(f"- {ctx[:150]}...")
            else:
                report.append(f"- Chat Error: {r.status_code}")
        except Exception as e:
            report.append(f"- Chat Exception: {str(e)}")

    # 3. Analytics Check
    report.append("\n## 3. Analytics Backend Status")
    try:
        r = requests.get(f"{BASE_URL}/data/summary", headers=headers)
        if r.status_code == 200:
            sum_data = r.json()
            report.append(f"- Total Database Records: {sum_data['total_profiles']}")
            report.append(f"- Unique Floats Detected: {sum_data['total_floats']}")
            report.append(f"- Global Temp Range: {sum_data['temperature_range']['min']} to {sum_data['temperature_range']['max']}°C")
        else:
            report.append(f"- Summary Error: {r.status_code}")
    except Exception as e:
        report.append(f"- Summary Exception: {str(e)}")

    # Save report
    with open("MEGA_TEST_REPORT.md", "w", encoding='utf-8') as f:
        f.write("\n".join(report))
    print("Mega Test Complete. Results saved to MEGA_TEST_REPORT.md")

if __name__ == "__main__":
    run_mega_test()
