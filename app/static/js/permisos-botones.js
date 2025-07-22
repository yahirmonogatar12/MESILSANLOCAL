/**
 * Sistema de Permisos de Botones/Dropdowns
 * Maneja la habilitación/deshabilitación de elementos basado en permisos del usuario
 */

class PermisosManager {
    constructor() {
        this.permisosUsuario = {};
        this.inicializado = false;
        this.debug = false;  // Cambiar a false para reducir logs
        this.elementosProcesados = new WeakSet();  // Evitar procesar el mismo elemento múltiples veces
    }

    /**
     * Inicializar el sistema de permisos
     */
    async inicializar() {
        try {
            await this.cargarPermisosUsuario();
            this.aplicarPermisos();
            
            // Solo configurar observer si es necesario (contenido dinámico)
            // this.configurarObservadores();  // COMENTADO temporalmente para debuggear
            
            this.inicializado = true;
            this.log('✅ Sistema de permisos inicializado correctamente');
        } catch (error) {
            console.error('❌ Error inicializando sistema de permisos:', error);
        }
    }

    /**
     * Cargar permisos del usuario actual desde el servidor
     */
    async cargarPermisosUsuario() {
        try {
            const response = await fetch('/admin/verificar_permisos_usuario');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.permisosUsuario = await response.json();
            this.log('📋 Permisos del usuario cargados:', this.permisosUsuario);
        } catch (error) {
            console.error('❌ Error cargando permisos:', error);
            this.permisosUsuario = {};
        }
    }

    /**
     * Aplicar permisos a todos los elementos en la página
     */
    aplicarPermisos() {
        // Buscar todos los elementos con atributos de permiso
        const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
        
        this.log(`🔍 Encontrados ${elementosConPermisos.length} elementos con permisos`);
        
        elementosConPermisos.forEach(elemento => {
            if (!this.elementosProcesados.has(elemento)) {
                this.verificarYAplicarPermiso(elemento);
                this.elementosProcesados.add(elemento);
            }
        });
    }

    /**
     * Verificar y aplicar permiso a un elemento específico
     */
    verificarYAplicarPermiso(elemento) {
        const pagina = elemento.getAttribute('data-permiso-pagina');
        const seccion = elemento.getAttribute('data-permiso-seccion');
        const boton = elemento.getAttribute('data-permiso-boton');

        if (!pagina || !seccion || !boton) {
            this.log('⚠️ Elemento sin permisos completos:', elemento);
            return;
        }

        const tienePermiso = this.usuarioTienePermiso(pagina, seccion, boton);
        
        if (tienePermiso) {
            this.habilitarElemento(elemento);
        } else {
            this.deshabilitarElemento(elemento);
        }

        this.log(`${tienePermiso ? '✅' : '❌'} ${pagina}>${seccion}>${boton}`, elemento);
    }

    /**
     * Verificar si el usuario tiene un permiso específico
     */
    usuarioTienePermiso(pagina, seccion, boton) {
        if (!this.permisosUsuario[pagina]) {
            return false;
        }
        
        if (!this.permisosUsuario[pagina][seccion]) {
            return false;
        }
        
        return this.permisosUsuario[pagina][seccion].includes(boton);
    }

    /**
     * Deshabilitar un elemento
     */
    deshabilitarElemento(elemento) {
        // Evitar procesar si ya está deshabilitado
        if (elemento.dataset.permisoBloqueado === 'true') {
            return;
        }
        
        // Agregar clase visual
        elemento.classList.add('disabled', 'permiso-denegado');
        
        // Deshabilitar según el tipo de elemento
        if (elemento.tagName === 'BUTTON') {
            elemento.disabled = true;
        } else if (elemento.tagName === 'A') {
            elemento.style.pointerEvents = 'none';
            elemento.setAttribute('aria-disabled', 'true');
        } else if (elemento.tagName === 'LI') {
            elemento.style.pointerEvents = 'none';
            elemento.style.opacity = '0.5';
            elemento.setAttribute('aria-disabled', 'true');
        }

        // Remover eventos de click
        this.removerEventosClick(elemento);
        
        // Agregar tooltip informativo
        elemento.title = 'No tienes permisos para acceder a esta funcionalidad';
    }

    /**
     * Habilitar un elemento
     */
    habilitarElemento(elemento) {
        // Remover clases de deshabilitado
        elemento.classList.remove('disabled', 'permiso-denegado');
        
        // Habilitar según el tipo de elemento
        if (elemento.tagName === 'BUTTON') {
            elemento.disabled = false;
        } else if (elemento.tagName === 'A') {
            elemento.style.pointerEvents = '';
            elemento.removeAttribute('aria-disabled');
        } else if (elemento.tagName === 'LI') {
            elemento.style.pointerEvents = '';
            elemento.style.opacity = '';
            elemento.removeAttribute('aria-disabled');
        }

        // Limpiar tooltip
        if (elemento.title === 'No tienes permisos para acceder a esta funcionalidad') {
            elemento.title = '';
        }
    }

    /**
     * Remover eventos de click de un elemento
     */
    removerEventosClick(elemento) {
        // En lugar de clonar, simplemente agregar el evento de bloqueo
        elemento.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.mostrarMensajePermisoDenegado();
            return false;
        }, { capture: true });
        
        // Marcar que ya tiene el evento bloqueador
        elemento.dataset.permisoBloqueado = 'true';
    }

    /**
     * Mostrar mensaje de permiso denegado
     */
    mostrarMensajePermisoDenegado() {
        // Mostrar notificación o modal
        if (window.Swal) {
            Swal.fire({
                icon: 'warning',
                title: 'Acceso Denegado',
                text: 'No tienes permisos para acceder a esta funcionalidad.',
                confirmButtonText: 'Entendido'
            });
        } else {
            alert('No tienes permisos para acceder a esta funcionalidad.');
        }
    }

    /**
     * Configurar observadores para contenido dinámico
     */
    configurarObservadores() {
        // Observer más específico para evitar bucles infinitos
        const observer = new MutationObserver((mutations) => {
            let hayNuevosElementos = false;
            
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Solo procesar si tiene atributos de permiso y no ha sido procesado
                        if (node.hasAttribute && node.hasAttribute('data-permiso-pagina') && 
                            !this.elementosProcesados.has(node)) {
                            this.verificarYAplicarPermiso(node);
                            this.elementosProcesados.add(node);
                            hayNuevosElementos = true;
                        }
                        
                        // Verificar nodos hijos nuevos
                        const elementosConPermisos = node.querySelectorAll && node.querySelectorAll('[data-permiso-pagina]');
                        if (elementosConPermisos) {
                            elementosConPermisos.forEach(elemento => {
                                if (!this.elementosProcesados.has(elemento)) {
                                    this.verificarYAplicarPermiso(elemento);
                                    this.elementosProcesados.add(elemento);
                                    hayNuevosElementos = true;
                                }
                            });
                        }
                    }
                });
            });
            
            if (hayNuevosElementos) {
                this.log('🔄 Nuevos elementos procesados por Observer');
            }
        });

        // Observar solo cambios en elementos específicos, no en atributos o texto
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false,  // No observar cambios de atributos
            characterData: false  // No observar cambios de texto
        });

        this.log('👁️ Observer optimizado configurado');
    }

    /**
     * Refrescar permisos (útil si cambian durante la sesión)
     */
    async refrescarPermisos() {
        try {
            await this.cargarPermisosUsuario();
            this.aplicarPermisos();
            this.log('🔄 Permisos refrescados');
        } catch (error) {
            console.error('❌ Error refrescando permisos:', error);
        }
    }

    /**
     * Función de logging con debug
     */
    log(mensaje, objeto = null) {
        if (this.debug) {
            if (objeto) {
                console.log(`[PermisosManager] ${mensaje}`, objeto);
            } else {
                console.log(`[PermisosManager] ${mensaje}`);
            }
        }
    }

    /**
     * Activar/desactivar debug
     */
    setDebug(estado) {
        this.debug = estado;
        this.log(`Debug ${estado ? 'activado' : 'desactivado'}`);
    }
}

// Crear instancia global
window.PermisosManager = new PermisosManager();

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.PermisosManager.inicializar();
});

// Agregar estilos CSS para elementos deshabilitados
const style = document.createElement('style');
style.textContent = `
    .permiso-denegado {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
        filter: grayscale(50%);
    }
    
    .permiso-denegado:hover {
        opacity: 0.5 !important;
        transform: none !important;
    }
    
    .sidebar-link.permiso-denegado {
        background-color: #f8f9fa !important;
        color: #6c757d !important;
    }
    
    .sidebar-link.permiso-denegado:hover {
        background-color: #f8f9fa !important;
        color: #6c757d !important;
    }
`;
document.head.appendChild(style);
