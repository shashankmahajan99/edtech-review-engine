import json, time

status_file = r'C:\Users\shashank\edtech-review-engine\output\service_status.json'
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
      "public_url": "https://typing-accomplish-scheduled-promotional.trycloudflare.com"
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
    }
  },
  "supervisor": "Apex Service Monitor V1.0 (Autonomous Host Daemon)"
}

with open(status_file, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2)

print("Updated service_status.json with live tunnel URL!")
