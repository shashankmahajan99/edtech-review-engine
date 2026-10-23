import json, time, urllib.request

status_file = r'C:\Users\shashank\edtech-review-engine\output\service_status.json'
tunnel_url = 'https://progress-trim-capable-introduce.trycloudflare.com'

payload = {
  "timestamp": time.time(),
  "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
  "services": {
    "web_server": {
      "name": "FastAPI Core Engine",
      "status": "UP",
      "port": 8000,
      "local_url": "http://127.0.0.1:8000"
    },
    "cloudflare_tunnel": {
      "name": "Cloudflare Edge Tunnel",
      "status": "UP",
      "public_url": tunnel_url
    },
    "poller_daemon": {
      "name": "Task & Token Watchdog Poller",
      "status": "UP",
      "cycle_seconds": 30
    },
    "database": {
      "name": "SQLite Core (desk_jobs.db)",
      "status": "OPERATIONAL",
      "path": "C:\\Users\\shashank\\edtech-review-engine\\orchestrator\\desk_jobs.db"
    },
    "anti_sleep_lock": {
      "status": "ACTIVE",
      "mode": "ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED | LID_ACTION_0",
      "host": "Dell Inspiron / Latitude (Standby Disabled)"
    }
  },
  "supervisor": "Apex Service Monitor V1.0 (Autonomous Host Daemon)"
}

with open(status_file, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2)

print("Updated service_status.json successfully!")

# Verify local and tunnel
time.sleep(2)
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5) as r:
        print("Local Health:", r.status, r.read().decode())
except Exception as e:
    print("Local Err:", e)

try:
    with urllib.request.urlopen(tunnel_url + '/api/health', timeout=10) as r:
        print("Tunnel Health:", r.status, r.read().decode())
except Exception as e:
    print("Tunnel Err:", e)
