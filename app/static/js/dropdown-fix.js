// ===============================================
// SOLUCIÓN UNIVERSAL PARA DROPDOWNS BOOTSTRAP
// ===============================================

(function() {
    'use strict';
    
    // Variables globales para control de estado
    let isInitialized = false;
    let dropdownInstances = new Map();
    let eventListenerCleanup = [];
    
    // Configuración universal
    const CONFIG = {
        DEBUG: false,
        CLICK_DELAY: 200,
        ANIMATION_DURATION: 300,
        MAX_RETRIES: 3
    };
    
    function log(...args) {
    }
    
    // ===============================================
    // FUNCIÓN PRINCIPAL DE INICIALIZACIÓN
    // ===============================================
    function initUniversalDropdownFix() {
        if (isInitialized) {
            log('Ya inicializado, ejecutando cleanup...');
            cleanup();
        }
        
        log('🚀 Inicializando solución universal de dropdowns...');
        
        // Limpiar cualquier instancia anterior
        cleanup();
        
        // Esperar a que Bootstrap esté completamente cargado
        waitForBootstrap(() => {
            setupDropdownFix();
            isInitialized = true;
            log(' Solución universal inicializada correctamente');
        });
    }
    
    // ===============================================
    // CONFIGURACIÓN DE LA SOLUCIÓN
    // ===============================================
    function setupDropdownFix() {
        // Interceptar TODOS los event listeners de Bootstrap Collapse
        interceptBootstrapCollapseEvents();
        
        // Configurar observador de mutaciones para nuevos elementos
        setupMutationObserver();
        
        // Configurar manejadores de eventos globales
        setupGlobalEventHandlers();
    }
    
    // ===============================================
    // INTERCEPTAR EVENTOS DE BOOTSTRAP
    // ===============================================
    function interceptBootstrapCollapseEvents() {
        log(' Interceptando eventos de Bootstrap Collapse...');
        
        // Buscar todos los elementos de collapse existentes
        document.querySelectorAll('.collapse').forEach(element => {
            setupCollapseElement(element);
        });
        
        // Buscar todos los botones de toggle existentes
        document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(button => {
            setupToggleButton(button);
        });
    }
    
    function setupCollapseElement(element) {
        const elementId = element.id || `collapse-${Math.random().toString(36).substr(2, 9)}`;
        if (!element.id) element.id = elementId;
        
        // Destruir instancia previa si existe
        const existingInstance = bootstrap.Collapse.getInstance(element);
        if (existingInstance) {
            existingInstance.dispose();
            log(`o️ Instancia previa destruida: ${elementId}`);
        }
        
        // Crear nueva instancia con configuración personalizada
        const collapseInstance = new bootstrap.Collapse(element, {
            toggle: false // No hacer toggle automático
        });
        
        dropdownInstances.set(elementId, collapseInstance);
        
        // Interceptar eventos nativos de Bootstrap
        const showHandler = (e) => {
            log(`📂 Showing: ${elementId}`);
        };
        
        const hideHandler = (e) => {
            log(`📁 Hiding: ${elementId}`);
        };
        
        const hiddenHandler = (e) => {
            log(` Hidden: ${elementId}`);
            // Asegurar que el elemento esté completamente cerrado
            setTimeout(() => {
                if (!element.classList.contains('show')) {
                    element.style.display = 'none';
                }
            }, 50);
        };
        
        element.addEventListener('show.bs.collapse', showHandler);
        element.addEventListener('hide.bs.collapse', hideHandler);
        element.addEventListener('hidden.bs.collapse', hiddenHandler);
        
        // Guardar handlers para cleanup
        eventListenerCleanup.push(() => {
            element.removeEventListener('show.bs.collapse', showHandler);
            element.removeEventListener('hide.bs.collapse', hideHandler);
            element.removeEventListener('hidden.bs.collapse', hiddenHandler);
        });
    }
    
    function setupToggleButton(button) {
        const targetSelector = button.getAttribute('data-bs-target');
        if (!targetSelector) return;
        
        const targetElement = document.querySelector(targetSelector);
        if (!targetElement) return;
        
        // Remover event listeners previos
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
        
        let lastClickTime = 0;
        let isProcessing = false;
        
        const clickHandler = function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const now = Date.now();
            if (isProcessing || (now - lastClickTime) < CONFIG.CLICK_DELAY) {
                log('🚫 Click ignorado - demasiado rápido');
                return false;
            }
            
            isProcessing = true;
            lastClickTime = now;
            
            // Obtener instancia de collapse
            const collapseInstance = bootstrap.Collapse.getInstance(targetElement);
            if (!collapseInstance) {
                log('❌ No se encontró instancia de collapse');
                isProcessing = false;
                return false;
            }
            
            // Determinar acción
            const isCurrentlyShown = targetElement.classList.contains('show');
            
            log(`🎬 Toggle: ${targetSelector} (${isCurrentlyShown ? 'cerrar' : 'abrir'})`);
            
            if (isCurrentlyShown) {
                collapseInstance.hide();
            } else {
                collapseInstance.show();
            }
            
            // Actualizar aria-expanded
            setTimeout(() => {
                const newState = targetElement.classList.contains('show');
                newButton.setAttribute('aria-expanded', newState.toString());
                isProcessing = false;
            }, CONFIG.ANIMATION_DURATION + 50);
            
            return false;
        };
        
        newButton.addEventListener('click', clickHandler);
        
        // Guardar handler para cleanup
        eventListenerCleanup.push(() => {
            newButton.removeEventListener('click', clickHandler);
        });
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
                        // Verificar si es un nuevo elemento collapse o toggle
                        if (node.classList && (
                            node.classList.contains('collapse') ||
                            node.querySelector && (
                                node.querySelector('.collapse') ||
                                node.querySelector('[data-bs-toggle="collapse"]')
                            )
                        )) {
                            shouldReinitialize = true;
                        }
                    }
                });
            });
            
            if (shouldReinitialize) {
                log(' Nuevos elementos detectados, reinicializando...');
                setTimeout(() => {
                    setupDropdownFix();
                }, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Guardar observer para cleanup
        eventListenerCleanup.push(() => {
            observer.disconnect();
        });
    }
    
    // ===============================================
    // MANEJADORES GLOBALES
    // ===============================================
    function setupGlobalEventHandlers() {
        // Cerrar dropdowns al hacer click fuera
        const documentClickHandler = (e) => {
            if (!e.target.closest('[data-bs-toggle="collapse"]') &&
                !e.target.closest('.collapse.show')) {
                closeAllDropdowns();
            }
        };
        
        document.addEventListener('click', documentClickHandler);
        
        // Cerrar con tecla Escape
        const keydownHandler = (e) => {
            if (e.key === 'Escape') {
                closeAllDropdowns();
            }
        };
        
        document.addEventListener('keydown', keydownHandler);
        
        // Guardar handlers para cleanup
        eventListenerCleanup.push(() => {
            document.removeEventListener('click', documentClickHandler);
            document.removeEventListener('keydown', keydownHandler);
        });
    }
    
    // ===============================================
    // FUNCIONES UTILITARIAS
    // ===============================================
    function closeAllDropdowns() {
        log('🔒 Cerrando todos los dropdowns...');
        
        dropdownInstances.forEach((instance, id) => {
            const element = document.getElementById(id);
            if (element && element.classList.contains('show')) {
                instance.hide();
            }
        });
    }
    
    function waitForBootstrap(callback, retries = 0) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
            callback();
        } else if (retries < CONFIG.MAX_RETRIES) {
            setTimeout(() => {
                waitForBootstrap(callback, retries + 1);
            }, 500);
        } else {
            log('❌ Bootstrap no se cargó después de varios intentos');
        }
    }
    
    function cleanup() {
        log('🧹 Ejecutando cleanup...');
        
        // Limpiar instancias de collapse
        dropdownInstances.forEach((instance) => {
            try {
                instance.dispose();
            } catch (e) {
                // Ignorar errores de disposal
            }
        });
        dropdownInstances.clear();
        
        // Limpiar event listeners
        eventListenerCleanup.forEach(cleanupFn => {
            try {
                cleanupFn();
            } catch (e) {
                // Ignorar errores de cleanup
            }
        });
        eventListenerCleanup = [];
        
        isInitialized = false;
    }
    
    // ===============================================
    // FUNCIONES GLOBALES PARA DEPURACIÓN
    // ===============================================
    window.dropdownFixDebug = {
        enable: () => { CONFIG.DEBUG = true; log('Debug habilitado'); },
        disable: () => { CONFIG.DEBUG = false; },
        reinit: initUniversalDropdownFix,
        cleanup: cleanup,
        closeAll: closeAllDropdowns,
        status: () => ({
            initialized: isInitialized,
            instances: dropdownInstances.size,
            listeners: eventListenerCleanup.length
        })
    };
    
    // ===============================================
    // INICIALIZACIÓN AUTOMÁTICA
    // ===============================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUniversalDropdownFix);
    } else {
        initUniversalDropdownFix();
    }
    
    // Reinicializar en cambios de ventana (para casos responsive)
    window.addEventListener('resize', debounce(() => {
        if (isInitialized) {
            initUniversalDropdownFix();
        }
    }, 250));
    
    // Función de debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    log('📁 Solución universal de dropdowns cargada');
    
})();