document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.getElementById('menu-toggle');
  const navContainer = document.getElementById('nav-container');
  const body = document.body;
  
  menuToggle.addEventListener('click', function() {
    // Alternar clases activas
    this.classList.toggle('active');
    navContainer.classList.toggle('active');
    body.classList.toggle('menu-open');
    
    // Crear o eliminar overlay
    let overlay = document.querySelector('.mobile-nav-overlay');
    if (!overlay && navContainer.classList.contains('active')) {
      overlay = document.createElement('div');
      overlay.className = 'mobile-nav-overlay active';
      document.body.appendChild(overlay);
      
      // Cerrar menú al hacer clic en el overlay
      overlay.addEventListener('click', function() {
        menuToggle.classList.remove('active');
        navContainer.classList.remove('active');
        body.classList.remove('menu-open');
        this.remove();
      });
    } else if (overlay && !navContainer.classList.contains('active')) {
      overlay.remove();
    }
  });
  
  // Animación para el botón hamburguesa
  menuToggle.addEventListener('click', function() {
    const spans = this.querySelectorAll('span');
    if (this.classList.contains('active')) {
      spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
    } else {
      spans.forEach(span => {
        span.style.transform = '';
        span.style.opacity = '';
      });
    }
  });
});