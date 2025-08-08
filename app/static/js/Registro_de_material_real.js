// Variables globales para el inventario general
let inventarioGeneralData = [];
let inventarioSelectedItems = new Set();
let filtrosActivos = {};

// Variables de control para evitar múltiples aperturas
let modalCargandoLotes = false;
let modalCargandoHistorial = false;

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
    tableBody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 20px; color: #b0b0b0;"><i class="fas fa-spinner fa-spin"></i> Consultando inventario...</td></tr>';
    
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
        tableBody.innerHTML = '<tr><td colspan="10" class="inventario-no-data"><i class="fas fa-info-circle"></i> No hay datos de inventario disponibles</td></tr>';
        return;
    }
    
    // Renderizar filas
    tableBody.innerHTML = inventarioGeneralData.map(item => {
        const remanente = item.cantidad_total || 0;
        const quantityStatusClass = remanente < 50 ? 'text-danger' : remanente < 100 ? 'text-warning' : 'text-success';
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
        const totalLotes = item.total_lotes || 0;
        const lotesBoton = totalLotes > 0
            ? `<button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); verDetallesLotes('${item.numero_parte}')" style="font-size: 11px; padding: 2px 8px;">
                <i class="fas fa-search"></i> Ver Lotes (${totalLotes})
               </button>`
            : '<small class="text-muted">Sin lotes</small>';
        
        const lotesTooltip = `${totalLotes} lotes disponibles. Haz clic para ver detalles.`;
        
        // Crear información detallada de cantidad con entradas y salidas
        const entradas = item.total_entradas || 0;
        const salidas = item.total_salidas || 0;
        const cantidadTooltip = `Entradas: ${formatearNumero(entradas)}\\nSalidas: ${formatearNumero(salidas)}\\nDisponible: ${formatearNumero(remanente)}`;
        
        // Determinar color basado en si hay inventario positivo, negativo o cero
        let statusClass, statusIcon;
        if (remanente > 0) {
            statusClass = 'cantidad-ok';
            statusIcon = '';
        } else if (remanente < 0) {
            statusClass = 'cantidad-baja';
            statusIcon = '';
        } else {
            statusClass = 'cantidad-media';
            statusIcon = '';
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
                <td class="cantidad-col cantidad-remanente ${statusClass}" style="text-align: right; font-weight: bold;" title="${cantidadTooltip}">
                    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 5px;">
                        <div style="text-align: right;">
                            <div style="font-size: 13px; line-height: 1.2;">${formatearNumero(remanente)}</div>
                        </div>
                    </div>
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
                <td style="text-align: center; padding: 5px;">
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-warning btn-sm" onclick="event.stopPropagation(); verHistorialCompleto('${item.numero_parte}')" title="Historial de Movimientos">
                            <i class="fas fa-history"></i>
                        </button>
                    </div>
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
    // Usar la nueva función de lotes detallados
    verLotesDetallados(numeroParte);
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

// Funciones para historial y lotes mejoradas
function verHistorialCompleto(numeroParte) {
    // Prevenir múltiples aperturas
    if (modalCargandoHistorial) {
        console.log('⏳ Modal de historial ya se está cargando...');
        return;
    }
    
    modalCargandoHistorial = true;
    console.log(`📈 Consultando historial completo para: ${numeroParte}`);
    
    // Mostrar indicador de carga (opcional)
    const loadingModal = document.querySelector('.trazabilidad-modal-overlay');
    if (!loadingModal) {
        document.body.insertAdjacentHTML('beforeend', `
            <div class="trazabilidad-modal-overlay" id="loadingModalHistorial">
                <div class="trazabilidad-modal-content" style="max-width: 400px; text-align: center;">
                    <div class="trazabilidad-modal-body">
                        <i class="fas fa-spinner fa-spin" style="font-size: 48px; color: #6c757d; margin-bottom: 15px;"></i>
                        <h4 style="color: #e8e8e8; margin-bottom: 10px;">Cargando Historial...</h4>
                        <p style="color: #6c757d; margin: 0;">Consultando movimientos de <strong>${numeroParte}</strong></p>
                    </div>
                </div>
            </div>
        `);
    }
    
    fetch('/api/inventario/historial', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ numero_parte: numeroParte })
    })
    .then(response => response.json())
    .then(data => {
        // Remover modal de carga
        const loadingModal = document.getElementById('loadingModalHistorial');
        if (loadingModal) {
            loadingModal.remove();
        }
        
        if (data.success) {
            mostrarModalHistorial(numeroParte, data.historial, data.balance_actual);
        } else {
            alert(`❌ Error al consultar historial: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Remover modal de carga
        const loadingModal = document.getElementById('loadingModalHistorial');
        if (loadingModal) {
            loadingModal.remove();
        }
        alert('❌ Error al consultar historial');
    })
    .finally(() => {
        modalCargandoHistorial = false;
    });
}

function verLotesDetallados(numeroParte) {
    // Prevenir múltiples aperturas
    if (modalCargandoLotes) {
        console.log('⏳ Modal de lotes ya se está cargando...');
        return;
    }
    
    modalCargandoLotes = true;
    console.log(`📦 Consultando lotes detallados para: ${numeroParte}`);
    
    // Mostrar indicador de carga
    const loadingModal = document.querySelector('.trazabilidad-modal-overlay');
    if (!loadingModal) {
        document.body.insertAdjacentHTML('beforeend', `
            <div class="trazabilidad-modal-overlay" id="loadingModalLotes">
                <div class="trazabilidad-modal-content" style="max-width: 400px; text-align: center;">
                    <div class="trazabilidad-modal-body">
                        <i class="fas fa-spinner fa-spin" style="font-size: 48px; color: #6c757d; margin-bottom: 15px;"></i>
                        <h4 style="color: #e8e8e8; margin-bottom: 10px;">Cargando Lotes...</h4>
                        <p style="color: #6c757d; margin: 0;">Consultando lotes de <strong>${numeroParte}</strong></p>
                    </div>
                </div>
            </div>
        `);
    }
    
    fetch('/api/inventario/lotes_detalle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ numero_parte: numeroParte })
    })
    .then(response => response.json())
    .then(data => {
        // Remover modal de carga
        const loadingModal = document.getElementById('loadingModalLotes');
        if (loadingModal) {
            loadingModal.remove();
        }
        
        if (data.success) {
            mostrarModalLotes(numeroParte, data.lotes);
        } else {
            alert(`❌ Error al consultar lotes: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Remover modal de carga
        const loadingModal = document.getElementById('loadingModalLotes');
        if (loadingModal) {
            loadingModal.remove();
        }
        alert('❌ Error al consultar lotes');
    })
    .finally(() => {
        modalCargandoLotes = false;
    });
}

function mostrarModalLotes(numeroParte, lotes) {
    const modalContent = `
        <div class="trazabilidad-modal-overlay" onclick="cerrarModalGeneral(event)">
            <div class="trazabilidad-modal-content" onclick="event.stopPropagation()" style="max-width: 1200px;">
                <div class="trazabilidad-modal-header">
                    <h3>Lotes Disponibles - ${numeroParte}</h3>
                    <button class="close-btn" onclick="cerrarModalGeneral()">&times;</button>
                </div>
                <div class="trazabilidad-modal-body">
                    ${lotes.length > 0 ? `
                        <!-- Filtro de búsqueda -->
                        <div class="lotes-filter-container" style="margin-bottom: 20px; display: flex; gap: 15px; align-items: center; background: rgba(74, 76, 90, 0.3); padding: 15px; border-radius: 8px; border-left: 4px solid #6c757d;">
                            <div style="flex: 1;">
                                <label style="display: block; color: #ffffff; font-weight: 600; margin-bottom: 5px; font-size: 13px;">Buscar Lote:</label>
                                <input type="text" id="filtroLotes" placeholder="Escriba el número de lote..." 
                                    style="width: 100%; padding: 8px 12px; border: 2px solid #6c757d; border-radius: 6px; background: #40424F; color: #ffffff; font-size: 14px;" 
                                    oninput="filtrarLotesModal()" autocomplete="off">
                            </div>
                            <div style="min-width: 120px; text-align: center;">
                                <div style="color: #ffffff; font-weight: 600; font-size: 13px;">Total:</div>
                                <div id="contadorLotesFiltrados" style="color: #ffffff; font-weight: bold; font-size: 16px;">${lotes.length}</div>
                            </div>
                        </div>
                        
                        <div class="table-responsive">
                            <table class="material-table">
                                <thead>
                                    <tr>
                                        <th style="width: 200px; padding: 12px 8px;">Lote</th>
                                        <th style="width: 150px; padding: 12px 8px; text-align: right;">Cantidad</th>
                                        <th style="width: 170px; padding: 12px 8px;">Fecha Recibo</th>
                                        <th style="width: 170px; padding: 12px 8px;">Ubicación</th>
                                        <th style="width: 100px; padding: 12px 8px; text-align: center;">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="tablaLotesBody">
                                    ${lotes.map(lote => `
                                        <tr class="fila-lote" data-lote="${lote.numero_lote.toLowerCase()}">
                                            <td style="width: 200px; padding: 12px 8px;">
                                                <code style="background: rgba(108, 117, 125, 0.3); color: #ffffff; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; display: inline-block; width: 100%; text-align: center;">
                                                    ${lote.numero_lote}
                                                </code>
                                            </td>
                                            <td style="width: 150px; padding: 12px 8px; text-align: right; font-weight: 600;" class="${lote.cantidad_disponible > 0 ? 'cantidad-ok' : 'cantidad-baja'}">${formatearNumero(lote.cantidad_disponible)}</td>
                                            <td style="width: 170px; padding: 12px 8px; font-size: 13px; color: #ffffff;">${formatearFecha(lote.fecha_recibo, true)}</td>
                                            <td style="width: 170px; padding: 12px 8px; font-size: 13px; color: #ffffff;">${lote.ubicacion_salida || 'N/E'}</td>
                                            <td style="width: 100px; padding: 12px 8px; text-align: center;">
                                                <button class="material-btn-small material-btn-info" onclick="verHistorialCompleto('${numeroParte}')" title="Ver Historial">
                                                    <i class="fas fa-history"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        
                        <!-- Mensaje cuando no hay resultados -->
                        <div id="noResultadosLotes" style="display: none; text-align: center; padding: 30px; color: #6c757d;">
                            <i class="fas fa-search" style="font-size: 36px; margin-bottom: 10px;"></i>
                            <p style="margin: 0; font-size: 14px;">No se encontraron lotes que coincidan con el filtro</p>
                        </div>
                        
                        <div class="modal-summary">
                            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                                <p><strong>Total de lotes:</strong> <span style="color: #ffffff; font-weight: 600;">${lotes.length}</span></p>
                                <p><strong>Cantidad total en inventario:</strong> <span style="color: #ffffff; font-weight: 600;">${formatearNumero(lotes.reduce((sum, lote) => sum + lote.cantidad_disponible, 0))}</span></p>
                            </div>
                        </div>
                    ` : `
                        <div class="no-data">
                            <i class="fas fa-box-open"></i>
                            <p>No se encontraron lotes disponibles para este número de parte</p>
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalContent);
    
    // Enfocar el campo de búsqueda después de crear el modal
    if (lotes.length > 0) {
        setTimeout(() => {
            const filtroInput = document.getElementById('filtroLotes');
            if (filtroInput) {
                filtroInput.focus();
            }
        }, 100);
    }
}

function mostrarModalHistorial(numeroParte, historial, balanceActual) {
    const modalContent = `
        <div class="trazabilidad-modal-overlay" onclick="cerrarModalGeneral(event)">
            <div class="trazabilidad-modal-content" onclick="event.stopPropagation()" style="max-width: 1200px;">
                <div class="trazabilidad-modal-header">
                    <h3>Historial de Movimientos - ${numeroParte}</h3>
                    <button class="close-btn" onclick="cerrarModalGeneral()">&times;</button>
                </div>
                <div class="trazabilidad-modal-body">
                    ${historial.length > 0 ? `
                        <div class="modal-summary" style="margin-bottom: 20px;">
                            <p><strong>Balance actual:</strong> <span class="${balanceActual > 0 ? 'cantidad-ok' : 'cantidad-baja'}">${formatearNumero(balanceActual)}</span></p>
                            <p><strong>Total de movimientos:</strong> ${historial.length}</p>
                        </div>
                        <div class="table-responsive">
                            <table class="material-table">
                                <thead>
                                    <tr>
                                        <th>Tipo</th>
                                        <th>Fecha</th>
                                        <th>Lote</th>
                                        <th>Cantidad</th>
                                        <th>Balance</th>
                                        <th>Código Material</th>
                                        <th>Detalle</th>
                                        <th>Especificación</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${historial.map(mov => `
                                        <tr>
                                            <td>
                                                <span class="tipo-movimiento ${mov.tipo_movimiento.toLowerCase()}">
                                                    ${mov.tipo_movimiento}
                                                </span>
                                            </td>
                                            <td class="fecha">${formatearFecha(mov.fecha_movimiento)}</td>
                                            <td><code>${mov.lote}</code></td>
                                            <td class="cantidad-col ${mov.cantidad >= 0 ? 'cantidad-entradas' : 'cantidad-salidas'}">
                                                ${mov.cantidad >= 0 ? '+' : ''}${formatearNumero(mov.cantidad)}
                                            </td>
                                            <td class="cantidad-col ${mov.balance_acumulado > 0 ? 'cantidad-ok' : 'cantidad-baja'}">
                                                ${formatearNumero(mov.balance_acumulado)}
                                            </td>
                                            <td><code style="font-size: 11px; background: rgba(108, 117, 125, 0.2); color: #6c757d; padding: 3px 6px; border-radius: 3px;">${mov.codigo_material_recibido || 'N/A'}</code></td>
                                            <td class="detalle-movimiento">${mov.detalle_movimiento}</td>
                                            <td class="especificacion" title="${mov.especificacion}">${mov.especificacion}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : `
                        <div class="no-data">
                            <i class="fas fa-history"></i>
                            <p>No se encontró historial para este número de parte</p>
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalContent);
}

// Función para filtrar lotes en el modal
function filtrarLotesModal() {
    const filtroTexto = document.getElementById('filtroLotes')?.value.toLowerCase() || '';
    const filas = document.querySelectorAll('.fila-lote');
    const noResultados = document.getElementById('noResultadosLotes');
    const contador = document.getElementById('contadorLotesFiltrados');
    
    let filasVisibles = 0;
    
    filas.forEach(fila => {
        const textoLote = fila.getAttribute('data-lote') || '';
        
        if (textoLote.includes(filtroTexto)) {
            fila.style.display = '';
            filasVisibles++;
        } else {
            fila.style.display = 'none';
        }
    });
    
    // Mostrar/ocultar mensaje de no resultados
    if (noResultados) {
        noResultados.style.display = filasVisibles === 0 ? 'block' : 'none';
    }
    
    // Actualizar contador
    if (contador) {
        contador.textContent = filasVisibles;
    }
}

function cerrarModalGeneral(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.querySelector('.trazabilidad-modal-overlay');
    if (modal) {
        modal.remove();
    }
}

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
window.verHistorialCompleto = verHistorialCompleto;
window.verLotesDetallados = verLotesDetallados;
window.mostrarModalLotes = mostrarModalLotes;
window.mostrarModalHistorial = mostrarModalHistorial;
window.cerrarModalGeneral = cerrarModalGeneral;
window.filtrarLotesModal = filtrarLotesModal;