"""
Tests access to ChatGPT (Astra) and Qwen (3.8 Max) in the persistent browser context.
"""

import time
from playwright.sync_api import sync_playwright

USER_DATA_DIR = r"C:\Users\shashank\edtech-review-engine\browser_data"

def test_access():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=["--remote-debugging-port=9222"]
        )
        
        # Open ChatGPT
        page1 = browser.pages[0] if browser.pages else browser.new_page()
        page1.goto("https://chatgpt.com", wait_until="domcontentloaded")
        time.sleep(3)
        print("ChatGPT Page URL:", page1.url)
        print("ChatGPT Title:", page1.title())
        
        # Check if textarea/prompt box exists
        input_box = page1.locator("textarea, #prompt-textarea, [contenteditable='true']").first
        has_input = input_box.is_visible() if input_box.count() > 0 else False
        print("ChatGPT Input Box Visible:", has_input)

        # Open Qwen
        page2 = browser.new_page()
        page2.goto("https://chat.qwen.ai", wait_until="domcontentloaded")
        time.sleep(3)
        print("Qwen Page URL:", page2.url)
        print("Qwen Title:", page2.title())
        qwen_input = page2.locator("textarea, [contenteditable='true']").first
        has_qwen_input = qwen_input.is_visible() if qwen_input.count() > 0 else False
        print("Qwen Input Box Visible:", has_qwen_input)

        # Keep browser open for interaction
        print("[*] Browser is open on screen.")
        browser.close()

if __name__ == "__main__":
    test_access()
