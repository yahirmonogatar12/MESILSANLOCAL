// ============================================= 
// MOBILE UTILITIES AND ENHANCEMENTS
// ============================================= 

(function() {
    'use strict';

    // Detectar capacidades del dispositivo
    const deviceCapabilities = {
        isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
        isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        isAndroid: /Android/i.test(navigator.userAgent),
        isTouchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
        hasMotion: typeof DeviceMotionEvent !== 'undefined',
        hasOrientation: typeof DeviceOrientationEvent !== 'undefined'
    };

    // Configuración global para móviles
    const mobileConfig = {
        swipeThreshold: 50,
        doubleTapDelay: 300,
        longPressDelay: 500,
        scrollThrottle: 16,
        resizeThrottle: 250
    };

    // ============================================= 
    // GESTURE DETECTION
    // ============================================= 
    
    class GestureDetector {
        constructor() {
            this.startTouch = { x: 0, y: 0, time: 0 };
            this.endTouch = { x: 0, y: 0, time: 0 };
            this.isSwipeDetected = false;
            this.tapCount = 0;
            this.tapTimer = null;
            this.longPressTimer = null;
            
            this.initializeGestures();
        }
        
        initializeGestures() {
            if (!deviceCapabilities.isTouchDevice) return;
            
            document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
            document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
            document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
        }
        
        handleTouchStart(e) {
            const touch = e.touches[0];
            this.startTouch = {
                x: touch.clientX,
                y: touch.clientY,
                time: Date.now()
            };
            
            this.isSwipeDetected = false;
            
            // Iniciar detección de long press
            this.longPressTimer = setTimeout(() => {
                this.dispatchGestureEvent('longpress', e);
            }, mobileConfig.longPressDelay);
        }
        
        handleTouchMove(e) {
            // Cancelar long press si hay movimiento
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
        }
        
        handleTouchEnd(e) {
            const touch = e.changedTouches[0];
            this.endTouch = {
                x: touch.clientX,
                y: touch.clientY,
                time: Date.now()
            };
            
            // Cancelar long press
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
            
            this.detectSwipe(e);
            this.detectTap(e);
        }
        
        detectSwipe(e) {
            const deltaX = this.endTouch.x - this.startTouch.x;
            const deltaY = this.endTouch.y - this.startTouch.y;
            const deltaTime = this.endTouch.time - this.startTouch.time;
            
            const absX = Math.abs(deltaX);
            const absY = Math.abs(deltaY);
            
            // Verificar si es un swipe válido
            if (absX > mobileConfig.swipeThreshold || absY > mobileConfig.swipeThreshold) {
                if (absX > absY) {
                    // Swipe horizontal
                    const direction = deltaX > 0 ? 'right' : 'left';
                    this.dispatchGestureEvent('swipe', e, { direction, deltaX, deltaY, deltaTime });
                } else {
                    // Swipe vertical
                    const direction = deltaY > 0 ? 'down' : 'up';
                    this.dispatchGestureEvent('swipe', e, { direction, deltaX, deltaY, deltaTime });
                }
                this.isSwipeDetected = true;
            }
        }
        
        detectTap(e) {
            if (this.isSwipeDetected) return;
            
            this.tapCount++;
            
            if (this.tapTimer) {
                clearTimeout(this.tapTimer);
            }
            
            this.tapTimer = setTimeout(() => {
                if (this.tapCount === 1) {
                    this.dispatchGestureEvent('tap', e);
                } else if (this.tapCount === 2) {
                    this.dispatchGestureEvent('doubletap', e);
                }
                this.tapCount = 0;
            }, mobileConfig.doubleTapDelay);
        }
        
        dispatchGestureEvent(type, originalEvent, data = {}) {
            const event = new CustomEvent(`mobile${type}`, {
                detail: {
                    originalEvent,
                    startTouch: this.startTouch,
                    endTouch: this.endTouch,
                    ...data
                },
                bubbles: true,
                cancelable: true
            });
            
            originalEvent.target.dispatchEvent(event);
        }
    }

    // ============================================= 
    // MOBILE NAVIGATION ENHANCEMENTS
    // ============================================= 
    
    class MobileNavigation {
        constructor() {
            this.menuOpen = false;
            this.lastScrollTop = 0;
            this.isScrollingUp = false;
            
            this.initializeNavigation();
        }
        
        initializeNavigation() {
            // Auto-hide navigation on scroll (optional)
            let scrollTimer;
            window.addEventListener('scroll', () => {
                if (scrollTimer) clearTimeout(scrollTimer);
                
                scrollTimer = setTimeout(() => {
                    this.handleScrollNavigation();
                }, mobileConfig.scrollThrottle);
            }, { passive: true });
            
            // Handle navigation gestures
            document.addEventListener('mobileswipe', (e) => {
                this.handleNavigationSwipe(e);
            });
        }
        
        handleScrollNavigation() {
            if (!deviceCapabilities.isMobile) return;
            
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const header = document.querySelector('.app-header');
            
            if (!header) return;
            
            if (scrollTop > this.lastScrollTop && scrollTop > 100) {
                // Scrolling down - hide header
                header.style.transform = 'translateY(-100%)';
            } else {
                // Scrolling up - show header
                header.style.transform = 'translateY(0)';
            }
            
            this.lastScrollTop = scrollTop;
        }
        
        handleNavigationSwipe(e) {
            const { direction } = e.detail;
            const navContainer = document.getElementById('nav-container');
            
            if (!navContainer) return;
            
            // Swipe from left edge to open menu
            if (direction === 'right' && e.detail.startTouch.x < 50 && !this.menuOpen) {
                this.openMenu();
            }
            // Swipe left to close menu
            else if (direction === 'left' && this.menuOpen) {
                this.closeMenu();
            }
        }
        
        openMenu() {
            const navContainer = document.getElementById('nav-container');
            const overlay = document.getElementById('mobile-nav-overlay');
            const hamburger = document.getElementById('menu-toggle');
            
            if (navContainer) navContainer.classList.add('active');
            if (overlay) overlay.classList.add('active');
            if (hamburger) hamburger.classList.add('active');
            
            document.body.classList.add('menu-open');
            this.menuOpen = true;
        }
        
        closeMenu() {
            const navContainer = document.getElementById('nav-container');
            const overlay = document.getElementById('mobile-nav-overlay');
            const hamburger = document.getElementById('menu-toggle');
            
            if (navContainer) navContainer.classList.remove('active');
            if (overlay) overlay.classList.remove('active');
            if (hamburger) hamburger.classList.remove('active');
            
            document.body.classList.remove('menu-open');
            this.menuOpen = false;
        }
    }

    // ============================================= 
    // PERFORMANCE OPTIMIZATIONS
    // ============================================= 
    
    class MobilePerformance {
        constructor() {
            this.initializeOptimizations();
        }
        
        initializeOptimizations() {
            // Lazy loading para imágenes
            this.setupLazyLoading();
            
            // Optimizar animaciones
            this.optimizeAnimations();
            
            // Virtual scrolling para listas largas
            this.setupVirtualScrolling();
            
            // Preload crítico
            this.preloadCriticalResources();
        }
        
        setupLazyLoading() {
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            if (img.dataset.src) {
                                img.src = img.dataset.src;
                                img.removeAttribute('data-src');
                                observer.unobserve(img);
                            }
                        }
                    });
                });
                
                document.querySelectorAll('img[data-src]').forEach(img => {
                    imageObserver.observe(img);
                });
            }
        }
        
        optimizeAnimations() {
            // Reducir animaciones en dispositivos lentos
            if (deviceCapabilities.isMobile) {
                const style = document.createElement('style');
                style.textContent = `
                    @media (prefers-reduced-motion: no-preference) {
                        .mobile-optimized {
                            transition-duration: 0.2s !important;
                        }
                    }
                    @media (prefers-reduced-motion: reduce) {
                        * {
                            animation-duration: 0.01ms !important;
                            animation-iteration-count: 1 !important;
                            transition-duration: 0.01ms !important;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
        }
        
        setupVirtualScrolling() {
            // Implementar virtual scrolling para listas con muchos elementos
            const longLists = document.querySelectorAll('.long-list, .virtual-scroll');
            
            longLists.forEach(list => {
                if (list.children.length > 50) {
                    this.enableVirtualScrolling(list);
                }
            });
        }
        
        enableVirtualScrolling(container) {
            // Implementación básica de virtual scrolling
            const items = Array.from(container.children);
            const itemHeight = 50; // altura estimada del item
            const visibleItems = Math.ceil(window.innerHeight / itemHeight) + 5;
            
            let scrollTop = 0;
            let startIndex = 0;
            
            container.style.height = `${items.length * itemHeight}px`;
            container.style.overflow = 'auto';
            
            const renderVisibleItems = () => {
                const endIndex = Math.min(startIndex + visibleItems, items.length);
                
                // Ocultar todos los items
                items.forEach(item => item.style.display = 'none');
                
                // Mostrar solo los items visibles
                for (let i = startIndex; i < endIndex; i++) {
                    if (items[i]) {
                        items[i].style.display = 'block';
                        items[i].style.transform = `translateY(${i * itemHeight}px)`;
                    }
                }
            };
            
            container.addEventListener('scroll', () => {
                scrollTop = container.scrollTop;
                startIndex = Math.floor(scrollTop / itemHeight);
                renderVisibleItems();
            }, { passive: true });
            
            renderVisibleItems();
        }
        
        preloadCriticalResources() {
            // Precargar recursos críticos
            const criticalPaths = [
                '/static/css/responsive-mobile.css',
                '/static/style.css',
                '/static/styleHeader.css'
            ];
            
            criticalPaths.forEach(path => {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.as = 'style';
                link.href = path;
                document.head.appendChild(link);
            });
        }
    }

    // ============================================= 
    // ACCESSIBILITY ENHANCEMENTS
    // ============================================= 
    
    class MobileAccessibility {
        constructor() {
            this.initializeAccessibility();
        }
        
        initializeAccessibility() {
            // Mejorar navegación por teclado
            this.enhanceKeyboardNavigation();
            
            // Añadir indicadores de focus visibles
            this.addFocusIndicators();
            
            // Mejorar anuncios para screen readers
            this.enhanceScreenReaderSupport();
        }
        
        enhanceKeyboardNavigation() {
            // Trap focus en modal/menú móvil
            const navContainer = document.getElementById('nav-container');
            if (navContainer) {
                navContainer.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        window.mobileNav?.closeMenu();
                    }
                });
            }
        }
        
        addFocusIndicators() {
            const style = document.createElement('style');
            style.textContent = `
                .mobile-focus-visible:focus {
                    outline: 2px solid var(--accent-color) !important;
                    outline-offset: 2px !important;
                    box-shadow: 0 0 0 4px rgba(52, 152, 219, 0.3) !important;
                }
            `;
            document.head.appendChild(style);
            
            // Añadir clase a elementos interactivos
            const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
            interactiveElements.forEach(el => {
                el.classList.add('mobile-focus-visible');
            });
        }
        
        enhanceScreenReaderSupport() {
            // Añadir regiones ARIA
            const header = document.querySelector('.app-header');
            if (header) header.setAttribute('role', 'banner');
            
            const nav = document.querySelector('.nav-buttons-container');
            if (nav) {
                nav.setAttribute('role', 'navigation');
                nav.setAttribute('aria-label', 'Navegación principal');
            }
            
            const main = document.querySelector('.main-content-container');
            if (main) main.setAttribute('role', 'main');
        }
    }

    // ============================================= 
    // INITIALIZATION
    // ============================================= 
    
    function initializeMobileEnhancements() {
        if (!deviceCapabilities.isMobile && window.innerWidth > 768) {
            return;
        }
        
        
        // Inicializar componentes
        const gestureDetector = new GestureDetector();
        const mobileNav = new MobileNavigation();
        const mobilePerf = new MobilePerformance();
        const mobileA11y = new MobileAccessibility();
        
        // Hacer disponibles globalmente
        window.gestureDetector = gestureDetector;
        window.mobileNav = mobileNav;
        window.mobilePerf = mobilePerf;
        window.mobileA11y = mobileA11y;
        
        // Configurar viewport dinámico
        function setDynamicViewport() {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', vh + 'px');
        }
        
        setDynamicViewport();
        window.addEventListener('resize', setDynamicViewport);
        window.addEventListener('orientationchange', () => {
            setTimeout(setDynamicViewport, 500);
        });
        
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeMobileEnhancements);
    } else {
        initializeMobileEnhancements();
    }

    // Exportar utilidades móviles
    window.mobileUtils = {
        deviceCapabilities,
        mobileConfig,
        isMobile: () => deviceCapabilities.isMobile || window.innerWidth <= 768,
        isTouch: () => deviceCapabilities.isTouchDevice,
        vibrate: (pattern = 100) => {
            if ('vibrate' in navigator) {
                navigator.vibrate(pattern);
            }
        }
    };

})();
