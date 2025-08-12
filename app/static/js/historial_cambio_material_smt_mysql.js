// Variables globales
let datosActuales = [];
let datosFiltrados = [];

// Función principal para cargar datos desde MySQL
async function cargarDatosCSV() {
    mostrarModal();
    actualizarContador('Cargando datos...');
    
    try {
        const response = await fetch('/api/smt/historial/data');
        const result = await response.json();
        
        if (result.success) {
            datosActuales = result.data;
            datosFiltrados = [...datosActuales];
            
            // Actualizar estadísticas
            actualizarEstadisticas(result.stats);
            
            // Mostrar datos en la tabla
            mostrarDatosEnTabla(datosFiltrados);
            
            actualizarContador(`${result.stats.total} registros encontrados`);
        } else {
            mostrarAlerta('Error al cargar datos: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al conectar con el servidor', 'error');
    } finally {
        ocultarModal();
    }
}

// Función para cargar datos por carpeta (línea/mounter)
async function cargarDatosPorCarpeta() {
    const selectFolder = document.getElementById('filterFolder');
    const folder = selectFolder.value;
    
    if (!folder) {
        mostrarAlerta('Por favor seleccione una línea y mounter', 'warning');
        return;
    }
    
    mostrarModal();
    actualizarContador('Cargando datos...');
    
    try {
        const response = await fetch(`/api/smt/historial/data?folder=${encodeURIComponent(folder)}`);
        const result = await response.json();
        
        if (result.success) {
            datosActuales = result.data;
            datosFiltrados = [...datosActuales];
            
            // Actualizar estadísticas
            actualizarEstadisticas(result.stats);
            
            // Mostrar datos en la tabla
            mostrarDatosEnTabla(datosFiltrados);
            
            actualizarContador(`${result.stats.total} registros encontrados`);
        } else {
            mostrarAlerta('Error al cargar datos: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al conectar con el servidor', 'error');
    } finally {
        ocultarModal();
    }
}

// Función para aplicar filtros
async function aplicarFiltros() {
    const folder = document.getElementById('filterFolder').value;
    const partName = document.getElementById('filterPartName').value;
    const result = document.getElementById('filterResult').value;
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    
    mostrarModal();
    actualizarContador('Aplicando filtros...');
    
    try {
        // Construir query string
        const params = new URLSearchParams();
        if (folder) params.append('folder', folder);
        if (partName) params.append('part_name', partName);
        if (result) params.append('result', result);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        const response = await fetch(`/api/smt/historial/data?${params.toString()}`);
        const resultData = await response.json();
        
        if (resultData.success) {
            datosFiltrados = resultData.data;
            
            // Actualizar estadísticas
            actualizarEstadisticas(resultData.stats);
            
            // Mostrar datos en la tabla
            mostrarDatosEnTabla(datosFiltrados);
            
            actualizarContador(`${resultData.stats.total} registros encontrados`);
        } else {
            mostrarAlerta('Error al aplicar filtros: ' + resultData.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al conectar con el servidor', 'error');
    } finally {
        ocultarModal();
    }
}

// Función para mostrar datos en la tabla
function mostrarDatosEnTabla(datos) {
    const tbody = document.getElementById('csvTableBody');
    tbody.innerHTML = '';
    
    if (datos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="13" class="no-data">
                    No se encontraron registros
                </td>
            </tr>
        `;
        return;
    }
    
    datos.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.className = row.result === 'NG' ? 'error-row' : '';
        
        tr.innerHTML = `
            <td class="col-index">${index + 1}</td>
            <td class="col-scandate">${row.scan_date || ''}</td>
            <td class="col-scantime">${row.scan_time || ''}</td>
            <td class="col-slotno">${row.slot_no || ''}</td>
            <td class="col-result">
                <span class="result-badge ${row.result === 'OK' ? 'ok' : 'ng'}">
                    ${row.result || ''}
                </span>
            </td>
            <td class="col-previousbarcode">${row.previous_barcode || ''}</td>
            <td class="col-productdate">${row.product_date || ''}</td>
            <td class="col-partname">${row.part_name || ''}</td>
            <td class="col-quantity">${row.quantity || ''}</td>
            <td class="col-lposition">${row.l_position || ''}</td>
            <td class="col-mposition">${row.m_position || ''}</td>
            <td class="col-seq">${row.seq || ''}</td>
            <td class="col-vendor">${row.vendor || ''}</td>
            <td class="col-lotno">${row.lot_no || ''}</td>
            <td class="col-barcode">${row.barcode || ''}</td>
            <td class="col-feederbase">${row.feeder_base || ''}</td>
            <td class="col-sourcefile" title="${row.source_file || ''}">
                ${row.source_file ? row.source_file.substring(0, 15) + '...' : ''}
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

// Función para actualizar estadísticas
function actualizarEstadisticas(stats) {
    document.getElementById('statTotalRecords').textContent = stats.total || 0;
    document.getElementById('statOkCount').textContent = stats.ok || 0;
    document.getElementById('statNgCount').textContent = stats.ng || 0;
}

// Función para exportar datos
async function exportarDatos() {
    mostrarModal();
    actualizarContador('Preparando exportación...');
    
    try {
        // Obtener los mismos filtros aplicados
        const folder = document.getElementById('filterFolder').value;
        const partName = document.getElementById('filterPartName').value;
        const result = document.getElementById('filterResult').value;
        const dateFrom = document.getElementById('filterDateFrom').value;
        const dateTo = document.getElementById('filterDateTo').value;
        
        const params = new URLSearchParams();
        if (folder) params.append('folder', folder);
        if (partName) params.append('part_name', partName);
        if (result) params.append('result', result);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        const response = await fetch(`/api/smt/historial/export?${params.toString()}`);
        const resultData = await response.json();
        
        if (resultData.success) {
            // Convertir a CSV
            const csv = convertirACSV(resultData.data);
            descargarCSV(csv, `historial_smt_${new Date().toISOString().split('T')[0]}.csv`);
            
            mostrarAlerta('Datos exportados exitosamente', 'success');
        } else {
            mostrarAlerta('Error al exportar datos: ' + resultData.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al exportar datos', 'error');
    } finally {
        ocultarModal();
    }
}

// Función para subir archivo CSV
async function subirArchivoCSV() {
    const form = document.getElementById('csvUploadForm');
    const formData = new FormData(form);
    
    mostrarModal();
    actualizarContador('Subiendo archivo...');
    
    try {
        const response = await fetch('/api/smt/historial/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarAlerta(result.message, 'success');
            form.reset();
            ocultarSeccionCarga();
            // Recargar datos después de subir
            setTimeout(() => cargarDatosCSV(), 1000);
        } else {
            mostrarAlerta('Error al subir archivo: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al subir archivo', 'error');
    } finally {
        ocultarModal();
    }
}

// Funciones para mostrar/ocultar sección de carga
function mostrarSeccionCarga() {
    document.getElementById('csvUploadSection').style.display = 'block';
}

function ocultarSeccionCarga() {
    document.getElementById('csvUploadSection').style.display = 'none';
}

// Función para convertir datos a CSV
function convertirACSV(datos) {
    if (!datos || datos.length === 0) return '';
    
    const headers = Object.keys(datos[0]);
    const csvHeaders = headers.join(',');
    
    const csvRows = datos.map(row => {
        return headers.map(header => {
            const value = row[header];
            // Escapar comillas y envolver en comillas si contiene comas
            if (value && value.toString().includes(',')) {
                return `"${value.toString().replace(/"/g, '""')}"`;
            }
            return value || '';
        }).join(',');
    });
    
    return [csvHeaders, ...csvRows].join('\n');
}

// Función para descargar CSV
function descargarCSV(contenido, nombreArchivo) {
    const blob = new Blob([contenido], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', nombreArchivo);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Funciones auxiliares
function mostrarModal() {
    document.getElementById('csvLoadingModal').style.display = 'flex';
}

function ocultarModal() {
    document.getElementById('csvLoadingModal').style.display = 'none';
}

function mostrarAlerta(mensaje, tipo = 'info') {
    const modal = document.getElementById('csvAlertModal');
    const messageDiv = document.getElementById('csvAlertMessage');
    
    const iconMap = {
        'success': '',
        'error': '❌', 
        'warning': '',
        'info': ''
    };
    
    messageDiv.innerHTML = `
        <div class="alert-icon ${tipo}">${iconMap[tipo] || iconMap.info}</div>
        <p>${mensaje}</p>
    `;
    
    modal.style.display = 'flex';
}

function hideCsvAlert() {
    document.getElementById('csvAlertModal').style.display = 'none';
}

function actualizarContador(mensaje) {
    document.getElementById('csvResultText').textContent = mensaje;
}

function limpiarFiltros() {
    document.getElementById('filterFolder').value = '';
    document.getElementById('filterPartName').value = '';
    document.getElementById('filterResult').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    
    // Recargar todos los datos
    cargarDatosCSV();
}

function establecerFechaHoy() {
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('filterDateFrom').value = hoy;
    document.getElementById('filterDateTo').value = hoy;
}

// Inicializar cuando el documento esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha de hoy por defecto
    establecerFechaHoy();
    
    // Configurar formulario de subida
    const uploadForm = document.getElementById('csvUploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            subirArchivoCSV();
        });
    }
    
    // Opcional: cargar datos automáticamente al inicio
    // cargarDatosCSV();
});
