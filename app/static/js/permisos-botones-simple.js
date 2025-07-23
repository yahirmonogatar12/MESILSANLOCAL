/**
 * Sistema de Permisos Simplificado para Debug
 * Versión sin MutationObserver para evitar bucles infinitos
 */

class PermisosManagerSimple {
    constructor() {
        this.permisosUsuario = {};
        this.inicializado = false;
        this.debug = true;
    }

    /**
     * Inicializar el sistema de permisos
     */
    async inicializar() {
        try {
            this.log('🚀 Iniciando sistema de permisos simplificado...');
            await this.cargarPermisosUsuario();
            
            // Pequeño delay para evitar problemas de carga
            setTimeout(() => {
                this.aplicarPermisos();
                this.inicializado = true;
                this.log('✅ Sistema de permisos inicializado correctamente');
            }, 100);
            
        } catch (error) {
            console.error('❌ Error inicializando sistema de permisos:', error);
        }
    }

    /**
     * Cargar permisos del usuario actual desde el servidor
     */
    async cargarPermisosUsuario() {
        try {
            this.log('📡 Cargando permisos del usuario...');
            
            // Usar endpoint de debug si no hay sesión
            const endpoint = '/admin/verificar_permisos_usuario';
            const response = await fetch(endpoint);
            
            if (!response.ok) {
                this.log(`⚠️ Endpoint principal falló (${response.status}), usando debug...`);
                const debugResponse = await fetch('/admin/test_permisos_debug');
                if (debugResponse.ok) {
                    const debugData = await debugResponse.json();
                    // Convertir formato de debug a formato esperado
                    this.permisosUsuario = this.convertirFormatoDebug(debugData.permisos);
                } else {
                    throw new Error('Ambos endpoints fallaron');
                }
            } else {
                this.permisosUsuario = await response.json();
            }
            
            this.log('📋 Permisos cargados:', Object.keys(this.permisosUsuario).length, 'páginas');
        } catch (error) {
            console.error('❌ Error cargando permisos:', error);
            this.permisosUsuario = {};
        }
    }

    /**
     * Convertir formato de debug a formato estructurado
     */
    convertirFormatoDebug(permisosArray) {
        const permisos = {};
        
        permisosArray.forEach(item => {
            const { pagina, seccion, boton } = item;
            
            if (!permisos[pagina]) {
                permisos[pagina] = {};
            }
            
            if (!permisos[pagina][seccion]) {
                permisos[pagina][seccion] = [];
            }
            
            permisos[pagina][seccion].push(boton);
        });
        
        return permisos;
    }

    /**
     * Aplicar permisos a todos los elementos en la página
     */
    aplicarPermisos() {
        const elementosConPermisos = document.querySelectorAll('[data-permiso-pagina]');
        
        this.log(`🔍 Procesando ${elementosConPermisos.length} elementos con permisos`);
        
        let habilitados = 0;
        let deshabilitados = 0;
        
        elementosConPermisos.forEach(elemento => {
            try {
                const tienePermiso = this.verificarPermiso(elemento);
                
                if (tienePermiso) {
                    this.habilitarElemento(elemento);
                    habilitados++;
                } else {
                    this.deshabilitarElemento(elemento);
                    deshabilitados++;
                }
            } catch (error) {
                this.log('❌ Error procesando elemento:', error, elemento);
            }
        });
        
        this.log(`📊 Resultado: ${habilitados} habilitados, ${deshabilitados} deshabilitados`);
    }

    /**
     * Verificar si un elemento tiene permiso
     */
    verificarPermiso(elemento) {
        const pagina = elemento.getAttribute('data-permiso-pagina');
        const seccion = elemento.getAttribute('data-permiso-seccion');
        const boton = elemento.getAttribute('data-permiso-boton');

        if (!pagina || !seccion || !boton) {
            this.log('⚠️ Elemento sin permisos completos:', elemento);
            return true; // Por defecto permitir si no tiene atributos
        }

        return this.usuarioTienePermiso(pagina, seccion, boton);
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
        // Solo visual, sin cambios complejos que causen bucles
        elemento.classList.add('permiso-denegado');
        elemento.style.opacity = '0.5';
        elemento.style.pointerEvents = 'none';
        elemento.title = 'No tienes permisos para esta funcionalidad';
        
        if (elemento.tagName === 'BUTTON') {
            elemento.disabled = true;
        }
    }

    /**
     * Habilitar un elemento
     */
    habilitarElemento(elemento) {
        elemento.classList.remove('permiso-denegado');
        elemento.style.opacity = '';
        elemento.style.pointerEvents = '';
        
        if (elemento.title === 'No tienes permisos para esta funcionalidad') {
            elemento.title = '';
        }
        
        if (elemento.tagName === 'BUTTON') {
            elemento.disabled = false;
        }
    }

    /**
     * Función de logging
     */
    log(...args) {
        if (this.debug) {
        }
    }

    /**
     * Replicar permisos manualmente (para contenido cargado por AJAX)
     */
    reaplicarPermisos() {
        if (this.inicializado) {
            this.log('🔄 Re-aplicando permisos...');
            this.aplicarPermisos();
        }
    }
}

// Crear instancia global
window.PermisosManagerSimple = new PermisosManagerSimple();

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.PermisosManagerSimple.inicializar();
});

// Agregar estilos CSS simplificados
const style = document.createElement('style');
style.textContent = `
    .permiso-denegado {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
        filter: grayscale(50%);
    }
`;
document.head.appendChild(style);
