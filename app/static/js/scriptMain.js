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
                
                // Ocultar contenedor de Plan SMD Diario
                const planSmdDiarioContainer = document.getElementById('plan-smd-diario-unique-container');
                if (planSmdDiarioContainer) {
                    planSmdDiarioContainer.style.display = 'none';
                }
                
                // Ocultar contenedor de Control de producción SMT
                const controlProduccionSMTContainer = document.getElementById('Control de produccion SMT-unique-container');
                if (controlProduccionSMTContainer) {
                    controlProduccionSMTContainer.style.display = 'none';
                }
                
                // Ocultar contenedores específicos de Control de Producción que pueden quedar visibles
                const controlProduccionSpecificContainers = [
                    'control-mask-metal-unique-container',
                    'control-squeegee-unique-container',
                    'control-caja-mask-metal-unique-container',
                    'estandares-soldadura-unique-container',
                    'registro-recibo-soldadura-unique-container',
                    'control-salida-soldadura-unique-container',
                    'historial-tension-mask-metal-unique-container'
                ];
                
                controlProduccionSpecificContainers.forEach(containerId => {
                    const container = document.getElementById(containerId);
                    if (container) {
                        container.style.display = 'none';
                    }
                });
                
                // Ocultar contenedores específicos de Control de Proceso que pueden quedar visibles
                const controlProcesoSpecificContainers = [
                    'control-proceso-info-container',
                    'control-produccion-smt-container',
                    'inventario-imd-terminado-unique-container'
                ];
                
                controlProcesoSpecificContainers.forEach(containerId => {
                    const container = document.getElementById(containerId);
                    if (container) {
                        container.style.display = 'none';
                    }
                });
                
                // Ocultar todos los contenedores AJAX de Control de Proceso
                const controlProcesoAjaxContainers = [
                    'plan-smd-diario-unique-container',
                    'operacion-linea-smt-unique-container',
                    'operacion-linea-main-unique-container',
                    'plan-main-assy-unique-container',
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
                    'return-warehousing-register-unique-container',
                    'return-warehousing-history-unique-container',
                    'registro-movimiento-identificacion-unique-container',
                    'control-otras-identificaciones-unique-container',
                    'control-movimiento-ns-producto-unique-container',
                    'model-sn-management-unique-container',
                    'control-scrap-unique-container'
                ];
                
                controlProcesoAjaxContainers.forEach(containerId => {
                    const container = document.getElementById(containerId);
                    if (container) {
                        container.style.display = 'none';
                    }
                });
                
                // Ocultar todos los contenedores AJAX de Control de Resultados
                const controlResultadosAjaxContainers = [
                    'historial-aoi-unique-container'
                ];
                
                controlResultadosAjaxContainers.forEach(containerId => {
                    const container = document.getElementById(containerId);
                    if (container) {
                        container.style.display = 'none';
                    }
                });
                
                // Ocultar contenedor de visor MySQL para control de modelos
                const controlModelosVisorContainer = document.getElementById('control-modelos-visor-unique-container');
                if (controlModelosVisorContainer) {
                    controlModelosVisorContainer.style.display = 'none';
                }
                
                // Ocultar contenedor de Control de Modelos SMT
                const controlModelosSMTContainer = document.getElementById('control-modelos-smt-unique-container');
                if (controlModelosSMTContainer) {
                    controlModelosSMTContainer.style.display = 'none';
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
                
                // Ocultar también el contenedor de Control de Modelos SMT AJAX
                const controlModelosSMTContainer = document.getElementById('control-modelos-smt-unique-container');
                if (controlModelosSMTContainer) {
                    controlModelosSMTContainer.style.display = 'none';
                }
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
                    
                    if (typeof window.hideAllInformacionBasicaContainers === 'function') {
                        window.hideAllInformacionBasicaContainers();
                    }
                    
                    // Ocultar otros contenedores dentro del área de control de proceso
                    const controlProcesoContainers = [
                        'control-proceso-info-container',
                        'control-produccion-smt-container',
                        'Control de produccion SMT-unique-container',
                        'inventario-imd-terminado-unique-container',
                        'bom-unique-container'
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


                    // Mostrar el contenedor específico
                    operacionLineaContainer.style.display = 'block';
                    operacionLineaContainer.style.opacity = '1';


                    // Cargar contenido dinámicamente usando la nueva ruta AJAX
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('operacion-linea-smt-unique-container', '/control-operacion-linea-smt-ajax', () => {

                            // Verificar que el contenedor esté visible
                            const containerAfterLoad = document.getElementById('operacion-linea-smt-unique-container');
                            if (containerAfterLoad) {
                            }

                            // Ejecutar inicialización específica del módulo si existe
                            if (typeof window.inicializarControlOperacionLineaSMTAjax === 'function') {
                                window.inicializarControlOperacionLineaSMTAjax();
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

            // Función AJAX: Control de operación de línea Main
            window.mostrarControlOperacionLineaMain = function() {
                try {
                    // Activar sección Control de proceso
                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => { if (btn.id !== 'Control de proceso') btn.classList.remove('active'); });
                    }
                    // Ocultar todo
                    if (typeof window.hideAllMaterialContainers === 'function') window.hideAllMaterialContainers();
                    if (typeof window.hideAllInformacionBasicaContainers === 'function') window.hideAllInformacionBasicaContainers();
                    // Mostrar área de Control de proceso
                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');
                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';
                    // Contenedor específico
                    const containerId = 'operacion-linea-main-unique-container';
                    const cont = document.getElementById(containerId);
                    if (!cont) return console.error('Contenedor no existe:', containerId);
                    cont.style.display = 'block';
                    cont.style.opacity = '1';
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico(containerId, '/control-operacion-linea-main-ajax', () => {
                            if (typeof window.inicializarControlOperacionLineaMainAjax === 'function') {
                                window.inicializarControlOperacionLineaMainAjax();
                            }
                        });
                    }
                } catch (e) {
                    console.error('Error en mostrarControlOperacionLineaMain:', e);
                }
            };

            // Función AJAX: Plan Main ASSY
            window.mostrarPlanMainASSY = function() {
                try {
                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => { if (btn.id !== 'Control de proceso') btn.classList.remove('active'); });
                    }
                    if (typeof window.hideAllMaterialContainers === 'function') window.hideAllMaterialContainers();
                    if (typeof window.hideAllInformacionBasicaContainers === 'function') window.hideAllInformacionBasicaContainers();
                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');
                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';
                    const containerId = 'plan-main-assy-unique-container';
                    const cont = document.getElementById(containerId);
                    if (!cont) return console.error('Contenedor no existe:', containerId);
                    cont.style.display = 'block';
                    cont.style.opacity = '1';
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico(containerId, '/plan-main-assy-ajax', () => {
                            // Inicializar event listeners de plan después de cargar contenido dinámico
                            if (typeof window.initializePlanEventListeners === 'function') {
                                window.initializePlanEventListeners();
                            } else {
                                console.warn('⚠️ initializePlanEventListeners no disponible');
                            }
                        });
                    }
                } catch (e) {
                    console.error('Error en mostrarPlanMainASSY:', e);
                }
            };


            // ========================================
            // FUNCIONES AJAX PARA CONTROL DE PROCESO
            // ========================================

            // Control de impresión de identificación SMT
            window.mostrarControlImpresionIdentificacionSMT = function() {
                try {

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

                    // Mostrar áreas necesarias
                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    // Obtener y mostrar el contenedor específico
                    const container = document.getElementById('control-impresion-identificacion-smt-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    // Cargar contenido dinámicamente
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-impresion-identificacion-smt-unique-container', '/control-impresion-identificacion-smt-ajax', () => {
                            
                            if (typeof window.inicializarControlImpresionIdentificacionSMTAjax === 'function') {
                                window.inicializarControlImpresionIdentificacionSMTAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control de registro de identificación SMT
            window.mostrarControlRegistroIdentificacionSMT = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-registro-identificacion-smt-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-registro-identificacion-smt-unique-container', '/control-registro-identificacion-smt-ajax', () => {
                            
                            if (typeof window.inicializarControlRegistroIdentificacionSMTAjax === 'function') {
                                window.inicializarControlRegistroIdentificacionSMTAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Historial de operación de proceso
            window.mostrarHistorialOperacionProceso = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('historial-operacion-proceso-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('historial-operacion-proceso-unique-container', '/historial-operacion-proceso-ajax', () => {
                            
                            if (typeof window.inicializarHistorialOperacionProcesoAjax === 'function') {
                                window.inicializarHistorialOperacionProcesoAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // BOM Management Process
            window.mostrarBomManagementProcess = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('bom-management-process-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('bom-management-process-unique-container', '/bom-management-process-ajax', () => {
                            
                            if (typeof window.inicializarBomManagementProcessAjax === 'function') {
                                window.inicializarBomManagementProcessAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Reporte diario de inspección SMT
            window.mostrarReporteDiarioInspeccionSMT = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('reporte-diario-inspeccion-smt-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('reporte-diario-inspeccion-smt-unique-container', '/reporte-diario-inspeccion-smt-ajax', () => {
                            
                            if (typeof window.inicializarReporteDiarioInspeccionSMTAjax === 'function') {
                                window.inicializarReporteDiarioInspeccionSMTAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control diario de inspección SMT
            window.mostrarControlDiarioInspeccionSMT = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-diario-inspeccion-smt-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-diario-inspeccion-smt-unique-container', '/control-diario-inspeccion-smt-ajax', () => {
                            
                            if (typeof window.inicializarControlDiarioInspeccionSMTAjax === 'function') {
                                window.inicializarControlDiarioInspeccionSMTAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Reporte diario de inspección de proceso
            window.mostrarReporteDiarioInspeccionProceso = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('reporte-diario-inspeccion-proceso-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('reporte-diario-inspeccion-proceso-unique-container', '/reporte-diario-inspeccion-proceso-ajax', () => {
                            
                            if (typeof window.inicializarReporteDiarioInspeccionProcesoAjax === 'function') {
                                window.inicializarReporteDiarioInspeccionProcesoAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control de unidad de empaque por modelo
            window.mostrarControlUnidadEmpaqueModelo = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-unidad-empaque-modelo-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-unidad-empaque-modelo-unique-container', '/control-unidad-empaque-modelo-ajax', () => {
                            
                            if (typeof window.inicializarControlUnidadEmpaqueModeloAjax === 'function') {
                                window.inicializarControlUnidadEmpaqueModeloAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Packaging Register Management
            window.mostrarPackagingRegisterManagement = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('packaging-register-management-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('packaging-register-management-unique-container', '/packaging-register-management-ajax', () => {
                            
                            if (typeof window.inicializarPackagingRegisterManagementAjax === 'function') {
                                window.inicializarPackagingRegisterManagementAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Search Packaging History
            window.mostrarSearchPackagingHistory = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('search-packaging-history-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('search-packaging-history-unique-container', '/search-packaging-history-ajax', () => {
                            
                            if (typeof window.inicializarSearchPackagingHistoryAjax === 'function') {
                                window.inicializarSearchPackagingHistoryAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Shipping Register Management
            window.mostrarShippingRegisterManagement = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('shipping-register-management-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('shipping-register-management-unique-container', '/shipping-register-management-ajax', () => {
                            
                            if (typeof window.inicializarShippingRegisterManagementAjax === 'function') {
                                window.inicializarShippingRegisterManagementAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Search Shipping History
            window.mostrarSearchShippingHistory = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('search-shipping-history-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('search-shipping-history-unique-container', '/search-shipping-history-ajax', () => {
                            
                            if (typeof window.inicializarSearchShippingHistoryAjax === 'function') {
                                window.inicializarSearchShippingHistoryAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Return Warehousing Register
            window.mostrarReturnWarehousingRegister = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('return-warehousing-register-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('return-warehousing-register-unique-container', '/return-warehousing-register-ajax', () => {
                            
                            if (typeof window.inicializarReturnWarehousingRegisterAjax === 'function') {
                                window.inicializarReturnWarehousingRegisterAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Return Warehousing History
            window.mostrarReturnWarehousingHistory = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('return-warehousing-history-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('return-warehousing-history-unique-container', '/return-warehousing-history-ajax', () => {
                            
                            if (typeof window.inicializarReturnWarehousingHistoryAjax === 'function') {
                                window.inicializarReturnWarehousingHistoryAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Registro de movimiento de identificación
            window.mostrarRegistroMovimientoIdentificacion = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('registro-movimiento-identificacion-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('registro-movimiento-identificacion-unique-container', '/registro-movimiento-identificacion-ajax', () => {
                            
                            if (typeof window.inicializarRegistroMovimientoIdentificacionAjax === 'function') {
                                window.inicializarRegistroMovimientoIdentificacionAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control de otras identificaciones
            window.mostrarControlOtrasIdentificaciones = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-otras-identificaciones-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-otras-identificaciones-unique-container', '/control-otras-identificaciones-ajax', () => {
                            
                            if (typeof window.inicializarControlOtrasIdentificacionesAjax === 'function') {
                                window.inicializarControlOtrasIdentificacionesAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control de movimiento NS producto
            window.mostrarControlMovimientoNSProducto = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-movimiento-ns-producto-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-movimiento-ns-producto-unique-container', '/control-movimiento-ns-producto-ajax', () => {
                            
                            if (typeof window.inicializarControlMovimientoNSProductoAjax === 'function') {
                                window.inicializarControlMovimientoNSProductoAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Model SN Management
            window.mostrarModelSNManagement = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('model-sn-management-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('model-sn-management-unique-container', '/model-sn-management-ajax', () => {
                            
                            if (typeof window.inicializarModelSNManagementAjax === 'function') {
                                window.inicializarModelSNManagementAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };

            // Control Scrap
            window.mostrarControlScrap = function() {
                try {

                    const controlProcesoButton = document.getElementById('Control de proceso');
                    if (controlProcesoButton) {
                        controlProcesoButton.classList.add('active');
                        document.querySelectorAll('.nav-button').forEach(btn => {
                            if (btn.id !== 'Control de proceso') {
                                btn.classList.remove('active');
                            }
                        });
                    }

                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }

                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    const container = document.getElementById('control-scrap-unique-container');
                    if (!container) {
                        console.error('Contenedor no encontrado');
                        return;
                    }

                    container.style.display = 'block';
                    container.style.opacity = '1';

                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('control-scrap-unique-container', '/control-scrap-ajax', () => {
                            
                            if (typeof window.inicializarControlScrapAjax === 'function') {
                                window.inicializarControlScrapAjax();
                            }
                        });
                    }

                } catch (error) {
                    console.error('Error crítico:', error);
                }
            };


            // ========================================
            // FUNCIÓN PARA CONTROL DE PRODUCCIÓN SMT
            // ========================================
            
            // Control de producción SMT - SIGUIENDO EL PATRÓN EXITOSO
            window.mostrarControldeproduccionSMT = function() {
                try {

                    // FORZAR ocultado de TODAS las secciones primero
                    const informacionBasicaElSMT = document.getElementById('informacion-basica-content');
                    const controlMaterialElSMT = document.getElementById('control-material-content');
                    const controlProduccionElSMT = document.getElementById('control-produccion-content');
                    const controlProcesoElSMT = document.getElementById('control-proceso-content');
                    const controlCalidadElSMT = document.getElementById('control-calidad-content');
                    const controlResultadosElSMT = document.getElementById('control-resultados-content');
                    const configuracionProgramaElSMT = document.getElementById('configuracion-programa-content');
                    const materialContentElSMT = document.getElementById('material-content-area');
                    const informacionBasicaContentElSMT = document.getElementById('informacion-basica-content-area');
                    
                    // Ocultar todas las secciones principales
                    if (informacionBasicaElSMT) informacionBasicaElSMT.style.display = 'none';
                    if (controlMaterialElSMT) controlMaterialElSMT.style.display = 'none';
                    if (controlProduccionElSMT) controlProduccionElSMT.style.display = 'none';
                    if (controlProcesoElSMT) controlProcesoElSMT.style.display = 'none';
                    if (controlCalidadElSMT) controlCalidadElSMT.style.display = 'none';
                    if (controlResultadosElSMT) controlResultadosElSMT.style.display = 'none';
                    if (configuracionProgramaElSMT) configuracionProgramaElSMT.style.display = 'none';
                    if (materialContentElSMT) materialContentElSMT.style.display = 'none';
                    if (informacionBasicaContentElSMT) informacionBasicaContentElSMT.style.display = 'none';

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
                    
                    if (typeof window.hideAllInformacionBasicaContainers === 'function') {
                        window.hideAllInformacionBasicaContainers();
                    }
                    
                    // Ocultar otros contenedores dentro del área de control de proceso
                    const controlProcesoContainers = [
                        'control-proceso-info-container',
                        'control-produccion-smt-container',
                        'operacion-linea-smt-unique-container',
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
                    const controlProduccionSMTContainer = document.getElementById('Control de produccion SMT-unique-container');
                    if (!controlProduccionSMTContainer) {
                        console.error('El contenedor Control de produccion SMT-unique-container no existe en el HTML');
                        return;
                    }


                    // Mostrar el contenedor específico
                    controlProduccionSMTContainer.style.display = 'block';
                    controlProduccionSMTContainer.style.opacity = '1';


                    // Cargar contenido dinámicamente usando la ruta completa
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('Control de produccion SMT-unique-container', '/control_proceso/control_produccion_smt', () => {

                            // Verificar que el contenedor esté visible
                            const containerAfterLoad = document.getElementById('Control de produccion SMT-unique-container');
                            if (containerAfterLoad) {
                                
                                // Verificar que el contenedor esté realmente visible
                                
                                // Verificar que los contenedores padre también estén visibles
                                const materialContainerAfter = document.getElementById('material-container');
                                const controlProcesoContentAfter = document.getElementById('control-proceso-content');
                                const controlProcesoContentAreaAfter = document.getElementById('control-proceso-content-area');
                                
                            }

                            // Ejecutar inicialización específica del módulo si existe
                            if (typeof window.inicializarControlProduccionSMTModule === 'function') {
                                window.inicializarControlProduccionSMTModule();
                            }
                        })
                        .catch(error => {
                            console.error('Error cargando Control de producción SMT:', error);

                            // Mostrar mensaje de error al usuario
                            const errorContainer = document.querySelector('#Control de produccion SMT-unique-container');
                            if (errorContainer) {
                                errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control de producción SMT</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControldeproduccionSMT()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
                            }
                        });
                    } else {
                        console.error('Función cargarContenidoDinamico no está disponible');
                    }

                } catch (error) {
                    console.error('Error crítico en mostrarControldeproduccionSMT:', error);
                    alert('Error crítico al cargar Control de producción SMT. Consulte la consola para más detalles.');
                }
            };


            // ========================================
// FUNCIÓN PARA CREAR PLAN MICOM
// ========================================

// Crear plan micom - SIGUIENDO EL PATRÓN EXITOSO
window.mostrarCrearPlanMicom = function() {
    try {

        // IMPORTANTE: Asegurar que estamos en la sección correcta
        // Activar el botón "Control de produccion" para que scriptMain.js no interfiera
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            // Remover active de otros botones
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion (esto es lo que scriptMain.js maneja)
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');


        if (materialContainer) {
            materialContainer.style.display = 'block';
        }
        if (produccionContent) {
            produccionContent.style.display = 'block';
        }
        if (produccionContentArea) {
            produccionContentArea.style.display = 'block';
        }

        // Obtener el contenedor específico
        const crearPlanMicomContainer = document.getElementById('produccion-info-container');
        if (!crearPlanMicomContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }


        // Mostrar el contenedor específico
        crearPlanMicomContainer.style.display = 'block';
        crearPlanMicomContainer.style.opacity = '1';


        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/crear-plan-micom-ajax', () => {

                                 // Verificar que el contenedor esté visible
                 const containerAfterLoad = document.getElementById('produccion-info-container');
                if (containerAfterLoad) {

                    // Verificar que el contenedor esté realmente visible

                    // Verificar que los contenedores padre también estén visibles
                    const materialContainerAfter = document.getElementById('material-container');
                    const produccionContentAfter = document.getElementById('produccion-content');
                    const produccionContentAreaAfter = document.getElementById('produccion-content-area');

                }

                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarCrearPlanMicomModule === 'function') {
                    window.inicializarCrearPlanMicomModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Crear plan micom:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarCrearPlanMicom:', error);
    }
};

// ========================================
// FUNCIÓN PARA CONTROL BOM
// ========================================

            // Control BOM - SIGUIENDO EL PATRÓN EXITOSO
            window.mostrarControlBOM = function() {
                try {
                    // PASO 1: Ocultar TODOS los contenedores de todas las secciones
                    // Ocultar secciones principales
                    const allSections = [
                        'informacion-basica-content',
                        'control-material-content', 
                        'control-produccion-content',
                        'control-proceso-content',
                        'control-calidad-content',
                        'control-resultados-content',
                        'configuracion-programa-content'
                    ];
                    
                    allSections.forEach(sectionId => {
                        const section = document.getElementById(sectionId);
                        if (section) section.style.display = 'none';
                    });

                    // Ocultar áreas de contenido
                    const allAreas = [
                        'material-content-area',
                        'informacion-basica-content-area',
                        'control-produccion-content-area',
                        'control-proceso-content-area'
                    ];
                    
                    allAreas.forEach(areaId => {
                        const area = document.getElementById(areaId);
                        if (area) area.style.display = 'none';
                    });

                    // Ocultar TODOS los contenedores AJAX específicos
                    if (typeof window.hideAllMaterialContainers === 'function') {
                        window.hideAllMaterialContainers();
                    }
                    
                    if (typeof window.hideAllInformacionBasicaContainers === 'function') {
                        window.hideAllInformacionBasicaContainers();
                    }
                    
                    // Ocultar contenedores de Control de Proceso manualmente
                    const allControlProcesoContainers = [
                        'control-proceso-info-container',
                        'control-produccion-smt-container',
                        'operacion-linea-smt-unique-container',
                        'inventario-imd-terminado-unique-container',
                        'Control de produccion SMT-unique-container',
                        'crear-plan-micom-unique-container',
                        'line-material-status-unique-container'
                    ];
                    
                    allControlProcesoContainers.forEach(containerId => {
                        const container = document.getElementById(containerId);
                        if (container) container.style.display = 'none';
                    });

                    // PASO 2: Mostrar el contenedor padre de Control de Proceso
                    const materialContainer = document.getElementById('material-container');
                    const controlProcesoContent = document.getElementById('control-proceso-content');
                    const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

                    if (materialContainer) materialContainer.style.display = 'block';
                    if (controlProcesoContent) controlProcesoContent.style.display = 'block';
                    if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

                    // PASO 3: Obtener y mostrar el contenedor específico de BOM
                    const bomContainer = document.getElementById('bom-unique-container');
                    if (!bomContainer) {
                        console.error('❌ El contenedor bom-unique-container no existe en el HTML');
                        return;
                    }

                    bomContainer.style.display = 'block';

                    // PASO 4: Cargar contenido dinámicamente (esto también ejecuta cleanup)
                    if (typeof window.cargarContenidoDinamico === 'function') {
                        window.cargarContenidoDinamico('bom-unique-container', '/control-bom-ajax', () => {
                            // Ejecutar inicialización específica del módulo si existe
                            if (typeof window.initializeControlBOMEventListeners === 'function') {
                                window.initializeControlBOMEventListeners();
                            }
                        })
                        .catch(error => {
                            console.error('❌ Error cargando Control BOM:', error);
                            const errorContainer = document.getElementById('bom-unique-container');
                            if (errorContainer) {
                                errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control BOM</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControlBOM()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
                            }
                        });
                    } else {
                        console.error('❌ Función cargarContenidoDinamico no está disponible');
                    }

                } catch (error) {
                    console.error('❌ Error crítico en mostrarControlBOM:', error);
                    alert('Error crítico al cargar Control BOM. Consulte la consola para más detalles.');
                }
            };

        });

// ========================================
// FUNCIÓN PARA LINE MATERIAL STATUS_ES
// ========================================

window.mostrarLineMaterialStatus = function() {
    try {

        // IMPORTANTE: Asegurar que estamos en la sección correcta
        // Activar el botón "Control de produccion" para que scriptMain.js no interfiera
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            // Remover active de otros botones
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion (esto es lo que scriptMain.js maneja)
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');


        if (materialContainer) {
            materialContainer.style.display = 'block';
        }
        if (produccionContent) {
            produccionContent.style.display = 'block';
        }
        if (produccionContentArea) {
            produccionContentArea.style.display = 'block';
        }

        // Obtener el contenedor específico
        const lineMaterialStatusContainer = document.getElementById('produccion-info-container');
        if (!lineMaterialStatusContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }


        // Mostrar el contenedor específico
        lineMaterialStatusContainer.style.display = 'block';
        lineMaterialStatusContainer.style.opacity = '1';


        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/line-material-status-ajax', () => {

                // Verificar que el contenedor esté visible
                const containerAfterLoad = document.getElementById('produccion-info-container');
                if (containerAfterLoad) {

                    // Verificar que el contenedor esté realmente visible

                    // Verificar que los contenedores padre también estén visibles
                    const materialContainerAfter = document.getElementById('material-container');
                    const produccionContentAfter = document.getElementById('produccion-content');
                    const produccionContentAreaAfter = document.getElementById('produccion-content-area');

                }

                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarLineMaterialStatusModule === 'function') {
                    window.inicializarLineMaterialStatusModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Line Material Status_es:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarLineMaterialStatus:', error);
    }
};


// ========================================
// FUNCIONES AJAX PARA MÓDULOS DE CONTROL DE PRODUCCIÓN
// ========================================

window.mostrarControlMaskMetal = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const controlMaskMetalContainer = document.getElementById('produccion-info-container');
        if (!controlMaskMetalContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        controlMaskMetalContainer.style.display = 'block';
        controlMaskMetalContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/control-mask-metal-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarControlMaskMetalModule === 'function') {
                    window.inicializarControlMaskMetalModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Control de mask de metal:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlMaskMetal:', error);
    }
};

window.mostrarControlSqueegee = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const controlSqueegeeContainer = document.getElementById('produccion-info-container');
        if (!controlSqueegeeContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        controlSqueegeeContainer.style.display = 'block';
        controlSqueegeeContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/control-squeegee-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarControlSqueegeeModule === 'function') {
                    window.inicializarControlSqueegeeModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Control de squeegee:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlSqueegee:', error);
    }
};

window.mostrarControlCajaMaskMetal = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const controlCajaMaskMetalContainer = document.getElementById('produccion-info-container');
        if (!controlCajaMaskMetalContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        controlCajaMaskMetalContainer.style.display = 'block';
        controlCajaMaskMetalContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/control-caja-mask-metal-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarControlCajaMaskMetalModule === 'function') {
                    window.inicializarControlCajaMaskMetalModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Control de caja de mask de metal:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlCajaMaskMetal:', error);
    }
};

window.mostrarEstandaresSoldadura = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const estandaresSoldaduraContainer = document.getElementById('produccion-info-container');
        if (!estandaresSoldaduraContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        estandaresSoldaduraContainer.style.display = 'block';
        estandaresSoldaduraContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/estandares-soldadura-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarEstandaresSoldaduraModule === 'function') {
                    window.inicializarEstandaresSoldaduraModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Estandares sobre control de soldadura:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarEstandaresSoldadura:', error);
    }
};

window.mostrarRegistroReciboSoldadura = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const registroReciboSoldaduraContainer = document.getElementById('produccion-info-container');
        if (!registroReciboSoldaduraContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        registroReciboSoldaduraContainer.style.display = 'block';
        registroReciboSoldaduraContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/registro-recibo-soldadura-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarRegistroReciboSoldaduraModule === 'function') {
                    window.inicializarRegistroReciboSoldaduraModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Registro de recibo de soldadura:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarRegistroReciboSoldadura:', error);
    }
};

window.mostrarControlSalidaSoldadura = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const controlSalidaSoldaduraContainer = document.getElementById('produccion-info-container');
        if (!controlSalidaSoldaduraContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        controlSalidaSoldaduraContainer.style.display = 'block';
        controlSalidaSoldaduraContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/control-salida-soldadura-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarControlSalidaSoldaduraModule === 'function') {
                    window.inicializarControlSalidaSoldaduraModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Control de salida de soldadura:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlSalidaSoldadura:', error);
    }
};

window.mostrarHistorialTensionMaskMetal = function() {
    try {

        // Activar el botón "Control de produccion"
        const controlProduccionButton = document.getElementById('Control de produccion');
        if (controlProduccionButton) {
            controlProduccionButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de produccion') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Ocultar otros contenedores dentro del área de produccion
        const produccionContainers = [
            'produccion-info-container',
            'crear-plan-produccion-unique-container',
            'plan-smt-unique-container',
            'control-embarque-unique-container'
        ];

        produccionContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar el área de produccion
        const materialContainer = document.getElementById('material-container');
        const produccionContent = document.getElementById('produccion-content');
        const produccionContentArea = document.getElementById('produccion-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (produccionContent) produccionContent.style.display = 'block';
        if (produccionContentArea) produccionContentArea.style.display = 'block';

        // Obtener el contenedor específico
        const historialTensionMaskMetalContainer = document.getElementById('produccion-info-container');
        if (!historialTensionMaskMetalContainer) {
            console.error('El contenedor produccion-info-container no existe en el HTML');
            return;
        }

        // Mostrar el contenedor específico
        historialTensionMaskMetalContainer.style.display = 'block';
        historialTensionMaskMetalContainer.style.opacity = '1';

        // Cargar contenido dinámicamente usando la ruta AJAX
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('produccion-info-container', '/historial-tension-mask-metal-ajax', () => {
                
                // Ejecutar inicialización específica del módulo si existe
                if (typeof window.inicializarHistorialTensionMaskMetalModule === 'function') {
                    window.inicializarHistorialTensionMaskMetalModule();
                }
            })
            .catch(error => {
                console.error('Error cargando Historial de tension de mask de metal:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialTensionMaskMetal:', error);
    }
};


// ============================================================================
// FUNCIONES PARA CONTROL DE CALIDAD
// ============================================================================

window.mostrarControlResultadoReparacion = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/control-resultado-reparacion-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Control de resultado de reparación:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlResultadoReparacion:', error);
    }
};

window.mostrarControlItemReparado = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/control-item-reparado-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Control de item reparado:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlItemReparado:', error);
    }
};

window.mostrarHistorialCambioMaterialMaquina = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/historial-cambio-material-maquina-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Historial de cambio de material por máquina:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialCambioMaterialMaquina:', error);
    }
};

window.mostrarHistorialUsoPegamentoSoldadura = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/historial-uso-pegamento-soldadura-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Historial de uso de pegamento de soldadura:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialUsoPegamentoSoldadura:', error);
    }
};

window.mostrarHistorialUsoMaskMetal = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/historial-uso-mask-metal-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Historial de uso de mask de metal:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialUsoMaskMetal:', error);
    }
};

window.mostrarHistorialUsoSqueegee = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/historial-uso-squeegee-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Historial de uso de squeegee:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialUsoSqueegee:', error);
    }
};

window.mostrarProcessInterlockHistory = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/process-interlock-history-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Process interlock History:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarProcessInterlockHistory:', error);
    }
};

window.mostrarControlMasterSampleSMT = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/control-master-sample-smt-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Control de Master Sample de SMT:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlMasterSampleSMT:', error);
    }
};

window.mostrarHistorialInspeccionMasterSampleSMT = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/historial-inspeccion-master-sample-smt-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Historial de inspección de Master Sample de SMT:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarHistorialInspeccionMasterSampleSMT:', error);
    }
};

window.mostrarControlInspeccionOQC = function() {
    try {

        // Activar el botón "Control de calidad"
        const controlCalidadButton = document.getElementById('Control de calidad');
        if (controlCalidadButton) {
            controlCalidadButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de calidad') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }

        // Mostrar el área de calidad
        const materialContainer = document.getElementById('material-container');
        const controlCalidadContent = document.getElementById('control-calidad-content');
        const calidadContentArea = document.getElementById('calidad-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlCalidadContent) controlCalidadContent.style.display = 'block';
        if (calidadContentArea) calidadContentArea.style.display = 'block';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('calidad-content-area', '/control-inspeccion-oqc-ajax', () => {
            })
            .catch(error => {
                console.error('Error cargando Control de inspección de OQC:', error);
            });
        } else {
            console.error('La función cargarContenidoDinamico no está disponible');
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlInspeccionOQC:', error);
    }
};


// Función AJAX para Historial AOI - GLOBAL
window.mostrarHistorialAOI = function() {
    try {

        // Activar el botón correcto en la navegación
        const controlResultadosButton = document.getElementById('Control de resultados');
        if (controlResultadosButton) {
            controlResultadosButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de resultados') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        // Limpiar módulos previos de Control de Resultados si existen
        if (typeof window.limpiarHistorialAOI === 'function') {
            window.limpiarHistorialAOI();
        }
        
        // Ocultar otros contenedores dentro del área de control de resultados
        const controlResultadosContainers = [
            'control-resultados-info-container'
        ];
        
        controlResultadosContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar TODAS las áreas necesarias
        const materialContainer = document.getElementById('material-container');
        const controlResultadosContent = document.getElementById('control-resultados-content');
        const controlResultadosContentArea = document.getElementById('control-resultados-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlResultadosContent) controlResultadosContent.style.display = 'block';
        if (controlResultadosContentArea) controlResultadosContentArea.style.display = 'block';

        // Obtener y mostrar el contenedor específico
        const historialAOIContainer = document.getElementById('historial-aoi-unique-container');
        if (!historialAOIContainer) {
            console.error('El contenedor no existe en el HTML');
            return;
        }

        historialAOIContainer.style.display = 'block';
        historialAOIContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('historial-aoi-unique-container', '/historial-aoi-ajax', () => {
                
                // Ejecutar inicialización del módulo si existe
                if (typeof window.inicializarHistorialAOI === 'function') {
                    window.inicializarHistorialAOI();
                }
            });
        }

    } catch (error) {
        console.error('Error crítico:', error);
    }
};


// Función AJAX para Plan SMD Diario - GLOBAL
window.mostrarPlanSmdDiario = function() {
    try {

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
            'operacion-linea-smt-unique-container',
            'Control de produccion SMT-unique-container',
            'bom-unique-container',
            'bom-management-process-unique-container'
        ];
        
        controlProcesoContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar TODAS las áreas necesarias
        const materialContainer = document.getElementById('material-container');
        const controlProcesoContent = document.getElementById('control-proceso-content');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlProcesoContent) controlProcesoContent.style.display = 'block';

        // Crear o mostrar el contenedor específico del plan SMD diario
        let planSmdDiarioContainer = document.getElementById('plan-smd-diario-unique-container');
        if (!planSmdDiarioContainer) {
            // Crear el contenedor si no existe
            planSmdDiarioContainer = document.createElement('div');
            planSmdDiarioContainer.id = 'plan-smd-diario-unique-container';
            planSmdDiarioContainer.className = 'unique-container';
            planSmdDiarioContainer.style.display = 'none';
            
            // Agregar al área de control de proceso
            const controlProcesoContentArea = document.getElementById('control-proceso-content-area');
            if (controlProcesoContentArea) {
                controlProcesoContentArea.appendChild(planSmdDiarioContainer);
            }
        }

        planSmdDiarioContainer.style.display = 'block';
        planSmdDiarioContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('plan-smd-diario-unique-container', '/plan-smd-diario', () => {
            });
        }

    } catch (error) {
        console.error('Error crítico en mostrarPlanSmdDiario:', error);
    }
};


// Función AJAX para Control de modelos - VISOR MYSQL - GLOBAL
window.mostrarControlModelosVisor = function() {
    try {

        // Activar el botón correcto en la navegación
        const informacionBasicaButton = document.getElementById('Información Básica');
        if (informacionBasicaButton) {
            informacionBasicaButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Información Básica') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        // Ocultar otros contenedores dentro del área de información básica
        const informacionBasicaContainers = [
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
            'info-empresa-info-container',
            'control-modelos-info-container',
            'control-bom-info-container',
            'control-bom-smt-info-container'
        ];
        
        informacionBasicaContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar TODAS las áreas necesarias
        const materialContainer = document.getElementById('material-container');
        const informacionBasicaContent = document.getElementById('informacion-basica-content');
        const informacionBasicaContentArea = document.getElementById('informacion-basica-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (informacionBasicaContent) informacionBasicaContent.style.display = 'block';
        if (informacionBasicaContentArea) informacionBasicaContentArea.style.display = 'block';

        // Obtener y mostrar el contenedor específico
        const controlModelosVisorContainer = document.getElementById('control-modelos-visor-unique-container');
        if (!controlModelosVisorContainer) {
            console.error('El contenedor control-modelos-visor-unique-container no existe en el HTML');
            return;
        }

        controlModelosVisorContainer.style.display = 'block';
        controlModelosVisorContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('control-modelos-visor-unique-container', '/control-modelos-visor-ajax', () => {
                
                // Ejecutar inicialización del módulo
                if (typeof window.inicializarControlModelosVisorAjax === 'function') {
                    window.inicializarControlModelosVisorAjax();
                }
            });
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlModelosVisor:', error);
    }
};


// Función AJAX para Control de Modelos SMT - GLOBAL
window.mostrarControlModelosSMT = function() {
    try {

        // Activar el botón correcto en la navegación
        const informacionBasicaButton = document.getElementById('Información básica');
        if (informacionBasicaButton) {
            informacionBasicaButton.classList.add('active');
            informacionBasicaButton.click();
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        if (typeof window.hideAllInformacionBasicaContainers === 'function') {
            window.hideAllInformacionBasicaContainers();
        }
        
        // Mostrar la jerarquía de contenedores necesaria
        const materialContainer = document.getElementById('material-container');
        const informacionBasicaContent = document.getElementById('informacion-basica-content');
        const informacionBasicaContentArea = document.getElementById('informacion-basica-content-area');
        const controlModelosSMTContainer = document.getElementById('control-modelos-smt-unique-container');

        if (materialContainer) {
            materialContainer.style.display = 'block';
            materialContainer.style.opacity = '1';
        }

        if (informacionBasicaContent) {
            informacionBasicaContent.style.display = 'block';
            informacionBasicaContent.style.opacity = '1';
        }

        if (informacionBasicaContentArea) {
            informacionBasicaContentArea.style.display = 'block';
            informacionBasicaContentArea.style.opacity = '1';
        }

        if (!controlModelosSMTContainer) {
            console.error('Contenedor control-modelos-smt-unique-container no encontrado');
            return;
        }

        controlModelosSMTContainer.style.display = 'block';
        controlModelosSMTContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('control-modelos-smt-unique-container', '/control-modelos-smt-ajax', () => {
                
                // Ejecutar inicialización del módulo
                if (typeof window.inicializarControlModelosSMTAjax === 'function') {
                    window.inicializarControlModelosSMTAjax();
                }
            });
        }

    } catch (error) {
        console.error('Error crítico en mostrarControlModelosSMT:', error);
    }
};

