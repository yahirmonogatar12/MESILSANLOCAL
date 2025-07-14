// ===============================================
// MENÚ HAMBURGUESA ESPECÍFICO PARA LISTAS MÓVIL
// ===============================================

class MobileListsHamburger {
    constructor() {
        this.isMobile = window.innerWidth <= 768;
        this.menuOpen = false;
        this.currentListTitle = 'Listas';
        
        // SOLO inicializar si estamos en móvil
        if (this.isMobile) {
            this.init();
            this.interceptListsContent(); // Solo interceptar en móvil
        }
        
        this.handleResize();
    }

    init() {
        console.log('📱 Inicializando menú hamburguesa de listas...');
        this.createMobileListsMenu();
        // interceptListsContent se llama desde el constructor
    }

    createMobileListsMenu() {
        // Crear el HTML del menú hamburguesa de listas
        const mobileListsHTML = `
            <!-- Botón hamburguesa flotante -->
            <button class="mobile-lists-hamburger" id="mobileListsToggle">
                <span class="hamburger-icon">▲</span>
            </button>
            
            <!-- Overlay -->
            <div class="mobile-lists-overlay" id="mobileListsOverlay"></div>
            
            <!-- Menú desplegable -->
            <div class="mobile-lists-menu" id="mobileListsMenu">
                <div class="mobile-lists-header">
                    <span id="mobileListsTitle">${this.currentListTitle}</span>
                    <button class="mobile-lists-close" id="mobileListsClose">×</button>
                </div>
                <div class="mobile-lists-content" id="mobileListsContent">
                    <p style="text-align: center; padding: 40px; color: white;">No hay listas cargadas</p>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', mobileListsHTML);
        this.setupEventListeners();
    }

    setupEventListeners() {
        const toggle = document.getElementById('mobileListsToggle');
        const close = document.getElementById('mobileListsClose');
        const overlay = document.getElementById('mobileListsOverlay');

        // Abrir menú
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openMenu();
        });

        // Cerrar menú
        close.addEventListener('click', () => {
            this.closeMenu();
        });

        overlay.addEventListener('click', () => {
            this.closeMenu();
        });

        // Cerrar con tecla ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.menuOpen) {
                this.closeMenu();
            }
        });
    }

    interceptListsContent() {
        // Observar cuando se cargan listas para convertirlas al formato móvil
        const observer = new MutationObserver((mutations) => {
            // SOLO procesar si estamos en móvil
            if (!this.isMobile) return;
            
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        const sidebar = node.querySelector('.app-sidebar');
                        if (sidebar) {
                            console.log('🔄 Sidebar detectado, convirtiendo a móvil...');
                            this.convertSidebarToMobile(sidebar);
                        }
                        
                        // También buscar si el nodo mismo es un sidebar
                        if (node.classList && node.classList.contains('app-sidebar')) {
                            console.log('🔄 Sidebar directo detectado, convirtiendo a móvil...');
                            this.convertSidebarToMobile(node);
                        }
                        // Buscar contenido de sidebar específico
                        if (node.classList && node.classList.contains('sidebar-content')) {
                            console.log('🔄 Sidebar-content detectado, ocultando en móvil...');
                            node.style.display = 'none';
                        }
                        
                        // Buscar cualquier elemento con ID que contenga 'sidebar'
                        if (node.id && node.id.includes('sidebar')) {
                            console.log('🔄 Elemento sidebar detectado por ID, ocultando en móvil...');
                            node.style.display = 'none';
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // También revisar si ya existe contenido al inicializar
        setTimeout(() => {
            const existingSidebar = document.querySelector('.app-sidebar');
            if (existingSidebar) {
                console.log('🔄 Sidebar existente encontrado, convirtiendo a móvil...');
                this.convertSidebarToMobile(existingSidebar);
            }
        }, 500);
    }

    convertSidebarToMobile(sidebar) {
        if (!this.isMobile) return;

        console.log('🔄 Convirtiendo sidebar a formato móvil...');
        // Ocultar el sidebar original en móvil
        if (sidebar) {
            sidebar.style.display = 'none';
        }
        
        // También ocultar cualquier contenedor padre que tenga clases relacionadas
        const sidebarContent = document.querySelector('.sidebar-content');
        if (sidebarContent) {
            sidebarContent.style.display = 'none';
        }
        
        // Ocultar cualquier elemento con ID sidebar
        const sidebarElements = document.querySelectorAll('[id*="sidebar"]');
        sidebarElements.forEach(element => {
            element.style.display = 'none';
        });
        // Crear el contenedor del menú móvil
        const menuContent = document.getElementById('mobileListsContent');
        if (!menuContent) return;

        // Extraer el contenido del sidebar
        const sections = sidebar.querySelectorAll('.sidebar-section');
        let mobileHTML = '';

        sections.forEach((section) => {
            const dropdownBtn = section.querySelector('.sidebar-dropdown-btn');
            const dropdownList = section.querySelector('.sidebar-dropdown-list');
            
            if (dropdownBtn && dropdownList) {
                const title = dropdownBtn.textContent.trim();
                const links = dropdownList.querySelectorAll('.sidebar-link');
                
                mobileHTML += `
                    <div class="mobile-sidebar-section">
                        <button class="mobile-sidebar-dropdown-btn" data-section="${title}">
                            <span>${title}</span>
                            <span class="mobile-sidebar-caret">▼</span>
                        </button>
                        <div class="mobile-sidebar-dropdown-list">
                `;
                
                links.forEach((link) => {
                    const text = link.textContent.trim();
                    const onclick = link.getAttribute('onclick');
                    
                    mobileHTML += `
                        <div class="mobile-sidebar-link" onclick="${onclick}">
                            ${text}
                        </div>
                    `;
                });
                
                mobileHTML += `
                        </div>
                    </div>
                `;
            }
        });

        menuContent.innerHTML = mobileHTML;
        this.setupMobileDropdowns();
        
        // Actualizar título si es posible detectarlo
        this.updateMenuTitle();
        
        // Mostrar el botón hamburguesa si no está visible
        this.showHamburgerButton();
    }

    setupMobileDropdowns() {
        const dropdownBtns = document.querySelectorAll('.mobile-sidebar-dropdown-btn');
        
        dropdownBtns.forEach((btn) => {
            btn.addEventListener('click', () => {
                const section = btn.parentElement;
                const dropdownList = section.querySelector('.mobile-sidebar-dropdown-list');
                const isActive = btn.classList.contains('active');
                
                // Cerrar otros dropdowns
                dropdownBtns.forEach((otherBtn) => {
                    if (otherBtn !== btn) {
                        otherBtn.classList.remove('active');
                        const otherSection = otherBtn.parentElement;
                        const otherList = otherSection.querySelector('.mobile-sidebar-dropdown-list');
                        if (otherList) {
                            otherList.classList.remove('active');
                        }
                    }
                });
                
                // Toggle current dropdown
                if (isActive) {
                    btn.classList.remove('active');
                    dropdownList.classList.remove('active');
                } else {
                    btn.classList.add('active');
                    dropdownList.classList.add('active');
                }
            });
        });

        // Manejar clicks en los enlaces
        const links = document.querySelectorAll('.mobile-sidebar-link');
        links.forEach((link) => {
            link.addEventListener('click', () => {
                this.closeMenu();
            });
        });
    }

    updateMenuTitle() {
        // Intentar detectar el tipo de lista cargada
        const titleElement = document.getElementById('mobileListsTitle');
        if (!titleElement) return;

        const currentURL = window.location.pathname;
        let title = 'Listas';

        if (currentURL.includes('informacion') || document.querySelector('[onclick*="mostrarAdminUsuario"]')) {
            title = 'Información Básica';
        } else if (document.querySelector('[onclick*="mostrarControlMaterial"]')) {
            title = 'Control de Material';
        } else if (document.querySelector('[onclick*="mostrarControlModelos"]')) {
            title = 'Control de Producción';
        } else if (document.querySelector('[onclick*="mostrarControlProceso"]')) {
            title = 'Control de Proceso';
        }

        titleElement.textContent = title;
        this.currentListTitle = title;
    }

    openMenu() {
        const menu = document.getElementById('mobileListsMenu');
        const overlay = document.getElementById('mobileListsOverlay');
        const toggle = document.getElementById('mobileListsToggle');

        if (menu && overlay && toggle) {
            menu.classList.add('active');
            overlay.classList.add('active');
            toggle.classList.add('active'); // Agregar clase active para rotar la flecha
            // No ocultar el botón para ver la animación
            document.body.style.overflow = 'hidden';
            this.menuOpen = true;
        }
    }

    closeMenu() {
        const menu = document.getElementById('mobileListsMenu');
        const overlay = document.getElementById('mobileListsOverlay');
        const toggle = document.getElementById('mobileListsToggle');

        if (menu && overlay && toggle) {
            menu.classList.remove('active');
            overlay.classList.remove('active');
            toggle.classList.remove('active'); // Remover clase active para volver flecha normal
            document.body.style.overflow = '';
            this.menuOpen = false;
        }
    }

    handleResize() {
        window.addEventListener('resize', () => {
            const wasMobile = this.isMobile;
            this.isMobile = window.innerWidth <= 768;
            
            // Si cambió de móvil a desktop, ocultar elementos móviles
            if (wasMobile && !this.isMobile) {
                const toggle = document.getElementById('mobileListsToggle');
                const menu = document.getElementById('mobileListsMenu');
                const overlay = document.getElementById('mobileListsOverlay');
                
                if (toggle) toggle.style.display = 'none';
                if (menu) menu.classList.remove('active');
                if (overlay) overlay.classList.remove('active');
                document.body.style.overflow = '';
                this.menuOpen = false;
            }
            // Si cambió de desktop a móvil, mostrar elementos móviles
            else if (!wasMobile && this.isMobile) {
                if (!document.getElementById('mobileListsToggle')) {
                    this.init();
                } else {
                    const toggle = document.getElementById('mobileListsToggle');
                    if (toggle) toggle.style.display = 'flex';
                }
            }
        });
    }

    showHamburgerButton() {
        const toggle = document.getElementById('mobileListsToggle');
        if (toggle && this.isMobile) {
            toggle.style.display = 'flex';
            console.log('📋 Botón hamburguesa de listas mostrado');
        }
    }

    hideHamburgerButton() {
        const toggle = document.getElementById('mobileListsToggle');
        if (toggle) {
            toggle.style.display = 'none';
            console.log('📋 Botón hamburguesa de listas ocultado');
        }
    }

    // Método público para actualizar el contenido cuando se carga una nueva lista
    updateContent(newContent) {
        if (!this.isMobile) return;
        
        const menuContent = document.getElementById('mobileListsContent');
        if (menuContent && newContent) {
            // Si newContent contiene un sidebar, convertirlo
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newContent;
            const sidebar = tempDiv.querySelector('.app-sidebar');
            
            if (sidebar) {
                this.convertSidebarToMobile(sidebar);
            }
        }
    }
}

// Inicializar cuando el DOM esté listo - SOLO EN MÓVIL
document.addEventListener('DOMContentLoaded', () => {
    if (window.innerWidth <= 768) {
        window.mobileListsHamburger = new MobileListsHamburger();
        console.log('✅ Menú hamburguesa de listas móvil inicializado');
    } else {
        console.log('🖥️ Desktop detectado - menú hamburguesa NO inicializado');
    }
});

// También verificar en resize para inicializar si se cambia a móvil
window.addEventListener('resize', () => {
    if (window.innerWidth <= 768 && !window.mobileListsHamburger) {
        window.mobileListsHamburger = new MobileListsHamburger();
        console.log('✅ Menú hamburguesa inicializado al cambiar a móvil');
    } else if (window.innerWidth > 768 && window.mobileListsHamburger) {
        // Destruir la instancia si cambiamos a desktop
        console.log('🖥️ Cambiando a desktop - limpiando menú hamburguesa');
        delete window.mobileListsHamburger;
    }
});

// Exportar para uso global
window.MobileListsHamburger = MobileListsHamburger;

// Función de prueba para verificar que todo funciona
window.testMobileListsHamburger = function() {
    console.log('🧪 Probando menú hamburguesa de listas...');
    
    if (window.mobileListsHamburger) {
        console.log('✅ MobileListsHamburger inicializado');
        
        // Mostrar el botón hamburguesa manualmente
        window.mobileListsHamburger.showHamburgerButton();

            
        // Ocultar elementos sidebar existentes
        window.mobileListsHamburger.hideSidebarElements();
        
        // Simular contenido de lista para prueba
        const testHTML = `
            <div class="app-sidebar">
                <ul class="sidebar-menu">
                    <li class="sidebar-section">
                        <button class="sidebar-dropdown-btn">
                            <span>Test - Administración de usuario</span>
                        </button>
                        <ul class="sidebar-dropdown-list">
                            <li class="sidebar-link" onclick="console.log('Test Admin Usuario')">Administración de usuario</li>
                            <li class="sidebar-link" onclick="console.log('Test Admin Menu')">Administración de menu</li>
                        </ul>
                    </li>
                    <li class="sidebar-section">
                        <button class="sidebar-dropdown-btn">
                            <span>Test - Control de Proceso</span>
                        </button>
                        <ul class="sidebar-dropdown-list">
                            <li class="sidebar-link" onclick="console.log('Test Control Proceso')">Control de proceso</li>
                            <li class="sidebar-link" onclick="console.log('Test Control Depto')">Control de departamento</li>
                        </ul>
                    </li>
                </ul>
            </div>
        `;
        
        // Convertir el HTML de prueba
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = testHTML;
        const testSidebar = tempDiv.querySelector('.app-sidebar');
        
        if (testSidebar) {
            window.mobileListsHamburger.convertSidebarToMobile(testSidebar);
            console.log('✅ Contenido de prueba convertido a formato móvil');
        }
        
        return 'Prueba completada. Revisa si aparece el botón hamburguesa en la esquina inferior derecha.';
    } else {
        console.error('❌ MobileListsHamburger no está inicializado');
        return 'Error: MobileListsHamburger no está inicializado';
    }
};
