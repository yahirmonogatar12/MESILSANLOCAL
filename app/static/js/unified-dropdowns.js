// ===============================================
// SISTEMA UNIFICADO DE DROPDOWNS UNIVERSAL
// Funciona en PC y Móvil - Reemplaza todos los sistemas anteriores
// ===============================================

(function() {
    'use strict';
    
    // Variables globales
    let isInitialized = false;
    let dropdownInstances = new Map();
    let eventListeners = [];
    let dropdownStateGuardInstalled = false;
    let globalEventsInstalled = false;
    let mutationObserverInstalled = false;
    let initializedDeviceType = null;
    let dropdownCounter = 0;
    
    // Configuración unificada
    const CONFIG = {
        DEBUG: false,
        MOBILE_BREAKPOINT: 768,
        CLICK_DELAY: 150,
        ANIMATION_DURATION: 300,
        MAX_RETRIES: 3,
        // Los grupos del sidebar conservan su estado al cambiar de modulo.
        // Solo se cierran por una accion explicita del usuario.
        PREVENT_AUTO_CLOSE: true
    };
    
    function log(...args) {
    }

    // ===============================================
    // RESOLUCION LOCAL DE TARGETS
    // ===============================================
    // Los LISTA_* de cada modulo conviven ocultos en el DOM y repiten
    // IDs (p.ej. #sidebarMSL existe en 4 modulos). Un querySelector
    // global agarra el del modulo oculto y el toggle opera sobre la
    // lista equivocada. Resolver primero dentro de la seccion del boton.
    function findLocalTarget(button, selector) {
        const section = button.closest('.sidebar-section') || button.parentElement;
        const local = section ? section.querySelector(selector) : null;
        return local || document.querySelector(selector);
    }

    // ===============================================
    // PERSISTENCIA EN LOCALSTORAGE
    // ===============================================
    // Cada sidebar conserva solamente las secciones que el usuario abrio.
    // La clave v3 separa este estado por panel y descarta los formatos
    // anteriores que mezclaban IDs repetidos o permitian solo una seccion.
    const STORAGE_KEY_DROPDOWNS = 'mes_sidebar_dropdowns_v3';

    function getSidebarScope(button) {
        const sidebar = button ? button.closest('.app-sidebar') : null;
        let container = sidebar ? sidebar.parentElement : null;
        while (container && container !== document.body) {
            if (container.id) return container.id;
            container = container.parentElement;
        }
        return 'sidebar-global';
    }

    function readDropdownStates() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY_DROPDOWNS);
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function saveDropdownState(button, id, isOpen) {
        if (!button || !id) return;
        try {
            const states = readDropdownStates();
            const scope = getSidebarScope(button);
            const openIds = Array.isArray(states[scope]) ? states[scope] : [];
            if (isOpen) {
                if (!openIds.includes(id)) openIds.push(id);
            } else {
                const index = openIds.indexOf(id);
                if (index !== -1) openIds.splice(index, 1);
            }

            if (openIds.length > 0) {
                states[scope] = openIds;
            } else {
                delete states[scope];
            }
            localStorage.setItem(STORAGE_KEY_DROPDOWNS, JSON.stringify(states));
        } catch (e) {
            // localStorage lleno o bloqueado: ignorar
        }
    }

    function getSavedDropdownState(button, id) {
        if (!button || !id) return null;
        const states = readDropdownStates();
        const scope = getSidebarScope(button);
        if (!Object.prototype.hasOwnProperty.call(states, scope)) return null;
        return Array.isArray(states[scope]) ? states[scope].includes(id) : null;
    }

    // ===============================================
    // DETECTOR DE DISPOSITIVO
    // ===============================================
    function isMobile() {
        return window.innerWidth <= CONFIG.MOBILE_BREAKPOINT;
    }
    
    function getDeviceType() {
        return isMobile() ? 'mobile' : 'desktop';
    }
    
    // ===============================================
    // INICIALIZACIÓN PRINCIPAL
    // ===============================================
    function initUnifiedDropdowns() {
        const deviceType = getDeviceType();

        // Los modulos llaman init() despues de cada carga AJAX. Si el
        // dispositivo no cambio, configurar solo botones nuevos; volver a
        // clonar todo el sidebar interrumpe Collapse y pliega grupos abiertos.
        if (isInitialized && initializedDeviceType === deviceType) {
            setupUnifiedDropdowns();
            return;
        }

        if (isInitialized) {
            cleanup();
        }
        
        log(`🚀 Inicializando dropdowns unificados para ${getDeviceType()}...`);
        
        // Limpiar sistemas anteriores
        cleanupLegacySystems();
        
        // Esperar a que Bootstrap esté listo
        waitForBootstrap(() => {
            setupUnifiedDropdowns();
            isInitialized = true;
            initializedDeviceType = deviceType;
            log(` Sistema unificado inicializado para ${getDeviceType()}`);
        });
    }
    
    // ===============================================
    // LIMPIEZA DE SISTEMAS ANTERIORES
    // ===============================================
    function cleanupLegacySystems() {
        log('🧹 Limpiando sistemas de dropdowns anteriores...');
        
        // Limpiar mobile-listas-menu
        if (window.mobileListas) {
            try {
                window.mobileListas.cleanup();
                window.mobileListas = null;
            } catch (e) { /* ignorar errores */ }
        }
        
        // Limpiar mobile-lists-hamburger
        if (window.mobileListsHamburger) {
            try {
                window.mobileListsHamburger.cleanup();
                window.mobileListsHamburger = null;
            } catch (e) { /* ignorar errores */ }
        }
        
        // Limpiar instancias de Bootstrap anteriores
        document.querySelectorAll('.sidebar-dropdown-list.collapse').forEach(el => {
            const instance = bootstrap.Collapse.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
        
        log(' Sistemas anteriores limpiados');
    }
    
    // ===============================================
    // CONFIGURACIÓN UNIFICADA
    // ===============================================
    function setupUnifiedDropdowns() {
        // Configurar solamente los botones laterales nuevos. Los ya listos
        // conservan sus nodos, listeners, animacion y estado abierto.
        const dropdownButtons = document.querySelectorAll(
            '.sidebar-dropdown-btn[data-bs-toggle="collapse"]:not([data-unified-dropdown-ready="true"])'
        );
        
        log(` Configurando ${dropdownButtons.length} dropdowns para ${getDeviceType()}`);
        
        dropdownButtons.forEach((button) => {
            setupDropdownButton(button);
        });
        
        // Configurar eventos globales una sola vez.
        if (!globalEventsInstalled) {
            setupGlobalEvents();
            globalEventsInstalled = true;
        }
        
        // Configurar un solo observador de mutaciones. Cada carga AJAX llama
        // setupUnifiedDropdowns(), pero no debe acumular observadores.
        if (!mutationObserverInstalled) {
            setupMutationObserver();
            mutationObserverInstalled = true;
        }
    }
    
    function setupDropdownButton(button) {
        const targetSelector = button.getAttribute('data-bs-target');
        if (!targetSelector) return;
        
        const targetElement = findLocalTarget(button, targetSelector);
        if (!targetElement) return;

        const dropdownId = `unified-dropdown-${dropdownCounter++}`;

        // No clonar el boton: otros sistemas (permisos, accesibilidad y tabs)
        // pueden conservar referencias o listeners en el nodo original.
        button.setAttribute('data-unified-dropdown-ready', 'true');
        
        // Configurar según el dispositivo
        if (isMobile()) {
            setupMobileDropdown(button, targetElement, dropdownId);
        } else {
            setupDesktopDropdown(button, targetElement, dropdownId, targetSelector);
        }
    }
    
    // ===============================================
    // CONFIGURACIÓN MÓVIL
    // ===============================================
    function setupMobileDropdown(button, targetElement, dropdownId) {
        log(`📱 Configurando dropdown móvil: ${dropdownId}`);
        
        const mobileTargetId = targetElement && targetElement.id ? targetElement.id : null;
        const savedState = getSavedDropdownState(button, mobileTargetId);
        const shouldOpen = savedState === null ? false : savedState;

        targetElement.classList.remove('collapsing');
        targetElement.classList.toggle('show', shouldOpen);
        targetElement.classList.toggle('collapsed-by-user', !shouldOpen);
        targetElement.style.display = shouldOpen ? 'block' : 'none';
        button.setAttribute('aria-expanded', shouldOpen.toString());
    }
    
    // ===============================================
    // CONFIGURACIÓN DESKTOP
    // ===============================================
    function setupDesktopDropdown(button, targetElement, dropdownId, targetSelector) {
        log(`🖥️ Configurando dropdown desktop: ${dropdownId}`);
        
        // Crear instancia de Bootstrap Collapse
        if (!targetElement) {
            // console.error(`Target element not found for dropdown: ${dropdownId}, selector: ${targetSelector}`);
            return;
        }
        const collapseInstance = new bootstrap.Collapse(targetElement, {
            toggle: false
        });
        
        dropdownInstances.set(dropdownId, collapseInstance);
        
        // RESTAURAR ESTADO GUARDADO O CERRAR POR DEFECTO
        // Por defecto todos los dropdowns arrancan cerrados; solo los
        // que el usuario abrio explicitamente se restauran abiertos.
        const targetId = targetSelector ? targetSelector.replace(/^#/, '') : null;
        const savedState = getSavedDropdownState(button, targetId);
        const shouldOpen = savedState === null ? false : savedState;
        if (shouldOpen) {
            targetElement.classList.remove('collapsed-by-user');
            targetElement.classList.remove('collapsing');
            targetElement.classList.add('show');
            targetElement.style.display = 'block';
            button.setAttribute('aria-expanded', 'true');
        } else {
            targetElement.classList.remove('show', 'collapsing');
            targetElement.classList.add('collapsed-by-user');
            targetElement.style.display = 'none';
            button.setAttribute('aria-expanded', 'false');
        }
        
    }
    
    // ===============================================
    // EVENTOS GLOBALES
    // ===============================================
    function setupGlobalEvents() {
        // Mantener los dropdowns al navegar entre botones superiores. Los
        // clicks internos siguen actualizando la seleccion activa.
        const documentClickHandler = (e) => {
            // NO cerrar si el click es en:
            // 1. Un botón de toggle
            if (e.target.closest('[data-bs-toggle="collapse"]')) {
                return;
            }
            
            // 2. Dentro del contenido del dropdown (sidebar-dropdown-list o collapse.show)
            if (e.target.closest('.sidebar-dropdown-list') || 
                e.target.closest('.collapse.show')) {
                
                // MANEJAR SELECCIÓN ACTIVA para elementos interactivos
                handleActiveSelection(e);
                return;
            }
            
            // 3. En elementos interactivos dentro del dropdown
            if (e.target.closest('a, button, input, select, textarea, .dropdown-item, .sidebar-link')) {
                const parentDropdown = e.target.closest('.collapse.show');
                if (parentDropdown) {
                    // MANEJAR SELECCIÓN ACTIVA antes de retornar
                    handleActiveSelection(e);
                    return; // No cerrar si es un elemento interactivo dentro de un dropdown
                }
            }
            
            // 4. En elementos con clase específica que no deben cerrar dropdowns
            if (e.target.closest('.no-dropdown-close, .sidebar-content, .material-content-area')) {
                return;
            }
            
            // El modo normal del MES conserva los grupos abiertos al cambiar
            // de modulo. Esta rama queda disponible solo para consumidores que
            // habiliten expresamente el cierre automatico mediante la API.
            if (!CONFIG.PREVENT_AUTO_CLOSE) {
                closeAllDropdowns();
            }
        };
        
        // Cerrar con Escape
        const keydownHandler = (e) => {
            if (e.key === 'Escape') {
                closeAllDropdowns();
            }
        };
        
        // Manejar cambios de orientación en móvil
        const orientationHandler = () => {
            if (isMobile()) {
                setTimeout(() => {
                    closeAllDropdowns();
                }, 100);
            }
        };
        
        document.addEventListener('click', documentClickHandler);
        document.addEventListener('keydown', keydownHandler);
        window.addEventListener('orientationchange', orientationHandler);
        
        // Guardar para cleanup
        eventListeners.push(() => {
            document.removeEventListener('click', documentClickHandler);
            document.removeEventListener('keydown', keydownHandler);
            window.removeEventListener('orientationchange', orientationHandler);
        });
    }
    
    // ===============================================
    // MANEJO DE SELECCIÓN ACTIVA
    // ===============================================
    function handleActiveSelection(event) {
        const clickedElement = event.target;
        
        // Buscar el elemento seleccionable más específico
        const selectableSelectors = [
            'a[href]',
            'button[onclick]',
            '.sidebar-link',
            '.dropdown-item',
            '[data-action]',
            '[data-target]'
        ];
        
        let selectableElement = null;
        
        // Buscar el elemento seleccionable
        for (const selector of selectableSelectors) {
            if (clickedElement.matches(selector)) {
                selectableElement = clickedElement;
                break;
            } else if (clickedElement.closest(selector)) {
                selectableElement = clickedElement.closest(selector);
                break;
            }
        }
        
        if (!selectableElement) return;
        
        log(` Elemento seleccionable clickeado: ${selectableElement.textContent.trim()}`);
        
        // LIMPIAR TODAS LAS SELECCIONES ACTIVAS EN TODO EL DOCUMENTO
        const allSelectableElements = document.querySelectorAll(
            'a, .sidebar-link, .dropdown-item, button[onclick], [data-action], [data-target]'
        );
        
        allSelectableElements.forEach(el => {
            if (el !== selectableElement) {
                el.classList.remove('active', 'selected', 'current');
                el.removeAttribute('data-selected');
                // Limpiar estilos inline previos
                el.style.backgroundColor = '';
                el.style.color = '';
                el.style.borderRadius = '';
                el.style.fontWeight = '';
            }
        });
        
        // Aplicar estado activo al elemento seleccionado
        selectableElement.classList.add('active');
        selectableElement.setAttribute('data-selected', 'true');
        
        // Aplicar estilos de selección
        selectableElement.style.backgroundColor = '#4a90e2';
        selectableElement.style.color = '#ffffff';
        selectableElement.style.borderRadius = '5px';
        selectableElement.style.fontWeight = '500';
        
        log(` Estado activo aplicado a: ${selectableElement.textContent.trim()}`);
        
        // Guardar referencia del elemento activo
        window.currentActiveElement = selectableElement;
        if (!window.unifiedDropdowns) window.unifiedDropdowns = {};
        window.unifiedDropdowns.activeElement = selectableElement;
    }
    
    // ===============================================
    // OBSERVADOR DE MUTACIONES (DESHABILITADO)
    // ===============================================
    function setupMutationObserver() {
        // Deshabilitamos el MutationObserver automático para evitar bucles infinitos
        // La reinicialización se manejará explícitamente desde AjaxContentManager
        log(' MutationObserver deshabilitado para evitar reinicializaciones duplicadas');
        
        // Si necesitas el observer para casos específicos, descomenta el código siguiente:
        /*
        const observer = new MutationObserver((mutations) => {
            let shouldReinitialize = false;
            
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.classList && (
                            node.classList.contains('collapse') ||
                            (node.querySelector && node.querySelector('[data-bs-toggle="collapse"]'))
                        )) {
                            shouldReinitialize = true;
                        }
                    }
                });
            });
            
            if (shouldReinitialize) {
                log(' Nuevos elementos detectados, reinicializando...');
                setTimeout(() => {
                    setupUnifiedDropdowns();
                }, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        eventListeners.push(() => {
            observer.disconnect();
        });
        */
    }
    
    // ===============================================
    // FUNCIONES UTILITARIAS
    // ===============================================
    function closeAllDropdowns() {
        log('🔒 Cerrando todos los dropdowns...');

        document.querySelectorAll('.sidebar-dropdown-list.collapse.show').forEach(element => {
            const section = element.closest('.sidebar-section');
            const button = section ? section.querySelector('[data-bs-toggle="collapse"]') : null;

            if (!isMobile() && typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
                const instance = bootstrap.Collapse.getInstance(element)
                    || new bootstrap.Collapse(element, { toggle: false });
                instance.hide();
            } else {
                element.classList.remove('show', 'collapsing');
                element.style.display = 'none';
            }

            element.classList.add('collapsed-by-user');
            if (button) {
                button.setAttribute('aria-expanded', 'false');
                saveDropdownState(button, element.id, false);
            }
        });
    }
    
    function closeOtherDropdowns(exceptElement) {
        log('🔒 Cerrando otros dropdowns (excepto el actual)...');

        // Limitar el cierre al sidebar actual. Los LISTA_* ocultos conviven
        // en el DOM y varios reutilizan IDs, por lo que un query global
        // puede plegar o asociar el boton de otra lista.
        const sidebarMenu = exceptElement ? exceptElement.closest('.sidebar-menu') : null;
        const scope = sidebarMenu || document;

        scope.querySelectorAll('.sidebar-dropdown-list.collapse.show').forEach(element => {
            if (element === exceptElement) return;

            const section = element.closest('.sidebar-section');
            const button = section ? section.querySelector('[data-bs-toggle="collapse"]') : null;

            if (!isMobile() && typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
                const instance = bootstrap.Collapse.getInstance(element)
                    || new bootstrap.Collapse(element, { toggle: false });
                instance.hide();
            } else {
                element.classList.remove('show', 'collapsing');
                element.style.display = 'none';
            }

            element.classList.add('collapsed-by-user');
            if (button) {
                button.setAttribute('aria-expanded', 'false');
                saveDropdownState(button, element.id, false);
            }
        });
    }

    // Guardia delegada permanente. Los sidebars se reemplazan por AJAX, por
    // eso el listener vive en el contenedor estable y no en cada boton. Al
    // ejecutarse antes de llegar a document evita el segundo toggle de
    // Bootstrap sin bloquear los listeners del sistema de permisos.
    function installDropdownStateGuard() {
        if (dropdownStateGuardInstalled) return;

        const delegatedToggleHandler = function(event) {
            const button = event.target.closest(
                '.sidebar-dropdown-btn[data-bs-toggle="collapse"]'
            );
            if (!button) return;

            const now = Date.now();
            const lastTouch = Number(button.dataset.unifiedDropdownTouch || 0);
            if (event.type === 'click' && now - lastTouch < 700) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (event.type === 'touchstart') {
                button.dataset.unifiedDropdownTouch = String(now);
            }

            const lastToggle = Number(button.dataset.unifiedDropdownToggle || 0);
            if (now - lastToggle < CONFIG.CLICK_DELAY) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            button.dataset.unifiedDropdownToggle = String(now);

            const targetSelector = button.getAttribute('data-bs-target');
            if (!targetSelector) return;

            const targetElement = findLocalTarget(button, targetSelector);
            if (!targetElement || !targetElement.id) return;

            event.preventDefault();
            // Bootstrap escucha el data-api en document. Este listener vive
            // en body/material-container, asi que stopPropagation corta solo
            // ese segundo toggle y permite otros listeners del mismo nodo.
            event.stopPropagation();
            // El sistema de permisos/Bootstrap puede dejar class="show" o
            // aria-expanded desfasados. El display inline lo controla este
            // manejador y representa el estado visual real.
            const inlineDisplay = targetElement.style.display;
            const currentOpen = inlineDisplay === 'none'
                ? false
                : inlineDisplay === 'block'
                    ? true
                    : targetElement.classList.contains('show');
            const willOpen = !currentOpen;

            // Aplicar el estado directamente. Bootstrap mantiene un listener
            // delegado propio en document y, con IDs repetidos entre modulos,
            // puede invertir aria-expanded aunque el panel quede visible.
            targetElement.classList.remove('collapsing');
            targetElement.classList.toggle('show', willOpen);
            targetElement.style.display = willOpen ? 'block' : 'none';
            targetElement.classList.toggle('collapsed-by-user', !willOpen);
            button.setAttribute('aria-expanded', willOpen.toString());
            saveDropdownState(button, targetElement.id, willOpen);
        };

        const eventRoot = document.getElementById('material-container')
            || document.body
            || document.documentElement;
        eventRoot.addEventListener('click', delegatedToggleHandler);
        eventRoot.addEventListener('touchstart', delegatedToggleHandler, {
            passive: false
        });

        dropdownStateGuardInstalled = true;
    }
    
    function waitForBootstrap(callback, retries = 0) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
            callback();
        } else if (retries < CONFIG.MAX_RETRIES) {
            setTimeout(() => {
                waitForBootstrap(callback, retries + 1);
            }, 500);
        } else {
            log(' Bootstrap no disponible, usando modo básico');
            callback(); // Continuar sin Bootstrap para móvil
        }
    }
    
    // ===============================================
    // FUNCIÓN PARA LIMPIAR TODAS LAS SELECCIONES
    // ===============================================
    function clearAllSelections() {
        log('🧹 Limpiando todas las selecciones activas...');
        
        const allSelectableElements = document.querySelectorAll(
            'a, .sidebar-link, .dropdown-item, button[onclick], [data-action], [data-target]'
        );
        
        allSelectableElements.forEach(el => {
            el.classList.remove('active', 'selected', 'current');
            el.removeAttribute('data-selected');
            // Limpiar estilos inline
            el.style.backgroundColor = '';
            el.style.color = '';
            el.style.borderRadius = '';
            el.style.fontWeight = '';
        });
        
        // Limpiar referencias globales
        if (window.currentActiveElement) {
            window.currentActiveElement = null;
        }
        if (window.unifiedDropdowns && window.unifiedDropdowns.activeElement) {
            window.unifiedDropdowns.activeElement = null;
        }
        
        log(' Todas las selecciones limpiadas');
    }
    
    function cleanup() {
        log('🧹 Limpiando sistema unificado...');
        
        // Limpiar instancias
        dropdownInstances.forEach(instance => {
            try {
                instance.dispose();
            } catch (e) { /* ignorar */ }
        });
        dropdownInstances.clear();
        
        // Limpiar event listeners
        eventListeners.forEach(cleanup => {
            try {
                cleanup();
            } catch (e) { /* ignorar */ }
        });
        eventListeners = [];

        document.querySelectorAll(
            '.sidebar-dropdown-btn[data-unified-dropdown-ready="true"]'
        ).forEach(button => {
            button.removeAttribute('data-unified-dropdown-ready');
        });
        
        isInitialized = false;
        globalEventsInstalled = false;
        mutationObserverInstalled = false;
        initializedDeviceType = null;
    }
    
    // ===============================================
    // MANEJO DE RESIZE RESPONSIVE
    // ===============================================
    function handleResize() {
        const currentType = getDeviceType();
        log(`📐 Resize detectado: ${currentType}`);
        
        // Reinicializar con la configuración apropiada
        setTimeout(() => {
            initUnifiedDropdowns();
        }, 100);
    }
    
    // ===============================================
    // API PÚBLICA
    // ===============================================
    // EXPORTAR FUNCIONES PÚBLICAS
    // ===============================================
    window.unifiedDropdowns = {
        init: initUnifiedDropdowns,
        cleanup: cleanup,
        closeAll: closeAllDropdowns,
        closeOthers: closeOtherDropdowns,
        clearAllSelections: clearAllSelections,
        enableDebug: () => { CONFIG.DEBUG = true; log('Debug habilitado'); },
        disableDebug: () => { CONFIG.DEBUG = false; },
        status: () => ({
            initialized: isInitialized,
            deviceType: getDeviceType(),
            instances: dropdownInstances.size,
            listeners: eventListeners.length,
            openDropdowns: document.querySelectorAll('.collapse.show').length
        }),
        // Control explicito del cierre automatico. Por defecto se conserva el
        // estado de cada sidebar al navegar entre modulos.
        preventAutoClose: (enabled = true) => {
            if (enabled) {
                log(' Auto-cierre deshabilitado');
                CONFIG.PREVENT_AUTO_CLOSE = true;
            } else {
                log(' Auto-cierre habilitado');
                CONFIG.PREVENT_AUTO_CLOSE = false;
            }
        },
        // Funciones para manejar selecciones activas
        setActiveElement: (element) => {
            if (element) {
                // Simular click para activar el elemento
                const event = new MouseEvent('click', { bubbles: true });
                Object.defineProperty(event, 'target', { value: element });
                handleActiveSelection(event);
            }
        },
        clearActiveElements: () => {
            // Limpiar todos los elementos activos
            document.querySelectorAll('.active[style*="background-color"]').forEach(el => {
                el.classList.remove('active', 'selected', 'current');
                el.style.backgroundColor = '';
                el.style.color = '';
                el.style.fontWeight = '';
                el.style.borderRadius = '';
            });
            window.currentActiveElement = null;
        },
        getActiveElement: () => {
            return window.currentActiveElement;
        }
    };

    // ===============================================
    // EXPONER FUNCIÓN PARA REINICIALIZACIÓN CONTROLADA
    // ===============================================
    window.setupUnifiedDropdowns = function() {
        log(' Reinicializando dropdowns desde llamada externa...');
        setupUnifiedDropdowns();
    };

    // ===============================================
    // INICIALIZACIÓN AUTOMÁTICA
    // ===============================================
    installDropdownStateGuard();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUnifiedDropdowns);
    } else {
        initUnifiedDropdowns();
    }
    
    // Manejar cambios de tamaño de ventana
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(handleResize, 250);
    });
    
    log(' Sistema unificado de dropdowns cargado');
    
})();
