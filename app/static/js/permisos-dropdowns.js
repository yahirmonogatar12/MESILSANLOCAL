/**
 * SISTEMA DE VALIDACION DE PERMISOS DE DROPDOWNS
 * =============================================
 * 
 * Este sistema valida los permisos en el frontend y oculta/deshabilita
 * elementos segun los permisos del usuario actual.
 */

(function() {
    'use strict';
    
    // Variables globales
    let permisosUsuario = {};
    let usuarioActual = null;
    let rolUsuario = null;
    let isInitialized = false;
    
    // Configuracion
    const CONFIG = {
        DEBUG: false,  // Deshabilitar debug para evitar spam
        CACHE_DURATION: 300000, // 5 minutos
        AUTO_REFRESH: true
    };
    
    /**
     * Sistema principal de validacion de permisos
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
                
                // Configurar observador para elementos dinamicos
                this.configurarObservadorMutaciones();
                
                isInitialized = true;
                
            } catch (error) {
                console.error('Error inicializando sistema de permisos:', error);
            }
        },
        
        /**
         * Cargar permisos del usuario actual desde el servidor
         */
        async cargarPermisosUsuario() {
            try {
                // Intento 1: endpoint bajo /admin
                let response = await fetch('/admin/obtener_permisos_usuario_actual', {
                    method: 'GET',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (!response.ok) throw new Error('Error HTTP: ' + response.status);
                let data = await response.json();

                // Fallback: completar rol/permisos desde el endpoint global si falta
                if (!data || (!data.rol && !data.role && !data.rol_nombre)) {
                    try {
                        const resp2 = await fetch('/obtener_permisos_usuario_actual', {
                            method: 'GET',
                            credentials: 'include',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        if (resp2.ok) {
                            const data2 = await resp2.json();
                            data = Object.assign({}, data, data2);
                        }
                    } catch (e) { /* ignore */ }
                }

                if (data && data.error) throw new Error(data.error);

                permisosUsuario = (data && data.permisos) ? data.permisos : {};
                usuarioActual = data && data.usuario ? data.usuario : null;
                rolUsuario = ((data && (data.rol || data.role || data.rol_nombre)) || '').toString().toLowerCase();

                // Cachear
                localStorage.setItem('permisos_dropdowns', JSON.stringify({
                    permisos: permisosUsuario,
                    usuario: usuarioActual,
                    rol: rolUsuario,
                    timestamp: Date.now()
                }));

            } catch (error) {
                if (CONFIG.DEBUG) console.warn('Error cargando permisos del servidor, usando cache:', error);
                // Intentar cargar desde cache
                const cached = localStorage.getItem('permisos_dropdowns');
                if (cached) {
                    const data = JSON.parse(cached);
                    if (Date.now() - data.timestamp < CONFIG.CACHE_DURATION) {
                        permisosUsuario = data.permisos;
                        usuarioActual = data.usuario;
                        rolUsuario = (data.rol || '').toString().toLowerCase();
                    }
                }
            }
        },
        
        /**
         * Verificar si el usuario tiene permiso para un dropdown especifico
         */
        tienePermiso(pagina, seccion, boton) {
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) console.warn('Parametros incompletos para verificar permiso');
                return false;
            }
            
            // SOLO SUPERADMIN tienen todos los permisos automaticamente
            if (rolUsuario === 'superadmin') {
                return true;
            }
            
            // Verificar en la estructura de permisos
            if (permisosUsuario[pagina] && 
                permisosUsuario[pagina][seccion] && 
                permisosUsuario[pagina][seccion].includes(boton)) {
                return true;
            }
            
            return false;
        },
        
        /**
         * Aplicar permisos a elementos existentes en la pagina
         */
        aplicarPermisosExistentes() {
            // Permitir a superadmin ver todo
            if (rolUsuario === 'superadmin') {
                return;
            }
            
            // Buscar todos los elementos con atributos de permisos
            const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
            
            elementosConPermisos.forEach((elemento) => {
                this.validarElemento(elemento);
            });
        },
        
        /**
         * Validar un elemento especifico
         */
        validarElemento(elemento) {
            const pagina = elemento.dataset.permisoPagina;
            const seccion = elemento.dataset.permisoSeccion;
            const boton = elemento.dataset.permisoBoton;
            
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) console.warn('Element missing permission attributes:', elemento);
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
         * Ocultar elemento sin permiso
         */
        ocultarElemento(elemento, pagina, seccion, boton) {
            elemento.style.display = 'none';
            elemento.setAttribute('data-sin-permiso', 'true');
            elemento.title = 'Sin permisos para: ' + boton;
            
            // Deshabilitar clicks en elementos sin permiso
            elemento.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                alert('No tienes permisos para acceder a: ' + boton);
                return false;
            });
            
            // Tambien bloquear eventos tactiles
            elemento.addEventListener('touchstart', function(e) {
                e.preventDefault();
                e.stopPropagation();
                alert('No tienes permisos para acceder a: ' + boton);
                return false;
            });
            
            // Agregar clase visual
            elemento.classList.add('sin-permisos');
            elemento.style.pointerEvents = 'none';
            elemento.style.opacity = '0.5';
            elemento.style.cursor = 'not-allowed';
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
         * Configurar observador de mutaciones para elementos dinamicos
         */
        configurarObservadorMutaciones() {
            const observador = new MutationObserver((mutaciones) => {
                mutaciones.forEach((mutacion) => {
                    mutacion.addedNodes.forEach((nodo) => {
                        if (nodo.nodeType === Node.ELEMENT_NODE) {
                            if (nodo.hasAttribute && nodo.hasAttribute('data-permiso-pagina')) {
                                this.validarElemento(nodo);
                            }
                            
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
         * Obtener informacion de estado
         */
        getStatus() {
            return {
                initialized: isInitialized,
                usuario: usuarioActual,
                rol: rolUsuario,
                totalPermisos: Object.keys(permisosUsuario).reduce((total, pagina) => {
                    return total + Object.keys(permisosUsuario[pagina]).reduce((subtotal, seccion) => {
                        return subtotal + permisosUsuario[pagina][seccion].length;
                    }, 0);
                }, 0)
            };
        }
    };
    
    // Auto-inicializar cuando el DOM este listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.PermisosDropdowns.init();
        });
    } else {
        window.PermisosDropdowns.init();
    }
    
    // Auto-recargar permisos periodicamente si esta habilitado
    if (CONFIG.AUTO_REFRESH) {
        setInterval(() => {
            if (isInitialized) {
                window.PermisosDropdowns.recargarPermisos();
            }
        }, CONFIG.CACHE_DURATION);
    }
    
})();
