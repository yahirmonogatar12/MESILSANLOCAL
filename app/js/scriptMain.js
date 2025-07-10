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
            }
            
            // Función para resetear completamente la pestaña de Información Básica
            function resetInformacionBasica() {
                console.log('Reseteando Información Básica (sin AJAX)');
                
                // Llamar a la función global de reseteo si existe
                if (typeof window.resetInfoBasicaToDefault === 'function') {
                    window.resetInfoBasicaToDefault();
                } else {
                    console.log('Función resetInfoBasicaToDefault no disponible aún');
                }
                
                // Asegurar que todos los sidebar-links funcionen
                const sidebarLinks = informacionBasicaContent.querySelectorAll('.sidebar-link');
                sidebarLinks.forEach(link => {
                    link.style.pointerEvents = 'auto';
                    link.style.cursor = 'pointer';
                });
                
                console.log('Sidebar links habilitados:', sidebarLinks.length);
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
            
            // Hacer la función disponible globalmente
            window.hideAllInformacionBasicaContainers = hideAllInformacionBasicaContainers;
            
            // Funciones globales para mostrar cada contenedor de Información Básica
            window.mostrarAdminUsuarioInfo = function() {
                console.log('Mostrando Administración de usuario');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-usuario-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminMenuInfo = function() {
                console.log('Mostrando Administración de menú');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-menu-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminAutoridadInfo = function() {
                console.log('Mostrando Administración de autoridad');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-autoridad-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlCodigoInfo = function() {
                console.log('Mostrando Control de lista de código');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-codigo-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarAdminItinerarioInfo = function() {
                console.log('Mostrando Administración de itinerario');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('admin-itinerario-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarConsultarLicenciasInfo = function() {
                console.log('Mostrando Consultar licencias');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('consultar-licencias-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlDepartamentoInfo = function() {
                console.log('Mostrando Control de departamento');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-departamento-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlProcesoInfo = function() {
                console.log('Mostrando Control de proceso');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-proceso-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlOrdenProcesoInfo = function() {
                console.log('Mostrando Control de orden de proceso');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-orden-proceso-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlOrdenProceso2Info = function() {
                console.log('Mostrando Control de orden de proceso 2');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-orden-proceso2-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlDefectoInfo = function() {
                console.log('Mostrando Control de defecto por proceso');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-defecto-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlInterfacesInfo = function() {
                console.log('Mostrando Control de interfaces de máquina');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-interfaces-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlInterlockInfo = function() {
                console.log('Mostrando Control de interlock de máquina en línea');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-interlock-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarConfiguracionMSLInfo = function() {
                console.log('Mostrando Configuración de MSL');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('configuracion-msl-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlClienteInfo = function() {
                console.log('Mostrando Control de cliente');
                hideAllInformacionBasicaContainers();
                const container = document.getElementById('control-cliente-info-container');
                if (container) {
                    container.style.display = 'block';
                }
            };
            
            window.mostrarControlProveedorInfo = function() {
                console.log('Mostrando Control de proveedor');
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
                console.log('🏪 === INICIANDO mostrarControlAlmacen ===');
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                controlAlmacenContainer.style.display = 'block';
                
                // Inicializar el contenido de control de almacén después de mostrarlo
                setTimeout(() => {
                    console.log('🔄 Inicializando funciones de control de almacén...');
                    
                    // Usar la nueva función global del módulo
                    if (typeof window.inicializarControlAlmacenModule === 'function') {
                        console.log('✅ Ejecutando inicializarControlAlmacenModule...');
                        window.inicializarControlAlmacenModule();
                    } else {
                        console.warn('⚠️ inicializarControlAlmacenModule no disponible, intentando métodos individuales');
                        
                        // Fallback a la función anterior
                        if (typeof window.inicializarControlAlmacen === 'function') {
                            console.log('✅ Ejecutando inicializarControlAlmacen...');
                            window.inicializarControlAlmacen();
                        } else {
                            console.warn('⚠️ inicializarControlAlmacen no disponible, usando métodos individuales');
                            // Fallback a métodos individuales
                            if (typeof cargarCodigosMaterial === 'function') {
                                console.log('✅ Ejecutando cargarCodigosMaterial...');
                                cargarCodigosMaterial();
                            } else {
                                console.warn('⚠️ cargarCodigosMaterial no disponible');
                            }
                            if (typeof cargarClienteSeleccionado === 'function') {
                                console.log('✅ Ejecutando cargarClienteSeleccionado...');
                                cargarClienteSeleccionado();
                            } else {
                                console.warn('⚠️ cargarClienteSeleccionado no disponible');
                            }
                            if (typeof cargarSiguienteSecuencial === 'function') {
                                console.log('✅ Ejecutando cargarSiguienteSecuencial...');
                                cargarSiguienteSecuencial();
                            } else {
                                console.warn('⚠️ cargarSiguienteSecuencial no disponible');
                            }
                        }
                    }
                    console.log('🏁 Inicialización de control de almacén completada');
                }, 200);
                console.log('🏪 === FIN mostrarControlAlmacen ===');
            };
            
            // Funciones para mostrar otros contenidos
            window.mostrarControlSalida = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                controlSalidaContainer.style.display = 'block';
            };
            
            window.mostrarControlRetorno = function() {
                hideAllMaterialContainers();
                materialContentArea.style.display = 'block';
                controlRetornoContainer.style.display = 'block';
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
                        console.log('Cargando pestaña Información Básica');
                        materialContainer.style.display = 'block';
                        informacionBasicaContent.style.display = 'block';
                        informacionBasicaContentArea.style.display = 'block';
                        
                        // Mostrar contenedor por defecto
                        hideAllInformacionBasicaContainers();
                        const defaultContainer = document.getElementById('info-basica-default-container');
                        if (defaultContainer) {
                            defaultContainer.style.display = 'block';
                        }
                        
                        console.log('Información Básica cargada correctamente');
                        
                    } else if (this.id === 'Control de material') {
                        console.log('Cargando pestaña Control de Material');
                        materialContainer.style.display = 'block';
                        controlMaterialContent.style.display = 'block';
                        // Mostrar el área de material con información por defecto
                        mostrarInfoMaterial();
                        console.log('Control de Material cargado con información por defecto');
                        
                    } else if (this.id === 'Control de producción') {
                        materialContainer.style.display = 'block';
                        controlProduccionContent.style.display = 'block';
                        // FORZAR ocultar el área de material cuando no estés en Control de material
                        materialContentArea.style.display = 'none';
                        
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
                    console.log('Activando pestaña por defecto: Información Básica');
                    infoBasicaButton.click();
                }
            }
            
            console.log('Sistema de navegación inicializado correctamente');
            
            // Función global para mostrar Control de Material en Información Básica
            window.mostrarControlMaterialInfo = function() {
                console.log('=== INICIANDO mostrarControlMaterialInfo (NUEVA ESTRUCTURA) ===');
                
                // Asegurarse de que estemos en el área correcta
                if (informacionBasicaContentArea) {
                    informacionBasicaContentArea.style.display = 'block';
                    console.log('Área de contenido de Información Básica activada');
                }
                
                // Ocultar todos los contenedores
                hideAllInformacionBasicaContainers();
                console.log('Todos los contenedores ocultados');
                
                // Mostrar el contenedor específico
                const container = document.getElementById('control-material-info-container');
                if (container) {
                    container.style.display = 'block';
                    container.style.visibility = 'visible';
                    container.style.opacity = '1';
                    console.log('✅ Container control-material-info-container mostrado');
                    console.log('Display:', window.getComputedStyle(container).display);
                    console.log('Visibility:', window.getComputedStyle(container).visibility);
                    console.log('Opacity:', window.getComputedStyle(container).opacity);
                } else {
                    console.error('✗ Container control-material-info-container no encontrado');
                }
                
                console.log('=== FIN mostrarControlMaterialInfo ===');
            };
        });