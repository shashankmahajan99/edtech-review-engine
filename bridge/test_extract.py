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
    
    # Try finding articles or text
    articles = page.locator("article").all()
    print("Found articles count:", len(articles))
    for i, a in enumerate(articles[-3:]):
        print(f"--- ARTICLE {i} ---")
        print(a.inner_text()[:300])

    browser.close()
