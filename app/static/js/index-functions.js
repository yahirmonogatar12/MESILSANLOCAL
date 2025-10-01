(function(){
  var s=document.createElement('script');
  s.src='/front-plan/static/index-functions.js';
  s.defer=true; s.async=false;
  var current=document.currentScript; (current? current.parentNode: document.head).insertBefore(s, current||document.head.firstChild);
})();

// Funciones especÃ­ficas para index.html

// FunciÃ³n para cerrar modal de ediciÃ³n
function closeEditModal() {
  document.getElementById('plan-editModal').style.display = 'none';
}

// Event listeners para cuando el DOM estÃ© listo
document.addEventListener('DOMContentLoaded', function() {
  // Event listener para el botÃ³n de cerrar modal de ediciÃ³n
  const editCloseBtn = document.querySelector('#plan-editForm button[type="button"]');
  if (editCloseBtn && editCloseBtn.textContent.includes('Cerrar')) {
    editCloseBtn.addEventListener('click', closeEditModal);
  }
});
// Funciones específicas para index.html

// Función para cerrar modal de edición
function closeEditModal() {
  const modal = document.getElementById('plan-editModal');
  if (modal) modal.style.display = 'none';
}

// Event listeners cuando el DOM está listo
document.addEventListener('DOMContentLoaded', function() {
  const editCloseBtn = document.querySelector('#plan-editForm button[type="button"]');
  if (editCloseBtn && editCloseBtn.textContent.includes('Cerrar')) {
    editCloseBtn.addEventListener('click', closeEditModal);
  }
});
