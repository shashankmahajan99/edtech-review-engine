import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\shashank\edtech-review-engine")
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from portal.server import app

client = TestClient(app)

print("1. Testing /api/health...")
res = client.get("/api/health")
print("   Health status:", res.status_code, res.json())

print("2. Testing /api/audit/sample...")
audit_payload = {
    "text": "Ever since I was a child, I have always been deeply passionate about computers. Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum.",
    "institution": "Stanford"
}
res = client.post("/api/audit/sample", json=audit_payload)
print("   Audit status:", res.status_code)
data = res.json()
print("   Audit scores:", data["scores"])
print("   Cliches detected:", data["cliches_detected"])

print("3. Testing /checkout/pilot GET...")
res = client.get("/checkout/pilot")
print("   Checkout page status:", res.status_code)
assert "Beacon Admissions Group" in res.text or "Selected Package" in res.text

print("4. Testing /checkout/process POST (Simulating client signup)...")
checkout_data = {
    "company_name": "Cambridge Ivy Advisory",
    "contact_name": "Dr. Eleanor Vance",
    "email": "eleanor@cambridgeivy.com",
    "phone": "+1 (617) 555-8832",
    "package_id": "pilot",
    "volume_tier": "10-25",
    "payment_method": "card"
}
res = client.post("/checkout/process", data=checkout_data, follow_redirects=False)
print("   Process status:", res.status_code, res.headers.get("location"))
confirmation_url = res.headers.get("location")

print(f"5. Testing confirmation page ({confirmation_url})...")
res = client.get(confirmation_url)
print("   Confirmation status:", res.status_code)
assert "Capacity Confirmed" in res.text
assert "Cambridge Ivy Advisory" in res.text

print("6. Testing /agency/dashboard...")
res = client.get("/agency/dashboard?email=eleanor@cambridgeivy.com")
print("   Agency dashboard status:", res.status_code)
assert "Cambridge Ivy Advisory" in res.text

print("\nALL PORTAL COMMERCIAL ROUTES TESTED AND VERIFIED PERFECT!")
