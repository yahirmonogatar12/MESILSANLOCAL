// Variables globales - prevent redeclaration in dynamic loading
if (typeof window.csvViewerLoaded === 'undefined') {
    window.csvViewerLoaded = true;
    console.log(' Loading CSV Viewer v3.5 - SMT Compatible');

// Variables globales
var allData = [];
var filteredData = [];

// Configuración
var API_BASE = '/api';

// === FUNCIONES AUXILIARES PARA COMPATIBILIDAD CON IDs CON SUFIJO ===

// Función auxiliar para obtener elemento por ID con flexibilidad para sufijos
function getElementByIdFlexible(baseId) {
    // Intentar primero con sufijo -smt
    let element = document.getElementById(baseId + '-smt');
    if (element) return element;
    
    // Si no existe, intentar sin sufijo
    element = document.getElementById(baseId);
    return element;
}

// Función auxiliar para obtener múltiples elementos con flexibilidad
function getElementsFlexible(baseIds) {
    const elements = {};
    baseIds.forEach(id => {
        elements[id] = getElementByIdFlexible(id);
    });
    return elements;
}

// InicializaciÃ³n cuando se carga la pÃ¡gina
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha actual en los filtros de fecha
    const fechaHoy = new Date().toISOString().split('T')[0]; // Formato YYYY-MM-DD
    document.getElementById('filterDateFrom').value = fechaHoy;
    document.getElementById('filterDateTo').value = fechaHoy;
    
    // No cargar datos automÃ¡ticamente al inicio
});

// âœ… FUNCIÃ“N DE DEBUG - Para probar la carga
async function probarCarga() {
    try {
        const url = '/api/csv_data?folder=2line/L2%20m2';
        
        const response = await fetch(url);
        
        if (response.ok) {
            const data = await response.json();
        } else {
            const errorText = await response.text();
        }
    } catch (error) {
        // Error de red
    }
}

// FunciÃ³n principal para cargar datos
async function cargarDatosCSV() {
    mostrarModal();
    try {
        // Obtener carpeta seleccionada usando función auxiliar
        const folderSelect = getElementByIdFlexible('filterFolder');
        const selectedFolder = folderSelect ? folderSelect.value : '';
        
        if (!selectedFolder) {
            mostrarAlerta('Por favor seleccione una lÃ­nea/mounter para cargar los datos');
            return;
        }
        
        // Verificar que las fechas estÃ©n establecidas, si no, usar fecha actual
        const fechaHoy = new Date().toISOString().split('T')[0];
        const dateFromField = document.getElementById('filterDateFrom');
        const dateToField = document.getElementById('filterDateTo');
        
        if (!dateFromField.value) dateFromField.value = fechaHoy;
        if (!dateToField.value) dateToField.value = fechaHoy;
        
        // Cargar datos y estadÃ­sticas en paralelo con filtro de carpeta
        const [dataResponse, statsResponse] = await Promise.all([
            fetch(`${API_BASE}/csv_data?folder=${encodeURIComponent(selectedFolder)}`).catch(err => {
                throw new Error(`Error de red al cargar datos: ${err.message}`);
            }),
            fetch(`${API_BASE}/csv_stats?folder=${encodeURIComponent(selectedFolder)}`).catch(err => {
                throw new Error(`Error de red al cargar estadÃ­sticas: ${err.message}`);
            })
        ]);

        if (!dataResponse.ok) {
            const errorText = await dataResponse.text();
            console.error('Error HTTP en datos:', dataResponse.status, errorText);
            throw new Error(`Error HTTP ${dataResponse.status}: ${errorText}`);
        }
        
        if (!statsResponse.ok) {
            const errorText = await statsResponse.text();
            console.error('Error HTTP en estadisticas:', statsResponse.status, errorText);
            throw new Error(`Error HTTP ${statsResponse.status}: ${errorText}`);
        }

        const dataResult = await dataResponse.json().catch(err => {
            console.error('Error parseando respuesta de datos:', err);
            console.error('Contenido de respuesta:', dataResponse);
            throw new Error('Error al parsear respuesta de datos como JSON. Verifique los logs del servidor.');
        });
        
        const statsResult = await statsResponse.json().catch(err => {
            console.error('Error parseando respuesta de estadisticas:', err);
            console.error('Contenido de respuesta:', statsResponse);
            throw new Error('Error al parsear respuesta de estadisticas como JSON. Verifique los logs del servidor.');
        });

        if (dataResult.success && statsResult.success) {
            allData = dataResult.data || [];
            filteredData = [...allData];
            
            actualizarEstadisticas(statsResult.stats);
            
            if (allData.length === 0) {
                // Si no hay datos, mostrar mensaje informativo
                const folderName = selectedFolder.split('/').pop();
                mostrarAlerta(`No hay archivos CSV disponibles en ${folderName}. Seleccione otra línea/mounter.`);
                actualizarTabla(); // Esto mostrará "No hay datos disponibles"
                actualizarContadorResultados();
            } else {
                // Aplicar filtros automáticamente por fecha del día después de cargar
                aplicarFiltros();
            }
        } else {
            const errorMsg = dataResult.error || statsResult.error || 'Error desconocido en la respuesta del servidor';
            throw new Error(errorMsg);
        }
    } catch (error) {
        mostrarAlerta(`Error al cargar los datos CSV: ${error.message}`);
    } finally {
        ocultarModal();
    }
}

// Actualizar estadÃ­sticas en el panel (solo las que quedan)
function actualizarEstadisticas(stats) {
    const elements = getElementsFlexible(['statTotalRecords', 'statOkCount', 'statNgCount']);
    
    if (elements.statTotalRecords) elements.statTotalRecords.textContent = stats.total_records || 0;
    if (elements.statOkCount) elements.statOkCount.textContent = stats.ok_count || 0;
    if (elements.statNgCount) elements.statNgCount.textContent = stats.ng_count || 0;
}

// Actualizar tabla con datos
function actualizarTabla() {
    const tbody = getElementByIdFlexible('csvTableBody');
    
    if (!tbody) {
        console.error('❌ No se encontró el elemento tbody de la tabla');
        return;
    }
    
    if (!filteredData || filteredData.length === 0) {
        const folderSelect = getElementByIdFlexible('filterFolder');
        const selectedFolder = folderSelect ? folderSelect.value : '';
        let mensaje = 'No hay datos disponibles';
        
        if (selectedFolder) {
            const folderName = selectedFolder.split('/').pop();
            mensaje = `No hay datos disponibles para ${folderName}`;
        }
        
        tbody.innerHTML = `
            <tr>
                <td colspan="13" class="no-data">
                    ${mensaje}
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    filteredData.forEach((row, index) => {
        const resultClass = row.Result === 'OK' ? 'result-ok' : 'result-ng';
        
        html += `
            <tr class="${resultClass}">
                <td class="col-index">${index + 1}</td>
                <td class="col-scandate">${formatearFecha(row.ScanDate) || '-'}</td>
                <td class="col-scantime">${formatearHora(row.ScanTime) || '-'}</td>
                <td class="col-slotno">${row.SlotNo || '-'}</td>
                <td class="col-result">
                    <span class="result-badge ${resultClass}">${row.Result || '-'}</span>
                </td>
                <td class="col-partname">${row.PartName || '-'}</td>
                <td class="col-quantity">${row.Quantity || '-'}</td>
                <td class="col-vendor">${row.Vendor || '-'}</td>
                <td class="col-lotno">${row.LOTNO || '-'}</td>
                <td class="col-barcode">${row.Barcode || '-'}</td>
                <td class="col-feederbase">${row.FeederBase || '-'}</td>
                <td class="col-previousbarcode">${row.PreviousBarcode || '-'}</td>
                <td class="col-sourcefile">${row.SourceFile || '-'}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

// Aplicar filtros
async function aplicarFiltros() {
    // Obtener carpeta seleccionada para incluir en filtros usando función auxiliar
    const folderSelect = getElementByIdFlexible('filterFolder');
    const selectedFolder = folderSelect ? folderSelect.value : '';
    
    if (!selectedFolder) {
        return;
    }

    // Obtener elementos de filtro usando función auxiliar
    const elements = getElementsFlexible(['filterPartName', 'filterResult', 'filterDateFrom', 'filterDateTo']);

    const filtros = {
        folder: selectedFolder,  // âœ… AGREGADO: Incluir carpeta en filtros
        partName: elements.filterPartName ? elements.filterPartName.value.trim() : '',
        result: elements.filterResult ? elements.filterResult.value : '',
        dateFrom: elements.filterDateFrom ? elements.filterDateFrom.value : '',
        dateTo: elements.filterDateTo ? elements.filterDateTo.value : ''
    };

    try {
        const response = await fetch(`${API_BASE}/filter_data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filtros)
        });

        if (!response.ok) {
            throw new Error('Error al aplicar filtros');
        }

        const result = await response.json();
        
        if (result.success) {
            filteredData = result.data;
            
            // Si no hay resultados con el filtro de fecha actual, intentar con rango mÃ¡s amplio
            if (filteredData.length === 0 && (filtros.dateFrom || filtros.dateTo)) {
                // Usar rango de fechas mÃ¡s amplio (Ãºltimos 7 dÃ­as)
                const hoy = new Date();
                const hace7dias = new Date(hoy.getTime() - 7*24*60*60*1000);
                
                const filtrosAmpliados = {
                    ...filtros,
                    dateFrom: hace7dias.toISOString().split('T')[0],
                    dateTo: hoy.toISOString().split('T')[0]
                };
                
                const responseAmpliado = await fetch(`${API_BASE}/filter_data`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(filtrosAmpliados)
                });
                
                if (responseAmpliado.ok) {
                    const resultAmpliado = await responseAmpliado.json();
                    if (resultAmpliado.success && resultAmpliado.data.length > 0) {
                        filteredData = resultAmpliado.data;
                        
                        // Actualizar los campos de fecha en la interfaz
                        document.getElementById('filterDateFrom').value = filtrosAmpliados.dateFrom;
                        document.getElementById('filterDateTo').value = filtrosAmpliados.dateTo;
                    }
                }
            }
            
            actualizarTabla();
            actualizarContadorResultados();
        } else {
            throw new Error(result.error || 'Error al filtrar datos');
        }
    } catch (error) {
        mostrarAlerta('Error al aplicar filtros: ' + error.message);
    }
}// Limpiar filtros
function limpiarFiltros() {
    const elements = getElementsFlexible(['filterPartName', 'filterResult', 'filterDateFrom', 'filterDateTo']);
    
    if (elements.filterPartName) elements.filterPartName.value = '';
    if (elements.filterResult) elements.filterResult.value = '';
    if (elements.filterDateFrom) elements.filterDateFrom.value = '';
    if (elements.filterDateTo) elements.filterDateTo.value = '';
    
    filteredData = [...allData];
    actualizarTabla();
    actualizarContadorResultados();
}

// Establecer fecha actual en los filtros
function establecerFechaHoy() {
    const fechaHoy = new Date().toISOString().split('T')[0];
    const elements = getElementsFlexible(['filterDateFrom', 'filterDateTo']);
    
    if (elements.filterDateFrom) elements.filterDateFrom.value = fechaHoy;
    if (elements.filterDateTo) elements.filterDateTo.value = fechaHoy;
    
    // Aplicar filtros automÃ¡ticamente despuÃ©s de establecer la fecha
    if (allData.length > 0) {
        aplicarFiltros();
    }
}

// Exportar datos
function exportarDatos() {
    if (!filteredData || filteredData.length === 0) {
        mostrarAlerta('No hay datos para exportar');
        return;
    }

    try {
        // Crear CSV
        const headers = [
            'Fecha Escaneo', 'Hora', 'Slot', 'Resultado', 'NÃºmero Parte',
            'Cantidad', 'Vendor', 'Lote', 'CÃ³digo Barras', 'Feeder',
            'CÃ³digo Anterior', 'Archivo Origen'
        ];
        
        const csvContent = [
            headers.join(','),
            ...filteredData.map(row => [
                formatearFecha(row.ScanDate),
                formatearHora(row.ScanTime),
                row.SlotNo,
                row.Result,
                row.PartName,
                row.Quantity,
                row.Vendor,
                row.LOTNO,
                row.Barcode,
                row.FeederBase,
                row.PreviousBarcode,
                row.SourceFile
            ].map(cell => `"${cell || ''}"`).join(','))
        ].join('\n');

        // Descargar archivo
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `logs_csv_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        mostrarAlerta('Datos exportados correctamente');
    } catch (error) {
        mostrarAlerta('Error al exportar datos');
    }
}

// Actualizar contador de resultados
function actualizarContadorResultados() {
    const totalRegistros = filteredData.length;
    const okCount = filteredData.filter(row => row.Result === 'OK').length;
    const ngCount = filteredData.filter(row => row.Result === 'NG').length;
    
    const texto = `Mostrando ${totalRegistros} registros | OK: ${okCount} | NG: ${ngCount}`;
    const textElement = getElementByIdFlexible('csvResultText');
    if (textElement) textElement.textContent = texto;
}

// Utilidades de formato
function formatearFecha(fecha) {
    if (!fecha) return '';
    
    // Convertir a string y limpiar
    const fechaStr = fecha.toString().trim();
    
    // Si viene en formato YYYYMMDD (8 digitos)
    if (fechaStr.length === 8 && /^\d{8}$/.test(fechaStr)) {
        const ano = fechaStr.substring(0, 4);
        const mes = fechaStr.substring(4, 6);
        const dia = fechaStr.substring(6, 8);
        return `${dia}/${mes}/${ano}`;
    }
    
    // Si ya tiene formato de fecha (contiene /)
    if (fechaStr.includes('/')) {
        return fechaStr;
    }
    
    // Si tiene formato con guiones
    if (fechaStr.includes('-')) {
        const partes = fechaStr.split('-');
        if (partes.length === 3) {
            return `${partes[2]}/${partes[1]}/${partes[0]}`;
        }
    }
    
    return fecha;
}

function formatearHora(hora) {
    if (!hora) return '';
    
    // Convertir a string y limpiar
    const horaStr = hora.toString().trim();
    
    // Si viene en formato HHMMSS (6 digitos) o 5 digitos
    if (horaStr.length >= 5 && /^\d+$/.test(horaStr)) {
        // Para formato de 5 digitos como 84453, agregar un 0 al inicio
        const paddedHora = horaStr.padStart(6, '0');
        const h = paddedHora.substring(0, 2);
        const m = paddedHora.substring(2, 4);
        const s = paddedHora.substring(4, 6);
        const resultado = `${h}:${m}:${s}`;
        return resultado;
    }
    
    // Si viene en formato HHMM (4 digitos)
    if (horaStr.length === 4 && /^\d+$/.test(horaStr)) {
        const h = horaStr.substring(0, 2);
        const m = horaStr.substring(2, 4);
        const resultado = `${h}:${m}`;
        return resultado;
    }
    
    // Si ya tiene formato de hora (contiene :)
    if (horaStr.includes(':')) {
        return horaStr;
    }
    
    // Si es muy corto, pad con ceros
    if (horaStr.length < 4 && /^\d+$/.test(horaStr)) {
        const paddedHora = horaStr.padStart(4, '0');
        const h = paddedHora.substring(0, 2);
        const m = paddedHora.substring(2, 4);
        const resultado = `${h}:${m}`;
        return resultado;
    }
    
    return hora;
}

// Modales y alertas
function mostrarModal() {
    const modal = getElementByIdFlexible('csvLoadingModal');
    if (modal) modal.style.display = 'flex';
}

function ocultarModal() {
    const modal = getElementByIdFlexible('csvLoadingModal');
    if (modal) modal.style.display = 'none';
}

function mostrarAlerta(mensaje) {
    const messageElement = getElementByIdFlexible('csvAlertMessage');
    const modalElement = getElementByIdFlexible('csvAlertModal');
    
    if (messageElement) messageElement.textContent = mensaje;
    if (modalElement) modalElement.style.display = 'flex';
}

function hideCsvAlert() {
    const modalElement = getElementByIdFlexible('csvAlertModal');
    if (modalElement) modalElement.style.display = 'none';
}

// Eventos de teclado para filtros
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha actual en los filtros (por si no se ejecutÃ³ arriba)
    // Usar una fecha mÃ¡s amplia para mostrar mÃ¡s datos
    const fechaHoy = new Date().toISOString().split('T')[0];
    const fechaAyer = new Date(Date.now() - 2*24*60*60*1000).toISOString().split('T')[0]; // Hace 2 dÃ­as
    
    const dateFromField = getElementByIdFlexible('filterDateFrom');
    const dateToField = getElementByIdFlexible('filterDateTo');
    
    if (dateFromField) dateFromField.value = fechaHoy;
    if (dateToField) dateToField.value = fechaHoy;
    
    // Establecer un rango de fechas mÃ¡s amplio
    if (dateFromField && !dateFromField.value) dateFromField.value = fechaAyer;
    if (dateToField && !dateToField.value) dateToField.value = fechaHoy;
    
    // Enter en campos de filtro
    const partNameField = getElementByIdFlexible('filterPartName');
    if (partNameField) {
        partNameField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') aplicarFiltros();
        });
    }
});

// Nueva funciÃ³n para cargar datos cuando se selecciona una carpeta
function cargarDatosPorCarpeta() {
    const folderSelect = document.getElementById('filterFolder');
    const selectedFolder = folderSelect.value;
    
    if (selectedFolder) {
        // Establecer fechas amplias para mostrar todos los datos disponibles
        const hoy = new Date();
        const hace30dias = new Date(hoy.getTime() - 30*24*60*60*1000);
        
        document.getElementById('filterDateFrom').value = hace30dias.toISOString().split('T')[0];
        document.getElementById('filterDateTo').value = hoy.toISOString().split('T')[0];
        
        cargarDatosCSV();
    } else {
        // Limpiar datos si no hay carpeta seleccionada
        allData = [];
        filteredData = [];
        actualizarTabla();
        actualizarEstadisticas({
            total_records: 0,
            ok_count: 0,
            ng_count: 0
        });
        document.getElementById('csvResultText').textContent = 'Seleccione línea/mounter para cargar datos';
    }
}

// Hacer funciones globalmente accesibles
window.cargarDatosPorCarpeta = cargarDatosPorCarpeta;
window.cargarDatosCSV = cargarDatosCSV;
window.aplicarFiltros = aplicarFiltros;
window.limpiarFiltros = limpiarFiltros;
window.establecerFechaHoy = establecerFechaHoy;
window.exportarDatos = exportarDatos;
window.hideCsvAlert = hideCsvAlert;

// === FUNCIONES CON SUFIJOS ÚNICOS PARA EVITAR CONFLICTOS EN CARGA AJAX ===

// Funciones con sufijo _smt para uso específico en carga dinámica
window.cargarDatosCSV_smt = function() {
    // Redirigir IDs únicos a las funciones originales
    const originalFilterFolder = document.getElementById('filterFolder');
    const smtFilterFolder = document.getElementById('filterFolder-smt');
    
    if (smtFilterFolder && originalFilterFolder) {
        // Temporalmente cambiar los IDs para que las funciones originales funcionen
        const originalId = originalFilterFolder.id;
        originalFilterFolder.id = 'temp-folder-id';
        smtFilterFolder.id = 'filterFolder';
        
        // Llamar función original
        cargarDatosCSV().then(() => {
            // Restaurar IDs
            smtFilterFolder.id = 'filterFolder-smt';
            originalFilterFolder.id = originalId;
        }).catch(() => {
            // Restaurar IDs en caso de error
            smtFilterFolder.id = 'filterFolder-smt';
            originalFilterFolder.id = originalId;
        });
    } else {
        cargarDatosCSV();
    }
};

window.cargarDatosPorCarpeta_smt = function() {
    cargarDatosCSV_smt();
};

window.aplicarFiltros_smt = function() {
    aplicarFiltros();
};

window.limpiarFiltros_smt = function() {
    limpiarFiltros();
};

window.establecerFechaHoy_smt = function() {
    establecerFechaHoy();
};

window.exportarDatos_smt = function() {
    exportarDatos();
};

window.hideCsvAlert_smt = function() {
    hideCsvAlert();
};

// Función específica para inicializar el módulo SMT en carga AJAX
window.initHistorialSMTModule = function() {
    console.log('🚀 Inicializando módulo Historial SMT con IDs únicos');
    
    // Verificar que todos los elementos con sufijo -smt existan
    const elements = [
        'csvStatsPanel-smt',
        'btnRefreshData-smt', 
        'filterFolder-smt',
        'csvDataTable-smt',
        'csvTableBody-smt'
    ];
    
    let allElementsFound = true;
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(` Elemento ${id} no encontrado`);
            allElementsFound = false;
        }
    });
    
    if (allElementsFound) {
        console.log(' Todos los elementos SMT encontrados correctamente');
        
        // Establecer fecha actual en los campos de fecha con sufijo
        const fechaHoy = new Date().toISOString().split('T')[0];
        const fechaDesde = document.getElementById('filterDateFrom-smt');
        const fechaHasta = document.getElementById('filterDateTo-smt');
        
        if (fechaDesde) fechaDesde.value = fechaHoy;
        if (fechaHasta) fechaHasta.value = fechaHoy;
        
        console.log(' Fechas establecidas en campos SMT');
    }
    
    return allElementsFound;
};

console.log('Funciones CSV disponibles globalmente:', {
    cargarDatosPorCarpeta: typeof window.cargarDatosPorCarpeta,
    cargarDatosCSV: typeof window.cargarDatosCSV,
    aplicarFiltros: typeof window.aplicarFiltros,
    // Nuevas funciones con sufijo
    cargarDatosCSV_smt: typeof window.cargarDatosCSV_smt,
    initHistorialSMTModule: typeof window.initHistorialSMTModule
});

} // End csvViewerLoaded check
