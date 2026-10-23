"""
Browser Bridge Launcher for ChatGPT (Astra) and Qwen (3.8 Max).
Launches an automated visible browser session with persistent user authentication.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path(__file__).resolve().parent.parent / "browser_data"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 65)
    print("  LAUNCHING SUPERVISOR BROWSER FOR CHATGPT & QWEN")
    print("=" * 65)
    print("[*] User data directory:", USER_DATA_DIR)
    print("[*] Opening ChatGPT (Astra) and Qwen (3.8 Max)...")
    
    with sync_playwright() as p:
        # Try MS Edge or Google Chrome
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                channel="msedge",
                headless=False,
                args=["--remote-debugging-port=9222", "--no-first-run", "--no-default-browser-check"]
            )
        except Exception:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                channel="chrome",
                headless=False,
                args=["--remote-debugging-port=9222", "--no-first-run", "--no-default-browser-check"]
            )

        # Tab 1: ChatGPT
        page1 = browser.pages[0] if browser.pages else browser.new_page()
        page1.goto("https://chatgpt.com")
        
        # Tab 2: Qwen
        page2 = browser.new_page()
        page2.goto("https://chat.qwen.ai")

        print("\n[OK] Browser launched successfully on your screen!")
        print("------------------------------------------------------------")
        print("ACTION REQUIRED:")
        print("1. Log in to ChatGPT on Tab 1 (Select GPT-6 Astra / Plus account)")
        print("2. Log in to Qwen on Tab 2 (Select Qwen 3.8 Max)")
        print("3. Leave this browser window open so the supervisor bridge can interact.")
        print("------------------------------------------------------------\n")
        print("Supervisory bridge is active and listening on port 9222...")
        
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nClosing browser bridge...")
            browser.close()


if __name__ == "__main__":
    main()
