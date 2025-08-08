/**
 * Administrador básico para cargar contenido HTML mediante AJAX.
 * Garantiza que las hojas de estilo se apliquen antes de renderizar
 * el contenido en pantalla para evitar parpadeos sin estilo.
 */
(function() {
    'use strict';

    async function loadContent(url, targetSelector = '.main-wrapper') {
        try {
            const response = await fetch(url, { credentials: 'include' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const htmlText = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');

            // Pre-cargar estilos antes de insertar el HTML
            const styleLinks = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
            await Promise.all(styleLinks.map(link => new Promise(resolve => {
                const href = link.getAttribute('href');
                if (document.querySelector(`link[href="${href}"]`)) return resolve();
                const newLink = document.createElement('link');
                newLink.rel = 'stylesheet';
                newLink.href = href;
                newLink.onload = resolve;
                newLink.onerror = resolve;
                document.head.appendChild(newLink);
            })));

            const target = document.querySelector(targetSelector);
            if (target) {
                target.innerHTML = doc.body.innerHTML;
            }
        } catch (error) {
            console.error('Error cargando contenido vía AJAX:', error);
        }
    }

    window.AjaxContentManager = {
        loadContent
    };
})();
