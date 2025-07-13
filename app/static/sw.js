// Service Worker para ISEMM MES
// Funcionalidad PWA y cache offline

const CACHE_NAME = 'isemm-mes-v1.0.0';
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/styleHeader.css',
    '/static/css/responsive-mobile.css',
    '/static/js/mobile-enhancements.js',
    '/static/logo.png',
    '/static/logoLogIn.png',
    '/static/manifest.json',
    // Bootstrap CSS y JS
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css',
    // Iconos
    '/static/icons/calidad.png',
    '/static/icons/configuracion.png',
    '/static/icons/controldeproceso.png',
    '/static/icons/engrane.png',
    '/static/icons/info.png',
    '/static/icons/material.png',
    '/static/icons/proceso.png',
    '/static/icons/produccion.png',
    '/static/icons/reporte.png',
    '/static/icons/resultados.png'
];

// Instalación del Service Worker
self.addEventListener('install', function(event) {
    console.log('📦 Service Worker: Instalando...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('📦 Service Worker: Cache abierto');
                return cache.addAll(urlsToCache);
            })
            .then(function() {
                console.log('✅ Service Worker: Recursos cacheados');
                // Forzar activación inmediata
                return self.skipWaiting();
            })
            .catch(function(error) {
                console.error('❌ Service Worker: Error al cachear recursos:', error);
            })
    );
});

// Activación del Service Worker
self.addEventListener('activate', function(event) {
    console.log('🚀 Service Worker: Activando...');
    
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    // Eliminar caches antiguos
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Service Worker: Eliminando cache antiguo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(function() {
            console.log('✅ Service Worker: Activado');
            // Tomar control inmediato de todas las páginas
            return self.clients.claim();
        })
    );
});

// Interceptar peticiones de red
self.addEventListener('fetch', function(event) {
    // Solo interceptar peticiones GET
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Ignorar peticiones a extensiones del navegador y otras URLs no relevantes
    if (event.request.url.startsWith('chrome-extension://') || 
        event.request.url.startsWith('moz-extension://') ||
        event.request.url.includes('localhost:3000')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Si está en cache, devolverlo
                if (response) {
                    console.log('📋 Service Worker: Sirviendo desde cache:', event.request.url);
                    return response;
                }
                
                // Si no está en cache, hacer petición de red
                return fetch(event.request).then(function(response) {
                    // Verificar si es una respuesta válida
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clonar la respuesta
                    const responseToCache = response.clone();
                    
                    // Añadir al cache para futuras peticiones
                    caches.open(CACHE_NAME)
                        .then(function(cache) {
                            // Solo cachear recursos específicos en tiempo de ejecución
                            if (shouldCache(event.request.url)) {
                                cache.put(event.request, responseToCache);
                                console.log('💾 Service Worker: Cacheando:', event.request.url);
                            }
                        });
                    
                    return response;
                }).catch(function(error) {
                    console.error('❌ Service Worker: Error en petición de red:', error);
                    
                    // Servir página offline personalizada para navegación
                    if (event.request.destination === 'document') {
                        return caches.match('/offline.html').then(function(response) {
                            return response || new Response(
                                '<html><body><h1>Sin conexión</h1><p>Por favor, verifica tu conexión a internet.</p></body></html>',
                                { headers: { 'Content-Type': 'text/html' } }
                            );
                        });
                    }
                    
                    // Para otros recursos, retornar error
                    return new Response('Recurso no disponible offline', {
                        status: 408,
                        statusText: 'Timeout'
                    });
                });
            })
    );
});

// Función para determinar si un recurso debe ser cacheado
function shouldCache(url) {
    // Cachear recursos estáticos
    const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2'];
    const isStatic = staticExtensions.some(ext => url.includes(ext));
    
    // Cachear páginas importantes
    const importantPages = ['/listas/', '/material/', '/informacion_basica/'];
    const isImportantPage = importantPages.some(page => url.includes(page));
    
    return isStatic || isImportantPage;
}

// Manejar mensajes del cliente
self.addEventListener('message', function(event) {
    console.log('📨 Service Worker: Mensaje recibido:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
    
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        caches.delete(CACHE_NAME).then(function() {
            event.ports[0].postMessage({ success: true });
        });
    }
});

// Manejar instalación de la aplicación (PWA)
self.addEventListener('beforeinstallprompt', function(event) {
    console.log('📱 Service Worker: Prompt de instalación detectado');
    event.preventDefault();
    
    // Guardar el evento para mostrarlo más tarde
    self.deferredPrompt = event;
    
    // Informar al cliente que la app puede ser instalada
    self.clients.matchAll().then(function(clients) {
        clients.forEach(function(client) {
            client.postMessage({
                type: 'INSTALL_AVAILABLE'
            });
        });
    });
});

// Manejar instalación exitosa
self.addEventListener('appinstalled', function(event) {
    console.log('🎉 Service Worker: App instalada exitosamente');
    
    // Informar al cliente que la app fue instalada
    self.clients.matchAll().then(function(clients) {
        clients.forEach(function(client) {
            client.postMessage({
                type: 'APP_INSTALLED'
            });
        });
    });
});

// Manejar notificaciones push (para futuras implementaciones)
self.addEventListener('push', function(event) {
    console.log('🔔 Service Worker: Push recibido');
    
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body || 'Nueva notificación de ISEMM MES',
            icon: '/static/logo.png',
            badge: '/static/logo.png',
            vibrate: [100, 50, 100],
            data: data.data || {},
            actions: [
                {
                    action: 'open',
                    title: 'Abrir',
                    icon: '/static/icons/info.png'
                },
                {
                    action: 'close',
                    title: 'Cerrar',
                    icon: '/static/icons/close.png'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title || 'ISEMM MES', options)
        );
    }
});

// Manejar clicks en notificaciones
self.addEventListener('notificationclick', function(event) {
    console.log('🔔 Service Worker: Click en notificación:', event.action);
    
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Sincronización en segundo plano (para cuando se recupera la conexión)
self.addEventListener('sync', function(event) {
    console.log('🔄 Service Worker: Sincronización en segundo plano:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

// Función de sincronización en segundo plano
function doBackgroundSync() {
    // Aquí puedes implementar lógica para sincronizar datos
    // cuando se recupera la conexión a internet
    return Promise.resolve()
        .then(function() {
            console.log('✅ Service Worker: Sincronización completada');
        })
        .catch(function(error) {
            console.error('❌ Service Worker: Error en sincronización:', error);
        });
}

console.log('🚀 Service Worker: Cargado y listo');
