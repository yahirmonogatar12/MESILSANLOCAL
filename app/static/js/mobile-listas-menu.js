// ===============================================
// MENÚ MÓVIL ESPECÍFICO PARA LISTAS
// ===============================================


// Prefijo único para evitar conflictos de IDs/clases
const MLM_PREFIX = 'mlm-';

class MobileListas {
    constructor() {
        this.isMobile = window.innerWidth <= 768;
        
        // VERIFICACIÓN ESTRICTA - Solo inicializar en móvil
        if (this.isMobile) {
            this.init();
        } else {
        }
    }

    init() {
        this.createMobileMenu();
        this.createModal();
        this.handleResize();
    }

    createMobileMenu() {
        // Eliminar menú anterior si existe (evita duplicados)
        const oldMenu = document.getElementById(MLM_PREFIX + 'mobileListas');
        if (oldMenu) oldMenu.remove();

        // Crear un menú flotante específico para móvil
        const mobileMenuHTML = `
            <div class="mobile-listas-menu" id="${MLM_PREFIX}mobileListas" aria-label="Menú móvil de listas" role="navigation">
                <button class="mobile-listas-toggle" id="${MLM_PREFIX}toggleMobileListas" aria-haspopup="true" aria-controls="${MLM_PREFIX}mobileListasDropdown" aria-expanded="false">
                    📋 Listas
                </button>
                <div class="mobile-listas-dropdown" id="${MLM_PREFIX}mobileListasDropdown" style="display: none;">
                    <div class="mobile-lista-item" data-lista="informacion-basica" tabindex="0">📋 Información Básica</div>
                    <div class="mobile-lista-item" data-lista="control-material" tabindex="0">🔧 Control de Material</div>
                    <div class="mobile-lista-item" data-lista="control-produccion" tabindex="0">🏭 Control de Producción</div>
                    <div class="mobile-lista-item" data-lista="control-proceso" tabindex="0">⚙️ Control de Proceso</div>
                    <div class="mobile-lista-item" data-lista="control-calidad" tabindex="0">✅ Control de Calidad</div>
                    <div class="mobile-lista-item" data-lista="control-resultados" tabindex="0">📊 Control de Resultados</div>
                    <div class="mobile-lista-item" data-lista="control-reporte" tabindex="0">📄 Control de Reporte</div>
                    <div class="mobile-lista-item" data-lista="configuracion" tabindex="0">⚙️ Configuración</div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', mobileMenuHTML);
        this.setupMenuEvents();
    }

    setupMenuEvents() {
        const toggle = document.getElementById(MLM_PREFIX + 'toggleMobileListas');
        const dropdown = document.getElementById(MLM_PREFIX + 'mobileListasDropdown');
        const items = dropdown.querySelectorAll('.mobile-lista-item');

        // Toggle del menú
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = dropdown.style.display !== 'none';
            dropdown.style.display = isVisible ? 'none' : 'block';
            toggle.setAttribute('aria-expanded', !isVisible);
        });

        // Cerrar menú al hacer click fuera - SOLO EN MÓVIL
        this.globalClickListener = (e) => {
            if (!this.isMobile || window.innerWidth > 768) return;
            if (!dropdown || dropdown.style.display === 'none') return;
            if (toggle.contains(e.target) || dropdown.contains(e.target)) return;
            dropdown.style.display = 'none';
            toggle.setAttribute('aria-expanded', 'false');
        };
        document.addEventListener('click', this.globalClickListener);

        // Eventos de los elementos de lista
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const lista = item.getAttribute('data-lista');
                const titulo = item.textContent;
                this.openListaModal(lista, titulo);
                dropdown.style.display = 'none';
                toggle.setAttribute('aria-expanded', 'false');
            });
            // Accesibilidad: permitir enter/space para seleccionar
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    item.click();
                }
            });
        });
    }

    createModal() {
        // Eliminar modal anterior si existe (evita duplicados)
        const oldModal = document.getElementById(MLM_PREFIX + 'mobileListaModalNew');
        if (oldModal) oldModal.remove();

        const modalHTML = `
            <div class="mobile-lista-modal-new" id="${MLM_PREFIX}mobileListaModalNew" role="dialog" aria-modal="true" aria-labelledby="${MLM_PREFIX}mobileListaTitleNew">
                <div class="mobile-lista-content-new">
                    <div class="mobile-lista-header-new">
                        <h3 class="mobile-lista-title-new" id="${MLM_PREFIX}mobileListaTitleNew">Lista</h3>
                        <button class="mobile-lista-close-new" id="${MLM_PREFIX}closeMobileModalNew" aria-label="Cerrar modal">×</button>
                    </div>
                    <div class="mobile-lista-body-new" id="${MLM_PREFIX}mobileListaBodyNew">
                        <p style="text-align: center; padding: 40px; color: white;">Cargando...</p>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById(MLM_PREFIX + 'mobileListaModalNew');
        this.modalBody = document.getElementById(MLM_PREFIX + 'mobileListaBodyNew');

        // Event listeners del modal
        document.getElementById(MLM_PREFIX + 'closeMobileModalNew').addEventListener('click', () => {
            this.closeModal();
        });
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }

    async openListaModal(lista, titulo) {
        
        // Mapear lista a URL
        const urlMap = {
            'informacion-basica': '/listas/LISTA_INFORMACIONBASICA.html',
            'control-material': '/listas/LISTA_DE_MATERIALES.html',
            'control-produccion': '/listas/LISTA_CONTROLDEPRODUCCION.html',
            'control-proceso': '/listas/LISTA_CONTROL_DE_PROCESO.html',
            'control-calidad': '/listas/LISTA_CONTROL_DE_CALIDAD.html',
            'control-resultados': '/listas/LISTA_DE_CONTROL_DE_RESULTADOS.html',
            'control-reporte': '/listas/LISTA_DE_CONTROL_DE_REPORTE.html',
            'configuracion': '/listas/LISTA_DE_CONFIGPG.html'
        };

        const url = urlMap[lista];
        
        if (url) {
            await this.loadContent(url, titulo);
        } else {
            this.showTestContent(titulo);
        }
    }

    async loadContent(url, titulo) {
        try {
            this.showModal();
            this.setTitle(titulo);
            this.modalBody.innerHTML = '<div style="text-align: center; padding: 40px; color: white;">Cargando...</div>';
            
            const response = await fetch(url);
            
            if (response.ok) {
                const html = await response.text();
                this.modalBody.innerHTML = `<div style="color: white; padding: 20px;">${html}</div>`;
            } else {
                throw new Error(`Error ${response.status}`);
            }
            
        } catch (error) {
            console.error('❌ Error:', error);
            this.showTestContent(titulo);
        }
    }

    showTestContent(titulo) {
        this.showModal();
        this.setTitle(titulo);
        
        this.modalBody.innerHTML = `
            <div style="padding: 20px; color: white;">
                <h4 style="color: #3498db; margin-bottom: 20px;">📋 ${titulo}</h4>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin: 10px 0;">
                    <h5 style="color: #2ecc71;">✅ Lista Cargada</h5>
                    <p>Esta es la lista de <strong>${titulo}</strong></p>
                    <p>El contenido específico se cargaría desde el servidor.</p>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin: 10px 0;">
                    <h5 style="color: #2ecc71;">⚙️ Funcionalidades Disponibles</h5>
                    <ul style="margin: 10px 0;">
                        <li>Ver elementos de la lista</li>
                        <li>Filtrar contenido</li>
                        <li>Buscar elementos</li>
                        <li>Exportar datos</li>
                    </ul>
                </div>
                <button onclick="window.mobileListas.closeModal()" style="background: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 6px; margin-top: 20px; cursor: pointer; font-size: 16px;">
                    Cerrar
                </button>
            </div>
        `;
    }

    showModal() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        // Accesibilidad: enfocar el modal
        setTimeout(() => {
            this.modal.focus && this.modal.focus();
        }, 10);
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    setTitle(titulo) {
        const titleElement = document.getElementById(MLM_PREFIX + 'mobileListaTitleNew');
        if (titleElement) {
            titleElement.textContent = titulo;
        }
    }

    handleResize() {
        window.addEventListener('resize', () => {
            const wasMobile = this.isMobile;
            this.isMobile = window.innerWidth <= 768;
            // Limpiar listener global si cambió a desktop
            if (wasMobile && !this.isMobile && this.globalClickListener) {
                document.removeEventListener('click', this.globalClickListener);
                this.globalClickListener = null;
            }
            // Mostrar/ocultar menú según el tamaño
            const menu = document.getElementById(MLM_PREFIX + 'mobileListas');
            if (menu) {
                menu.style.display = this.isMobile ? 'block' : 'none';
            }
            // Cerrar modal si cambió a desktop
            if (wasMobile && !this.isMobile && this.modal && this.modal.style.display === 'flex') {
                this.closeModal();
            }
        });
    }
    
    // Método para limpiar event listeners y DOM
    cleanup() {
        // Eliminar listener global
        if (this.globalClickListener) {
            document.removeEventListener('click', this.globalClickListener);
            this.globalClickListener = null;
        }
        // Eliminar menú del DOM
        const menu = document.getElementById(MLM_PREFIX + 'mobileListas');
        if (menu) menu.remove();
        // Eliminar modal del DOM
        const modal = document.getElementById(MLM_PREFIX + 'mobileListaModalNew');
        if (modal) modal.remove();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // SOLO en móvil y si no existe ya
    if (window.innerWidth <= 768 && !window.mobileListas) {
        window.mobileListas = new MobileListas();
    }
});

// Variable para prevenir múltiples ejecuciones rápidas en resize
let resizeTimeout;

// También verificar en resize - CON LIMPIEZA y DEBOUNCE
window.addEventListener('resize', () => {
    // Limpiamos el timeout anterior si existe
    if (resizeTimeout) clearTimeout(resizeTimeout);
    
    // Establecemos un nuevo timeout para debounce
    resizeTimeout = setTimeout(() => {
        
        if (window.innerWidth <= 768 && !window.mobileListas) {
            // Cambio a móvil: inicializar
            window.mobileListas = new MobileListas();
        } else if (window.innerWidth > 768 && window.mobileListas) {
            // Cambio a desktop: limpiar
            window.mobileListas.cleanup();
            window.mobileListas = null;
            
            // Forzar reinicio del fix de dropdowns
            if (typeof initBalancedDropdowns === 'function') {
                setTimeout(() => initBalancedDropdowns(), 100);
            }
        }
    }, 250); // Esperar 250ms después del último evento resize
});