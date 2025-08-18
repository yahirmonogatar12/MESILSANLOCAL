 // Mostrar/ocultar el contenedor de material según el botón
        document.addEventListener('DOMContentLoaded', function() {
            const materialContainer = document.getElementById('material-container');
            const informacionBasicaContent = document.getElementById('informacion-basica-content');
            const controlMaterialContent = document.getElementById('control-material-content');
            const controlProduccionContent = document.getElementById('control-produccion-content');
            const controlProcesoContent = document.getElementById('control-proceso-content');
            const controlCalidadContent = document.getElementById('control-calidad-content');
            const controlResultadosContent = document.getElementById('control-resultados-content');
            const controlReporteContent = document.getElementById('control-reporte-content');
            const configuracionProgramaContent = document.getElementById('configuracion-programa-content');
            const materialContentArea = document.getElementById('material-content-area');
            const informacionBasicaContentArea = document.getElementById('informacion-basica-content-area');
            const materialInfoContainer = document.getElementById('material-info-container');
            const controlAlmacenContainer = document.getElementById('control-almacen-container');
            const controlSalidaContainer = document.getElementById('control-salida-container');
            const controlRetornoContainer = document.getElementById('control-retorno-container');
            const reciboPagoContainer = document.getElementById('recibo-pago-container');
            const historialMaterialContainer = document.getElementById('historial-material-container');
            const estatusMaterialContainer = document.getElementById('estatus-material-container');
            const materialSustitutoContainer = document.getElementById('material-sustituto-container');
            const consultarPepsContainer = document.getElementById('consultar-peps-container');
            const longtermInventoryContainer = document.getElementById('longterm-inventory-container');
            const registroMaterialContainer = document.getElementById('registro-material-container');
            const historialInventarioContainer = document.getElementById('historial-inventario-container');
            const ajusteNumeroContainer = document.getElementById('ajuste-numero-container');
            const navButtons = document.querySelectorAll('.nav-button');
            
            // Función para ocultar todo el contenido
            function hideAllContent() {
                informacionBasicaContent.style.display = 'none';
                controlMaterialContent.style.display = 'none';
                controlProduccionContent.style.display = 'none';
                controlProcesoContent.style.display = 'none';
                controlCalidadContent.style.display = 'none';
                controlResultadosContent.style.display = 'none';
                if (controlReporteContent) controlReporteContent.style.display = 'none';
                configuracionProgramaContent.style.display = 'none';
                
                // FORZAR ocultar completamente las áreas de contenido
                materialContentArea.style.display = 'none';
                informacionBasicaContentArea.style.display = 'none';
                hideAllMaterialContainers();
                hideAllInformacionBasicaContainers();
                
                // Cerrar Control de Embarque cuando se cambie a otra sección
                if (typeof window.cerrarControlEmbarque === 'function') {
                    window.cerrarControlEmbarque();
                }
            }
            
            // Función para resetear completamente la pestaña de Información Básica
            function resetInformacionBasica() {
                
                // Llamar a la función global de reseteo si existe
                if (typeof window.resetInfoBasicaToDefault === 'function') {
                    window.resetInfoBasicaToDefault();
                } else {
                }
                
                // Asegurar que todos los sidebar-links funcionen
                const sidebarLinks = informacionBasicaContent.querySelectorAll('.sidebar-link');
                sidebarLinks.forEach(link => {
                    link.style.pointerEvents = 'auto';
                    link.style.cursor = 'pointer';
                });
                
            }
            
            // Función para ocultar todos los contenedores de material
            function hideAllMaterialContainers() {
                materialInfoContainer.style.display = 'none';
                controlAlmacenContainer.style.display = 'none';
                controlSalidaContainer.style.display = 'none';
                controlRetornoContainer.style.display = 'none';
                reciboPagoContainer.style.display = 'none';
                historialMaterialContainer.style.display = 'none';
                estatusMaterialContainer.style.display = 'none';
                materialSustitutoContainer.style.display = 'none';
                consultarPepsContainer.style.display = 'none';
                longtermInventoryContainer.style.display = 'none';
                registroMaterialContainer.style.display = 'none';
                historialInventarioContainer.style.display = 'none';
                ajusteNumeroContainer.style.display = 'none';
                
                // Ocultar contenedor de operación de línea SMT
                const operacionLineaSMTContainer = document.getElementById('operacion-linea-smt-unique-container');
                if (operacionLineaSMTContainer) {
                    operacionLineaSMTContainer.style.display = 'none';
                }
            }
            
            function hideAllInformacionBasicaContainers() {
                const containers = [
                    'info-basica-default-container',
                    'admin-usuario-info-container', 
                    'admin-menu-info-container',
                    'admin-autoridad-info-container',
                    'control-codigo-info-container',
                    'admin-itinerario-info-container',
                    'consultar-licencias-info-container',
                    'control-departamento-info-container',
                    'control-proceso-info-container',
                    'control-orden-proceso-info-container',
                    'control-orden-proceso2-info-container',
                    'control-defecto-info-container',
                    'control-interfaces-info-container',
                    'control-interlock-info-container',
                    'control-material-info-container',
                    'configuracion-msl-info-container',
                    'control-cliente-info-container',
                    'control-proveedor-info-container',
                    'control-moneda-info-container',
                    'info-empresa-info-container'
                ];
                
                containers.forEach(containerId => {
                    const container = document.getElementById(containerId);
                    if (container) {
                        container.style.display = 'none';
                    }
                });
            }
            
            // Hacer las funciones disponibles globalmente
            window.hideAllInformacionBasicaContainers = hideAllInformacionBasicaContainers;
            window.hideAllMaterialContainers = hideAllMaterialContainers;
            
            // Funciones globales para mostrar cada contenedor de Información Básica
            window.mostrarAdminUsuarioInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-usuario-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminMenuInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-menu-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminAutoridadInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-autoridad-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlCodigoInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-codigo-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminItinerarioInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-itinerario-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarConsultarLicenciasInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('consultar-licencias-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlDepartamentoInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-departamento-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlProcesoInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-proceso-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlOrdenProcesoInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-orden-proceso-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlOrdenProceso2Info = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-orden-proceso2-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlDefectoInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-defecto-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlInterfacesInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-interfaces-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlInterlockInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-interlock-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarConfiguracionMSLInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('configuracion-msl-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlClienteInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-cliente-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlProveedorInfo = function() {
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-proveedor-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            // Función para mostrar el contenido por defecto de material
            window.mostrarInfoMaterial = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                materialInfoContainer.style.display = 'block';
            };
            
            // Función global para mostrar el contenido de almacén
            window.mostrarControlAlmacen = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                controlAlmacenContainer.style.display = 'block';
                
                // Inicializar el contenido de control de almacén después de mostrarlo
                setTimeout(() => {
                    
                    // Usar la nueva función global del módulo
                    if (typeof window.inicializarControlAlmacenModule === 'function') {
                        window.inicializarControlAlmacenModule();
                    } else {
                        console.warn(' inicializarControlAlmacenModule no disponible, intentando métodos individuales');
                        
                        // Fallback a la función anterior
                        if (typeof window.inicializarControlAlmacen === 'function') {
                            window.inicializarControlAlmacen();
                        } else {
                            console.warn(' inicializarControlAlmacen no disponible, usando métodos individuales');
                            // Fallback a métodos individuales
                            if (typeof cargarCodigosMaterial === 'function') {
                                cargarCodigosMaterial();
                            } else {
                                console.warn(' cargarCodigosMaterial no disponible');
                            }
                            if (typeof cargarClienteSeleccionado === 'function') {
                                cargarClienteSeleccionado();
                            } else {
                                console.warn(' cargarClienteSeleccionado no disponible');
                            }
                            if (typeof cargarSiguienteSecuencial === 'function') {
                                cargarSiguienteSecuencial();
                            } else {
                                console.warn(' cargarSiguienteSecuencial no disponible');
                            }
                        }
                    }
                }, 200);
            };
            
            // Funciones para mostrar otros contenidos
            window.mostrarControlSalida = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                controlSalidaContainer.style.display = 'block';
                
                // Inicializar el contenido de control de salida después de mostrarlo
                setTimeout(() => {
                    
                    // Usar la nueva función global del módulo
                    if (typeof window.inicializarControlSalidaModule === 'function') {
                        window.inicializarControlSalidaModule();
                    } else {
                        console.warn(' inicializarControlSalidaModule no disponible, intentando métodos individuales');
                        
                        // Fallback a la función anterior
                        if (typeof window.inicializarControlSalida === 'function') {
                            window.inicializarControlSalida();
                        } else {
                            console.warn(' inicializarControlSalida no disponible');
                        }
                    }
                }, 200);
            };
            
            window.mostrarControlRetorno = async function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                
                // Usar AjaxContentManager para cargar contenido dinámicamente
                if (window.AjaxContentManager) {
                    await AjaxContentManager.loadContent('/material/control_retorno', '#control-retorno-container');
                } else {
                    // Fallback al método original
                    controlRetornoContainer.style.display = 'block';
                }
            };
            
            window.mostrarReciboPago = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                reciboPagoContainer.style.display = 'block';
            };
            
            window.mostrarHistorialMaterial = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                historialMaterialContainer.style.display = 'block';
            };
            
            window.mostrarEstatusMaterial = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                estatusMaterialContainer.style.display = 'block';
                
                // Cargar contenido dinámicamente usando la ruta del servidor
                cargarContenidoDinamico('estatus-material-container', '/material/estatus_material', () => {
                    
                    // Inicializar funcionalidades específicas del estatus de material si es necesario
                    if (typeof window.initEstatusMaterial === 'function') {
                        window.initEstatusMaterial();
                    }
                });
            };
            
            window.mostrarMaterialSustituto = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                materialSustitutoContainer.style.display = 'block';
            };
            
            window.mostrarConsultarPeps = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                consultarPepsContainer.style.display = 'block';
            };
            
            window.mostrarLongtermInventory = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                longtermInventoryContainer.style.display = 'block';
            };
            
            window.mostrarRegistroMaterial = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                registroMaterialContainer.style.display = 'block';
            };
            
            window.mostrarHistorialInventario = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                historialInventarioContainer.style.display = 'block';
            };
            
            window.mostrarAjusteNumero = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                ajusteNumeroContainer.style.display = 'block';
            };
            
            // Función global para ocultar el contenido de almacén
            window.ocultarControlAlmacen = function() {
                materialContentArea.style.display = 'none';
                hideAllMaterialContainers();
            };
            
            navButtons.forEach(btn => {
                btn.addEventListener('click', function() {
                    // Remover la clase 'active' de todos los botones
                    navButtons.forEach(b => b.classList.remove('active'));
                    // Agregar la clase 'active' al botón clickeado
                    this.classList.add('active');
                    
                    // Ocultar todo el contenido primero
                    hideAllContent();
                    
                    if (this.id === 'Información Basica') {
                        
                        // Usar la función global de MaterialTemplate.html si está disponible
                        if (typeof window.mostrarInformacionBasica === 'function') {
                            window.mostrarInformacionBasica();
                        } else {
                            // Fallback básico
                            materialContainer.style.display = 'block';
                            informacionBasicaContent.style.display = 'block';
                            informacionBasicaContentArea.style.display = 'block';
                            hideAllInformacionBasicaContainers();
                            const defaultContainer = document.getElementById('info-basica-default-container');
                            if (defaultContainer) {
                                defaultContainer.style.display = 'block';
                            }
                        }
                        
                    } else if (this.id === 'Control de material') {
                        
                        // Usar la función global de MaterialTemplate.html si está disponible
                        if (typeof window.mostrarControlMaterial === 'function') {
                            window.mostrarControlMaterial();
                        } else {
                            // Fallback básico
                            materialContainer.style.display = 'block';
                            controlMaterialContent.style.display = 'block';
                            mostrarInfoMaterial();
                        }
                        
                    } else if (this.id === 'Control de producción') {
                        // Usar la función global de MaterialTemplate.html si está disponible
                        if (typeof window.mostrarControlProduccion === 'function') {
                            window.mostrarControlProduccion();
                        } else {
                            // Fallback básico
                            materialContainer.style.display = 'block';
                            controlProduccionContent.style.display = 'block';
                            materialContentArea.style.display = 'none';
                        }
                        
                    } else if (this.id === 'Control de proceso') {
                        materialContainer.style.display = 'block';
                        controlProcesoContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
                    } else if (this.id === 'Control de calidad') {
                        materialContainer.style.display = 'block';
                        controlCalidadContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
                    } else if (this.id === 'Control de resultados') {
                        materialContainer.style.display = 'block';
                        controlResultadosContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
                    } else if (this.id === 'Control de reporte') {
                        materialContainer.style.display = 'block';
                        if (controlReporteContent) controlReporteContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
                    } else if (this.id === 'Configuración de programa') {
                        materialContainer.style.display = 'block';
                        configuracionProgramaContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
                    } else {
                        materialContainer.style.display = 'none';
                        // FORZAR ocultar el área de material para cualquier otro caso
                        materialContentArea.style.display = 'none';
                    }
                });
            });
            
            // Por defecto oculto
            materialContainer.style.display = 'none';
            
            // FORZAR estado inicial correcto
            materialContentArea.style.display = 'none';
            hideAllMaterialContainers();
            
            // Activar por defecto la primera pestaña (Información Básica) si no hay ninguna activa
            const activeButton = document.querySelector('.nav-button.active');
            if (!activeButton) {
                const infoBasicaButton = document.getElementById('Información Basica');
                if (infoBasicaButton) {
                    infoBasicaButton.click();
                }
            }
            
            
            // ============== FUNCIONES PARA CONTROL DE CALIDAD ==============
            
            // Función global para mostrar historial de cambio de material de SMT
            window.mostrarHistorialSMT = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                // Llamar a la función específica del MaterialTemplate
                if (typeof window.mostrarHistorialCambioSMT === 'function') {
                    window.mostrarHistorialCambioSMT();
                } else {
                    console.warn(' mostrarHistorialCambioSMT no disponible');
                    // Fallback básico
                    const appContent = document.querySelector('main.app-content');
                    if (appContent) {
                        appContent.innerHTML = `
                            <div class="container-fluid mt-4">
                                <h2>Historial de cambio de material de SMT</h2>
                                <p>Funcionalidad en desarrollo...</p>
                            </div>
                        `;
                    }
                }
            };
            
            // Función para historial de cambio de material por máquina
            window.mostrarHistorialMaterialMaquina = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                // Aquí puedes agregar la lógica específica para esta funcionalidad
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de cambio de material por máquina</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para control de resultado de reparación
            window.mostrarControlReparacion = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Control de resultado de reparación</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para control de item reparado
            window.mostrarControlItemReparado = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Control de item reparado</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para historial de uso de pegamento de soldadura
            window.mostrarHistorialPegamento = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de uso de pegamento de soldadura</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para historial de uso de mask de metal
            window.mostrarHistorialMask = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de uso de mask de metal</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para historial de uso de squeeguee
            window.mostrarHistorialSqueeguee = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de uso de squeeguee</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para process interlock history
            window.mostrarProcessInterlockHistory = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Process Interlock History</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para control de master sample de SMT
            window.mostrarControlMasterSample = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Control de Master Sample de SMT</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para historial de inspección de master sample de SMT
            window.mostrarHistorialInspeccionMaster = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de inspección de Master Sample de SMT</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // Función para control de inspección de OQC
            window.mostrarControlInspeccionOQC = function() {
                hideAllContent();
                controlCalidadContent.style.display = 'block';
                
                const appContent = document.querySelector('main.app-content');
                if (appContent) {
                    appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Control de inspección de OQC</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
                }
            };
            
            // NOTA: mostrarControlMaterialInfo está definida en MaterialTemplate.html con AJAX
            // No redefinir aquí para evitar conflictos
            
            // Función AJAX para Control de operación de línea SMT - GLOBAL
            window.mostrarControlOperacionLineaSMT = function() {
                try {
                    console.log('FUNCIÓN mostrarControlOperacionLineaSMT EJECUTÁNDOSE...');
                    console.log('Iniciando carga AJAX de Control de operación de línea SMT...');

                    // IMPORTANTE: Asegurar que estamos en la sección correcta
                    // Activar el botón "Control de proceso" para que scriptMain.js no interfiera
                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        // Remover active de otros botones
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
                        'inventario-imd-terminado-unique-container'
                    ];
                    
                    controlProcesoContainers.forEach(containerId => {
                        const container = document.getElementById(containerId);
                        if (container) {
                            container.style.display = 'none';
                        }
                    });

                    // Mostrar el área de control de proceso (esto es lo que scriptMain.js maneja)
                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    // Obtener el contenedor específico
                    const operacionLineaContainer = document.getElementById('operacion-linea-smt-unique-container');
                    if (!operacionLineaContainer) {
                        console.error('El contenedor operacion-linea-smt-unique-container no existe en el HTML');
                        return;
                    }

                    console.log('Contenedor encontrado:', operacionLineaContainer);
                    console.log('Estado inicial - Display:', operacionLineaContainer.style.display);

                    // Mostrar el contenedor específico
                    operacionLineaContainer.style.display = 'block';
                    operacionLineaContainer.style.opacity = '1';

                    console.log('Estado después de mostrar - Display:', operacionLineaContainer.style.display);

                    // Cargar contenido dinámicamente usando la nueva ruta AJAX
                    console.log('Iniciando carga AJAX...');
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('operacion-linea-smt-unique-container', '/control-operacion-linea-smt-ajax', () => {
                            console.log('Control de operación de línea SMT AJAX cargado exitosamente');
                            console.log('Verificando contenedor después de carga...');

                            // Verificar que el contenedor esté visible
                            const containerAfterLoad = document.getElementById('operacion-linea-smt-unique-container');
                            if (containerAfterLoad) {
                                console.log('Contenedor encontrado después de carga:', containerAfterLoad);
                                console.log('Display:', containerAfterLoad.style.display);
                                console.log('HTML contenido:', containerAfterLoad.innerHTML.substring(0, 200) + '...');
                            }

                            // Ejecutar inicialización específica del módulo si existe
                            if (typeof window.inicializarControlOperacionLineaSMTAjax === 'function') {
                                window.inicializarControlOperacionLineaSMTAjax();
                                console.log('Módulo inicializado correctamente');
                            }
                        })
                        .catch(error => {
                            console.error('Error cargando Control de operación de línea SMT AJAX:', error);

                            // Mostrar mensaje de error al usuario
                            const errorContainer = document.querySelector('#operacion-linea-smt-unique-container');
                            if (errorContainer) {
                                errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control de operación de línea SMT</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControlOperacionLineaSMT()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
                            }
                        });
                    } else {
                        console.error('Función cargarContenidoDinamico no está disponible');
                    }

                } catch (error) {
                    console.error('Error crítico en mostrarControlOperacionLineaSMT:', error);
                    alert('Error crítico al cargar Control de operación de línea SMT. Consulte la consola para más detalles.');
                }
            };

            console.log('Función mostrarControlOperacionLineaSMT registrada globalmente');
        });