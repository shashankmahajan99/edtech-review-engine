"""
Apex SMTP Server Daemon Runner.
Starts the aiosmtpd RFC 5321 server daemon on port 1025.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mail.smtp_server import ApexSMTPServer

if __name__ == "__main__":
    server = ApexSMTPServer(host="127.0.0.1", port=1025)
    server.start()
    print("Apex SMTP Daemon is active. Ready to process institutional email traffic.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping SMTP Daemon...")
        server.stop()
