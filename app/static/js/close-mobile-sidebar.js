(function(){
    function closeMobileSidebar(){
        const menu = document.getElementById('mobileListsMenu') || document.getElementById('mobile-lists-menu');
        const overlay = document.getElementById('mobileListsOverlay') || document.getElementById('mobile-lists-overlay');
        const toggle = document.getElementById('mobileListsToggle') || document.getElementById('mobile-lists-toggle');
        if(menu) menu.classList.remove('active');
        if(overlay) overlay.classList.remove('active');
        if(toggle) toggle.classList.remove('active');
    }
    // Exponer globalmente solo si no existe
    if(typeof window.closeMobileSidebar !== 'function'){
        window.closeMobileSidebar = closeMobileSidebar;
    }
})();