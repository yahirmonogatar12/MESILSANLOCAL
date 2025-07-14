// ===============================================
// MENÚ MÓVIL ESPECÍFICO PARA LISTAS
// ===============================================

class MobileListas {
    constructor() {
        this.isMobile = window.innerWidth <= 768;
        
        if (this.isMobile) {
            this.init();
        }
    }

    init() {
        console.log('📱 Inicializando menú móvil de listas...');
        this.createMobileMenu();
        this.createModal();
        this.handleResize();
    }

    createMobileMenu() {
        // Crear un menú flotante específico para móvil
        const mobileMenuHTML = `
            <div class="mobile-listas-menu" id="mobileListas">
                <button class="mobile-listas-toggle" id="toggleMobileListas">
                    📋 Listas
                </button>
                <div class="mobile-listas-dropdown" id="mobileListasDropdown" style="display: none;">
                    <div class="mobile-lista-item" data-lista="informacion-basica">📋 Información Básica</div>
                    <div class="mobile-lista-item" data-lista="control-material">🔧 Control de Material</div>
                    <div class="mobile-lista-item" data-lista="control-produccion">🏭 Control de Producción</div>
                    <div class="mobile-lista-item" data-lista="control-proceso">⚙️ Control de Proceso</div>
                    <div class="mobile-lista-item" data-lista="control-calidad">✅ Control de Calidad</div>
                    <div class="mobile-lista-item" data-lista="control-resultados">📊 Control de Resultados</div>
                    <div class="mobile-lista-item" data-lista="control-reporte">📄 Control de Reporte</div>
                    <div class="mobile-lista-item" data-lista="configuracion">⚙️ Configuración</div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', mobileMenuHTML);
        this.setupMenuEvents();
    }

    setupMenuEvents() {
        const toggle = document.getElementById('toggleMobileListas');
        const dropdown = document.getElementById('mobileListasDropdown');
        const items = document.querySelectorAll('.mobile-lista-item');

        // Toggle del menú
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = dropdown.style.display !== 'none';
            dropdown.style.display = isVisible ? 'none' : 'block';
        });

        // Cerrar menú al hacer click fuera - SOLO EN MÓVIL
        this.globalClickListener = (e) => {
            // VERIFICACIÓN MÚLTIPLE para asegurar que solo funcione en móvil
            if (!this.isMobile || window.innerWidth > 768) return;
            
            // Verificar que el dropdown existe y está visible
            if (!dropdown || dropdown.style.display === 'none') return;
            
            // No cerrar si el click es en el toggle o dropdown mismo
            if (toggle.contains(e.target) || dropdown.contains(e.target)) return;
            
            dropdown.style.display = 'none';
        };
        
        document.addEventListener('click', this.globalClickListener);

        // Eventos de los elementos de lista
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const lista = item.getAttribute('data-lista');
                const titulo = item.textContent;
                
                console.log('📋 Seleccionada lista:', lista, titulo);
                this.openListaModal(lista, titulo);
                dropdown.style.display = 'none';
            });
        });
    }

    createModal() {
        const modalHTML = `
            <div class="mobile-lista-modal-new" id="mobileListaModalNew">
                <div class="mobile-lista-content-new">
                    <div class="mobile-lista-header-new">
                        <h3 class="mobile-lista-title-new">Lista</h3>
                        <button class="mobile-lista-close-new" id="closeMobileModalNew">×</button>
                    </div>
                    <div class="mobile-lista-body-new" id="mobileListaBodyNew">
                        <p style="text-align: center; padding: 40px; color: white;">Cargando...</p>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        this.modal = document.getElementById('mobileListaModalNew');
        this.modalBody = document.getElementById('mobileListaBodyNew');
        
        // Event listeners del modal
        document.getElementById('closeMobileModalNew').addEventListener('click', () => {
            this.closeModal();
        });

        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    }

    async openListaModal(lista, titulo) {
        console.log('🔄 Abriendo modal para:', lista);
        
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
            console.log('📡 Respuesta:', response.status);
            
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
    }

    closeModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    setTitle(titulo) {
        const titleElement = document.querySelector('.mobile-lista-title-new');
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
            const menu = document.getElementById('mobileListas');
            if (menu) {
                menu.style.display = this.isMobile ? 'block' : 'none';
            }
            
            // Cerrar modal si cambió a desktop
            if (wasMobile && !this.isMobile && this.modal && this.modal.style.display === 'flex') {
                this.closeModal();
            }
        });
    }
    
    // Método para limpiar event listeners
    cleanup() {
        if (this.globalClickListener) {
            document.removeEventListener('click', this.globalClickListener);
            this.globalClickListener = null;
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // SOLO en móvil y si no existe ya
    if (window.innerWidth <= 768 && !window.mobileListas) {
        window.mobileListas = new MobileListas();
        console.log('✅ Menú móvil de listas inicializado');
    }
});

// También verificar en resize - CON LIMPIEZA
window.addEventListener('resize', () => {
    if (window.innerWidth <= 768 && !window.mobileListas) {
        window.mobileListas = new MobileListas();
    } else if (window.innerWidth > 768 && window.mobileListas) {
        // Limpiar en desktop
        window.mobileListas.cleanup();
        window.mobileListas = null;
    }
});
