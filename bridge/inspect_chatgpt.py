import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=r'C:\Users\shashank\edtech-review-engine\browser_data',
        channel='msedge',
        headless=False
    )
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto('https://chatgpt.com', wait_until='domcontentloaded')
    time.sleep(4)
    
    # Save a screenshot to inspect the state visually
    screenshot_path = r'C:\Users\shashank\edtech-review-engine\output\chatgpt_view.png'
    page.screenshot(path=screenshot_path)
    print("Screenshot saved to:", screenshot_path)

    # Print main container classes
    divs = page.locator("main").inner_text()
    print("Main inner text length:", len(divs))
    print("Main text excerpt:", divs[:500])

    browser.close()
