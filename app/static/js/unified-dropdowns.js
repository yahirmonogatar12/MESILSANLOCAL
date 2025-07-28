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
    
    // Configuración unificada
    const CONFIG = {
        DEBUG: false,
        MOBILE_BREAKPOINT: 768,
        CLICK_DELAY: 150,
        ANIMATION_DURATION: 300,
        MAX_RETRIES: 3,
        PREVENT_AUTO_CLOSE: false
    };
    
    function log(...args) {
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
            log(`✅ Sistema unificado inicializado para ${getDeviceType()}`);
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
        document.querySelectorAll('.collapse').forEach(el => {
            const instance = bootstrap.Collapse.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
        
        log('✅ Sistemas anteriores limpiados');
    }
    
    // ===============================================
    // CONFIGURACIÓN UNIFICADA
    // ===============================================
    function setupUnifiedDropdowns() {
        // Configurar todos los dropdowns existentes
        const dropdownButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
        
        log(`🔍 Configurando ${dropdownButtons.length} dropdowns para ${getDeviceType()}`);
        
        dropdownButtons.forEach((button, index) => {
            setupDropdownButton(button, index);
        });
        
        // Configurar eventos globales
        setupGlobalEvents();
        
        // Configurar observador de mutaciones
        setupMutationObserver();
    }
    
    function setupDropdownButton(button, index) {
        const targetSelector = button.getAttribute('data-bs-target');
        if (!targetSelector) return;
        
        const targetElement = document.querySelector(targetSelector);
        if (!targetElement) return;
        
        const dropdownId = `unified-dropdown-${index}`;
        
        // Limpiar listeners anteriores clonando el botón
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
        
        // Variables de control
        let lastClickTime = 0;
        let isProcessing = false;
        
        // Configurar según el dispositivo
        if (isMobile()) {
            setupMobileDropdown(newButton, targetElement, dropdownId);
        } else {
            setupDesktopDropdown(newButton, targetElement, dropdownId, targetSelector);
        }
    }
    
    // ===============================================
    // CONFIGURACIÓN MÓVIL
    // ===============================================
    function setupMobileDropdown(button, targetElement, dropdownId) {
        log(`📱 Configurando dropdown móvil: ${dropdownId}`);
        
        let lastClickTime = 0;
        
        const clickHandler = function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const now = Date.now();
            if (now - lastClickTime < CONFIG.CLICK_DELAY) {
                return false;
            }
            lastClickTime = now;
            
            // Toggle simple para móvil
            const isOpen = targetElement.classList.contains('show');
            
            if (isOpen) {
                // Cerrar
                targetElement.classList.remove('show');
                targetElement.style.display = 'none';
                button.setAttribute('aria-expanded', 'false');
                log(`📱 Cerrado: ${dropdownId}`);
            } else {
                // Cerrar otros dropdowns primero (pero no todos los elementos interactivos)
                closeOtherDropdowns(targetElement);
                
                // Abrir este
                targetElement.classList.add('show');
                targetElement.style.display = 'block';
                button.setAttribute('aria-expanded', 'true');
                log(`📱 Abierto: ${dropdownId}`);
            }
            
            return false;
        };
        
        button.addEventListener('click', clickHandler);
        button.addEventListener('touchstart', clickHandler, { passive: false });
        
        // Guardar para cleanup
        eventListeners.push(() => {
            button.removeEventListener('click', clickHandler);
            button.removeEventListener('touchstart', clickHandler);
        });
    }
    
    // ===============================================
    // CONFIGURACIÓN DESKTOP
    // ===============================================
    function setupDesktopDropdown(button, targetElement, dropdownId, targetSelector) {
        log(`🖥️ Configurando dropdown desktop: ${dropdownId}`);
        
        // Crear instancia de Bootstrap Collapse
        if (!targetElement) {
            console.error(`Target element not found for dropdown: ${dropdownId}, selector: ${targetSelector}`);
            return;
        }
        const collapseInstance = new bootstrap.Collapse(targetElement, {
            toggle: false
        });
        
        dropdownInstances.set(dropdownId, collapseInstance);
        
        // EXPANDIR POR DEFECTO EN PC (solo si no tiene clase collapsed-by-user)
        if (targetElement && !targetElement.classList.contains('collapsed-by-user')) {
            setTimeout(() => {
                if (!targetElement) {
                    console.error(`Target element became null for dropdown: ${dropdownId}`);
                    return;
                }
                if (!collapseInstance._element) {
                    console.error(`Collapse instance element is null for ${dropdownId}`);
                    return;
                }
                if (!targetElement.classList.contains('show')) {
                    collapseInstance.show();
                    button.setAttribute('aria-expanded', 'true');
                    log(`🖥️ Expandido por defecto: ${dropdownId}`);
                }
            }, 100);
        }
        
        let lastClickTime = 0;
        let isProcessing = false;
        
        const clickHandler = function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const now = Date.now();
            if (isProcessing || now - lastClickTime < CONFIG.CLICK_DELAY) {
                return false;
            }
            
            isProcessing = true;
            lastClickTime = now;
            
            const isOpen = targetElement.classList.contains('show');
            
            log(`🖥️ Toggle: ${dropdownId} (${isOpen ? 'cerrar' : 'abrir'})`);
            
            if (isOpen) {
                // Marcar como cerrado por el usuario para evitar re-apertura automática
                targetElement.classList.add('collapsed-by-user');
                collapseInstance.hide();
                log(`🖥️ Cerrado por usuario: ${dropdownId}`);
            } else {
                // Remover marca de cerrado por usuario al abrir manualmente
                targetElement.classList.remove('collapsed-by-user');
                // En desktop, cerrar otros dropdowns antes de abrir este
                closeOtherDropdowns(targetElement);
                collapseInstance.show();
                log(`🖥️ Abierto por usuario: ${dropdownId}`);
            }
            
            // Actualizar aria-expanded después de la animación
            setTimeout(() => {
                const newState = targetElement.classList.contains('show');
                button.setAttribute('aria-expanded', newState.toString());
                isProcessing = false;
            }, CONFIG.ANIMATION_DURATION + 50);
            
            return false;
        };
        
        button.addEventListener('click', clickHandler);
        
        // Guardar para cleanup
        eventListeners.push(() => {
            button.removeEventListener('click', clickHandler);
        });
    }
    
    // ===============================================
    // EVENTOS GLOBALES
    // ===============================================
    function setupGlobalEvents() {
        // Cerrar dropdowns al hacer click fuera - MEJORADO
        const documentClickHandler = (e) => {
            // Si el modo testing está activo, no cerrar automáticamente
            if (CONFIG.PREVENT_AUTO_CLOSE) {
                return;
            }
            
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
            
            // Solo cerrar si el click es realmente fuera de todo el área de dropdowns
            closeAllDropdowns();
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
        
        log(`🎯 Elemento seleccionable clickeado: ${selectableElement.textContent.trim()}`);
        
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
        
        log(`✅ Estado activo aplicado a: ${selectableElement.textContent.trim()}`);
        
        // Guardar referencia del elemento activo
        window.currentActiveElement = selectableElement;
        if (!window.unifiedDropdowns) window.unifiedDropdowns = {};
        window.unifiedDropdowns.activeElement = selectableElement;
    }
    
    // ===============================================
    // OBSERVADOR DE MUTACIONES
    // ===============================================
    function setupMutationObserver() {
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
                log('🔄 Nuevos elementos detectados, reinicializando...');
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
    }
    
    // ===============================================
    // FUNCIONES UTILITARIAS
    // ===============================================
    function closeAllDropdowns() {
        log('🔒 Cerrando todos los dropdowns...');
        
        if (isMobile()) {
            // Móvil: cerrar usando clases
            document.querySelectorAll('.collapse.show').forEach(el => {
                el.classList.remove('show');
                el.style.display = 'none';
            });
            
            document.querySelectorAll('[aria-expanded="true"]').forEach(btn => {
                btn.setAttribute('aria-expanded', 'false');
            });
        } else {
            // Desktop: usar instancias de Bootstrap
            dropdownInstances.forEach((instance, id) => {
                const element = document.querySelector(`[data-bs-target="#${id.replace('unified-dropdown-', '')}"]`);
                if (element) {
                    const targetSelector = element.getAttribute('data-bs-target');
                    const targetElement = document.querySelector(targetSelector);
                    if (targetElement && targetElement.classList.contains('show')) {
                        instance.hide();
                    }
                }
            });
        }
    }
    
    function closeOtherDropdowns(exceptElement) {
        log('🔒 Cerrando otros dropdowns (excepto el actual)...');
        
        if (isMobile()) {
            // Móvil: cerrar todos excepto el especificado
            document.querySelectorAll('.collapse.show').forEach(el => {
                if (el !== exceptElement) {
                    el.classList.remove('show');
                    el.style.display = 'none';
                }
            });
            
            // Actualizar aria-expanded solo en botones que no sean del elemento actual
            document.querySelectorAll('[aria-expanded="true"]').forEach(btn => {
                const targetSelector = btn.getAttribute('data-bs-target');
                const targetElement = document.querySelector(targetSelector);
                if (targetElement && targetElement !== exceptElement) {
                    btn.setAttribute('aria-expanded', 'false');
                }
            });
        } else {
            // Desktop: usar instancias de Bootstrap
            dropdownInstances.forEach((instance, id) => {
                const element = document.querySelector(`[data-bs-target="#${id.replace('unified-dropdown-', '')}"]`);
                if (element) {
                    const targetSelector = element.getAttribute('data-bs-target');
                    const targetElement = document.querySelector(targetSelector);
                    if (targetElement && targetElement !== exceptElement && targetElement.classList.contains('show')) {
                        instance.hide();
                    }
                }
            });
        }
    }
    
    function waitForBootstrap(callback, retries = 0) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
            callback();
        } else if (retries < CONFIG.MAX_RETRIES) {
            setTimeout(() => {
                waitForBootstrap(callback, retries + 1);
            }, 500);
        } else {
            log('❌ Bootstrap no disponible, usando modo básico');
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
        
        log('✅ Todas las selecciones limpiadas');
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
        
        isInitialized = false;
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
        // Función para testing - NO cerrar dropdowns en clicks específicos
        preventAutoClose: (enabled = true) => {
            if (enabled) {
                log('⚠️ Modo testing: Auto-cierre deshabilitado');
                // Remover el event listener de document click temporalmente
                CONFIG.PREVENT_AUTO_CLOSE = true;
            } else {
                log('✅ Modo normal: Auto-cierre habilitado');
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
    // INICIALIZACIÓN AUTOMÁTICA
    // ===============================================
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
    
    log('📁 Sistema unificado de dropdowns cargado');
    
})();
