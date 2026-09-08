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
    
    # Test calling cargarContenidoDinamico for AOI
    print("Testing dynamic load for AOI...")
    page.evaluate("cargarContenidoDinamico('historial-aoi-unique-container', '/historial-aoi-ajax')")
    time.sleep(3)
    page.screenshot(path='output/screenshots/test_aoi.png')
    print("AOI screenshot taken.")

    # Test dynamic load for Trazabilidad
    print("Testing dynamic load for Trazabilidad PCB...")
    page.evaluate("cargarContenidoDinamico('trazabilidad-pcb-unique-container', '/control_resultados/trazabilidad_pcb')")
    time.sleep(3)
    page.screenshot(path='output/screenshots/test_trazabilidad.png')
    print("Trazabilidad screenshot taken.")

    browser.close()
