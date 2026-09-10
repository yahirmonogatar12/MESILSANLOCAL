import os
import sys
import time
from playwright.sync_api import sync_playwright

output_dir = os.path.join(os.getcwd(), 'output', 'screenshots')
os.makedirs(output_dir, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()

    # 1. Login Page
    print("Navigating to login...")
    page.goto('http://127.0.0.1:5000/login', wait_until='networkidle')
    page.screenshot(path=os.path.join(output_dir, '01_login.png'))
    print("Login screenshot saved.")

    # Fill credentials
    page.locator('input[name="username"]').fill('jesus')
    page.locator('input[name="password"]').fill('2707')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    time.sleep(1)

    print("Current URL after login:", page.url)
    page.screenshot(path=os.path.join(output_dir, '02_portal_inicio.png'))
    print("Portal screenshot saved.")

    # 2. Go to ILSAN-ELECTRONICS
    print("Navigating to /ILSAN-ELECTRONICS...")
    page.goto('http://127.0.0.1:5000/ILSAN-ELECTRONICS', wait_until='networkidle')
    time.sleep(2)
    page.screenshot(path=os.path.join(output_dir, '03_mes_main.png'))
    print("MES Main screenshot saved.")

    # Print available nav buttons
    buttons = page.locator('.nav-button').all()
    print("Nav buttons found:", len(buttons))
    for b in buttons:
        try:
            print(" - Button text/id:", b.get_attribute('id'), b.inner_text().replace('\n', ' '))
        except Exception:
            pass

    browser.close()
