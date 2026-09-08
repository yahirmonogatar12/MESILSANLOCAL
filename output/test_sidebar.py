import os
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('http://127.0.0.1:5000/login')
    page.locator('input[name="username"]').fill('jesus')
    page.locator('input[name="password"]').fill('2707')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    page.goto('http://127.0.0.1:5000/ILSAN-ELECTRONICS')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    # Click Control de material
    btn = page.locator('#Control\\ de\\ material')
    btn.click()
    time.sleep(1)

    # Click dropdown button inside sidebar
    drop = page.locator('#sidebarControlMaterial')
    page.locator('button[data-bs-target="#sidebarControlMaterial"]').click()
    time.sleep(1)

    # Click Inventario actual
    inv = page.locator("text='Inventario actual'")
    print("Clicking Inventario actual...")
    inv.click()
    time.sleep(3)

    page.screenshot(path='output/screenshots/test_material_inventory.png')
    print("Screenshot saved to output/screenshots/test_material_inventory.png")

    browser.close()
