/**
 * SISTEMA DE VALIDACIÓN DE PERMISOS DE DROPDOWNS
 * =============================================
 * 
 * Este sistema valida los permisos en el frontend y oculta/deshabilita
 * elementos según los permisos del usuario actual.
 */

(function() {
    'use strict';
    
    // Variables globales
    let permisosUsuario = {};
    let usuarioActual = null;
    let rolUsuario = null;
    let isInitialized = false;
    
    // Configuración
    const CONFIG = {
        DEBUG: true,  // Habilitar debug para ver qué está pasando
        CACHE_DURATION: 300000, // 5 minutos
        AUTO_REFRESH: true
    };
    
    /**
     * Sistema principal de validación de permisos
     */
    window.PermisosDropdowns = {
        
        /**
         * Inicializar el sistema de permisos
         */
        async init() {
            if (isInitialized) return;
            
            try {
                
                // Cargar permisos del usuario actual
                await this.cargarPermisosUsuario();
                
                // Aplicar permisos a elementos existentes
                this.aplicarPermisosExistentes();
                
                // Configurar observador para elementos dinámicos
                this.configurarObservadorMutaciones();
                
                isInitialized = true;
                
            } catch (error) {
                console.error('❌ Error inicializando sistema de permisos:', error);
            }
        },
        
        /**
         * Cargar permisos del usuario actual desde el servidor
         */
        async cargarPermisosUsuario() {
            try {
                const response = await fetch('/admin/obtener_permisos_usuario_actual', {
                    method: 'GET',
                    credentials: 'include',  // Incluir cookies de sesión
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`Error HTTP: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                permisosUsuario = data.permisos || {};
                usuarioActual = data.usuario;
                rolUsuario = data.rol;
                
                if (CONFIG.DEBUG) {
                }
                
                // Guardar en localStorage para cache
                localStorage.setItem('permisos_dropdowns', JSON.stringify({
                    permisos: permisosUsuario,
                    usuario: usuarioActual,
                    rol: rolUsuario,
                    timestamp: Date.now()
                }));
                
            } catch (error) {
                console.warn('⚠️ Error cargando permisos del servidor, usando cache:', error);
                
                // Intentar cargar desde cache
                const cached = localStorage.getItem('permisos_dropdowns');
                if (cached) {
                    const data = JSON.parse(cached);
                    if (Date.now() - data.timestamp < CONFIG.CACHE_DURATION) {
                        permisosUsuario = data.permisos;
                        usuarioActual = data.usuario;
                        rolUsuario = data.rol;
                    }
                }
            }
        },
        
        /**
         * Verificar si el usuario tiene permiso para un dropdown específico
         */
        tienePermiso(pagina, seccion, boton) {
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) console.warn('⚠️ Parámetros incompletos para verificar permiso');
                return false;
            }
            
            // SUPERADMIN y ADMIN tienen todos los permisos automáticamente
            if (rolUsuario === 'superadmin' || rolUsuario === 'admin') {
                if (CONFIG.DEBUG) {
                }
                return true;
            }
            
            // Verificar en la estructura de permisos
            if (permisosUsuario[pagina] && 
                permisosUsuario[pagina][seccion] && 
                permisosUsuario[pagina][seccion].includes(boton)) {
                if (CONFIG.DEBUG) {
                }
                return true;
            }
            
            if (CONFIG.DEBUG) {
            }
            
            return false;
        },
        
        /**
         * Aplicar permisos a elementos existentes en la página
         */
        aplicarPermisosExistentes() {
            
            // Buscar todos los elementos con atributos de permisos
            const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
            
            
            elementosConPermisos.forEach(elemento => {
                this.validarElemento(elemento);
            });
            
            // Validar elementos específicos de listas
            this.validarElementosListas();
        },
        
        /**
         * Validar un elemento específico
         */
        validarElemento(elemento) {
            const pagina = elemento.dataset.permisoPagina;
            const seccion = elemento.dataset.permisoSeccion;
            const boton = elemento.dataset.permisoBoton;
            
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) {
                    console.warn('⚠️ Elemento sin datos de permisos completos:', elemento);
                }
                return;
            }
            
            const tienePermiso = this.tienePermiso(pagina, seccion, boton);
            
            if (!tienePermiso) {
                this.ocultarElemento(elemento, pagina, seccion, boton);
            } else {
                this.mostrarElemento(elemento);
            }
        },
        
        /**
         * Validar elementos específicos de las listas
         */
        validarElementosListas() {
            // Validar sidebar links de LISTA_DE_MATERIALES
            this.validarSidebarLinks('LISTA_DE_MATERIALES', [
                { selector: 'li.sidebar-link:contains("Control de material de almacén")', seccion: 'Control de material', boton: 'Control de material de almacén' },
                { selector: 'li.sidebar-link:contains("Control de salida")', seccion: 'Control de material', boton: 'Control de salida' },
                { selector: 'li.sidebar-link:contains("Control de material retorno")', seccion: 'Control de material', boton: 'Control de material retorno' },
                { selector: 'li.sidebar-link:contains("Historial de material")', seccion: 'Control de material', boton: 'Historial de material' },
                { selector: 'li.sidebar-link:contains("Estatus de material")', seccion: 'Control de material', boton: 'Estatus de material' }
            ]);
            
            // Validar sidebar links de LISTA_INFORMACIONBASICA
            this.validarSidebarLinks('LISTA_INFORMACIONBASICA', [
                { selector: 'li.sidebar-link:contains("Gestión de departamentos")', seccion: 'Información básica', boton: 'Gestión de departamentos' },
                { selector: 'li.sidebar-link:contains("Gestión de empleados")', seccion: 'Información básica', boton: 'Gestión de empleados' },
                { selector: 'li.sidebar-link:contains("Gestión de proveedores")', seccion: 'Información básica', boton: 'Gestión de proveedores' }
            ]);
        },
        
        /**
         * Validar sidebar links para una lista específica
         */
        validarSidebarLinks(pagina, elementos) {
            elementos.forEach(({ selector, seccion, boton }) => {
                const elemento = document.querySelector(selector);
                if (elemento) {
                    if (!this.tienePermiso(pagina, seccion, boton)) {
                        this.ocultarElemento(elemento, pagina, seccion, boton);
                    }
                }
            });
        },
        
        /**
         * Ocultar elemento sin permiso
         */
        ocultarElemento(elemento, pagina, seccion, boton) {
            elemento.style.display = 'none';
            elemento.setAttribute('data-sin-permiso', 'true');
            elemento.title = `Sin permisos para: ${boton}`;
            
            // Deshabilitar clicks en elementos sin permiso
            elemento.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                alert(`⚠️ No tienes permisos para acceder a: ${boton}`);
                return false;
            });
            
            // También bloquear eventos táctiles
            elemento.addEventListener('touchstart', function(e) {
                e.preventDefault();
                e.stopPropagation();
                alert(`⚠️ No tienes permisos para acceder a: ${boton}`);
                return false;
            });
            
            // Agregar clase visual para indicar que está deshabilitado
            elemento.classList.add('sin-permisos');
            elemento.style.pointerEvents = 'none';
            elemento.style.opacity = '0.5';
            elemento.style.cursor = 'not-allowed';
            
            if (CONFIG.DEBUG) {
            }
        },
        
        /**
         * Mostrar elemento con permiso
         */
        mostrarElemento(elemento) {
            elemento.style.display = '';
            elemento.removeAttribute('data-sin-permiso');
            elemento.title = '';
        },
        
        /**
         * Configurar observador de mutaciones para elementos dinámicos
         */
        configurarObservadorMutaciones() {
            const observador = new MutationObserver((mutaciones) => {
                mutaciones.forEach((mutacion) => {
                    mutacion.addedNodes.forEach((nodo) => {
                        if (nodo.nodeType === Node.ELEMENT_NODE) {
                            // Verificar si el nodo agregado tiene atributos de permisos
                            if (nodo.hasAttribute && nodo.hasAttribute('data-permiso-pagina')) {
                                this.validarElemento(nodo);
                            }
                            
                            // Verificar hijos del nodo
                            const elementosConPermisos = nodo.querySelectorAll && nodo.querySelectorAll('[data-permiso-pagina]');
                            if (elementosConPermisos) {
                                elementosConPermisos.forEach(elemento => {
                                    this.validarElemento(elemento);
                                });
                            }
                        }
                    });
                });
            });
            
            // Observar cambios en todo el documento
            observador.observe(document.body, {
                childList: true,
                subtree: true
            });
        },
        
        /**
         * Recargar permisos del servidor
         */
        async recargarPermisos() {
            await this.cargarPermisosUsuario();
            this.aplicarPermisosExistentes();
        },
        
        /**
         * Verificar permiso específico (para uso en código)
         */
        async verificarPermiso(pagina, seccion, boton) {
            // Primero verificar en cache local
            if (this.tienePermiso(pagina, seccion, boton)) {
                return true;
            }
            
            // Si no está en cache, verificar en servidor
            try {
                const response = await fetch('/admin/verificar_permiso_dropdown', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ pagina, seccion, boton })
                });
                
                const data = await response.json();
                return data.tiene_permiso || false;
                
            } catch (error) {
                console.error('Error verificando permiso en servidor:', error);
                return false;
            }
        },
        
        /**
         * Habilitar modo debug
         */
        enableDebug() {
            CONFIG.DEBUG = true;
        },
        
        /**
         * Obtener información de estado
         */
        getStatus() {
            return {
                initialized: isInitialized,
                totalPermisos: Object.keys(permisosUsuario).reduce((total, pagina) => {
                    return total + Object.keys(permisosUsuario[pagina]).reduce((subtotal, seccion) => {
                        return subtotal + permisosUsuario[pagina][seccion].length;
                    }, 0);
                }, 0),
                permisos: permisosUsuario
            };
        },
        
        /**
         * Función de testing para verificar permisos específicos
         */
        testPermiso(pagina, seccion, boton) {
            
            // Buscar elementos relacionados
            const elementos = document.querySelectorAll(`[data-permiso-pagina="${pagina}"][data-permiso-seccion="${seccion}"][data-permiso-boton="${boton}"]`);
            
            return this.tienePermiso(pagina, seccion, boton);
        },
        
        /**
         * Verificar permiso antes de ejecutar una función
         */
        verificarPermisoAntesFuncion(pagina, seccion, boton, funcionCallback) {
            if (!this.tienePermiso(pagina, seccion, boton)) {
                alert(`⚠️ No tienes permisos para acceder a: ${boton}`);
                console.warn(`🚫 Acceso denegado a función: ${pagina} > ${seccion} > ${boton}`);
                return false;
            }
            
            // Si tiene permiso, ejecutar la función
            if (typeof funcionCallback === 'function') {
                funcionCallback();
            }
            return true;
        },
        
        /**
         * Envolver función existente con verificación de permisos
         */
        protegerFuncion(nombreFuncion, pagina, seccion, boton) {
            const funcionOriginal = window[nombreFuncion];
            
            if (typeof funcionOriginal === 'function') {
                window[nombreFuncion] = (...args) => {
                    if (this.tienePermiso(pagina, seccion, boton)) {
                        return funcionOriginal.apply(this, args);
                    } else {
                        alert(`⚠️ No tienes permisos para acceder a: ${boton}`);
                        console.warn(`🚫 Acceso denegado a función: ${nombreFuncion}`);
                        return false;
                    }
                };
                
            }
        }
    };
    
    // Auto-inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.PermisosDropdowns.init();
        });
    } else {
        window.PermisosDropdowns.init();
    }
    
    // Auto-recargar permisos periódicamente si está habilitado
    if (CONFIG.AUTO_REFRESH) {
        setInterval(() => {
            if (isInitialized) {
                window.PermisosDropdowns.recargarPermisos();
            }
        }, CONFIG.CACHE_DURATION);
    }
    
})();

