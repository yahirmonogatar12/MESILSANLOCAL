/**
 * Integración Plan Main - Combina funcionalidades existentes con nuevo loader
 * Este archivo coordina entre el sistema existente y el nuevo plan-main-loader
 */
(function() {
    "use strict";

    let integrationInitialized = false;

    /**
     * Configurar integración entre sistemas
     */
    function configurarIntegracion() {
        if (integrationInitialized) {
            return;
        }
        
        // Esperar a que ambos sistemas estén disponibles
        const checkSystems = setInterval(() => {
            const existingSystem = window.cargarDatosPlanMain;
            const newLoader = window.PlanMainLoader;
            
            if (newLoader) {
                clearInterval(checkSystems);
                setupIntegration();
            }
        }, 100);

        // Timeout después de 10 segundos
        setTimeout(() => {
            clearInterval(checkSystems);
            if (!integrationInitialized) {
                // Intentar setup básico
                setupBasicIntegration();
            }
        }, 10000);
    }

    /**
     * Configurar la integración entre sistemas
     */
    function setupIntegration() {
        integrationInitialized = true;

        // Configurar eventos del modo focus
        configurarEventosModoFocus();

        // Sincronizar cuando el sistema existente carga datos
        const originalCargarDatos = window.cargarDatosPlanMain;
        if (originalCargarDatos) {
            window.cargarDatosPlanMain = async function(params = {}) {
                // Llamar al sistema original
                const result = await originalCargarDatos(params);
                
                // Si el nuevo loader está disponible, sincronizar
                if (window.planMainLoader && window.planMainLoader.cargarDatos) {
                    try {
                        await window.planMainLoader.cargarDatos(params);
                    } catch (error) {
                        // Error sincronizando con nuevo loader
                    }
                }
                
                return result;
            };
        }

        // Evento personalizado para sincronización
        document.addEventListener("planSelected", function(event) {
            const plan = event.detail.plan;
            
            // Sincronizar con otros sistemas si es necesario
            if (window.updateBOMForPlan) {
                window.updateBOMForPlan(plan);
            }
            
            if (window.updateMaterialHistoryForPlan) {
                window.updateMaterialHistoryForPlan(plan);
            }
        });

        // Configurar botones existentes para usar el nuevo sistema
        setupExistingButtons();
    }

    /**
     * Configurar eventos del modo focus
     */
    function configurarEventosModoFocus() {

        // Agregar atajos de teclado para modo focus
        document.addEventListener('keydown', (e) => {
            // ESC para salir del modo focus
            if (e.key === 'Escape' && window.PlanMainLoader && window.PlanMainLoader.esModoFocusActivo()) {
                e.preventDefault();
                window.PlanMainLoader.desactivarModoFocus();
            }
        });

        // Ayuda visual deshabilitada
        // agregarAyudaVisualModoFocus();
    }

    /**
     * Agregar ayuda visual para el modo focus (DESHABILITADO)
     */
    function agregarAyudaVisualModoFocus() {
        // Función deshabilitada - no mostrar tooltips
    }

    /**
     * Setup básico de integración
     */
    function setupBasicIntegration() {
        integrationInitialized = true;
        configurarFechasPorDefecto();
    }

    /**
     * Configurar botones existentes (DESHABILITADO - usa plan-main-loader.js)
     */
    function setupExistingButtons() {
        // NO configurar el botón Consultar aquí - lo maneja plan-main-loader.js
        // Esto evita conflictos de múltiples event listeners
    }

    /**
     * Configurar fechas por defecto - Ahora para inputs de calendario
     */
    function configurarFechasPorDefecto() {
        const today = new Date();
        const fechaHoy = today.toISOString().slice(0, 10); // Formato YYYY-MM-DD
        
        const fechaDesde = document.getElementById("fechaDesde-Control de operacion de linea Main");
        const fechaHasta = document.getElementById("fechaHasta-Control de operacion de linea Main");
        
        // Configurar fecha desde (hoy)
        if (fechaDesde && fechaDesde.type === 'date') {
            if (!fechaDesde.value) {
                fechaDesde.value = fechaHoy;
            }
        }
        
        // Configurar fecha hasta (hoy)
        if (fechaHasta && fechaHasta.type === 'date') {
            if (!fechaHasta.value) {
                fechaHasta.value = fechaHoy;
            }
        }
    }

    /**
     * Inicialización automática
     */
    function inicializar() {
        
        // Configurar fechas por defecto
        configurarFechasPorDefecto();
        
        // Configurar integración
        configurarIntegracion();
        
        // Cargar datos iniciales después de un breve delay
        setTimeout(() => {
            if (window.planMainLoader && window.planMainLoader.cargarDatos) {
                const filtrosIniciales = {
                    q: "",
                    linea: "Todos",
                    desde: "",
                    hasta: ""
                };
                window.planMainLoader.cargarDatos(filtrosIniciales);
            }
        }, 1000);
    }

    // Funciones públicas
    window.planMainIntegration = {
        configurar: configurarIntegracion,
        recargar: () => {
            if (window.PlanMainLoader && window.PlanMainLoader.cargarDatos) {
                return window.PlanMainLoader.cargarDatos();
            }
        },
        obtenerSeleccionado: () => {
            if (window.PlanMainLoader && window.PlanMainLoader.obtenerPlanSeleccionado) {
                return window.PlanMainLoader.obtenerPlanSeleccionado();
            }
            return null;
        },
        activarModoFocus: (planData) => {
            if (window.PlanMainLoader && window.PlanMainLoader.activarModoFocus) {
                return window.PlanMainLoader.activarModoFocus(planData);
            }
        },
        desactivarModoFocus: () => {
            if (window.PlanMainLoader && window.PlanMainLoader.desactivarModoFocus) {
                return window.PlanMainLoader.desactivarModoFocus();
            }
        },
        esModoFocusActivo: () => {
            if (window.PlanMainLoader && window.PlanMainLoader.esModoFocusActivo) {
                return window.PlanMainLoader.esModoFocusActivo();
            }
            return false;
        }
    };

    // Auto-inicialización
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", inicializar);
    } else {
        setTimeout(inicializar, 200);
    }

})();