import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=r'C:\Users\shashank\edtech-review-engine\browser_data',
        channel='msedge',
        headless=False
    )
    page = browser.new_page()
    page.goto('https://chat.qwen.ai', wait_until='domcontentloaded')
    time.sleep(4)
    
    screenshot_path = r'C:\Users\shashank\edtech-review-engine\output\qwen_view.png'
    page.screenshot(path=screenshot_path)
    print("Qwen Screenshot saved to:", screenshot_path)
    browser.close()
