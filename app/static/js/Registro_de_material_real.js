// Variables globales para el inventario general
let inventarioGeneralData = [];
let inventarioSelectedItems = new Set();
let filtrosActivos = {};

// Función principal de inicialización
function initRegistroMaterial() {
    
    // Configurar filtros por defecto
    filtrosActivos = {
        numeroParte: '',
        propiedad: '',
        cantidadMinima: 0
    };
    
    // Cargar datos iniciales
    consultarInventarioGeneral();
    
    // Configurar eventos de los modales
    setupInventarioModalEvents();
    
}

// Función para consultar inventario general
function consultarInventarioGeneral() {
    const tableBody = document.getElementById('registroMaterialTableBody');
    
    if (!tableBody) {
        console.error('❌ Tabla de inventario no encontrada');
        return;
    }
    
    // Mostrar loading
    tableBody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 20px; color: #b0b0b0;"><i class="fas fa-spinner fa-spin"></i> Consultando inventario...</td></tr>';
    
    // Llamada a la API
    setTimeout(() => {
        fetch('/api/inventario/consultar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(filtrosActivos)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                inventarioGeneralData = data.inventario;
                renderizarInventarioTabla();
                actualizarInventarioContadorSeleccionados();
            } else {
                console.error('Error al consultar inventario:', data.message);
                inventarioGeneralData = [];
                renderizarInventarioTabla();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            inventarioGeneralData = [];
            renderizarInventarioTabla();
        });
    }, 800);
}

// Función para renderizar la tabla de inventario
function renderizarInventarioTabla() {
    const tableBody = document.getElementById('registroMaterialTableBody');
    
    if (!tableBody) {
        console.error('❌ No se encontró el tbody de la tabla');
        return;
    }
    
    if (!inventarioGeneralData || inventarioGeneralData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" class="inventario-no-data"><i class="fas fa-info-circle"></i> No hay datos de inventario disponibles</td></tr>';
        return;
    }
    
    // Renderizar filas
    tableBody.innerHTML = inventarioGeneralData.map(item => {
        const remanente = item.cantidad_total || (item.cantidad_entradas - item.cantidad_salidas);
        const statusClass = remanente < 50 ? 'text-danger' : remanente < 100 ? 'text-warning' : 'text-success';
        const isSelected = inventarioSelectedItems.has(item.id);
        
        // Crear celda con tooltip si el texto es largo
        function crearCelda(valor, maxLength = 20) {
            const valorStr = String(valor || '');
            if (valorStr.length > maxLength) {
                return `<td data-full-text="${valorStr}" title="${valorStr}">${valorStr.substring(0, maxLength)}...</td>`;
            }
            return `<td>${valorStr}</td>`;
        }
        
        return `
            <tr class="${isSelected ? 'registro-selected' : ''}" onclick="seleccionarInventarioItem(${item.id})" style="cursor: pointer; transition: all 0.3s ease;">
                <td class="inventario-checkbox-column">
                    <input type="checkbox" class="inventario-checkbox registro-row-checkbox" 
                        data-id="${item.id}" ${isSelected ? 'checked' : ''}
                        onchange="toggleInventarioSelection(${item.id})"
                        onclick="event.stopPropagation()">
                </td>
                ${crearCelda(item.numero_parte, 15)}
                ${crearCelda(item.codigo_material, 15)}
                ${crearCelda(item.especificacion || 'N/A', 25)}
                <td class="cantidad-col cantidad-remanente ${statusClass}" style="text-align: right; font-weight: bold;">
                    ${formatearNumero(remanente)}
                </td>
                <td class="cantidad-col cantidad-entradas" style="text-align: right;">
                    ${formatearNumero(item.cantidad_entradas)}
                </td>
                <td class="cantidad-col cantidad-salidas" style="text-align: right;">
                    ${formatearNumero(item.cantidad_salidas)}
                </td>
                <td style="font-size: 12px; color: #b0b0b0;">
                    ${formatearFecha(item.fecha_actualizacion, true)}
                </td>
                <td style="font-size: 12px; color: #b0b0b0;">
                    ${formatearFecha(item.fecha_creacion, true)}
                </td>
            </tr>
        `;
    }).join('');
    
    actualizarInventarioContadorSeleccionados();
}

// Función para formatear números
function formatearNumero(numero) {
    if (numero === null || numero === undefined) return '0.00';
    return Number(numero).toLocaleString('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Función para formatear fechas
function formatearFecha(fecha, compacto = false) {
    if (!fecha) return 'N/A';
    try {
        const date = new Date(fecha);
        if (compacto) {
            return date.toLocaleDateString('es-MX', {
                year: '2-digit',
                month: '2-digit',
                day: '2-digit'
            });
        } else {
            return date.toLocaleDateString('es-MX', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }) + ' ' + date.toLocaleTimeString('es-MX', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    } catch (e) {
        return fecha;
    }
}

// Función para seleccionar item de inventario
function seleccionarInventarioItem(id) {
    const checkbox = document.querySelector(`.registro-row-checkbox[data-id="${id}"]`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        toggleInventarioSelection(id);
    }
}

// Función para toggle selección de inventario
function toggleInventarioSelection(id) {
    if (inventarioSelectedItems.has(id)) {
        inventarioSelectedItems.delete(id);
    } else {
        inventarioSelectedItems.add(id);
    }
    
    renderizarInventarioTabla();
    
    // Actualizar checkbox "seleccionar todo"
    const selectAllCheckbox = document.getElementById('registroSelectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = inventarioSelectedItems.size === inventarioGeneralData.length;
        selectAllCheckbox.indeterminate = inventarioSelectedItems.size > 0 && inventarioSelectedItems.size < inventarioGeneralData.length;
    }
}

// Función para toggle selección de todos los elementos
function toggleInventarioSelectAll() {
    const selectAllCheckbox = document.getElementById('registroSelectAll');
    const isChecked = selectAllCheckbox.checked;
    
    if (isChecked) {
        inventarioGeneralData.forEach(item => {
            inventarioSelectedItems.add(item.id);
        });
    } else {
        inventarioSelectedItems.clear();
    }
    
    renderizarInventarioTabla();
}

// Función para actualizar contador de seleccionados
function actualizarInventarioContadorSeleccionados() {
    const totalRows = document.getElementById('registroTotalRows');
    const totalSeleccionados = inventarioSelectedItems.size;
    
    if (totalRows) {
        totalRows.textContent = inventarioGeneralData.length;
    }
    
    const selectedCount = document.getElementById('registroSelectedCount');
    if (selectedCount) {
        selectedCount.textContent = totalSeleccionados;
    }
    
}

// Función para actualizar inventario general (botón Actualizar)
function actualizarInventarioGeneral() {
    consultarInventarioGeneral();
}

// Función para reiniciar selección de inventario (botón Reiniciar Selección)
function reiniciarInventarioSeleccion() {
    inventarioSelectedItems.clear();
    renderizarInventarioTabla();
    
    const selectAllCheckbox = document.getElementById('registroSelectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    }
}

// Función para abrir modal de filtros avanzados
function abrirFiltrosInventarioModal() {
    document.getElementById('filtroNumeroParte').value = filtrosActivos.numeroParte || '';
    document.getElementById('filtroPropiedad').value = filtrosActivos.propiedad || '';
    document.getElementById('filtroCantidadMinima').value = filtrosActivos.cantidadMinima || 0;
    
    const modal = document.getElementById('registroImportModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

// Función para cerrar modal de filtros
function cerrarFiltrosInventarioModal() {
    const modal = document.getElementById('registroImportModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Función para aplicar filtros de inventario
function aplicarFiltrosInventario() {
    filtrosActivos = {
        numeroParte: document.getElementById('filtroNumeroParte').value.trim(),
        propiedad: document.getElementById('filtroPropiedad').value.trim(),
        cantidadMinima: parseFloat(document.getElementById('filtroCantidadMinima').value) || 0
    };
    
    
    cerrarFiltrosInventarioModal();
    consultarInventarioGeneral();
}

// Función para limpiar filtros
function limpiarFiltrosInventario() {
    filtrosActivos = {
        numeroParte: '',
        propiedad: '',
        cantidadMinima: 0
    };
    
    document.getElementById('filtroNumeroParte').value = '';
    document.getElementById('filtroPropiedad').value = '';
    document.getElementById('filtroCantidadMinima').value = 0;
    
    
    consultarInventarioGeneral();
}

// Función para exportar inventario a Excel
function exportarInventarioExcel() {
    
    if (!inventarioGeneralData || inventarioGeneralData.length === 0) {
        console.warn('No hay datos para exportar');
        return;
    }
    
    const datosParaExportar = inventarioSelectedItems.size > 0 
        ? inventarioGeneralData.filter(item => inventarioSelectedItems.has(item.id))
        : inventarioGeneralData;
    
    const headers = ['Número de Parte', 'Código Material', 'Especificación', 'Propiedad', 'Entradas', 'Salidas', 'Remanente', 'Fecha Actualización'];
    
    const rows = datosParaExportar.map(item => [
        item.numero_parte,
        item.codigo_material,
        item.especificacion || '',
        item.propiedad_material,
        item.cantidad_entradas,
        item.cantidad_salidas,
        item.cantidad_total || (item.cantidad_entradas - item.cantidad_salidas),
        item.fecha_actualizacion
    ]);
    
    const csvContent = [headers, ...rows]
        .map(row => row.map(field => `"${field}"`).join(','))
        .join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `inventario_general_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
}

// Configurar eventos de modales para inventario
function setupInventarioModalEvents() {
    // Cerrar modales al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('registro-modal')) {
            e.target.style.display = 'none';
        }
    });
    
    // Cerrar modales con Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            cerrarFiltrosInventarioModal();
        }
    });
    
}

// Inicialización cuando se carga el contenido
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initRegistroMaterial, 100);
});

// Hacer funciones disponibles globalmente
window.initRegistroMaterial = initRegistroMaterial;
window.consultarInventarioGeneral = consultarInventarioGeneral;
window.renderizarInventarioTabla = renderizarInventarioTabla;
window.exportarInventarioExcel = exportarInventarioExcel;
window.actualizarInventarioGeneral = actualizarInventarioGeneral;
window.reiniciarInventarioSeleccion = reiniciarInventarioSeleccion;
window.abrirFiltrosInventarioModal = abrirFiltrosInventarioModal;
window.cerrarFiltrosInventarioModal = cerrarFiltrosInventarioModal;
window.aplicarFiltrosInventario = aplicarFiltrosInventario;
window.limpiarFiltrosInventario = limpiarFiltrosInventario;
window.toggleInventarioSelectAll = toggleInventarioSelectAll;
window.toggleInventarioSelection = toggleInventarioSelection;