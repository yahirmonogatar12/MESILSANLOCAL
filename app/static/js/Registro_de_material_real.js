// Variables globales para el inventario general
let inventarioGeneralData = [];
let inventarioSelectedItems = new Set();
let filtrosActivos = {};
let filtrosHeaders = {};

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
    
    // Inicializar filtros de headers
    filtrosHeaders = {};
    
    // Cargar datos iniciales
    consultarInventarioGeneral();
    
    // Configurar eventos de los modales
    setupInventarioModalEvents();
    
    // Agregar event listener para cerrar filtros al hacer clic fuera
    document.addEventListener('click', function(event) {
        // Si el clic no es en un botón de filtro o dentro de un filtro
        if (!event.target.closest('.filter-btn') && !event.target.closest('.header-filter')) {
            // Cerrar todos los filtros
            document.querySelectorAll('.header-filter').forEach(filter => {
                filter.style.display = 'none';
            });
            
            // Remover clase active de todos los botones
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
        }
    });
    
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
                datosInventarioOriginal = [...data.inventario]; // Guardar copia para filtros
                renderizarInventarioTabla();
                actualizarInventarioContadorSeleccionados();
                
                // Poblar opciones de filtros con valores únicos
                setTimeout(() => {
                    poblarTodasLasOpcionesFiltros();
                }, 100);
            } else {
                console.error('Error al consultar inventario:', data.message);
                inventarioGeneralData = [];
                datosInventarioOriginal = [];
                renderizarInventarioTabla();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            inventarioGeneralData = [];
            datosInventarioOriginal = [];
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
                <i class="fas fa-search"></i> Ver Lotes
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
                        <!-- Filtros avanzados para lotes -->
                        <div class="lotes-filter-container" style="margin-bottom: 20px; background: rgba(74, 76, 90, 0.3); padding: 15px; border-radius: 8px; border-left: 4px solid #6c757d;">
                            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 15px; margin-bottom: 10px;">
                                <div>
                                    <label style="display: block; color: #ffffff; font-weight: 600; margin-bottom: 5px; font-size: 13px;">Buscar Lote:</label>
                                    <input type="text" id="filtroLotes" placeholder="Escriba el número de lote..." 
                                        style="width: 100%; padding: 8px 12px; border: 2px solid #6c757d; border-radius: 6px; background: #40424F; color: #ffffff; font-size: 14px;" 
                                        oninput="filtrarLotesModal()" autocomplete="off">
                                </div>
                                <div>
                                    <label style="display: block; color: #ffffff; font-weight: 600; margin-bottom: 5px; font-size: 13px;">Cantidad Mínima:</label>
                                    <input type="number" id="filtroCantidadMin" placeholder="0" min="0"
                                        style="width: 100%; padding: 8px 12px; border: 2px solid #6c757d; border-radius: 6px; background: #40424F; color: #ffffff; font-size: 14px;" 
                                        oninput="filtrarLotesModal()">
                                </div>
                                <div>
                                    <label style="display: block; color: #ffffff; font-weight: 600; margin-bottom: 5px; font-size: 13px;">Fecha Desde:</label>
                                    <input type="date" id="filtroFechaDesde"
                                        style="width: 100%; padding: 8px 12px; border: 2px solid #6c757d; border-radius: 6px; background: #40424F; color: #ffffff; font-size: 14px;" 
                                        onchange="filtrarLotesModal()">
                                </div>
                                <div>
                                    <label style="display: block; color: #ffffff; font-weight: 600; margin-bottom: 5px; font-size: 13px;">Fecha Hasta:</label>
                                    <input type="date" id="filtroFechaHasta"
                                        style="width: 100%; padding: 8px 12px; border: 2px solid #6c757d; border-radius: 6px; background: #40424F; color: #ffffff; font-size: 14px;" 
                                        onchange="filtrarLotesModal()">
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <button onclick="limpiarFiltrosLotes()" style="padding: 6px 12px; background: #6c757d; border: none; border-radius: 4px; color: white; cursor: pointer; font-size: 12px;">
                                    <i class="fas fa-broom"></i> Limpiar Filtros
                                </button>
                                <div style="text-align: center;">
                                    <div style="color: #ffffff; font-weight: 600; font-size: 13px;">Lotes Mostrados:</div>
                                    <div id="contadorLotesFiltrados" style="color: #ffffff; font-weight: bold; font-size: 16px;">${lotes.length}</div>
                                </div>
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

// Función para filtrar lotes en el modal (mejorada)
function filtrarLotesModal() {
    const filtroTexto = document.getElementById('filtroLotes')?.value.toLowerCase() || '';
    const filtroCantidadMin = parseFloat(document.getElementById('filtroCantidadMin')?.value) || 0;
    const filtroFechaDesde = document.getElementById('filtroFechaDesde')?.value || '';
    const filtroFechaHasta = document.getElementById('filtroFechaHasta')?.value || '';
    
    const filas = document.querySelectorAll('.fila-lote');
    const noResultados = document.getElementById('noResultadosLotes');
    const contador = document.getElementById('contadorLotesFiltrados');
    
    let filasVisibles = 0;
    
    filas.forEach(fila => {
        const textoLote = fila.getAttribute('data-lote') || '';
        const cantidadTexto = fila.querySelector('td:nth-child(2)')?.textContent || '0';
        const cantidad = parseFloat(cantidadTexto.replace(/[,\s]/g, '')) || 0;
        const fechaTexto = fila.querySelector('td:nth-child(3)')?.textContent || '';
        
        let mostrar = true;
        
        // Filtro por texto de lote
        if (filtroTexto && !textoLote.includes(filtroTexto)) {
            mostrar = false;
        }
        
        // Filtro por cantidad mínima
        if (filtroCantidadMin > 0 && cantidad < filtroCantidadMin) {
            mostrar = false;
        }
        
        // Filtro por fechas
        if (filtroFechaDesde || filtroFechaHasta) {
            // Convertir fecha del formato DD/MM/YY a Date
            const fechaParts = fechaTexto.split('/');
            if (fechaParts.length === 3) {
                const dia = parseInt(fechaParts[0]);
                const mes = parseInt(fechaParts[1]) - 1; // Los meses en JS van de 0-11
                const anio = 2000 + parseInt(fechaParts[2]); // Asumir 20xx
                const fechaLote = new Date(anio, mes, dia);
                
                if (filtroFechaDesde) {
                    const fechaDesde = new Date(filtroFechaDesde);
                    if (fechaLote < fechaDesde) mostrar = false;
                }
                
                if (filtroFechaHasta) {
                    const fechaHasta = new Date(filtroFechaHasta);
                    if (fechaLote > fechaHasta) mostrar = false;
                }
            }
        }
        
        if (mostrar) {
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

// Función para limpiar filtros de lotes
function limpiarFiltrosLotes() {
    document.getElementById('filtroLotes').value = '';
    document.getElementById('filtroCantidadMin').value = '';
    document.getElementById('filtroFechaDesde').value = '';
    document.getElementById('filtroFechaHasta').value = '';
    filtrarLotesModal();
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

// Variables globales para filtros
let datosInventarioOriginal = [];
// Variable filtrosActivos ya declarada anteriormente

// Función para togglear la visibilidad de un filtro específico
function toggleFiltro(campo) {
    const filtroDiv = document.getElementById(`filtro-${campo}`);
    const boton = document.querySelector(`[onclick="toggleFiltro('${campo}')"]`);
    
    if (!filtroDiv || !boton) {
        return;
    }
    
    // Cerrar otros filtros abiertos
    document.querySelectorAll('.header-filter').forEach(filter => {
        if (filter.id !== `filtro-${campo}`) {
            filter.style.display = 'none';
        }
    });
    
    // Remover clase active de otros botones
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn !== boton) {
            btn.classList.remove('active');
        }
    });
    
    // Toggle del filtro actual
    const isVisible = filtroDiv.style.display === 'block';
    
    if (!isVisible) {
        filtroDiv.style.display = 'block';
        boton.classList.add('active');
        
        // Poblar opciones si es necesario
        setTimeout(() => {
            poblarOpcionesFiltro(campo);
        }, 10);
    } else {
        filtroDiv.style.display = 'none';
        boton.classList.remove('active');
    }
}

// Función para aplicar filtro desde un header específico
function aplicarFiltroHeader(campo, valor) {
    filtrosHeaders[campo] = valor;
    
    // Marcar botón como activo si hay filtro aplicado
    const boton = document.querySelector(`[onclick="toggleFiltro('${campo}')"]`);
    if (valor && valor !== '') {
        boton.classList.add('active');
        boton.style.backgroundColor = '#3498db';
    } else {
        boton.classList.remove('active');
        boton.style.backgroundColor = '';
    }
    
    // Aplicar todos los filtros
    aplicarTodosLosFiltros();
    
    // Cerrar el dropdown del filtro
    document.getElementById(`filtro-${campo}`).style.display = 'none';
    boton.classList.remove('active');
}

// Función principal para aplicar todos los filtros
function aplicarTodosLosFiltros() {
    if (!datosInventarioOriginal.length) {
        console.log('No hay datos para filtrar');
        return;
    }
    
    // Función helper para manejar filtros de "Blanks" y "Non blanks"
    function aplicarFiltroBlank(valor, filtro) {
        if (filtro === "(Blanks)") {
            return !valor || valor === "" || valor === null || valor === undefined;
        }
        if (filtro === "(Non blanks)") {
            return valor && valor !== "" && valor !== null && valor !== undefined;
        }
        if (!filtro) return true; // Sin filtro
        return String(valor || '').toLowerCase().includes(String(filtro).toLowerCase());
    }
    
    // Función helper para filtros de fecha
    function aplicarFiltroFecha(fecha, filtro) {
        if (!filtro) return true;
        
        const fechaItem = new Date(fecha);
        const ahora = new Date();
        
        switch(filtro) {
            case "(Blanks)":
                return !fecha || fecha === "" || isNaN(fechaItem.getTime());
            case "(Non blanks)":
                return fecha && fecha !== "" && !isNaN(fechaItem.getTime());
            case "ultimos_30":
                const hace30Dias = new Date(ahora.getTime() - (30 * 24 * 60 * 60 * 1000));
                return fechaItem >= hace30Dias;
            case "ultimos_90":
                const hace90Dias = new Date(ahora.getTime() - (90 * 24 * 60 * 60 * 1000));
                return fechaItem >= hace90Dias;
            case "mas_antiguos":
                const hace6Meses = new Date(ahora.getTime() - (180 * 24 * 60 * 60 * 1000));
                return fechaItem < hace6Meses;
            case "este_ano":
                return fechaItem.getFullYear() === ahora.getFullYear();
            case "ano_pasado":
                return fechaItem.getFullYear() === (ahora.getFullYear() - 1);
            default:
                return true;
        }
    }
    
    // Aplicar filtros
    let datosFiltrados = datosInventarioOriginal.filter(item => {
        // Filtro por número de parte
        if (filtrosHeaders.numeroParte && !aplicarFiltroBlank(item.numero_parte, filtrosHeaders.numeroParte)) {
            return false;
        }
        
        // Filtro por código de material
        if (filtrosHeaders.codigoMaterial && !aplicarFiltroBlank(item.codigo_material, filtrosHeaders.codigoMaterial)) {
            return false;
        }
        
        // Filtro por especificación
        if (filtrosHeaders.especificacion && !aplicarFiltroBlank(item.especificacion, filtrosHeaders.especificacion)) {
            return false;
        }
        
        // Filtro por cantidad
        if (filtrosHeaders.cantidadTotal) {
            const cantidad = parseFloat(item.cantidad_total) || 0;
            switch(filtrosHeaders.cantidadTotal) {
                case 'positivo':
                    if (cantidad <= 0) return false;
                    break;
                case 'negativo':
                    if (cantidad >= 0) return false;
                    break;
                case 'cero':
                    if (cantidad !== 0) return false;
                    break;
                case '>=100':
                    if (cantidad < 100) return false;
                    break;
                case '>=500':
                    if (cantidad < 500) return false;
                    break;
                case '>=1000':
                    if (cantidad < 1000) return false;
                    break;
            }
        }
        
        // Filtro por lotes
        if (filtrosHeaders.lotes) {
            const numLotes = item.total_lotes || 0;
            switch(filtrosHeaders.lotes) {
                case 'con_lotes':
                    if (numLotes <= 0) return false;
                    break;
                case 'sin_lotes':
                    if (numLotes > 0) return false;
                    break;
                case 'muchos_lotes':
                    if (numLotes <= 5) return false;
                    break;
            }
        }
        
        // Filtro por fecha último recibo
        if (filtrosHeaders.ultimoRecibo && !aplicarFiltroFecha(item.fecha_ultimo_recibo, filtrosHeaders.ultimoRecibo)) {
            return false;
        }
        
        // Filtro por fecha primer recibo
        if (filtrosHeaders.primerRecibo && !aplicarFiltroFecha(item.fecha_primer_recibo, filtrosHeaders.primerRecibo)) {
            return false;
        }
        
        // Filtro por propiedad
        if (filtrosHeaders.propiedad && !aplicarFiltroBlank(item.propiedad_material, filtrosHeaders.propiedad)) {
            return false;
        }
        
        return true;
    });
    
    // Actualizar los datos mostrados y renderizar tabla
    inventarioGeneralData = datosFiltrados;
    renderizarInventarioTabla();
    actualizarContadorFiltrado(datosFiltrados.length, datosInventarioOriginal.length);
    
    console.log(`Filtros aplicados: ${datosFiltrados.length}/${datosInventarioOriginal.length} elementos mostrados`);
}

// Función para poblar opciones de un filtro específico
function poblarOpcionesFiltro(campo) {
    if (!datosInventarioOriginal.length) {
        return;
    }
    
    const select = document.querySelector(`#filtro-${campo} .filter-select`);
    if (!select) {
        return;
    }
    
    // Mapeo de campos a propiedades del objeto
    const campoMap = {
        'numeroParte': 'numero_parte',
        'codigoMaterial': 'codigo_material', 
        'especificacion': 'especificacion',
        'propiedad': 'propiedad_material'
    };
    
    const propiedadObjeto = campoMap[campo];
    if (!propiedadObjeto) {
        return;
    }
    
    // Obtener valores únicos
    const valoresUnicos = [...new Set(datosInventarioOriginal
        .map(item => item[propiedadObjeto])
        .filter(val => val && val !== "" && val !== null && val !== undefined)
    )].sort();
    
    // Guardar valor actual
    const valorActual = select.value;
    
    // Limpiar opciones existentes (mantener las primeras 3)
    const opciones = Array.from(select.options);
    opciones.forEach((opcion, index) => {
        if (index > 2) { // Mantener "Todos", "(No vacíos)", "(Vacíos)"
            opcion.remove();
        }
    });
    
    // Agregar valores únicos
    valoresUnicos.forEach(valor => {
        const option = document.createElement('option');
        option.value = valor;
        option.textContent = valor.length > 30 ? valor.substring(0, 30) + '...' : valor;
        option.title = valor; // Tooltip completo
        select.appendChild(option);
    });
    
    // Restaurar valor si aún existe
    if (valorActual && Array.from(select.options).some(opt => opt.value === valorActual)) {
        select.value = valorActual;
    }
}

// Función para limpiar todos los filtros
function limpiarTodosLosFiltros() {
    // Limpiar objeto de filtros
    filtrosHeaders = {};
    
    // Resetear todos los selectores
    document.querySelectorAll('.filter-select').forEach(select => {
        select.value = '';
    });
    
    // Remover estado activo de botones
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.backgroundColor = '';
    });
    
    // Cerrar todos los filtros
    document.querySelectorAll('.header-filter').forEach(filter => {
        filter.style.display = 'none';
    });
    
    // Resetear datos y renderizar tabla completa
    inventarioGeneralData = [...datosInventarioOriginal];
    renderizarInventarioTabla();
    actualizarContadorFiltrado(datosInventarioOriginal.length, datosInventarioOriginal.length);
    
    console.log('Todos los filtros han sido limpiados');
}

// Función para actualizar contador con información de filtrado
function actualizarContadorFiltrado(filtrados, total) {
    const totalSpan = document.getElementById('registroTotalRows');
    const selectedSpan = document.getElementById('registroSelectedCount');
    
    if (totalSpan) {
        if (filtrados < total) {
            totalSpan.innerHTML = `${filtrados} <small style="color: #f39c12;">(de ${total})</small>`;
        } else {
            totalSpan.textContent = total;
        }
    }
    
    if (selectedSpan) {
        const seleccionados = Array.from(inventarioSelectedItems).filter(id => 
            inventarioGeneralData.some(item => item.id === id)
        ).length;
        selectedSpan.textContent = seleccionados;
    }
}

// Función para poblar todas las opciones de filtros
function poblarTodasLasOpcionesFiltros() {
    const campos = ['numeroParte', 'codigoMaterial', 'especificacion', 'propiedad'];
    campos.forEach(campo => {
        poblarOpcionesFiltro(campo);
    });
}

// Función para renderizar tabla (modificada para manejar filtros)
function renderizarTablaInventario(datos) {
    const tbody = document.getElementById('registroMaterialTableBody');
    if (!tbody) return;
    
    if (!datos || datos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="loading-row">
                    <i class="fas fa-search"></i>
                    ${filtrosActivos ? 'No se encontraron resultados con los filtros aplicados' : 'No hay datos de inventario disponibles'}
                </td>
            </tr>
        `;
        actualizarContadores(0, 0);
        return;
    }
    
    // Usar la función existente para renderizar filas
    tbody.innerHTML = datos.map(item => crearFilaInventario(item)).join('');
    
    // Actualizar contadores
    actualizarContadores(datos.length, 0);
}

// Función para crear fila de inventario (extraída del código existente)
function crearFilaInventario(item) {
    // Funciones auxiliares del código original
    function formatearNumero(numero) {
        if (numero === null || numero === undefined || numero === '') return '0';
        const num = parseFloat(numero);
        return isNaN(num) ? '0' : num.toLocaleString('es-ES', { maximumFractionDigits: 0 });
    }
    
    function crearCelda(valor, maxLength = 20) {
        const valorStr = String(valor || '');
        if (valorStr.length > maxLength) {
            return `<td data-full-text="${valorStr}" title="${valorStr}">${valorStr.substring(0, maxLength)}...</td>`;
        }
        return `<td>${valorStr}</td>`;
    }
    
    // Código del botón de lotes
    const totalLotes = item.total_lotes || 0;
    const lotesBoton = totalLotes > 0
        ? `<button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); verDetallesLotes('${item.numero_parte}')" style="font-size: 11px; padding: 2px 8px;">
            <i class="fas fa-search"></i> Ver Lotes
           </button>`
        : '<small class="text-muted">Sin lotes</small>';
    
    const lotesTooltip = `${totalLotes} lotes disponibles. Haz clic para ver detalles.`;
    
    // Código de cantidad y estado
    const remanente = parseFloat(item.cantidad_total) || 0;
    const entradas = item.total_entradas || 0;
    const salidas = item.total_salidas || 0;
    const cantidadTooltip = `Entradas: ${formatearNumero(entradas)}\\nSalidas: ${formatearNumero(salidas)}\\nDisponible: ${formatearNumero(remanente)}`;
    
    let statusClass, statusIcon;
    if (remanente > 0) {
        statusClass = 'cantidad-ok';
        statusIcon = '';
    } else if (remanente < 0) {
        statusClass = 'cantidad-baja';
        statusIcon = '';
    } else {
        statusClass = 'cantidad-cero';
        statusIcon = '';
    }
    
    // Crear fila
    return `
        <tr class="inventario-row ${statusClass}" data-numero-parte="${item.numero_parte}">
            <td class="inventario-checkbox-column">
                <input type="checkbox" class="inventario-checkbox" value="${item.numero_parte}">
            </td>
            ${crearCelda(item.numero_parte, 15)}
            ${crearCelda(item.codigo_material, 20)}
            ${crearCelda(item.especificacion, 25)}
            <td class="cantidad-cell" title="${cantidadTooltip}">
                <span class="cantidad-valor ${statusClass}">
                    ${statusIcon} ${formatearNumero(remanente)}
                </span>
            </td>
            <td class="lotes-cell" title="${lotesTooltip}">
                ${lotesBoton}
            </td>
            <td>${item.fecha_ultimo_recibo || 'N/A'}</td>
            <td>${item.fecha_primer_recibo || 'N/A'}</td>
            <td>${item.propiedad_material || 'N/A'}</td>
            <td class="acciones-cell">
                <button class="btn btn-sm btn-outline-info" onclick="verHistorialCompleto('${item.numero_parte}')" style="font-size: 11px; padding: 2px 8px;">
                    <i class="fas fa-history"></i> Historial
                </button>
            </td>
        </tr>
    `;
}

// Función para actualizar contadores
function actualizarContadores(total, seleccionados) {
    const totalElement = document.getElementById('registroTotalRows');
    const selectedElement = document.getElementById('registroSelectedCount');
    
    if (totalElement) totalElement.textContent = total;
    if (selectedElement) selectedElement.textContent = seleccionados;
}

// Exponer funciones globalmente
window.toggleFiltro = toggleFiltro;
window.aplicarFiltroHeader = aplicarFiltroHeader;
window.aplicarTodosLosFiltros = aplicarTodosLosFiltros;
window.limpiarTodosLosFiltros = limpiarTodosLosFiltros;
window.poblarOpcionesFiltro = poblarOpcionesFiltro;
window.poblarTodasLasOpcionesFiltros = poblarTodasLasOpcionesFiltros;
window.actualizarContadorFiltrado = actualizarContadorFiltrado;
window.limpiarFiltrosLotes = limpiarFiltrosLotes;