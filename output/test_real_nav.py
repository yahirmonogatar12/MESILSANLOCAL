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

    # Click Control de resultados
    btn = page.locator('#Control\\ de\\ resultados')
    btn.click()
    time.sleep(1)

    # Click sidebar dropdown for Historial de maquinas SMT
    page.locator('button[data-bs-target="#sidebarMaquinasSMT"]').click()
    time.sleep(1)

    # Click Historial de maquina AOI
    page.locator("text='Historial de maquina AOI'").click()
    time.sleep(3)

    page.screenshot(path='output/screenshots/test_real_aoi.png')
    print("AOI Screenshot saved.")

    browser.close()
