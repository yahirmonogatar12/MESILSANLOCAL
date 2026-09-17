"""Regresiones de los dropdowns laterales cargados por AJAX."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNIFIED_DROPDOWNS = PROJECT_ROOT / "app/static/js/unified-dropdowns.js"
PERMISSION_DROPDOWNS = PROJECT_ROOT / "app/static/js/permisos-dropdowns.js"
MAIN_TEMPLATE = PROJECT_ROOT / "app/templates/MainTemplate.html"
LISTAS_DIR = PROJECT_ROOT / "app/templates/LISTAS"


def test_sidebar_persiste_varias_secciones_abiertas_por_panel():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "mes_sidebar_dropdowns_v3" in source
    assert "mes_sidebar_dropdowns_v1" not in source
    assert "mes_sidebar_dropdowns_v2" not in source
    assert "const openIds = Array.isArray(states[scope])" in source
    assert "if (!openIds.includes(id)) openIds.push(id);" in source
    assert "states[scope] = openIds;" in source
    assert "states[scope].includes(id)" in source
    assert "closeOtherDropdowns(targetElement);" not in source
    assert "closeOtherDropdowns(elementoActual);" not in source


def test_guardia_delegada_conserva_el_estado_durante_recargas_ajax():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "function installDropdownStateGuard()" in source
    assert "event.preventDefault();" in source
    assert "event.stopImmediatePropagation();" not in source
    assert "event.stopPropagation();" in source
    assert "const inlineDisplay = targetElement.style.display;" in source
    assert "inlineDisplay === 'none'" in source
    assert "inlineDisplay === 'block'" in source
    assert "targetElement.classList.toggle('show', willOpen);" in source
    assert "targetElement.style.display = willOpen ? 'block' : 'none';" in source
    assert "button.setAttribute('aria-expanded', willOpen.toString());" in source
    assert "saveDropdownState(button, targetElement.id, willOpen);" in source
    assert "installDropdownStateGuard();" in source
    assert "document.getElementById('material-container')" in source
    assert "eventRoot.addEventListener('click', delegatedToggleHandler);" in source


def test_click_en_navbar_no_cierra_ni_sobrescribe_dropdowns_abiertos():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "PREVENT_AUTO_CLOSE: true" in source
    assert "if (!CONFIG.PREVENT_AUTO_CLOSE) {\n                closeAllDropdowns();" in source
    assert "if (CONFIG.PREVENT_AUTO_CLOSE) {\n                return;" not in source


def test_reinicializacion_ajax_no_clona_ni_cierra_botones_ya_configurados():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "if (isInitialized && initializedDeviceType === deviceType)" in source
    assert "setupUnifiedDropdowns();\n            return;" in source
    assert ':not([data-unified-dropdown-ready="true"])' in source
    assert "button.setAttribute('data-unified-dropdown-ready', 'true');" in source
    assert "cloneNode(true)" not in source
    assert "if (!globalEventsInstalled)" in source
    assert "if (!mutationObserverInstalled)" in source


def test_aria_expanded_conserva_el_estado_solicitado_durante_la_transicion():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "setTimeout(() => {\n            // Si el usuario alcanzo a pulsar" not in source
    assert "targetElement.classList.remove('show', 'collapsing');" in source
    assert "targetElement.style.display = 'none';" in source
    assert "button.setAttribute('aria-expanded', willOpen.toString());" in source
    assert "const newState = t.classList.contains('show');" not in source


def test_el_cierre_de_hermanos_se_limita_al_sidebar_actual():
    source = UNIFIED_DROPDOWNS.read_text(encoding="utf-8")

    assert "exceptElement.closest('.sidebar-menu')" in source
    assert "scope.querySelectorAll('.sidebar-dropdown-list.collapse.show')" in source


def test_main_template_publica_la_version_corregida_del_menu_multiple():
    template = MAIN_TEMPLATE.read_text(encoding="utf-8")

    assert "permisos-dropdowns.js?v=20260917permfix" in template
    assert "unified-dropdowns.js?v=20260917m" in template
    assert "SIDEBAR_CONTENT_VERSION = '20260917permfix'" in template


def test_las_listas_no_declaran_parent_de_bootstrap_y_permiten_varias_abiertas():
    templates = sorted(LISTAS_DIR.glob("LISTA_*.html"))
    templates_con_dropdowns = 0

    for path in templates:
        source = path.read_text(encoding="utf-8")
        dropdowns = re.findall(
            r'<ul class="collapse sidebar-dropdown-list"[^>]*>',
            source,
        )
        if not dropdowns:
            continue

        templates_con_dropdowns += 1
        parent_match = re.search(r'<ul class="sidebar-menu" id="([^"]+)">', source)
        assert parent_match, f"{path.name} no declara un id para el acordeon"

        assert all("data-bs-parent" not in dropdown for dropdown in dropdowns), (
            f"{path.name} todavia fuerza el comportamiento de acordeon"
        )

    assert templates_con_dropdowns == 8


def test_permisos_no_dejan_listeners_bloqueadores_permanentes():
    source = PERMISSION_DROPDOWNS.read_text(encoding="utf-8")

    assert "elemento.addEventListener('click'" not in source
    assert "elemento.addEventListener('touchstart'" not in source
    assert "permisosCargados = false" in source
    assert "if (!permisosCargados)" in source
    assert "localStorage.getItem('permisos_dropdowns')" not in source


def test_sistema_de_permisos_se_carga_una_sola_vez_desde_main_template():
    template = MAIN_TEMPLATE.read_text(encoding="utf-8")
    assert template.count("permisos-dropdowns.js") == 1

    for path in sorted(LISTAS_DIR.glob("LISTA_*.html")):
        source = path.read_text(encoding="utf-8")
        assert "permisos-dropdowns.js" not in source, (
            f"{path.name} vuelve a inicializar el sistema de permisos"
        )
