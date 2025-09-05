/**
 * SISTEMA DE VALIDACIÃ“N DE PERMISOS DE DROPDOWNS
 * =============================================
 * 
 * Este sistema valida los permisos en el frontend y oculta/deshabilita
 * elementos segÃºn los permisos del usuario actual.
 */

(function() {
    'use strict';
    
    // Variables globales
    let permisosUsuario = {};
    let usuarioActual = null;
    let rolUsuario = null;
    let isInitialized = false;
    
    // ConfiguraciÃ³n
    const CONFIG = {
        DEBUG: true,  // Habilitar debug para ver quÃ© estÃ¡ pasando
        CACHE_DURATION: 300000, // 5 minutos
        AUTO_REFRESH: true
    };
    
    /**
     * Sistema principal de validaciÃ³n de permisos
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
                
                // Configurar observador para elementos dinÃ¡micos
                this.configurarObservadorMutaciones();
                
                isInitialized = true;
                
            } catch (error) {
                console.error('âŒ Error inicializando sistema de permisos:', error);
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
                    credentials: 'include',  // Incluir cookies de sesiÃ³n
                    headers: { 'Content-Type': 'application/json' }
                });
                if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
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
                console.warn(' Error cargando permisos del servidor, usando cache:', error);
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
         * Verificar si el usuario tiene permiso para un dropdown especÃ­fico
         */
        tienePermiso(pagina, seccion, boton) {
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) console.warn(' ParÃ¡metros incompletos para verificar permiso');
                return false;
            }
            
            // SOLO SUPERADMIN tienen todos los permisos automÃ¡ticamente
            if (rolUsuario === 'superadmin') {
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
         * Aplicar permisos a elementos existentes en la pÃ¡gina
         */
        aplicarPermisosExistentes() {
            console.log(`ðŸ›¡ï¸ Aplicando permisos. Usuario: ${usuarioActual}, Rol: ${rolUsuario}`);
            console.log(`ðŸ“‹ Permisos disponibles:`, permisosUsuario);
            
            // Permitir a superadmin/admin ver todo
            if (rolUsuario === 'superadmin') {
                console.log(`ðŸ‘‘ Usuario es ${rolUsuario}, permitir todo`);
                return;
            }
            
            // Buscar todos los elementos con atributos de permisos
            const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
            
            console.log(`ðŸŽ¯ Encontrados ${elementosConPermisos.length} elementos con permisos`);
            
            elementosConPermisos.forEach((elemento, index) => {
                const pagina = elemento.dataset.permisoPagina;
                const seccion = elemento.dataset.permisoSeccion;
                const boton = elemento.dataset.permisoBoton;
                console.log(`   ${index + 1}. Elemento: ${pagina} > ${seccion} > ${boton}`);
                this.validarElemento(elemento);
            });
            
            // La validaciÃ³n de elementos de lista ahora se maneja completamente
            // por el bucle genÃ©rico de 'elementosConPermisos'.
            // this.validarElementosListas();
            
            // Log final
            const elementosOcultos = document.querySelectorAll('[data-sin-permiso="true"]');
            console.log(`ðŸš« Total elementos ocultados: ${elementosOcultos.length}`);
        },
        
        /**
         * Validar un elemento especÃ­fico
         */
        validarElemento(elemento) {
            const pagina = elemento.dataset.permisoPagina;
            const seccion = elemento.dataset.permisoSeccion;
            const boton = elemento.dataset.permisoBoton;
            
            if (!pagina || !seccion || !boton) {
                if (CONFIG.DEBUG) {
                    console.warn(`âš ï¸ Element missing permission attributes:`, elemento);
                }
                return;
            }
            
            const tienePermiso = this.tienePermiso(pagina, seccion, boton);
            
            console.log(`ðŸ” Validando: ${pagina} > ${seccion} > ${boton}`);
            console.log(`   Resultado: ${tienePermiso ? 'âœ… PERMITIDO' : 'âŒ DENEGADO'}`);
            console.log(`   Elemento:`, elemento);
            
            if (!tienePermiso) {
                console.log(`   ðŸš« OCULTANDO elemento: ${boton}`);
                this.ocultarElemento(elemento, pagina, seccion, boton);
            } else {
                console.log(`   âœ… MOSTRANDO elemento: ${boton}`);
                this.mostrarElemento(elemento);
            }
        },
        
        /**
         * Validar elementos especÃ­ficos de las listas
         */
        validarElementosListas() {
            // Validar sidebar links de LISTA_DE_MATERIALES - CONTROL DE MATERIAL (13 elementos)
            this.validarSidebarLinks('LISTA_DE_MATERIALES', [
                { selector: 'li.sidebar-link:contains("Control de material de almacÃ©n")', seccion: 'Control de material', boton: 'Control de material de almacÃ©n' },
                { selector: 'li.sidebar-link:contains("Control de salida")', seccion: 'Control de material', boton: 'Control de salida' },
                { selector: 'li.sidebar-link:contains("Control de material retorno")', seccion: 'Control de material', boton: 'Control de material retorno' },
                { selector: 'li.sidebar-link:contains("Recibo y pago del material")', seccion: 'Control de material', boton: 'Recibo y pago del material' },
                { selector: 'li.sidebar-link:contains("Historial de material")', seccion: 'Control de material', boton: 'Historial de material' },
                { selector: 'li.sidebar-link:contains("Estatus de material")', seccion: 'Control de material', boton: 'Estatus de material' },
                { selector: 'li.sidebar-link:contains("Material sustituto")', seccion: 'Control de material', boton: 'Material sustituto' },
                { selector: 'li.sidebar-link:contains("Consultar PEPS")', seccion: 'Control de material', boton: 'Consultar PEPS' },
                { selector: 'li.sidebar-link:contains("Control de Long-Term Inventory")', seccion: 'Control de material', boton: 'Control de Long-Term Inventory' },
                { selector: 'li.sidebar-link:contains("Registro de material real")', seccion: 'Control de material', boton: 'Registro de material real' },
                { selector: 'li.sidebar-link:contains("Historial de inventario real")', seccion: 'Control de material', boton: 'Historial de inventario real' },
                { selector: 'li.sidebar-link:contains("Inventario de rollos SMD")', seccion: 'Control de material', boton: 'Inventario de rollos SMD' },
                { selector: 'li.sidebar-link:contains("Ajuste de nÃºmero de parte")', seccion: 'Control de material', boton: 'Ajuste de nÃºmero de parte' }
            ]);
            
            // Validar sidebar links de LISTA_DE_MATERIALES - CONTROL DE MATERIAL MSL (3 elementos)
            this.validarSidebarLinks('LISTA_DE_MATERIALES', [
                { selector: 'li.sidebar-link:contains("Control total de material")', seccion: 'Control de material MSL', boton: 'Control total de material' },
                { selector: 'li.sidebar-link:contains("Control de entrada y salida de material")', seccion: 'Control de material MSL', boton: 'Control de entrada y salida de material' },
                { selector: 'li.sidebar-link:contains("Estatus de material MSL")', seccion: 'Control de material MSL', boton: 'Estatus de material MSL' }
            ]);
            
            // Validar sidebar links de LISTA_DE_MATERIALES - CONTROL DE REFACCIONES (3 elementos)
            this.validarSidebarLinks('LISTA_DE_MATERIALES', [
                { selector: 'li.sidebar-link:contains("EstÃ¡ndares sobre refacciones")', seccion: 'Control de refacciones', boton: 'EstÃ¡ndares sobre refacciones' },
                { selector: 'li.sidebar-link:contains("Control de recibo de refacciones")', seccion: 'Control de refacciones', boton: 'Control de recibo de refacciones' },
                { selector: 'li.sidebar-link:contains("Control de salida de refacciones")', seccion: 'Control de refacciones', boton: 'Control de salida de refacciones' },
                { selector: 'li.sidebar-link:contains("Estatus de inventario de refacciones")', seccion: 'Control de refacciones', boton: 'Estatus de inventario de refacciones' }
            ]);
            
            // Validar sidebar links de LISTA_INFORMACIONBASICA
            this.validarSidebarLinks('LISTA_INFORMACIONBASICA', [
                { selector: 'li.sidebar-link:contains("GestiÃ³n de departamentos")', seccion: 'InformaciÃ³n bÃ¡sica', boton: 'GestiÃ³n de departamentos' },
                { selector: 'li.sidebar-link:contains("GestiÃ³n de empleados")', seccion: 'InformaciÃ³n bÃ¡sica', boton: 'GestiÃ³n de empleados' },
                { selector: 'li.sidebar-link:contains("GestiÃ³n de proveedores")', seccion: 'InformaciÃ³n bÃ¡sica', boton: 'GestiÃ³n de proveedores' }
            ]);
        },
        
        /**
         * Validar sidebar links para una lista especÃ­fica
         */
        validarSidebarLinks(pagina, elementos) {
            elementos.forEach(({ selector, seccion, boton }) => {
                let elemento = null;

                // Permitir sintaxis :contains("texto") en el selector
                const containsMatch = selector.match(/^(.*):contains\("(.+)"\)$/);
                if (containsMatch) {
                    const baseSelector = containsMatch[1];
                    const texto = containsMatch[2];
                    elemento = Array.from(document.querySelectorAll(baseSelector))
                        .find(el => el.textContent.trim().includes(texto));
                } else {
                    try {
                        elemento = document.querySelector(selector);
                    } catch (error) {
                        console.warn(`Selector invÃ¡lido ignorado: ${selector}`, error);
                        return; // Saltar a siguiente elemento
                    }
                }

                if (elemento && !this.tienePermiso(pagina, seccion, boton)) {
                    this.ocultarElemento(elemento, pagina, seccion, boton);
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
                alert(` No tienes permisos para acceder a: ${boton}`);
                return false;
            });
            
            // TambiÃ©n bloquear eventos tÃ¡ctiles
            elemento.addEventListener('touchstart', function(e) {
                e.preventDefault();
                e.stopPropagation();
                alert(` No tienes permisos para acceder a: ${boton}`);
                return false;
            });
            
            // Agregar clase visual para indicar que estÃ¡ deshabilitado
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
         * Configurar observador de mutaciones para elementos dinÃ¡micos
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
         * Verificar permiso especÃ­fico (para uso en cÃ³digo)
         */
        async verificarPermiso(pagina, seccion, boton) {
            // Primero verificar en cache local
            if (this.tienePermiso(pagina, seccion, boton)) {
                return true;
            }
            
            // Si no estÃ¡ en cache, verificar en servidor
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
         * Obtener informaciÃ³n de estado
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
         * FunciÃ³n de testing para verificar permisos especÃ­ficos
         */
        testPermiso(pagina, seccion, boton) {
            console.log(`ðŸ§ª Testing permiso: ${pagina} > ${seccion} > ${boton}`);
            console.log(`Usuario actual: ${usuarioActual}`);
            console.log(`Rol usuario: ${rolUsuario}`);
            console.log(`Permisos disponibles:`, permisosUsuario);
            
            // Buscar elementos relacionados
            const elementos = document.querySelectorAll(`[data-permiso-pagina="${pagina}"][data-permiso-seccion="${seccion}"][data-permiso-boton="${boton}"]`);
            console.log(`Elementos encontrados con estos permisos:`, elementos);
            
            return this.tienePermiso(pagina, seccion, boton);
        },
        
        /**
         * FunciÃ³n de diagnÃ³stico completo del sistema de permisos
         */
        diagnosticarPermisos() {
            console.log(`
ðŸ” === DIAGNÃ“STICO COMPLETO DE PERMISOS ===
Usuario: ${usuarioActual}
Rol: ${rolUsuario}
Sistema inicializado: ${isInitialized}
Total permisos: ${Object.keys(permisosUsuario).length}
            `);
            
            // Analizar cada pÃ¡gina
            Object.keys(permisosUsuario).forEach(pagina => {
                console.log(`\nðŸ“„ PÃGINA: ${pagina}`);
                Object.keys(permisosUsuario[pagina]).forEach(seccion => {
                    console.log(`  ðŸ“‚ SECCIÃ“N: ${seccion}`);
                    permisosUsuario[pagina][seccion].forEach(boton => {
                        console.log(`    âœ… BOTÃ“N: ${boton}`);
                    });
                });
            });
            
            // Buscar elementos con atributos de permisos que no estÃ©n funcionando
            const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
            console.log(`\nðŸŽ¯ ELEMENTOS EN DOM CON PERMISOS: ${elementosConPermisos.length}`);
            
            elementosConPermisos.forEach((elemento, index) => {
                const pagina = elemento.dataset.permisoPagina;
                const seccion = elemento.dataset.permisoSeccion;
                const boton = elemento.dataset.permisoBoton;
                const tienePermiso = this.tienePermiso(pagina, seccion, boton);
                const visible = elemento.style.display !== 'none';
                
                console.log(`${index + 1}. ${pagina} > ${seccion} > ${boton}`);
                console.log(`   Permiso: ${tienePermiso ? 'âœ…' : 'âŒ'} | Visible: ${visible ? 'ðŸ‘€' : 'ðŸ™ˆ'}`);
                
                if (!tienePermiso && visible) {
                    console.warn(`   âš ï¸ PROBLEMA: Element should be hidden but is visible!`);
                    elemento.style.border = '2px solid red';
                }
            });
        },
        
        /**
         * Verificar permiso antes de ejecutar una funciÃ³n
         */
        verificarPermisoAntesFuncion(pagina, seccion, boton, funcionCallback) {
            if (!this.tienePermiso(pagina, seccion, boton)) {
                alert(` No tienes permisos para acceder a: ${boton}`);
                console.warn(`ðŸš« Acceso denegado a funciÃ³n: ${pagina} > ${seccion} > ${boton}`);
                return false;
            }
            
            // Si tiene permiso, ejecutar la funciÃ³n
            if (typeof funcionCallback === 'function') {
                funcionCallback();
            }
            return true;
        },
        
        /**
         * Envolver funciÃ³n existente con verificaciÃ³n de permisos
         */
        protegerFuncion(nombreFuncion, pagina, seccion, boton) {
            const funcionOriginal = window[nombreFuncion];
            
            if (typeof funcionOriginal === 'function') {
                window[nombreFuncion] = (...args) => {
                    if (this.tienePermiso(pagina, seccion, boton)) {
                        return funcionOriginal.apply(this, args);
                    } else {
                        alert(` No tienes permisos para acceder a: ${boton}`);
                        console.warn(`ðŸš« Acceso denegado a funciÃ³n: ${nombreFuncion}`);
                        return false;
                    }
                };
                
            }
        }
    };
    
    // Auto-inicializar cuando el DOM estÃ© listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.PermisosDropdowns.init();
        });
    } else {
        window.PermisosDropdowns.init();
    }
    
    // Auto-recargar permisos periÃ³dicamente si estÃ¡ habilitado
    if (CONFIG.AUTO_REFRESH) {
        setInterval(() => {
            if (isInitialized) {
                window.PermisosDropdowns.recargarPermisos();
            }
        }, CONFIG.CACHE_DURATION);
    }
    
    // Funciones globales para debugging
    window.debugPermisos = function() {
        if (window.PermisosDropdowns) {
            window.PermisosDropdowns.diagnosticarPermisos();
        } else {
            console.error('âŒ Sistema de permisos no disponible');
        }
    };
    
    window.testPermiso = function(pagina, seccion, boton) {
        if (window.PermisosDropdowns) {
            return window.PermisosDropdowns.testPermiso(pagina, seccion, boton);
        } else {
            console.error('âŒ Sistema de permisos no disponible');
            return false;
        }
    };
    
    window.recargarPermisos = function() {
        if (window.PermisosDropdowns) {
            window.PermisosDropdowns.recargarPermisos();
        } else {
            console.error('âŒ Sistema de permisos no disponible');
        }
    };
    
})();



