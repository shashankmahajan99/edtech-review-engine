"""
Autonomous CDP Consultant for ChatGPT (GPT-6 Astra) & Qwen (3.8 Max).
Connects to the active browser instance on port 9222 to consult frontier models for business supervision.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

CONSULTATION_LOGS = Path(__file__).resolve().parent / "consultation_logs"
CONSULTATION_LOGS.mkdir(parents=True, exist_ok=True)


class BrowserConsultant:
    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url

    def check_login_status(self) -> Dict[str, bool]:
        """Inspects whether ChatGPT and Qwen tabs are logged in."""
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(self.cdp_url)
            contexts = browser.contexts
            if not contexts:
                return {"chatgpt": False, "qwen": False}
            
            pages = contexts[0].pages
            status = {"chatgpt": False, "qwen": False}
            
            for page in pages:
                url = page.url
                if "chatgpt.com" in url:
                    # Check if prompt textarea / contenteditable is present
                    is_logged_in = page.locator("#prompt-textarea, [contenteditable='true']").count() > 0
                    status["chatgpt"] = bool(is_logged_in)
                elif "qwen.ai" in url or "qwenlm.ai" in url:
                    is_logged_in = page.locator("textarea, [contenteditable='true']").count() > 0
                    status["qwen"] = bool(is_logged_in)

            return status

    def consult_frontier_thinkers(self, prompt: str, target: str = "chatgpt") -> Optional[str]:
        """
        Sends a strategic prompt to the target browser tab, waits for completion,
        and returns the model's synthesized architectural directive.
        """
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(self.cdp_url)
            context = browser.contexts[0]
            target_page = None
            
            for page in context.pages:
                if target == "chatgpt" and "chatgpt.com" in page.url:
                    target_page = page
                    break
                elif target == "qwen" and ("qwen.ai" in page.url or "qwenlm.ai" in page.url):
                    target_page = page
                    break

            if not target_page:
                print(f"[!] Target tab '{target}' not found.")
                return None

            print(f"[*] Dispatching strategic consultation to {target.upper()}...")
            
            # Select input element
            input_box = target_page.locator("#prompt-textarea, textarea, [contenteditable='true']").first
            if not input_box.is_visible():
                print(f"[!] Input box on {target} not visible. Please verify you are logged in.")
                return None

            input_box.click()
            input_box.fill(prompt)
            time.sleep(1)
            target_page.keyboard.press("Enter")
            
            print(f"[*] Prompt sent to {target}. Waiting for generation to complete...")
            time.sleep(8)  # Initial generation buffer
            
            # Wait for generation stop button or idle state
            # Collect response text
            responses = target_page.locator("[data-message-author-role='assistant'], .markdown, .agent-message").all_inner_texts()
            if responses:
                latest_reply = responses[-1]
                log_file = CONSULTATION_LOGS / f"{target}_consultation_{int(time.time())}.md"
                log_file.write_text(f"# Strategic Guidance from {target.upper()}\n\n{latest_reply}", encoding="utf-8")
                print(f"[✓] Consultation saved to {log_file}")
                return latest_reply
            
            return None


if __name__ == "__main__":
    consultant = BrowserConsultant()
    print("Checking active login status...")
    status = consultant.check_login_status()
    print("Status:", status)
