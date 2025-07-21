// ==========================================
// ESTATUS DE MATERIAL - JavaScript Actualizado
// ==========================================

console.log("🔧 Cargando Estatus de Material JavaScript");

// Variables globales
let estatusInventarioData = [];
let estatusRecibidoData = [];

// ==========================================
// FUNCIONES DE CONSULTA Y CARGA DE DATOS
// ==========================================

function estatus_consultarInventario() {
    console.log("🔍 Consultando inventario para estatus de material");
    
    const codigoMaterial = document.getElementById('estatus-codigo-material-filtro').value || '';
    
    const filtros = {
        codigo_material: codigoMaterial
    };
    
    console.log("Filtros enviados:", filtros);
    
    fetch('/api/estatus_material/consultar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(filtros)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Respuesta del servidor:", data);
        
        if (data.success) {
            estatusInventarioData = data.inventario || [];
            estatus_cargarTablaInventario(estatusInventarioData);
            estatus_actualizarTotalesInventario(estatusInventarioData);
        } else {
            console.error("Error en la consulta:", data.error);
            alert("Error al consultar inventario: " + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Error de conexión: " + error.message);
    });
}

function estatus_cargarTablaInventario(inventario) {
    console.log("📋 Cargando tabla de inventario:", inventario.length, "items");
    
    const tbody = document.getElementById('estatus-inventario-body');
    tbody.innerHTML = '';
    
    if (inventario.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">No hay datos disponibles</td></tr>';
        return;
    }
    
    inventario.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.codigo_material || ''}</td>
            <td>${item.numero_parte_fabricante || ''}</td>
            <td>${item.especificacion || ''}</td>
            <td>${item.vendedor || ''}</td>
            <td>${item.ubicacion_almacen || ''}</td>
            <td>${parseFloat(item.cantidad || 0).toFixed(2)}</td>
        `;
        tbody.appendChild(row);
    });
}

function estatus_actualizarTotalesInventario(inventario) {
    const totalRows = inventario.length;
    const totalElement = document.getElementById('estatus-total-inventario');
    if (totalElement) {
        totalElement.textContent = `Total Rows: ${totalRows}`;
    }
}

// ==========================================
// FUNCIONES DE EXPORTACIÓN
// ==========================================

function estatus_exportarInventario() {
    console.log("📊 Exportando inventario de estatus de material");
    
    if (estatusInventarioData.length === 0) {
        alert("No hay datos para exportar");
        return;
    }
    
    // Preparar datos para exportación
    const datosExportar = estatusInventarioData.map(item => ({
        'Código de Material': item.codigo_material || '',
        'Número de Parte del Fabricante': item.numero_parte_fabricante || '',
        'Especificación': item.especificacion || '',
        'Vendedor': item.vendedor || '',
        'Ubicación de Almacén': item.ubicacion_almacen || '',
        'Cantidad': parseFloat(item.cantidad || 0).toFixed(2)
    }));
    
    // Crear CSV
    const csv = convertirACSV(datosExportar);
    
    // Descargar archivo
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `estatus_material_inventario_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function estatus_exportarRecibido() {
    console.log("📊 Exportando material recibido");
    
    if (estatusRecibidoData.length === 0) {
        alert("No hay datos para exportar");
        return;
    }
    
    // Función placeholder - implementar según necesidades
    alert("Funcionalidad de exportación de material recibido en desarrollo");
}

// ==========================================
// UTILIDADES
// ==========================================

function convertirACSV(objArray) {
    const array = typeof objArray !== 'object' ? JSON.parse(objArray) : objArray;
    let str = '';
    let line = '';
    
    // Headers
    for (let index in array[0]) {
        if (line !== '') line += ';';
        line += index;
    }
    str += line + '\n';
    
    // Data
    for (let i = 0; i < array.length; i++) {
        let line = '';
        for (let index in array[i]) {
            if (line !== '') line += ';';
            line += array[i][index];
        }
        str += line + '\n';
    }
    return str;
}

// ==========================================
// FUNCIONES MÓVILES Y RESPONSIVAS
// ==========================================

window.setupMobileNavigation = function() {
    const inventarioPanel = document.getElementById('estatus-inventario-panel');
    const recibidoPanel = document.getElementById('estatus-recibido-panel');
    const btnVerInventario = document.getElementById('estatus-btn-ver-inventario');
    const btnVerRecibidos = document.getElementById('estatus-btn-ver-recibidos');
    
    if (!inventarioPanel || !recibidoPanel || !btnVerInventario || !btnVerRecibidos) {
        return;
    }
    
    if (window.innerWidth <= 768) {
        // Mostrar solo inventario inicialmente en móvil
        inventarioPanel.classList.remove('mobile-hidden');
        recibidoPanel.classList.add('mobile-hidden');
        btnVerInventario.classList.add('active');
        btnVerRecibidos.classList.remove('active');
        
        // Event listeners para navegación móvil
        btnVerInventario.addEventListener('click', () => {
            inventarioPanel.classList.remove('mobile-hidden');
            recibidoPanel.classList.add('mobile-hidden');
            btnVerInventario.classList.add('active');
            btnVerRecibidos.classList.remove('active');
        });
        
        btnVerRecibidos.addEventListener('click', () => {
            inventarioPanel.classList.add('mobile-hidden');
            recibidoPanel.classList.remove('mobile-hidden');
            btnVerInventario.classList.remove('active');
            btnVerRecibidos.classList.add('active');
        });
    } else {
        // En desktop, mostrar ambos paneles
        inventarioPanel.classList.remove('mobile-hidden');
        recibidoPanel.classList.remove('mobile-hidden');
    }
};

// ==========================================
// INICIALIZACIÓN Y EVENT LISTENERS
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 Inicializando Estatus de Material");
    
    // Event listeners para botones
    const btnConsultar = document.getElementById('estatus-btn-consultar-inventario');
    if (btnConsultar) {
        btnConsultar.addEventListener('click', estatus_consultarInventario);
    }
    
    const btnExportarInventario = document.getElementById('estatus-btn-exportar-inventario');
    if (btnExportarInventario) {
        btnExportarInventario.addEventListener('click', estatus_exportarInventario);
    }
    
    const btnExportarRecibido = document.getElementById('estatus-btn-exportar-recibido');
    if (btnExportarRecibido) {
        btnExportarRecibido.addEventListener('click', estatus_exportarRecibido);
    }
    
    // Event listener para Enter en el campo de filtro
    const codigoFiltro = document.getElementById('estatus-codigo-material-filtro');
    if (codigoFiltro) {
        codigoFiltro.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                estatus_consultarInventario();
            }
        });
    }
    
    // Configurar navegación móvil
    window.addEventListener('resize', window.setupMobileNavigation);
    window.setupMobileNavigation();
    
    // Cargar datos iniciales
    setTimeout(() => {
        console.log("🔄 Cargando datos iniciales de estatus de material");
        estatus_consultarInventario();
    }, 500);
});

// ==========================================
// FUNCIÓN DE INICIALIZACIÓN PARA CARGA DINÁMICA
// ==========================================

window.initEstatusMaterial = function() {
    console.log('🎯 Inicializando Estatus de Material dinámicamente...');
    
    // Verificar elementos DOM
    const inventarioBody = document.getElementById('estatus-inventario-body');
    const recibidoBody = document.getElementById('estatus-recibido-body');
    
    if (!inventarioBody || !recibidoBody) {
        console.error('❌ Elementos DOM no encontrados para Estatus de Material');
        return;
    }
    
    // Event listeners para botones
    const btnConsultar = document.getElementById('estatus-btn-consultar-inventario');
    if (btnConsultar) {
        btnConsultar.removeEventListener('click', estatus_consultarInventario);
        btnConsultar.addEventListener('click', estatus_consultarInventario);
    }
    
    const btnExportarInventario = document.getElementById('estatus-btn-exportar-inventario');
    if (btnExportarInventario) {
        btnExportarInventario.removeEventListener('click', estatus_exportarInventario);
        btnExportarInventario.addEventListener('click', estatus_exportarInventario);
    }
    
    const btnExportarRecibido = document.getElementById('estatus-btn-exportar-recibido');
    if (btnExportarRecibido) {
        btnExportarRecibido.removeEventListener('click', estatus_exportarRecibido);
        btnExportarRecibido.addEventListener('click', estatus_exportarRecibido);
    }
    
    // Event listener para Enter en campo de filtro
    const codigoFiltro = document.getElementById('estatus-codigo-material-filtro');
    if (codigoFiltro) {
        codigoFiltro.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                estatus_consultarInventario();
            }
        });
    }
    
    // Configurar navegación móvil
    window.setupMobileNavigation();
    
    // Cargar datos iniciales
    setTimeout(() => {
        console.log("🔄 Cargando datos iniciales de estatus de material (dinámico)");
        estatus_consultarInventario();
    }, 300);
    
    console.log('✅ Estatus de Material inicializado correctamente (dinámico)');
};

// Funciones globales para compatibilidad
window.estatus_consultarInventario = estatus_consultarInventario;
window.estatus_exportarInventario = estatus_exportarInventario;
window.estatus_exportarRecibido = estatus_exportarRecibido;

console.log("✅ Estatus de Material JavaScript cargado completamente");

// Datos de ejemplo para material recibido (globales)
const materialRecibidoData = [];

document.addEventListener('DOMContentLoaded', function() {
    // Event Listeners para cuando se carga normalmente (no dinámicamente)
    const btnConsultarInventario = document.getElementById('btn-consultar-inventario');
    const btnExportarInventario = document.getElementById('btn-exportar-inventario');
    const btnExportarRecibido = document.getElementById('btn-exportar-recibido');
    const codigoMaterialFiltro = document.getElementById('codigo-material-filtro');

    // Función para cargar datos de inventario
    window.cargarInventario = function(filtro = '') {
        const inventarioBody = document.getElementById('inventario-body');
        const totalInventario = document.getElementById('total-inventario');
        
        if (!inventarioBody || !totalInventario) {
            console.error('❌ Elementos DOM no encontrados para inventario');
            return;
        }
        
        let filteredData = inventarioData;
        
        if (filtro) {
            filteredData = inventarioData.filter(item => 
                item.codigo.toLowerCase().includes(filtro.toLowerCase()) ||
                item.numParte.toLowerCase().includes(filtro.toLowerCase())
            );
        }
        
        let html = '';
        
        if (filteredData.length === 0) {
            html = `<tr><td colspan="6" class="no-data">No hay datos disponibles</td></tr>`;
        } else {
            filteredData.forEach(item => {
                html += `
                <tr data-codigo="${item.codigo}">
                    <td>${item.codigo}</td>
                    <td>${item.numParte}</td>
                    <td>${item.propiedad}</td>
                    <td>${item.vendedor}</td>
                    <td>${item.ubicacion}</td>
                    <td>${item.cantidad.toLocaleString()}</td>
                </tr>`;
            });
        }
        
        inventarioBody.innerHTML = html;
        totalInventario.textContent = `Total Rows: ${filteredData.length}`;
        
        // Agregar evento de clic a las filas
        const filas = inventarioBody.querySelectorAll('tr');
        filas.forEach(fila => {
            fila.addEventListener('click', () => {
                filas.forEach(f => f.classList.remove('selected'));
                fila.classList.add('selected');
            });
        });
    }

    // Función para cargar datos de material recibido
    window.cargarMaterialRecibido = function() {
        const recibidoBody = document.getElementById('recibido-body');
        const totalRecibido = document.getElementById('total-recibido');
        
        if (!recibidoBody || !totalRecibido) {
            console.error('❌ Elementos DOM no encontrados para material recibido');
            return;
        }
        
        let html = '';
        
        if (materialRecibidoData.length === 0) {
            html = `<tr><td colspan="4" class="no-data">No hay dato registrado</td></tr>`;
            totalRecibido.textContent = `Total Rows: 0 | Total Qty: 0`;
        } else {
            let totalQty = 0;
            materialRecibidoData.forEach(item => {
                html += `
                <tr>
                    <td>${item.codigo}</td>
                    <td>${item.lote}</td>
                    <td>${item.importacion}</td>
                    <td>${item.cantidad.toLocaleString()}</td>
                </tr>`;
                totalQty += item.cantidad;
            });
            totalRecibido.textContent = `Total Rows: ${materialRecibidoData.length} | Total Qty: ${totalQty.toLocaleString()}`;
        }
        
        recibidoBody.innerHTML = html;
    }

    // Función para exportar a Excel
    window.exportarAExcel = function(tableId, filename) {
        alert(`Exportando tabla "${tableId}" a Excel con nombre "${filename}.xlsx"`);
        // Aquí iría la lógica real de exportación a Excel
    }

    // Gestión de la navegación en móviles
    window.setupMobileNavigation = function() {
        const inventarioPanel = document.getElementById('inventario-panel');
        const recibidoPanel = document.getElementById('recibido-panel');
        const btnVerInventario = document.getElementById('btn-ver-inventario');
        const btnVerRecibidos = document.getElementById('btn-ver-recibidos');
        
        if (!inventarioPanel || !recibidoPanel || !btnVerInventario || !btnVerRecibidos) {
            console.error('❌ Elementos DOM no encontrados para navegación móvil');
            return;
        }
        
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            // Por defecto, en móviles solo mostrar el panel de inventario
            recibidoPanel.style.display = 'none';
            inventarioPanel.style.display = 'block';
            
            // Configurar botones de navegación
            btnVerInventario.addEventListener('click', () => {
                inventarioPanel.style.display = 'block';
                recibidoPanel.style.display = 'none';
                btnVerInventario.classList.add('active');
                btnVerRecibidos.classList.remove('active');
            });
            
            btnVerRecibidos.addEventListener('click', () => {
                inventarioPanel.style.display = 'none';
                recibidoPanel.style.display = 'block';
                btnVerInventario.classList.remove('active');
                btnVerRecibidos.classList.add('active');
            });
        } else {
            // En desktop, mostrar ambos paneles
            inventarioPanel.style.display = 'block';
            recibidoPanel.style.display = 'block';
        }
    }

    // Event Listeners
    if (btnConsultarInventario) {
        btnConsultarInventario.addEventListener('click', () => {
            const filtro = codigoMaterialFiltro ? codigoMaterialFiltro.value : '';
            window.cargarInventario(filtro);
        });
    }

    if (btnExportarInventario) {
        btnExportarInventario.addEventListener('click', () => {
            window.exportarAExcel('tabla-inventario', 'Inventario_Material');
        });
    }

    if (btnExportarRecibido) {
        btnExportarRecibido.addEventListener('click', () => {
            window.exportarAExcel('tabla-recibido', 'Material_Recibido');
        });
    }

    // Permitir filtrar presionando Enter
    if (codigoMaterialFiltro) {
        codigoMaterialFiltro.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                btnConsultarInventario.click();
            }
        });
    }

    // Manejar cambios de tamaño de pantalla
    window.addEventListener('resize', window.setupMobileNavigation);

    // Inicialización
    window.cargarInventario();
    window.cargarMaterialRecibido();
    window.setupMobileNavigation();
});

// Función de inicialización para cuando se carga dinámicamente
window.initEstatusMaterial = function() {
    console.log('🎯 Inicializando Estatus de Material...');
    
    // Obtener referencias a elementos DOM
    const inventarioBody = document.getElementById('inventario-body');
    const recibidoBody = document.getElementById('recibido-body');
    const totalInventario = document.getElementById('total-inventario');
    const totalRecibido = document.getElementById('total-recibido');
    const codigoMaterialFiltro = document.getElementById('codigo-material-filtro');
    const btnConsultarInventario = document.getElementById('btn-consultar-inventario');
    const btnExportarInventario = document.getElementById('btn-exportar-inventario');
    const btnExportarRecibido = document.getElementById('btn-exportar-recibido');
    const inventarioPanel = document.getElementById('inventario-panel');
    const recibidoPanel = document.getElementById('recibido-panel');
    const btnVerInventario = document.getElementById('btn-ver-inventario');
    const btnVerRecibidos = document.getElementById('btn-ver-recibidos');
    
    if (!inventarioBody || !recibidoBody) {
        console.error('❌ Elementos DOM no encontrados para Estatus de Material');
        return;
    }
    
    // Event Listeners
    if (btnConsultarInventario) {
        btnConsultarInventario.addEventListener('click', () => {
            const filtro = codigoMaterialFiltro ? codigoMaterialFiltro.value : '';
            window.cargarInventario(filtro);
        });
    }

    if (btnExportarInventario) {
        btnExportarInventario.addEventListener('click', () => {
            window.exportarAExcel('tabla-inventario', 'Inventario_Material');
        });
    }

    if (btnExportarRecibido) {
        btnExportarRecibido.addEventListener('click', () => {
            window.exportarAExcel('tabla-recibido', 'Material_Recibido');
        });
    }

    // Permitir filtrar presionando Enter
    if (codigoMaterialFiltro) {
        codigoMaterialFiltro.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                btnConsultarInventario.click();
            }
        });
    }

    // Manejar cambios de tamaño de pantalla
    window.addEventListener('resize', window.setupMobileNavigation);
    
    // Inicializar datos
    window.cargarInventario();
    window.cargarMaterialRecibido();
    window.setupMobileNavigation();
    
    console.log('✅ Estatus de Material inicializado correctamente');
};