"""
Frontier Model Autonomous Dispatcher (ChatGPT 6 Astra & Qwen 3.8 Max).
Executes heavy reasoning, manuscript deep diagnostics, and B2B growth strategy
directly through persistent browser sessions with automatic rate-limit detection.
"""

import time
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USER_DATA_DIR = str(PROJECT_ROOT / "browser_data")
LOGS_DIR = PROJECT_ROOT / "bridge" / "consultation_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class FrontierDispatcher:
    def __init__(self, user_data_dir: str = USER_DATA_DIR):
        self.user_data_dir = user_data_dir

    def query_chatgpt(self, prompt: str, timeout_seconds: int = 120) -> Dict[str, Any]:
        """
        Dispatches a prompt to ChatGPT (Astra), streams the output,
        and detects rate limits or errors.
        """
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ASTRA] Connecting to ChatGPT session...", flush=True)
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                channel="msedge",
                headless=False,
                args=["--remote-debugging-port=9222"]
            )
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto("https://chatgpt.com", wait_until="domcontentloaded")
                time.sleep(3)

                # Locate prompt input
                input_box = page.locator("#prompt-textarea, textarea, [contenteditable='true']").first
                if not input_box.is_visible():
                    return {"success": False, "error": "ChatGPT input box not visible. Check login."}

                input_box.click()
                input_box.fill(prompt)
                time.sleep(1)
                page.keyboard.press("Enter")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ASTRA] Prompt sent. Waiting for deep reasoning response...", flush=True)

                # Wait for stream to start and complete
                start_time = time.time()
                time.sleep(8)
                while time.time() - start_time < timeout_seconds:
                    # Check for stop button
                    stop_btn = page.locator("button[data-testid='stop-button'], button[aria-label='Stop streaming'], button[aria-label='Stop generating']")
                    if stop_btn.count() > 0 and stop_btn.first.is_visible():
                        time.sleep(4)
                        continue
                    
                    # Check for rate limit or cap warning
                    body_text = page.locator("body").inner_text()
                    if "You've reached your usage cap" in body_text or "try again later" in body_text.lower():
                        return {"success": False, "rate_limited": True, "error": "ChatGPT token usage cap reached."}

                    break

                time.sleep(2)
                articles = page.locator("article, [data-message-author-role='assistant'], .markdown").all()
                if articles:
                    response_text = articles[-1].inner_text()
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                    out_path = LOGS_DIR / f"chatgpt_response_{timestamp_str}.txt"
                    out_path.write_text(response_text, encoding="utf-8")
                    return {
                        "success": True,
                        "model": "ChatGPT 6 Astra",
                        "response": response_text,
                        "saved_to": str(out_path)
                    }
                else:
                    return {"success": False, "error": "No response text found in conversation DOM."}
            finally:
                browser.close()

    def query_qwen(self, prompt: str, timeout_seconds: int = 120) -> Dict[str, Any]:
        """
        Dispatches a prompt to Qwen (3.8 Max), streams output,
        and detects rate limits or errors.
        """
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [QWEN] Connecting to Qwen session...", flush=True)
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                channel="msedge",
                headless=False,
                args=["--remote-debugging-port=9222"]
            )
            try:
                page = browser.new_page()
                page.goto("https://chat.qwen.ai", wait_until="domcontentloaded")
                time.sleep(4)

                input_box = page.locator("textarea, [contenteditable='true']").first
                if not input_box.is_visible():
                    return {"success": False, "error": "Qwen input box not visible."}

                input_box.click()
                input_box.fill(prompt)
                time.sleep(1)
                page.keyboard.press("Enter")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [QWEN] Prompt sent. Waiting for generation...", flush=True)

                start_time = time.time()
                time.sleep(8)
                while time.time() - start_time < timeout_seconds:
                    stop_btn = page.locator("button[aria-label='Stop'], .stop-button, button:has-text('Stop')")
                    if stop_btn.count() > 0 and stop_btn.first.is_visible():
                        time.sleep(4)
                        continue
                    break

                time.sleep(2)
                messages = page.locator(".message-content, .markdown, .qwen-assistant-message").all()
                if messages:
                    response_text = messages[-1].inner_text()
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                    out_path = LOGS_DIR / f"qwen_response_{timestamp_str}.txt"
                    out_path.write_text(response_text, encoding="utf-8")
                    return {
                        "success": True,
                        "model": "Qwen 3.8 Max",
                        "response": response_text,
                        "saved_to": str(out_path)
                    }
                else:
                    return {"success": False, "error": "Could not extract Qwen message content."}
            finally:
                browser.close()


if __name__ == "__main__":
    dispatcher = FrontierDispatcher()
    print("Testing connection to ChatGPT Astra...")
    res = dispatcher.query_chatgpt("Hello Astra, confirm you are standing by as Chief Strategic Supervisor for Apex Review Desk.")
    print("Result:", res.get("success"), res.get("model"))
    if res.get("response"):
        print("Response Excerpt:", res["response"][:300])
