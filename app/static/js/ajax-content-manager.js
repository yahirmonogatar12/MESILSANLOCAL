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
            console.log('🔍 Verificando CSS:', href);
            
            // Si ya existe el CSS, verificar que esté REALMENTE cargado
            const existingLink = document.querySelector(`link[href="${href}"]`);
            if (existingLink) {
                // Verificar que tenga reglas CSS cargadas
                try {
                    if (existingLink.sheet && existingLink.sheet.cssRules && existingLink.sheet.cssRules.length > 0) {
                        console.log('✅ CSS ya cargado:', href);
                        return resolve();
                    }
                } catch (e) {
                    // Puede fallar por CORS, pero significa que está cargado
                    console.log('✅ CSS cargado (CORS):', href);
                    return resolve();
                }
                
                // Si existe pero no está cargado, esperar
                existingLink.onload = () => {
                    console.log('✅ CSS terminó de cargar:', href);
                    setTimeout(resolve, 100); // Pausa extra para aplicación
                };
                existingLink.onerror = () => {
                    console.warn('⚠️ Error cargando CSS:', href);
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
                console.log('✅ Nuevo CSS cargado:', href);
                // Pausa adicional para asegurar que se aplique
                setTimeout(() => {
                    // Verificar que realmente se aplicó
                    try {
                        if (newLink.sheet && newLink.sheet.cssRules) {
                            console.log('✅ CSS aplicado correctamente:', href);
                        }
                    } catch (e) {
                        console.log('✅ CSS aplicado (CORS):', href);
                    }
                    resolve();
                }, 150); // Pausa más larga para asegurar aplicación
            };
            
            newLink.onerror = () => {
                console.warn('⚠️ Error cargando nuevo CSS:', href);
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

    // Función para mostrar/ocultar indicador de carga
    function setLoadingState(target, isLoading) {
        if (isLoading) {
            target.style.opacity = '0.7';
            target.style.pointerEvents = 'none';
            // Opcional: añadir spinner o mensaje
            const loader = document.createElement('div');
            loader.id = 'ajax-loader';
            loader.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(32, 104, 140, 0.9);
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                z-index: 9999;
                font-size: 14px;
            `;
            loader.textContent = 'Cargando estilos...';
            target.style.position = 'relative';
            target.appendChild(loader);
        } else {
            target.style.opacity = '';
            target.style.pointerEvents = '';
            const loader = target.querySelector('#ajax-loader');
            if (loader) loader.remove();
        }
    }

    async function loadContent(url, targetSelector = '.main-wrapper', showLoader = true) {
        const target = document.querySelector(targetSelector);
        if (!target) {
            console.error('Target no encontrado:', targetSelector);
            return;
        }

        try {
            console.log('🔄 Iniciando carga AJAX:', url);
            
            // Mostrar indicador de carga
            if (showLoader) setLoadingState(target, true);
            
            // 1. Obtener HTML pero NO mostrarlo aún
            const response = await fetch(url, { credentials: 'include' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const htmlText = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');

            // 2. Extraer TODOS los CSS del documento
            const styleLinks = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
            console.log('📋 CSS detectados:', styleLinks.map(l => l.getAttribute('href')));

            // 3. CRÍTICO: Cargar y verificar TODOS los CSS ANTES de mostrar HTML
            if (styleLinks.length > 0) {
                console.log('⏳ Esperando carga completa de', styleLinks.length, 'archivos CSS...');
                
                // Cargar todos los CSS en paralelo
                await Promise.all(styleLinks.map(link => 
                    waitForStylesheet(link.getAttribute('href'))
                ));
                
                // Verificación adicional: esperar que se apliquen
                await ensureStylesApplied();
                console.log('✅ TODOS los CSS cargados y aplicados');
                
                // Pausa adicional para asegurar renderizado
                await new Promise(resolve => setTimeout(resolve, 100));
            }

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
            
            // 7. AHORA hacer visible el contenido con estilos aplicados
            tempDiv.style.visibility = 'visible';
            tempDiv.style.opacity = '1';
            tempDiv.style.transition = 'opacity 0.2s ease-in-out';
            
            // 8. Mover contenido del div temporal al contenedor final
            target.innerHTML = tempDiv.innerHTML;
            
            console.log('📄 HTML insertado con estilos completamente aplicados');
            
            // Quitar indicador de carga
            if (showLoader) setLoadingState(target, false);
            
            console.log('🎉 Carga AJAX completada SIN parpadeos');
            
        } catch (error) {
            console.error('❌ Error cargando contenido vía AJAX:', error);
            if (showLoader) setLoadingState(target, false);
        }
    }

    // API pública
    window.AjaxContentManager = {
        loadContent: loadContent
    };

})();
