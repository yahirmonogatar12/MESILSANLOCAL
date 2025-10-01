// Funciones específicas para index.html

// Función para cerrar modal de edición
function closeEditModal() {
  document.getElementById('plan-editModal').style.display = 'none';
}

// Event listeners para cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  // Event listener para el botón de cerrar modal de edición
  const editCloseBtn = document.querySelector('#plan-editForm button[type="button"]');
  if (editCloseBtn && editCloseBtn.textContent.includes('Cerrar')) {
    editCloseBtn.addEventListener('click', closeEditModal);
  }
});