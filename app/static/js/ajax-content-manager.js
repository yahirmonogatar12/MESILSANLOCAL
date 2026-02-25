/**
 * Administrador avanzado para cargar contenido HTML mediante AJAX.
 * GARANTIZA que las hojas de estilo se carguen y apliquen COMPLETAMENTE
 * antes de mostrar cualquier contenido HTML para eliminar parpadeos.
 */
(function() {
    'use strict';

    // Función para esperar a que un CSS esté completamente cargado
    function waitForStylesheet(href) {
        return new Promise((resolve) => {
            console.log(' Verificando CSS:', href);
            
            // Si ya existe el CSS, verificar que esté REALMENTE cargado
            const existingLink = document.querySelector(`link[href="${href}"]`);
            if (existingLink) {
                // Verificar que tenga reglas CSS cargadas
                try {
                    if (existingLink.sheet && existingLink.sheet.cssRules && existingLink.sheet.cssRules.length > 0) {
                        console.log(' CSS ya cargado:', href);
                        return resolve();
                    }
                } catch (e) {
                    // Puede fallar por CORS, pero significa que está cargado
                    console.log(' CSS cargado (CORS):', href);
                    return resolve();
                }
                
                // Si existe pero no está cargado, esperar
                existingLink.onload = () => {
                    console.log(' CSS terminó de cargar:', href);
                    setTimeout(resolve, 100); // Pausa extra para aplicación
                };
                existingLink.onerror = () => {
                    console.warn(' Error cargando CSS:', href);
                    resolve(); // Continuar aunque falle
                };
                return;
            }

            // Crear nuevo link CSS
            console.log('📥 Cargando nuevo CSS:', href);
            const newLink = document.createElement('link');
            newLink.rel = 'stylesheet';
            newLink.href = href;
            
            // Esperar carga completa con verificación estricta
            newLink.onload = () => {
                console.log(' Nuevo CSS cargado:', href);
                // Pausa adicional para asegurar que se aplique
                setTimeout(() => {
                    // Verificar que realmente se aplicó
                    try {
                        if (newLink.sheet && newLink.sheet.cssRules) {
                            console.log(' CSS aplicado correctamente:', href);
                        }
                    } catch (e) {
                        console.log(' CSS aplicado (CORS):', href);
                    }
                    resolve();
                }, 150); // Pausa más larga para asegurar aplicación
            };
            
            newLink.onerror = () => {
                console.warn(' Error cargando nuevo CSS:', href);
                resolve(); // Continuar aunque falle
            };
            
            document.head.appendChild(newLink);
        });
    }

    // Función para verificar que todos los estilos estén aplicados
    function ensureStylesApplied() {
        return new Promise(resolve => {
            // Esperar un frame de renderizado completo
            requestAnimationFrame(() => {
                requestAnimationFrame(resolve);
            });
        });
    }

    // Función para mostrar/ocultar modal de carga
    function showLoadingModal(show, message = 'Cargando contenido...') {
        const modalId = 'ajax-loading-modal';
        
        if (show) {
            // Crear modal si no existe
            let modal = document.getElementById(modalId);
            if (!modal) {
                modal = document.createElement('div');
                modal.id = modalId;
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 99999;
                    font-family: Arial, sans-serif;
                `;
                
                modal.innerHTML = `
                    <div style="
                        background: linear-gradient(135deg, #20688C, #32323E);
                        padding: 40px;
                        border-radius: 12px;
                        text-align: center;
                        color: white;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                        max-width: 400px;
                        width: 90%;
                    ">
                        <div style="
                            width: 50px;
                            height: 50px;
                            border: 4px solid #ffffff30;
                            border-top: 4px solid #ffffff;
                            border-radius: 50%;
                            animation: ajax-spin 1s linear infinite;
                            margin: 0 auto 20px;
                        "></div>
                        <h3 style="margin: 0 0 10px; font-size: 18px;">${message}</h3>
                        <p style="margin: 0; opacity: 0.8; font-size: 14px;" id="ajax-loading-text">
                            Preparando contenido...
                        </p>
                    </div>
                `;
                
                // Añadir CSS para animación
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes ajax-spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `;
                document.head.appendChild(style);
                
                document.body.appendChild(modal);
            }
            modal.style.display = 'flex';
        } else {
            // Ocultar modal
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.display = 'none';
            }
        }
    }

    // Función para actualizar texto del modal
    function updateLoadingText(text) {
        const textElement = document.getElementById('ajax-loading-text');
        if (textElement) {
            textElement.textContent = text;
        }
    }

    // Función para gestionar scripts después de cargar contenido
    function reinitializeScripts() {
        console.log(' Reinicializando scripts para contenido dinámico...');
        
        // 1. Reinicializar dropdowns unificados de forma controlada
        if (window.setupUnifiedDropdowns && typeof window.setupUnifiedDropdowns === 'function') {
            console.log(' Reinicializando dropdowns unificados...');
            try {
                // Llamar directamente sin MutationObserver
                window.setupUnifiedDropdowns();
            } catch (error) {
                console.warn(' Error reinicializando dropdowns:', error);
            }
        }
        
        // 2. Reaplicar permisos de forma controlada
        if (window.PermisosManagerSimple && window.PermisosManagerSimple.inicializado) {
            console.log(' Reaplicando permisos para nuevo contenido...');
            try {
                // Solo reaplicar permisos, no reinicializar completamente
                if (typeof window.PermisosManagerSimple.aplicarPermisos === 'function') {
                    window.PermisosManagerSimple.aplicarPermisos();
                }
            } catch (error) {
                console.warn(' Error reaplicando permisos:', error);
            }
        }
        
        // 3. Inicializar otros scripts que puedan necesitarlo
        reinitializeOtherScripts();
    }
    
    // Función para otros scripts que necesiten reinicialización
    function reinitializeOtherScripts() {
        // Aquí se pueden añadir otros scripts que necesiten reinicialización
        // después de cargar contenido dinámico
        
        // Ejemplo: Tooltips de Bootstrap
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            try {
                // Reinicializar tooltips
                const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                tooltipTriggerList.map(function (tooltipTriggerEl) {
                    return new bootstrap.Tooltip(tooltipTriggerEl);
                });
            } catch (error) {
                console.warn(' Error reinicializando tooltips:', error);
            }
        }
    }

    // Ejecuta los <script> del HTML insertado dinámicamente
    async function executeScriptsIn(container) {
        const scripts = Array.from(container.querySelectorAll('script'));
        const newlyLoaded = [];
        for (const oldScript of scripts) {
            try {
                if (oldScript.src) {
                    const src = oldScript.getAttribute('src');
                    if (!window.__loadedScriptUrls || !window.__loadedScriptUrls.has(src)) {
                        window.__loadedScriptUrls = window.__loadedScriptUrls || new Set();
                        await new Promise((resolve, reject) => {
                            const s = document.createElement('script');
                            s.src = src;
                            s.onload = () => { window.__loadedScriptUrls.add(src); resolve(); };
                            s.onerror = reject;
                            document.body.appendChild(s);
                        });
                        newlyLoaded.push(src);
                    }
                } else if (oldScript.textContent && oldScript.textContent.trim()) {
                    const s = document.createElement('script');
                    s.text = oldScript.textContent;
                    document.body.appendChild(s);
                }
            } catch (e) {
                console.warn('Error ejecutando script dinámico:', e);
            }
        }
        return newlyLoaded;
    }

    // Desactiva CSS de módulos no activos para evitar conflicto de #mm-grid entre pantallas
    function applyModuleStyles(mod) {
        try {
            const known = ['control_metal_mask.css', 'control_storage_box.css'];
            const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            links.forEach(link => {
                const href = link.getAttribute('href') || '';
                if (!known.some(n => href.includes(n))) return;
                const enable = (mod === 'metal-mask' && href.includes('control_metal_mask.css')) ||
                               (mod === 'storage-box' && href.includes('control_storage_box.css'));
                link.disabled = !enable;
            });
        } catch (e) {
            console.warn('applyModuleStyles error:', e);
        }
    }

    async function loadContent(url, targetSelector = '.main-wrapper', showLoader = true) {
        const target = document.querySelector(targetSelector);
        if (!target) {
            console.error('Target no encontrado:', targetSelector);
            return;
        }

        // Teardown del módulo activo antes de cargar uno nuevo
        try {
            if (typeof window.destroyMetalMask === 'function') {
                window.destroyMetalMask();
            }
            if (typeof window.destroyStorageBox === 'function') {
                window.destroyStorageBox();
            }
            const removeOwned = (owner) => {
                ['#mm-drawer', '#mm-loading', '#mm-toast', '#mm-storage-modal'].forEach(id => {
                    const el = document.querySelector(`${id}[data-owner="${owner}"]`);
                    if (el && el.parentElement === document.body) {
                        try { el.remove(); } catch (_) {}
                    }
                });
            };
            removeOwned('metal-mask');
            removeOwned('storage-box');
        } catch (e) {
            console.warn('Error en teardown previo:', e);
        }

        try {
            console.log(' Iniciando carga AJAX:', url);
            
            // Mostrar modal de carga
            if (showLoader) {
                showLoadingModal(true, 'Cargando contenido...');
                updateLoadingText('Obteniendo datos del servidor...');
            }
            
            // 1. Obtener HTML pero NO mostrarlo aún
            const response = await fetch(url, { credentials: 'include' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            updateLoadingText('Procesando contenido HTML...');
            await new Promise(resolve => setTimeout(resolve, 300)); // Pausa visual

            const htmlText = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');

            // 2. Extraer TODOS los CSS del documento
            const styleLinks = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
            console.log(' CSS detectados:', styleLinks.map(l => l.getAttribute('href')));

            // 3. CRÍTICO: Cargar y verificar TODOS los CSS ANTES de mostrar HTML
            if (styleLinks.length > 0) {
                updateLoadingText(`Cargando ${styleLinks.length} archivos de estilo...`);
                console.log('⏳ Esperando carga completa de', styleLinks.length, 'archivos CSS...');
                
                // Cargar todos los CSS en paralelo
                await Promise.all(styleLinks.map(link => 
                    waitForStylesheet(link.getAttribute('href'))
                ));
                
                // Verificación adicional: esperar que se apliquen
                await ensureStylesApplied();
                console.log(' TODOS los CSS cargados y aplicados');
                
                // Pausa adicional para asegurar renderizado
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            updateLoadingText('Aplicando estilos...');
            await new Promise(resolve => setTimeout(resolve, 500)); // Pausa visual

            // 4. Crear el contenido OCULTO primero
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = doc.body.innerHTML;
            tempDiv.style.visibility = 'hidden';
            tempDiv.style.opacity = '0';
            
            // 5. Insertar contenido oculto
            target.innerHTML = '';
            target.appendChild(tempDiv);
            
            // 6. Esperar que se apliquen los estilos al contenido oculto
            await ensureStylesApplied();
            await new Promise(resolve => setTimeout(resolve, 50));
            
            updateLoadingText('Finalizando carga...');
            
            // 7. DELAY ADICIONAL DE 2 SEGUNDOS como solicitaste
            console.log('⏰ Aplicando delay adicional de 2 segundos...');
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // 8. AHORA hacer visible el contenido con estilos aplicados
            tempDiv.style.visibility = 'visible';
            tempDiv.style.opacity = '1';
            tempDiv.style.transition = 'opacity 0.3s ease-in-out';
            
            // 9. Mover contenido del div temporal al contenedor final
            await new Promise(resolve => setTimeout(resolve, 300)); // Esperar transición
            target.innerHTML = tempDiv.innerHTML;
            
            // Ejecutar scripts incluidos en el HTML cargado
            const newlyLoadedScripts = await executeScriptsIn(target);
            
            console.log(' HTML insertado con estilos completamente aplicados');
            
            // 10. REINICIALIZAR SCRIPTS para el nuevo contenido
            updateLoadingText('Configurando funcionalidades...');
            reinitializeScripts();

            // Inicializar módulos específicos si aplica (siempre; son idempotentes)
            try {
                const modEl = target.querySelector('#mm-app[data-module]');
                if (modEl) {
                    const mod = modEl.getAttribute('data-module');
                    applyModuleStyles(mod);
                    if (mod === 'metal-mask' && typeof window.initMetalMask === 'function') {
                        window.initMetalMask();
                    }
                    if (mod === 'storage-box' && typeof window.initStorageBox === 'function') {
                        window.initStorageBox();
                    }
                }
            } catch (e) {
                console.warn('Error inicializando módulo específico:', e);
            }
            
            console.log('⚙️ Scripts reinicializados para contenido dinámico');
            
            // Ocultar modal de carga
            if (showLoader) showLoadingModal(false);
            
            console.log(' Carga AJAX completada SIN parpadeos (con delay de 2s y scripts)');
            
        } catch (error) {
            console.error(' Error cargando contenido vía AJAX:', error);
            if (showLoader) showLoadingModal(false);
        }
    }

    // API pública
    window.AjaxContentManager = {
        loadContent: loadContent
    };

})();
