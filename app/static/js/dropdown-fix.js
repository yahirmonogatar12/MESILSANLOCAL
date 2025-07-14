// ===============================================
// SCRIPT BALANCEADO PARA DROPDOWNS EN DESKTOP
// ===============================================

document.addEventListener('DOMContentLoaded', function() {
    // Solo ejecutar en desktop (NO en móvil) - VERIFICACIÓN MÚLTIPLE
    if (window.innerWidth > 768) {
        console.log('🖥️ Inicializando dropdowns balanceados para desktop...');
        
        // Limpiar cualquier interferencia de scripts móviles
        if (window.mobileListas) {
            window.mobileListas.cleanup();
            window.mobileListas = null;
        }
        
        // Esperar a que Bootstrap se cargue completamente
        setTimeout(() => {
            initBalancedDropdowns();
        }, 300);
    } else {
        console.log('📱 Móvil detectado - No inicializar dropdowns de desktop');
    }
});

function initBalancedDropdowns() {
    const dropdownButtons = document.querySelectorAll('.sidebar-dropdown-btn[data-bs-toggle="collapse"]');
    
    console.log(`🔍 Encontrados ${dropdownButtons.length} botones de dropdown`);
    
    dropdownButtons.forEach((button, index) => {
        const targetSelector = button.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetSelector);
        
        if (!targetElement) return;
        
        console.log(`🔧 Configurando dropdown balanceado ${index + 1}: ${targetSelector}`);
        
        // Obtener estado inicial
        const isInitiallyOpen = targetElement.classList.contains('show');
        
        // Variables para controlar el estado
        let isProcessingClick = false;
        let lastClickTime = 0;
        
        // Remover listeners anteriores y crear nuevo botón
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);
        
        // Configurar estado inicial
        newButton.setAttribute('aria-expanded', isInitiallyOpen.toString());
        
        // Event listener principal
        newButton.addEventListener('click', function(e) {
            // VERIFICACIÓN ADICIONAL - Solo en desktop
            if (window.innerWidth <= 768) {
                console.log('🚫 Click ignorado - estamos en móvil');
                return;
            }
            
            const now = Date.now();
            
            // Prevenir clics múltiples rápidos
            if (isProcessingClick || (now - lastClickTime) < 300) {
                console.log('🚫 Click ignorado - demasiado rápido o procesando');
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
            
            isProcessingClick = true;
            lastClickTime = now;
            
            console.log(`🖱️ Click válido en dropdown: ${targetSelector}`);
            
            const isCurrentlyOpen = targetElement.classList.contains('show');
            const willOpen = !isCurrentlyOpen;
            
            console.log(`📊 Estado: ${isCurrentlyOpen ? 'abierto' : 'cerrado'} → ${willOpen ? 'abierto' : 'cerrado'}`);
            
            // Usar Bootstrap pero con protección
            if (typeof bootstrap !== 'undefined' && bootstrap.Collapse) {
                try {
                    const bsCollapse = bootstrap.Collapse.getOrCreateInstance(targetElement, {
                        toggle: false // No auto-toggle para mayor control
                    });
                    
                    if (willOpen) {
                        bsCollapse.show();
                    } else {
                        bsCollapse.hide();
                    }
                } catch (error) {
                    console.warn('Error con Bootstrap, usando fallback:', error);
                    // Fallback manual
                    toggleManually(targetElement, newButton, willOpen);
                }
            } else {
                // Fallback manual si Bootstrap no está disponible
                toggleManually(targetElement, newButton, willOpen);
            }
            
            // Resetear flag después de un tiempo
            setTimeout(() => {
                isProcessingClick = false;
                console.log(`✅ Procesamiento completado para ${targetSelector}`);
            }, 500);
            
            // Prevenir propagación
            e.preventDefault();
            e.stopPropagation();
            return false;
        });
        
        // Listeners para eventos de Bootstrap (para debugging)
        targetElement.addEventListener('show.bs.collapse', function() {
            console.log(`🔄 Bootstrap show: ${targetSelector}`);
            newButton.setAttribute('aria-expanded', 'true');
        });
        
        targetElement.addEventListener('hide.bs.collapse', function() {
            console.log(`🔄 Bootstrap hide: ${targetSelector}`);
            newButton.setAttribute('aria-expanded', 'false');
        });
        
        targetElement.addEventListener('shown.bs.collapse', function() {
            console.log(`✅ Bootstrap shown: ${targetSelector}`);
        });
        
        targetElement.addEventListener('hidden.bs.collapse', function() {
            console.log(`❌ Bootstrap hidden: ${targetSelector}`);
        });
        
        console.log(`✅ Dropdown balanceado configurado: ${targetSelector}`);
    });
}

function toggleManually(targetElement, button, willOpen) {
    if (willOpen) {
        // Abrir con animación manual
        targetElement.classList.remove('collapse');
        targetElement.classList.add('collapsing');
        targetElement.style.height = '0px';
        targetElement.style.display = 'block';
        
        // Obtener altura natural
        const scrollHeight = targetElement.scrollHeight;
        
        // Animar
        setTimeout(() => {
            targetElement.style.height = scrollHeight + 'px';
        }, 10);
        
        // Finalizar animación
        setTimeout(() => {
            targetElement.classList.remove('collapsing');
            targetElement.classList.add('collapse', 'show');
            targetElement.style.height = '';
            button.setAttribute('aria-expanded', 'true');
        }, 350);
        
        console.log(`✅ Abierto manualmente`);
    } else {
        // Cerrar con animación manual
        targetElement.style.height = targetElement.scrollHeight + 'px';
        targetElement.classList.remove('collapse', 'show');
        targetElement.classList.add('collapsing');
        
        // Forzar reflow
        targetElement.offsetHeight;
        
        // Animar cierre
        targetElement.style.height = '0px';
        
        // Finalizar animación
        setTimeout(() => {
            targetElement.classList.remove('collapsing');
            targetElement.classList.add('collapse');
            targetElement.style.display = 'none';
            targetElement.style.height = '';
            button.setAttribute('aria-expanded', 'false');
        }, 350);
        
        console.log(`❌ Cerrado manualmente`);
    }
}

// Verificar cambios de ventana
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        setTimeout(() => {
            console.log('📱→🖥️ Cambiando a desktop, reinicializando dropdowns balanceados...');
            initBalancedDropdowns();
        }, 300);
    }
});

console.log('📁 Script BALANCEADO de dropdowns cargado');
