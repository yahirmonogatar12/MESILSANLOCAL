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
        const totalLotes = item.total_lotes || 0;
        const lotesBoton = totalLotes > 0
            ? `<span class="badge bg-primary">${totalLotes} lotes</span>`
            : '<span class="badge bg-secondary">Sin lotes</span>';
        
        const lotesTooltip = `${totalLotes} lotes disponibles`;
        
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
                <td style="text-align: center; padding: 5px;">
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info btn-sm" onclick="event.stopPropagation(); verLotesDetallados('${item.numero_parte}')" title="Ver Lotes Detallados">
                            <i class="fas fa-boxes"></i>
                        </button>
                        <button class="btn btn-outline-warning btn-sm" onclick="event.stopPropagation(); verHistorialCompleto('${item.numero_parte}')" title="Ver Historial Completo">
                            <i class="fas fa-history"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Funciones para historial y lotes
function verHistorialCompleto(numeroParte) {
    console.log(`📈 Consultando historial completo para: ${numeroParte}`);
    
    fetch('/api/inventario/historial', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ numero_parte: numeroParte })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarModalHistorial(numeroParte, data.historial, data.balance_actual);
        } else {
            alert(`❌ Error al consultar historial: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Error al consultar historial');
    });
}

function verLotesDetallados(numeroParte) {
    console.log(`📦 Consultando lotes detallados para: ${numeroParte}`);
    
    fetch('/api/inventario/lotes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ numero_parte: numeroParte })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarModalLotes(numeroParte, data.lotes);
        } else {
            alert(`❌ Error al consultar lotes: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('❌ Error al consultar lotes');
    });
}

function mostrarModalLotes(numeroParte, lotes) {
    const modalContent = `
        <div class="trazabilidad-modal-overlay" onclick="cerrarModalGeneral(event)">
            <div class="trazabilidad-modal-content" onclick="event.stopPropagation()">
                <div class="trazabilidad-modal-header">
                    <h3>📦 Lotes Disponibles - ${numeroParte}</h3>
                    <button class="close-btn" onclick="cerrarModalGeneral()">&times;</button>
                </div>
                <div class="trazabilidad-modal-body">
                    ${lotes.length > 0 ? `
                        <div class="table-responsive">
                            <table class="material-table">
                                <thead>
                                    <tr>
                                        <th>Número de Lote</th>
                                        <th>Cantidad Original</th>
                                        <th>Total Salidas</th>
                                        <th>Cantidad Disponible</th>
                                        <th>Fecha Recibo</th>
                                        <th>Ubicación</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${lotes.map(lote => `
                                        <tr>
                                            <td><strong>${lote.numero_lote}</strong></td>
                                            <td class="cantidad-col">${formatearNumero(lote.cantidad_original)}</td>
                                            <td class="cantidad-col cantidad-salidas">${formatearNumero(lote.total_salidas)}</td>
                                            <td class="cantidad-col ${lote.cantidad_disponible > 0 ? 'cantidad-ok' : 'cantidad-baja'}">${formatearNumero(lote.cantidad_disponible)}</td>
                                            <td class="fecha">${formatearFecha(lote.fecha_recibo)}</td>
                                            <td>${lote.ubicacion_salida || 'No especificada'}</td>
                                            <td>
                                                <button class="material-btn material-btn-small material-btn-info" onclick="verHistorialCompleto('${numeroParte}')" title="Ver Historial">
                                                    <i class="fas fa-history"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        <div class="modal-summary">
                            <p><strong>Total de lotes:</strong> ${lotes.length}</p>
                            <p><strong>Cantidad total disponible:</strong> ${formatearNumero(lotes.reduce((sum, lote) => sum + lote.cantidad_disponible, 0))}</p>
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
}

function mostrarModalHistorial(numeroParte, historial, balanceActual) {
    const modalContent = `
        <div class="trazabilidad-modal-overlay" onclick="cerrarModalGeneral(event)">
            <div class="trazabilidad-modal-content" onclick="event.stopPropagation()" style="max-width: 1200px;">
                <div class="trazabilidad-modal-header">
                    <h3>📈 Historial de Movimientos - ${numeroParte}</h3>
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
                                        <th>Detalle</th>
                                        <th>Especificación</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${historial.map(mov => `
                                        <tr>
                                            <td>
                                                <span class="tipo-movimiento ${mov.tipo_movimiento.toLowerCase()}">
                                                    ${mov.tipo_movimiento === 'ENTRADA' ? '📥' : '📤'} ${mov.tipo_movimiento}
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

function cerrarModalGeneral(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.querySelector('.trazabilidad-modal-overlay');
    if (modal) {
        modal.remove();
    }
}

// Funciones auxiliares existentes (simplificadas)
function formatearNumero(numero) {
    return parseFloat(numero || 0).toLocaleString('es-ES', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatearFecha(fecha, corto = false) {
    if (!fecha) return '-';
    const date = new Date(fecha);
    if (corto) {
        return date.toLocaleDateString('es-ES');
    }
    return date.toLocaleDateString('es-ES') + ' ' + date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function setupInventarioModalEvents() {
    // Configuración básica de eventos
    console.log('📋 Configurando eventos de modales de inventario');
}

function actualizarInventarioContadorSeleccionados() {
    const totalCount = document.getElementById('registroTotalRows');
    const selectedCount = document.getElementById('registroSelectedCount');
    
    if (totalCount) {
        totalCount.textContent = inventarioGeneralData.length;
    }
    
    if (selectedCount) {
        selectedCount.textContent = inventarioSelectedItems.size;
    }
}

function toggleInventarioSelection(id) {
    if (inventarioSelectedItems.has(id)) {
        inventarioSelectedItems.delete(id);
    } else {
        inventarioSelectedItems.add(id);
    }
    
    actualizarInventarioContadorSeleccionados();
    renderizarInventarioTabla();
}

function seleccionarInventarioItem(id) {
    toggleInventarioSelection(id);
}

function toggleInventarioSelectAll() {
    const selectAllCheckbox = document.getElementById('registroSelectAll');
    
    if (selectAllCheckbox.checked) {
        inventarioGeneralData.forEach(item => {
            inventarioSelectedItems.add(item.id);
        });
    } else {
        inventarioSelectedItems.clear();
    }
    
    actualizarInventarioContadorSeleccionados();
    renderizarInventarioTabla();
}

function exportarInventarioExcel() {
    console.log('📊 Exportando inventario a Excel');
    const params = new URLSearchParams({
        tipo: 'inventario_general',
        formato: 'excel'
    });
    window.open(`/exportar_inventario?${params}`, '_blank');
}

function actualizarInventarioGeneral() {
    consultarInventarioGeneral();
}

function reiniciarInventarioSeleccion() {
    inventarioSelectedItems.clear();
    document.getElementById('registroSelectAll').checked = false;
    actualizarInventarioContadorSeleccionados();
    renderizarInventarioTabla();
}

function abrirFiltrosInventarioModal() {
    const modal = document.getElementById('registroImportModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function cerrarFiltrosInventarioModal() {
    const modal = document.getElementById('registroImportModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function aplicarFiltrosInventario() {
    const numeroParte = document.getElementById('filtroNumeroParte').value.trim();
    const propiedad = document.getElementById('filtroPropiedad').value.trim();
    const cantidadMinima = parseFloat(document.getElementById('filtroCantidadMinima').value) || 0;
    
    filtrosActivos = {
        numeroParte: numeroParte,
        propiedad: propiedad,
        cantidadMinima: cantidadMinima
    };
    
    consultarInventarioGeneral();
    cerrarFiltrosInventarioModal();
}

function limpiarFiltrosInventario() {
    document.getElementById('filtroNumeroParte').value = '';
    document.getElementById('filtroPropiedad').value = '';
    document.getElementById('filtroCantidadMinima').value = '0';
    
    filtrosActivos = {
        numeroParte: '',
        propiedad: '',
        cantidadMinima: 0
    };
    
    consultarInventarioGeneral();
}

// Inicialización cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    initRegistroMaterial();
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
window.verHistorialCompleto = verHistorialCompleto;
window.verLotesDetallados = verLotesDetallados;
window.mostrarModalLotes = mostrarModalLotes;
window.mostrarModalHistorial = mostrarModalHistorial;
window.cerrarModalGeneral = cerrarModalGeneral;
