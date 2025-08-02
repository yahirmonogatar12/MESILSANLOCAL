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
        const remanente = item.cantidad_total || 0;
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
        
        // Crear botón para ver lotes disponibles
        const totalLotes = item.lotes_disponibles ? item.lotes_disponibles.length : 0;
        const lotesBoton = totalLotes > 0
            ? `<button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); verDetallesLotes('${item.numero_parte}')" style="font-size: 11px; padding: 2px 8px;">
                <i class="fas fa-search"></i> Ver Lotes (${totalLotes})
               </button>`
            : '<small class="text-muted">Sin lotes</small>';
        
        const lotesTooltip = `${totalLotes} lotes disponibles. Haz clic para ver detalles.`;
        
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
                <td style="text-align: center; padding: 8px;" title="${lotesTooltip}">
                    ${lotesBoton}
                </td>
                <td style="font-size: 12px; color: #b0b0b0;">
                    ${formatearFecha(item.fecha_ultimo_recibo, true)}
                </td>
                <td style="font-size: 12px; color: #b0b0b0;">
                    ${formatearFecha(item.fecha_primer_recibo, true)}
                </td>
                <td style="font-size: 11px; color: #6c757d;">
                    ${item.propiedad_material || 'COMMON USE'}
                </td>
            </tr>
        `;
    }).join('');
}

// Variables para gestionar event listeners del modal
let modalEventListeners = {
    keydown: null,
    click: null
};

// Función para ver detalles de lotes específicos
function verDetallesLotes(numeroParte) {
    console.log(`🔍 Consultando detalles de lotes para: ${numeroParte}`);
    
    // Crear modal para mostrar detalles de lotes
    const modalHtml = `
        <div class="modal fade" id="lotesDetalleModal" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-boxes"></i> Detalles de Lotes - ${numeroParte}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <!-- Barra de búsqueda -->
                        <div class="row mb-3">
                            <div class="col-md-8">
                                <div class="input-group">
                                    <div class="input-group-prepend">
                                        <span class="input-group-text"><i class="fas fa-search"></i></span>
                                    </div>
                                    <input type="text" class="form-control" id="buscarLote" placeholder="Buscar por número de lote..." onkeyup="filtrarLotes()">
                                </div>
                            </div>
                            <div class="col-md-4">
                                <select class="form-control" id="filtroDisponibilidad" onchange="filtrarLotes()">
                                    <option value="todos">Todos los lotes</option>
                                    <option value="disponibles">Solo disponibles</option>
                                    <option value="agotados">Solo agotados</option>
                                </select>
                            </div>
                        </div>
                        <div id="lotesDetalleContent">
                            <div class="text-center">
                                <i class="fas fa-spinner fa-spin"></i> Cargando detalles de lotes...
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remover modal existente si existe
    const existingModal = document.getElementById('lotesDetalleModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Agregar modal al DOM
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Mostrar modal
    const modal = document.getElementById('lotesDetalleModal');
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    // Consultar detalles de lotes
    fetch('/api/inventario/lotes_detalle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ numero_parte: numeroParte })
    })
    .then(response => response.json())
    .then(data => {
        const contentDiv = document.getElementById('lotesDetalleContent');
        
        if (data.success && data.lotes && data.lotes.length > 0) {
            const tablaLotes = `
                <div class="table-responsive">
                    <table class="table table-striped table-sm" id="tablaLotesDetalle">
                        <thead class="thead-dark">
                            <tr>
                                <th>Lote</th>
                                <th>Cantidad Disponible</th>
                                <th>Cantidad Original</th>
                                <th>Total Salidas</th>
                                <th>Fecha Recibo</th>
                                <th>Ubicación</th>
                                <th>Código Material</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.lotes.map(lote => `
                                <tr class="fila-lote" data-lote="${lote.numero_lote.toLowerCase()}" data-disponible="${lote.cantidad_disponible > 0 ? 'si' : 'no'}">
                                    <td><strong>${lote.numero_lote}</strong></td>
                                    <td class="text-right">
                                        <span class="badge badge-${lote.cantidad_disponible > 0 ? 'success' : 'danger'}">
                                            ${formatearNumero(lote.cantidad_disponible)}
                                        </span>
                                    </td>
                                    <td class="text-right">${formatearNumero(lote.cantidad_original)}</td>
                                    <td class="text-right">${formatearNumero(lote.total_salidas)}</td>
                                    <td>${formatearFecha(lote.fecha_recibo)}</td>
                                    <td>${lote.ubicacion || 'N/A'}</td>
                                    <td>${lote.codigo_material || 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Total de lotes:</strong> ${data.total_lotes}
                        </div>
                        <div class="col-md-6">
                            <strong>Cantidad total disponible:</strong> 
                            <span class="badge badge-primary">
                                ${formatearNumero(data.lotes.reduce((sum, lote) => sum + lote.cantidad_disponible, 0))}
                            </span>
                        </div>
                    </div>
                </div>
            `;
            
            contentDiv.innerHTML = tablaLotes;
        } else {
            contentDiv.innerHTML = `
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle"></i>
                    No se encontraron lotes disponibles para el número de parte: <strong>${numeroParte}</strong>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error al consultar detalles de lotes:', error);
        const contentDiv = document.getElementById('lotesDetalleContent');
        contentDiv.innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="fas fa-exclamation-circle"></i>
                Error al cargar los detalles de lotes: ${error.message}
            </div>
        `;
    });
    
    // Configurar event listeners para cerrar modal
    modalEventListeners.keydown = function(e) {
        if (e.key === 'Escape') {
            cerrarModalLotes();
        }
    };
    
    modalEventListeners.click = function(e) {
        if (e.target === modal) {
            cerrarModalLotes();
        }
    };
    
    document.addEventListener('keydown', modalEventListeners.keydown);
    modal.addEventListener('click', modalEventListeners.click);
    
    // Limpiar modal cuando se cierre
    modal.addEventListener('hidden.bs.modal', function () {
        // Limpiar event listeners antes de remover el modal
        if (modalEventListeners.keydown) {
            document.removeEventListener('keydown', modalEventListeners.keydown);
            modalEventListeners.keydown = null;
        }
        if (modalEventListeners.click) {
            modal.removeEventListener('click', modalEventListeners.click);
            modalEventListeners.click = null;
        }
        modal.remove();
    });
}

// Función para cerrar modal de lotes
function cerrarModalLotes() {
    const modal = document.getElementById('lotesDetalleModal');
    if (modal) {
        // Limpiar event listeners ANTES de remover el modal
        if (modalEventListeners.keydown) {
            document.removeEventListener('keydown', modalEventListeners.keydown);
            modalEventListeners.keydown = null;
        }
        if (modalEventListeners.click) {
            modal.removeEventListener('click', modalEventListeners.click);
            modalEventListeners.click = null;
        }
        
        // Si existe una instancia de Bootstrap Modal, cerrarla primero
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal) {
            bootstrapModal.hide();
            // Esperar a que se complete la animación de cierre
            modal.addEventListener('hidden.bs.modal', function() {
                modal.remove();
            }, { once: true });
        } else {
            // Si no hay instancia de Bootstrap, remover directamente
            modal.remove();
        }
    }
    
    // Restaurar scroll del body
    document.body.style.overflow = 'auto';
}

// Función para filtrar lotes en la tabla de detalles
function filtrarLotes() {
    const busqueda = document.getElementById('buscarLote').value.toLowerCase();
    const filtroDisponibilidad = document.getElementById('filtroDisponibilidad').value;
    const filas = document.querySelectorAll('.fila-lote');
    let filasVisibles = 0;
    
    filas.forEach(fila => {
        const numeroLote = fila.getAttribute('data-lote');
        const disponible = fila.getAttribute('data-disponible');
        
        let mostrarPorBusqueda = numeroLote.includes(busqueda);
        let mostrarPorDisponibilidad = true;
        
        if (filtroDisponibilidad === 'disponibles') {
            mostrarPorDisponibilidad = disponible === 'si';
        } else if (filtroDisponibilidad === 'agotados') {
            mostrarPorDisponibilidad = disponible === 'no';
        }
        
        if (mostrarPorBusqueda && mostrarPorDisponibilidad) {
            fila.style.display = '';
            filasVisibles++;
        } else {
            fila.style.display = 'none';
        }
    });
    
    // Mostrar mensaje si no hay resultados
    const tabla = document.getElementById('tablaLotesDetalle');
    let mensajeNoResultados = document.getElementById('mensajeNoResultados');
    
    if (filasVisibles === 0) {
        if (!mensajeNoResultados) {
            mensajeNoResultados = document.createElement('div');
            mensajeNoResultados.id = 'mensajeNoResultados';
            mensajeNoResultados.className = 'alert alert-info text-center mt-3';
            mensajeNoResultados.innerHTML = '<i class="fas fa-search"></i> No se encontraron lotes que coincidan con los criterios de búsqueda.';
            tabla.parentNode.appendChild(mensajeNoResultados);
        }
        mensajeNoResultados.style.display = 'block';
    } else {
        if (mensajeNoResultados) {
            mensajeNoResultados.style.display = 'none';
        }
    }
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
window.verDetallesLotes = verDetallesLotes;
window.cerrarModalLotes = cerrarModalLotes;