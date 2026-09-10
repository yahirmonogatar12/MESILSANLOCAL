import os
import time
from playwright.sync_api import sync_playwright

output_dir = os.path.join(os.getcwd(), 'output', 'screenshots')

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('http://127.0.0.1:5000/login')
    page.locator('input[name="username"]').fill('jesus')
    page.locator('input[name="password"]').fill('2707')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    time.sleep(1)

    # 1. Auditoria
    print("Capturing Auditoria...")
    page.goto('http://127.0.0.1:5000/admin/auditoria')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    page.screenshot(path=os.path.join(output_dir, '21_admin_auditoria.png'))

    # 2. Permisos
    print("Capturing Permisos...")
    page.goto('http://127.0.0.1:5000/admin/permisos')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    page.screenshot(path=os.path.join(output_dir, '22_admin_permisos.png'))

    # 3. Defect Management
    print("Capturing Defect Management...")
    page.goto('http://127.0.0.1:5000/defect-management')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    page.screenshot(path=os.path.join(output_dir, '23_defect_management.png'))

    browser.close()
    print("Extra captures done.")
