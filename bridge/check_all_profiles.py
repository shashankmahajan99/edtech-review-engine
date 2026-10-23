import time
from playwright.sync_api import sync_playwright

EDGE_DEFAULT = r"C:\Users\shashank\AppData\Local\Microsoft\Edge\User Data"

def check_edge_default():
    print("Testing Edge Default Profile...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=EDGE_DEFAULT,
                channel="msedge",
                headless=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://chatgpt.com", wait_until="domcontentloaded")
            time.sleep(3)
            page.screenshot(path=r"C:\Users\shashank\edtech-review-engine\output\edge_default_chatgpt.png")
            print("Edge Default ChatGPT URL:", page.url)
            browser.close()
    except Exception as e:
        print("Error checking Edge Default:", e)

if __name__ == "__main__":
    check_edge_default()
