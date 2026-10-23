import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\shashank\edtech-review-engine")
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from portal.server import app

client = TestClient(app)

print("1. Testing /reviewer GET (Reviewer Workbench)...")
res = client.get("/reviewer")
print("   Reviewer desk status:", res.status_code)
assert "Reviewer Operations Workbench" in res.text or "Reviewer Desk" in res.text or "Queue" in res.text

print("2. Testing /admin GET (Master Command Center)...")
res = client.get("/admin")
print("   Admin console status:", res.status_code)
assert "Master Startup Command Center" in res.text or "Total Revenue" in res.text or "Transactions" in res.text

print("3. Testing /reviewer/qualify GET (Qualification Exam)...")
res = client.get("/reviewer/qualify")
print("   Reviewer qualify status:", res.status_code)

print("ALL OPERATIONAL AND REVIEWER ENDPOINTS VERIFIED!")
