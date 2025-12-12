// Variables globales
let tableData = [];

// Función para inicializar la aplicación
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar event listeners
    initializeEventListeners();
    
    // Actualizar contador de filas
    updateRowCount();
});

// Inicializar todos los event listeners
function initializeEventListeners() {
    // Checkbox principal
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }
    
    // Botón Guardar
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', handleSave);
    }
    
    // Botón Consultar
    const btnConsultar = document.getElementById('btnConsultar');
    if (btnConsultar) {
        btnConsultar.addEventListener('click', handleConsult);
    }
    
    // Botón Exportar
    const btnExportar = document.getElementById('btnExportar');
    if (btnExportar) {
        btnExportar.addEventListener('click', handleExport);
    }
    
    // Botón Reimprimir
    const btnReimprimir = document.getElementById('btnReimprimir');
    if (btnReimprimir) {
        btnReimprimir.addEventListener('click', handleReprint);
    }
    
    // Botón Configuración de Impresora
    const btnConfigImpresora = document.getElementById('btnConfigImpresora');
    if (btnConfigImpresora) {
        btnConfigImpresora.addEventListener('click', handlePrinterConfig);
    }
}

// Manejar selección de todos los checkboxes
function handleSelectAll(event) {
    const checkboxes = document.querySelectorAll('#tableBody input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = event.target.checked;
    });
}

// Manejar guardado de datos
function handleSave() {
    const formData = {
        codigoMaterialRecibido: document.getElementById('codigoMaterialRecibido').value,
        codigoMaterial: document.getElementById('codigoMaterial').value,
        especificacionMaterial: document.getElementById('especificacionMaterial').value,
        numeroParte: document.getElementById('numeroParte').value,
        cantidadEstandarizada: document.getElementById('cantidadEstandarizada').value,
        cantidadRemanente: document.getElementById('cantidadRemanente').value,
        cantidadRetorno: document.getElementById('cantidadRetorno').value
    };
    
    // Aquí iría la lógica para guardar en el servidor
    
    // Mostrar mensaje de éxito (ejemplo)
    alert('Datos guardados correctamente');
}

// Manejar consulta
function handleConsult() {
    const fechaInicio = document.getElementById('fechaRetornoInicio').value;
    const fechaFin = document.getElementById('fechaRetornoFin').value;
    
    // Aquí iría la lógica para consultar datos del servidor
    
    // Ejemplo de carga de datos
    loadTableData();
}

// Manejar exportación a Excel
function handleExport() {
    // Aquí iría la lógica para exportar a Excel
    alert('Exportación a Excel iniciada');
}

// Manejar reimpresión
function handleReprint() {
    window.print();
}

// Manejar configuración de impresora
function handlePrinterConfig() {
    // Aquí iría la lógica para abrir configuración de impresora
    alert('Configuración de impresora');
}

// Cargar datos en la tabla (ejemplo)
function loadTableData() {
    // Datos de ejemplo
    const exampleData = [
        {
            fechaRetorno: '21/07/2025',
            codigoMaterialRecibido: 'MAT001',
            codigoMaterial: 'CM001',
            numeroParte: 'NP001',
            numeroLote: 'LT001',
            cantidadEstandarizada: '100',
            cantidadRetorno: '95',
            cantidadPerdida: '5',
            especificacion: 'Material de prueba'
        }
    ];
    
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';
    
    exampleData.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="checkbox-col">
                <input type="checkbox" id="row-${index}">
            </td>
            <td>${row.fechaRetorno}</td>
            <td>${row.codigoMaterialRecibido}</td>
            <td>${row.codigoMaterial}</td>
            <td>${row.numeroParte}</td>
            <td>${row.numeroLote}</td>
            <td>${row.cantidadEstandarizada}</td>
            <td>${row.cantidadRetorno}</td>
            <td>${row.cantidadPerdida}</td>
            <td>${row.especificacion}</td>
        `;
        tableBody.appendChild(tr);
    });
    
    updateRowCount();
}

// Actualizar contador de filas
function updateRowCount() {
    const rowCount = document.querySelectorAll('#tableBody tr').length;
    const rowCounter = document.getElementById('rowCounter');
    if (rowCounter) {
        rowCounter.textContent = `Total Rows : ${rowCount}`;
    }
}

// Validaciones de formulario
function validateForm() {
    const requiredFields = [
        'codigoMaterialRecibido',
        'codigoMaterial',
        'numeroParte',
        'cantidadEstandarizada',
        'cantidadRemanente',
        'cantidadRetorno'
    ];
    
    let isValid = true;
    requiredFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field && !field.value.trim()) {
            field.style.borderColor = '#e53e3e';
            isValid = false;
        } else if (field) {
            field.style.borderColor = '#5e9ed6';
        }
    });
    
    return isValid;
}

// Limpiar formulario
function clearForm() {
    const inputs = document.querySelectorAll('.form-control:not([readonly])');
    inputs.forEach(input => {
        input.value = '';
        input.style.borderColor = '#5e9ed6';
    });
}