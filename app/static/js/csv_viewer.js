// Variables globales - prevent redeclaration in dynamic loading
if (typeof window.csvViewerLoaded === 'undefined') {
    window.csvViewerLoaded = true;
    console.log('🔄 Loading CSV Viewer v3.4');

// Variables globales
var allData = [];
var filteredData = [];

// Configuración
var API_BASE = '/api';

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
        // Obtener carpeta seleccionada
        const folderSelect = document.getElementById('filterFolder');
        const selectedFolder = folderSelect.value;
        
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
            throw new Error(`Error HTTP ${dataResponse.status}: ${errorText}`);
        }
        
        if (!statsResponse.ok) {
            const errorText = await statsResponse.text();
            throw new Error(`Error HTTP ${statsResponse.status}: ${errorText}`);
        }

        const dataResult = await dataResponse.json().catch(err => {
            throw new Error('Error al parsear respuesta de datos como JSON');
        });
        
        const statsResult = await statsResponse.json().catch(err => {
            throw new Error('Error al parsear respuesta de estadÃ­sticas como JSON');
        });

        if (dataResult.success && statsResult.success) {
            allData = dataResult.data || [];
            filteredData = [...allData];
            
            actualizarEstadisticas(statsResult.stats);
            
            // Aplicar filtros automáticamente por fecha del día después de cargar
            aplicarFiltros();
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
    document.getElementById('statTotalRecords').textContent = stats.total_records || 0;
    document.getElementById('statOkCount').textContent = stats.ok_count || 0;
    document.getElementById('statNgCount').textContent = stats.ng_count || 0;
}

// Actualizar tabla con datos
function actualizarTabla() {
    const tbody = document.getElementById('csvTableBody');
    
    if (!filteredData || filteredData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="13" class="no-data">
                    No hay datos disponibles
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
    // Obtener carpeta seleccionada para incluir en filtros
    const folderSelect = document.getElementById('filterFolder');
    const selectedFolder = folderSelect.value;
    
    if (!selectedFolder) {
        return;
    }

    const filtros = {
        folder: selectedFolder,  // âœ… AGREGADO: Incluir carpeta en filtros
        partName: document.getElementById('filterPartName').value.trim(),
        result: document.getElementById('filterResult').value,
        dateFrom: document.getElementById('filterDateFrom').value,
        dateTo: document.getElementById('filterDateTo').value
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
    document.getElementById('filterPartName').value = '';
    document.getElementById('filterResult').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    
    filteredData = [...allData];
    actualizarTabla();
    actualizarContadorResultados();
}

// Establecer fecha actual en los filtros
function establecerFechaHoy() {
    const fechaHoy = new Date().toISOString().split('T')[0];
    document.getElementById('filterDateFrom').value = fechaHoy;
    document.getElementById('filterDateTo').value = fechaHoy;
    
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
    document.getElementById('csvResultText').textContent = texto;
}

// Utilidades de formato
function formatearFecha(fecha) {
    if (!fecha) return '';
    
    // Convertir a string y limpiar
    const fechaStr = fecha.toString().trim();
    
    // Si viene en formato YYYYMMDD (8 dÃ­gitos)
    if (fechaStr.length === 8 && /^\d{8}$/.test(fechaStr)) {
        const aÃ±o = fechaStr.substring(0, 4);
        const mes = fechaStr.substring(4, 6);
        const dia = fechaStr.substring(6, 8);
        return `${dia}/${mes}/${aÃ±o}`;
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
    
    // Si viene en formato HHMMSS (6 dÃ­gitos) o 5 dÃ­gitos
    if (horaStr.length >= 5 && /^\d+$/.test(horaStr)) {
        // Para formato de 5 dÃ­gitos como 84453, agregar un 0 al inicio
        const paddedHora = horaStr.padStart(6, '0');
        const h = paddedHora.substring(0, 2);
        const m = paddedHora.substring(2, 4);
        const s = paddedHora.substring(4, 6);
        const resultado = `${h}:${m}:${s}`;
        return resultado;
    }
    
    // Si viene en formato HHMM (4 dÃ­gitos)
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
    document.getElementById('csvLoadingModal').style.display = 'flex';
}

function ocultarModal() {
    document.getElementById('csvLoadingModal').style.display = 'none';
}

function mostrarAlerta(mensaje) {
    document.getElementById('csvAlertMessage').textContent = mensaje;
    document.getElementById('csvAlertModal').style.display = 'flex';
}

function hideCsvAlert() {
    document.getElementById('csvAlertModal').style.display = 'none';
}

// Eventos de teclado para filtros
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha actual en los filtros (por si no se ejecutÃ³ arriba)
    // Usar una fecha mÃ¡s amplia para mostrar mÃ¡s datos
    const fechaHoy = new Date().toISOString().split('T')[0];
    const fechaAyer = new Date(Date.now() - 2*24*60*60*1000).toISOString().split('T')[0]; // Hace 2 dÃ­as
    
    const dateFromField = document.getElementById('filterDateFrom');
    const dateToField = document.getElementById('filterDateTo');
    
    // Establecer un rango de fechas mÃ¡s amplio
    if (!dateFromField.value) dateFromField.value = fechaAyer;
    if (!dateToField.value) dateToField.value = fechaHoy;
    
    // Enter en campos de filtro
    document.getElementById('filterPartName').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') aplicarFiltros();
    });
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

} // End csvViewerLoaded check
