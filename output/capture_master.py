import os
import time
from playwright.sync_api import sync_playwright

output_dir = os.path.join(os.getcwd(), 'output', 'screenshots')
os.makedirs(output_dir, exist_ok=True)

def wait_render(page, seconds=2.5):
    page.wait_for_load_state('networkidle')
    time.sleep(seconds)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()

    # 1. Login
    print("1. Capturing Login...")
    page.goto('http://127.0.0.1:5000/login')
    wait_render(page, 1)
    page.screenshot(path=os.path.join(output_dir, '01_login.png'))

    # Submit login
    page.locator('input[name="username"]').fill('jesus')
    page.locator('input[name="password"]').fill('2707')
    page.locator('button[type="submit"]').click()
    wait_render(page, 1.5)

    # 2. Portal Hub / Inicio
    print("2. Capturing Portal Hub...")
    page.screenshot(path=os.path.join(output_dir, '02_portal_inicio.png'))

    # 3. Portal Tickets
    print("3. Capturing Tickets Portal...")
    page.goto('http://127.0.0.1:5000/portal-tickets')
    wait_render(page, 2)
    page.screenshot(path=os.path.join(output_dir, '18_tickets_portal.png'))

    # 4. Calendario
    print("4. Capturing Calendario...")
    page.goto('http://127.0.0.1:5000/calendario')
    wait_render(page, 2)
    page.screenshot(path=os.path.join(output_dir, '19_calendario.png'))

    # 5. Admin Panel
    print("5. Capturing Admin Panel...")
    page.goto('http://127.0.0.1:5000/admin/panel')
    wait_render(page, 2)
    page.screenshot(path=os.path.join(output_dir, '20_admin_panel.png'))

    # 6. MES Shell Main
    print("6. Capturing MES Main Shell...")
    page.goto('http://127.0.0.1:5000/ILSAN-ELECTRONICS')
    wait_render(page, 2)
    page.screenshot(path=os.path.join(output_dir, '03_mes_shell.png'))

    # 7. Información Básica - Visor Modelos SMT
    print("7. Capturing Información Básica - Modelos SMT...")
    page.locator('#Información\\ Basica').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarControlModelosVisor ? window.mostrarControlModelosVisor() : (window.mostrarControlModelosSMT ? window.mostrarControlModelosSMT() : null)")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '04_info_modelos_smt.png'))
    except Exception as e:
        print("Error in 7:", e)

    # 8. Información Básica - Control de BOM
    print("8. Capturing Control de BOM...")
    try:
        page.evaluate("window.mostrarControlBOM && window.mostrarControlBOM()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '05_info_control_bom.png'))
    except Exception as e:
        print("Error in 8:", e)

    # 9. Control de Material - Inventario Actual
    print("9. Capturing Control de Material - Inventario Actual...")
    page.locator('#Control\\ de\\ material').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarInventarioActual && window.mostrarInventarioActual()")
        wait_render(page, 3)
        page.screenshot(path=os.path.join(output_dir, '06_material_inventario.png'))
    except Exception as e:
        print("Error in 9:", e)

    # 10. Control de Material - Invoices & Valuación
    print("10. Capturing Control de Material - Invoices...")
    try:
        page.evaluate("window.mostrarMaterialInvoices && window.mostrarMaterialInvoices()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '07_material_invoices.png'))
    except Exception as e:
        print("Error in 10:", e)

    # 11. Control de Producción - Plan SMD Diario
    print("11. Capturing Control de Producción - Plan SMD...")
    page.locator('#Control\\ de\\ producción').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarPlanSmdDiario ? window.mostrarPlanSmdDiario() : (window.mostrarPlanMainSMT ? window.mostrarPlanMainSMT() : null)")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '08_produccion_plan_smd.png'))
    except Exception as e:
        print("Error in 11:", e)

    # 12. Control de Producción - Herramentales Metal Mask
    print("12. Capturing Control de Herramentales - Metal Mask...")
    try:
        page.evaluate("window.mostrarControlMaskMetal && window.mostrarControlMaskMetal()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '09_produccion_metal_mask.png'))
    except Exception as e:
        print("Error in 12:", e)

    # 13. Control de Producción - Cuchillas de Corte
    print("13. Capturing Control de Cuchillas de Corte...")
    try:
        page.evaluate("window.mostrarControlCuchillasCorte && window.mostrarControlCuchillasCorte()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '10_produccion_cuchillas.png'))
    except Exception as e:
        print("Error in 13:", e)

    # 14. Control de Calidad - Liberación OQC
    print("14. Capturing Control de Calidad - Liberación OQC...")
    page.locator('#Control\\ de\\ calidad').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarHistorialLiberacionOQC && window.mostrarHistorialLiberacionOQC()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '11_calidad_liberacion_oqc.png'))
    except Exception as e:
        print("Error in 14:", e)

    # 15. Control de Calidad - PPMS
    print("15. Capturing Control de Calidad - PPMS OQC...")
    try:
        page.evaluate("window.mostrarPPMsOQC && window.mostrarPPMsOQC()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '12_calidad_ppms.png'))
    except Exception as e:
        print("Error in 15:", e)

    # 16. Control de Calidad - Master Sample
    print("16. Capturing Master Sample SMT...")
    try:
        page.evaluate("window.mostrarControlMasterSampleSMT && window.mostrarControlMasterSampleSMT()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '13_calidad_master_sample.png'))
    except Exception as e:
        print("Error in 16:", e)

    # 17. Control de Resultados - Historial AOI
    print("17. Capturing Historial AOI...")
    page.locator('#Control\\ de\\ resultados').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarHistorialAOI && window.mostrarHistorialAOI()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '14_resultados_aoi.png'))
    except Exception as e:
        print("Error in 17:", e)

    # 18. Control de Resultados - Historial ICT / FCT
    print("18. Capturing Historial ICT...")
    try:
        page.evaluate("window.mostrarHistorialICT && window.mostrarHistorialICT()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '15_resultados_ict.png'))
    except Exception as e:
        print("Error in 18:", e)

    # 19. Control de Resultados - Inventario Reparación SMD
    print("19. Capturing Inventario Reparación SMD...")
    try:
        page.evaluate("window.mostrarInventarioReparacionSMD && window.mostrarInventarioReparacionSMD()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '16_resultados_reparacion.png'))
    except Exception as e:
        print("Error in 19:", e)

    # 20. Control de Proceso - Almacén de Embarques & FIFO
    print("20. Capturing Almacén de Embarques...")
    page.locator('#Control\\ de\\ proceso').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarAlmacenEmbarquesInventarioGeneral && window.mostrarAlmacenEmbarquesInventarioGeneral()")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '17_proceso_embarques.png'))
    except Exception as e:
        print("Error in 20:", e)

    # 21. Control de Reporte - Trazabilidad PCB
    print("21. Capturing Trazabilidad PCB...")
    page.locator('#Control\\ de\\ reporte').click()
    time.sleep(1)
    try:
        page.evaluate("window.mostrarTrazabilidadPcb ? window.mostrarTrazabilidadPcb() : (window.mostrarTrazabilidad ? window.mostrarTrazabilidad() : null)")
        wait_render(page, 2.5)
        page.screenshot(path=os.path.join(output_dir, '18_reporte_trazabilidad_pcb.png'))
    except Exception as e:
        print("Error in 21:", e)

    browser.close()
    print("All captures completed successfully!")
