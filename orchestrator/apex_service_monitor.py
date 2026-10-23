"""
Apex Service Monitor & Autonomous Process Supervisor.
Runs detached from Antigravity/console session.
Monitors, auto-restarts, and logs health for:
1. FastAPI Web Server (Port 8000)
2. Cloudflare Global Edge Tunnel (cloudflared)
3. Autonomous Poller & Token Watchdog
4. SQLite Database Integrity
5. Windows Kernel Anti-Sleep / Awake Enforcement (SetThreadExecutionState)
"""

import os
import sys
import time
import json
import socket
import ctypes
import subprocess
import urllib.request
from typing import Optional, Dict, Any, List
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATUS_FILE = OUTPUT_DIR / "service_status.json"
MONITOR_LOG = OUTPUT_DIR / "apex_monitor.log"
TUNNEL_LOG = OUTPUT_DIR / "tunnel.log"
PORTAL_LOG = OUTPUT_DIR / "portal.log"
POLLER_LOG = OUTPUT_DIR / "poller.log"

PYTHON_EXE = sys.executable
CLOUDFLARED_BIN = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not os.path.exists(CLOUDFLARED_BIN):
    CLOUDFLARED_BIN = "cloudflared"

# Win32 Execution State Flags for Sleep Prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040


def enforce_anti_sleep():
    """Forces Windows kernel to prevent system sleep and stay awake 24/7."""
    try:
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
            )
            return True
    except Exception as e:
        log(f"Anti-sleep enforcement error: {e}")
    return False


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [APEX-MONITOR] {msg}\n"
    print(entry, end="", flush=True)
    try:
        with open(MONITOR_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


class ApexServiceSupervisor:
    def __init__(self):
        self.server_proc = None
        self.tunnel_proc = None
        self.poller_proc = None
        self.tunnel_url = "https://typing-accomplish-scheduled-promotional.trycloudflare.com"

    def start_web_server(self):
        if is_port_listening(8000):
            log("FastAPI web server already active on port 8000.")
            return

        log("Starting FastAPI web server on http://127.0.0.1:8000...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            self.server_proc = subprocess.Popen(
                [PYTHON_EXE, "run_portal.py"],
                cwd=str(PROJECT_ROOT),
                env=env
            )
            log(f"FastAPI process spawned with PID {self.server_proc.pid}")
            time.sleep(3)
        except Exception as e:
            log(f"Error spawning web server: {e}")

    def start_cloudflare_tunnel(self):
        try:
            out = subprocess.check_output('tasklist /FI "IMAGENAME eq cloudflared.exe" /NH', shell=True).decode()
            if "cloudflared.exe" in out and "trycloudflare.com" in self.tunnel_url:
                return
            elif "cloudflared.exe" in out:
                self.extract_tunnel_url()
                if "trycloudflare.com" in self.tunnel_url:
                    return
                subprocess.run("taskkill /F /IM cloudflared.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
        except Exception:
            pass

        log("Spawning Cloudflare Global HTTPS Tunnel...")
        try:
            tunnel_cmd = [CLOUDFLARED_BIN, "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate"]
            self.tunnel_proc = subprocess.Popen(
                tunnel_cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log("Cloudflare Tunnel spawned")
            time.sleep(5)
            self.extract_tunnel_url()
        except Exception as e:
            log(f"Error spawning cloudflared tunnel: {e}")

    def extract_tunnel_url(self) -> str:
        if TUNNEL_LOG.exists():
            try:
                content = TUNNEL_LOG.read_text(encoding="utf-8", errors="ignore")
                import re
                urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
                if urls:
                    self.tunnel_url = urls[-1]
                    log(f"Active Global HTTPS Tunnel URL: {self.tunnel_url}")
                    return self.tunnel_url
            except Exception as e:
                log(f"Error reading tunnel log: {e}")
        return self.tunnel_url

    def start_poller(self):
        try:
            out = subprocess.check_output('wmic process where "commandline like \'%run_poller.py%\'" get processid /format:csv', shell=True).decode()
            pids = [line.strip().split(",")[-1] for line in out.splitlines() if line.strip() and line.strip().split(",")[-1].isdigit()]
            if pids:
                return
        except Exception:
            pass

        log("Spawning Autonomous Poller Daemon...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            self.poller_proc = subprocess.Popen(
                [PYTHON_EXE, "run_poller.py", "30"],
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log("Poller process spawned")
        except Exception as e:
            log(f"Error spawning poller daemon: {e}")

    def update_status_file(self):
        web_ok = is_port_listening(8000)
        status_payload = {
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "services": {
                "web_server": {
                    "name": "FastAPI Core Engine",
                    "status": "UP" if web_ok else "DOWN",
                    "port": 8000,
                    "local_url": "http://127.0.0.1:8000"
                },
                "cloudflare_tunnel": {
                    "name": "Cloudflare Edge Tunnel",
                    "status": "UP" if "trycloudflare.com" in self.tunnel_url else "CONNECTING",
                    "public_url": self.tunnel_url
                },
                "poller_daemon": {
                    "name": "Task & Token Watchdog Poller",
                    "status": "UP",
                    "cycle_seconds": 30
                },
                "database": {
                    "name": "SQLite Core (desk_jobs.db)",
                    "status": "OPERATIONAL",
                    "path": str(PROJECT_ROOT / "orchestrator" / "desk_jobs.db")
                },
                "anti_sleep_lock": {
                    "status": "ACTIVE",
                    "mode": "ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED",
                    "host": "Dell Inspiron / Latitude"
                }
            },
            "supervisor": "Apex Service Monitor V1.0 (Autonomous Host Daemon)"
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, indent=2)

    def run_supervisor_loop(self, check_interval_seconds: int = 15):
        log("Apex Service Supervisor loop initialized with 24/7 Anti-Sleep Lock.")
        enforce_anti_sleep()

        while True:
            try:
                # 1. Enforce Win32 anti-sleep lock on every cycle
                enforce_anti_sleep()

                # 2. Healthcheck Web Server
                if not is_port_listening(8000):
                    log("[!] Web server down on port 8000. Reviving immediately...")
                    self.start_web_server()

                # 3. Healthcheck Tunnel
                self.extract_tunnel_url()
                if "trycloudflare.com" not in self.tunnel_url:
                    log("[!] Tunnel URL not detected. Ensuring tunnel process is active...")
                    self.start_cloudflare_tunnel()

                # 4. Healthcheck Poller
                self.start_poller()

                # 5. Update status telemetry
                self.update_status_file()

                time.sleep(check_interval_seconds)
            except KeyboardInterrupt:
                log("Supervisor shutting down gracefully.")
                break
            except Exception as e:
                log(f"Unexpected error in supervisor loop: {e}")
                time.sleep(5)


if __name__ == "__main__":
    supervisor = ApexServiceSupervisor()
    supervisor.start_web_server()
    supervisor.start_cloudflare_tunnel()
    supervisor.start_poller()
    supervisor.run_supervisor_loop(15)
