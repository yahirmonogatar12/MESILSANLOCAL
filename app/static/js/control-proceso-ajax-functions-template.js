// PLANTILLA DE FUNCIONES AJAX PARA CONTROL DE PROCESO
// Copiar estas funciones a scriptMain.js y reemplazar los comentarios con la lógica específica

// Control de impresion de identificacion de SMT
window.mostrarControlImpresionIdentificacionSMT = function() {
    mostrarModuloControlProceso(
        'control-impresion-identificacion-smt-unique-container',
        '/control-impresion-identificacion-smt-ajax',
        'inicializarControlImpresionIdentificacionSMTAjax'
    );
};

// Control de registro de identificacion de SMT
window.mostrarControlRegistroIdentificacionSMT = function() {
    mostrarModuloControlProceso(
        'control-registro-identificacion-smt-unique-container',
        '/control-registro-identificacion-smt-ajax',
        'inicializarControlRegistroIdentificacionSMTAjax'
    );
};

// Historial de operacion por proceso
window.mostrarHistorialOperacionProceso = function() {
    mostrarModuloControlProceso(
        'historial-operacion-proceso-unique-container',
        '/historial-operacion-proceso-ajax',
        'inicializarHistorialOperacionProcesoAjax'
    );
};

// BOM Management By Process
window.mostrarBOMManagementProcess = function() {
    mostrarModuloControlProceso(
        'bom-management-process-unique-container',
        '/bom-management-process-ajax',
        'inicializarBOMManagementProcessAjax'
    );
};

// Reporte diario de inspeccion de SMT
window.mostrarReporteDiarioInspeccionSMT = function() {
    mostrarModuloControlProceso(
        'reporte-diario-inspeccion-smt-unique-container',
        '/reporte-diario-inspeccion-smt-ajax',
        'inicializarReporteDiarioInspeccionSMTAjax'
    );
};

// Control diario de inspeccion de SMT
window.mostrarControlDiarioInspeccionSMT = function() {
    mostrarModuloControlProceso(
        'control-diario-inspeccion-smt-unique-container',
        '/control-diario-inspeccion-smt-ajax',
        'inicializarControlDiarioInspeccionSMTAjax'
    );
};

// Reporte diario de inspeccion por proceso
window.mostrarReporteDiarioInspeccionProceso = function() {
    mostrarModuloControlProceso(
        'reporte-diario-inspeccion-proceso-unique-container',
        '/reporte-diario-inspeccion-proceso-ajax',
        'inicializarReporteDiarioInspeccionProcesoAjax'
    );
};

// Control de unidad de empaque por modelo
window.mostrarControlUnidadEmpaqueModelo = function() {
    mostrarModuloControlProceso(
        'control-unidad-empaque-modelo-unique-container',
        '/control-unidad-empaque-modelo-ajax',
        'inicializarControlUnidadEmpaqueModeloAjax'
    );
};

// Packaging Register Management
window.mostrarPackagingRegisterManagement = function() {
    mostrarModuloControlProceso(
        'packaging-register-management-unique-container',
        '/packaging-register-management-ajax',
        'inicializarPackagingRegisterManagementAjax'
    );
};

// Search Packaging History
window.mostrarSearchPackagingHistory = function() {
    mostrarModuloControlProceso(
        'search-packaging-history-unique-container',
        '/search-packaging-history-ajax',
        'inicializarSearchPackagingHistoryAjax'
    );
};

// Shipping Register Management
window.mostrarShippingRegisterManagement = function() {
    mostrarModuloControlProceso(
        'shipping-register-management-unique-container',
        '/shipping-register-management-ajax',
        'inicializarShippingRegisterManagementAjax'
    );
};

// Search Shipping History
window.mostrarSearchShippingHistory = function() {
    mostrarModuloControlProceso(
        'search-shipping-history-unique-container',
        '/search-shipping-history-ajax',
        'inicializarSearchShippingHistoryAjax'
    );
};

// Almacén de Embarques - Entradas
window.mostrarAlmacenEmbarquesEntradas = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-entradas-unique-container',
        '/almacen-embarques-entradas-ajax',
        'inicializarAlmacenEmbarquesEntradasAjax'
    );
};

// Almacén de Embarques - Salidas
window.mostrarAlmacenEmbarquesSalidas = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-salidas-unique-container',
        '/almacen-embarques-salidas-ajax',
        'inicializarAlmacenEmbarquesSalidasAjax'
    );
};

// Almacén de Embarques - Retorno
window.mostrarAlmacenEmbarquesRetorno = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-retorno-unique-container',
        '/almacen-embarques-retorno-ajax?v=20260507a',
        'inicializarAlmacenEmbarquesRetornoAjax'
    );
};

// Almacén de Embarques - Modificar movimientos
window.mostrarAlmacenEmbarquesMovimientos = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-movimientos-unique-container',
        '/almacen-embarques-movimientos-ajax',
        'inicializarAlmacenEmbarquesMovimientosAjax'
    );
};

// Almacén de Embarques - Inventario general
window.mostrarAlmacenEmbarquesInventarioGeneral = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-inventario-general-unique-container',
        '/almacen-embarques-inventario-general-ajax',
        'inicializarAlmacenEmbarquesInventarioGeneralAjax'
    );
};

// Almacén de Embarques - Catálogo
window.mostrarAlmacenEmbarquesCatalogo = function() {
    mostrarModuloControlProceso(
        'almacen-embarques-catalogo-unique-container',
        '/almacen-embarques-catalogo-ajax?v=20260507a',
        'inicializarAlmacenEmbarquesCatalogoAjax'
    );
};

// Registro de movimiento de identificacion
window.mostrarRegistroMovimientoIdentificacion = function() {
    mostrarModuloControlProceso(
        'registro-movimiento-identificacion-unique-container',
        '/registro-movimiento-identificacion-ajax',
        'inicializarRegistroMovimientoIdentificacionAjax'
    );
};

// Control de otras identificaciones
window.mostrarControlOtrasIdentificaciones = function() {
    mostrarModuloControlProceso(
        'control-otras-identificaciones-unique-container',
        '/control-otras-identificaciones-ajax',
        'inicializarControlOtrasIdentificacionesAjax'
    );
};

// Control de movimiento de N/S de producto
window.mostrarControlMovimientoNSProducto = function() {
    mostrarModuloControlProceso(
        'control-movimiento-ns-producto-unique-container',
        '/control-movimiento-ns-producto-ajax',
        'inicializarControlMovimientoNSProductoAjax'
    );
};

// Model S/N Management
window.mostrarModelSNManagement = function() {
    mostrarModuloControlProceso(
        'model-sn-management-unique-container',
        '/model-sn-management-ajax',
        'inicializarModelSNManagementAjax'
    );
};

// Control de Scrap
window.mostrarControlScrap = function() {
    mostrarModuloControlProceso(
        'control-scrap-unique-container',
        '/control-scrap-ajax',
        'inicializarControlScrapAjax'
    );
};

// FUNCIÓN HELPER GENÉRICA PARA CONTROL DE PROCESO
function mostrarModuloControlProceso(containerId, ajaxUrl, initFunction) {
    try {
        console.log(`Iniciando carga AJAX de ${containerId}...`);

        // Activar el botón correcto en la navegación
        const controlProcesoButton = document.getElementById('Control de proceso');
        if (controlProcesoButton) {
            controlProcesoButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de proceso') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        // Ocultar otros contenedores dentro del área de control de proceso
        const controlProcesoContainers = [
            'control-proceso-info-container',
            'control-produccion-smt-container',
            'Control de produccion SMT-unique-container',
            'inventario-imd-terminado-unique-container',
            'operacion-linea-smt-unique-container'
        ];
        
        // Agregar todos los contenedores AJAX a la lista
        const allContainers = controlProcesoContainers.concat([
            'control-impresion-identificacion-smt-unique-container',
            'control-registro-identificacion-smt-unique-container',
            'historial-operacion-proceso-unique-container',
            'bom-management-process-unique-container',
            'reporte-diario-inspeccion-smt-unique-container',
            'control-diario-inspeccion-smt-unique-container',
            'reporte-diario-inspeccion-proceso-unique-container',
            'control-unidad-empaque-modelo-unique-container',
            'packaging-register-management-unique-container',
            'search-packaging-history-unique-container',
            'shipping-register-management-unique-container',
            'search-shipping-history-unique-container',
            'almacen-embarques-entradas-unique-container',
            'almacen-embarques-salidas-unique-container',
            'almacen-embarques-retorno-unique-container',
            'almacen-embarques-movimientos-unique-container',
            'almacen-embarques-inventario-general-unique-container',
            'almacen-embarques-catalogo-unique-container',
            'registro-movimiento-identificacion-unique-container',
            'control-otras-identificaciones-unique-container',
            'control-movimiento-ns-producto-unique-container',
            'model-sn-management-unique-container',
            'control-scrap-unique-container'
        ]);
        
        allContainers.forEach(id => {
            const container = document.getElementById(id);
            if (container && id !== containerId) {
                container.style.display = 'none';
            }
        });

        // Mostrar TODAS las áreas necesarias
        const materialContainer = document.getElementById('material-container');
        const controlProcesoContent = document.getElementById('control-proceso-content');
        const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlProcesoContent) controlProcesoContent.style.display = 'block';
        if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

        // Obtener y mostrar el contenedor específico
        const targetContainer = document.getElementById(containerId);
        if (!targetContainer) {
            console.error(`El contenedor ${containerId} no existe en el HTML`);
            return;
        }

        targetContainer.style.display = 'block';
        targetContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico(containerId, ajaxUrl, () => {
                console.log(`${containerId} cargado exitosamente`);
                
                // Ejecutar inicialización del módulo
                if (typeof window[initFunction] === 'function') {
                    window[initFunction]();
                    console.log(`${initFunction} ejecutado correctamente`);
                }
            });
        }

    } catch (error) {
        console.error(`Error crítico en mostrarModuloControlProceso:`, error);
    }
}
