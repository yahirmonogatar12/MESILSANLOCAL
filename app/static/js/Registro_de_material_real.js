// Datos de inventario
const inventoryData = [
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ1500E672", parte: "0RJ1500E672", especificacion: "150J 1/8W (SMD 2...", codigoMaterial: "0RJ1500E672/2402...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "0RJ5601D677", parte: "0RJ5601D677", especificacion: "5.6KJ 1/10W (SMD...", codigoMaterial: "0RJ5601D677/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 5000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "49111007000", parte: "49111007000", especificacion: "LFM-48W TM-HP S...", codigoMaterial: "49111007000/2409...", fechaRecibo: "2024-09-26", fechaFabricacion: "2024-09-26", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "49111009", parte: "49111009", especificacion: "SOLDER WIRE 1KG", codigoMaterial: "49111009/2405200...", fechaRecibo: "2024-05-20", fechaFabricacion: "2024-05-20", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "49111009", parte: "49111009", especificacion: "SOLDER WIRE 1KG", codigoMaterial: "49111009/2405200...", fechaRecibo: "2024-05-20", fechaFabricacion: "2024-05-20", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "49111009", parte: "49111009", especificacion: "SOLDER WIRE 1KG", codigoMaterial: "49111009/2405200...", fechaRecibo: "2024-05-20", fechaFabricacion: "2024-05-20", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EAH64252901", parte: "EAH64252901", especificacion: "51NBC80", codigoMaterial: "EAH64252901/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 1000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EAH64252901", parte: "EAH64252901", especificacion: "51NBC80", codigoMaterial: "EAH64252901/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 1000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EAH64252901", parte: "EAH64252901", especificacion: "51NBC80", codigoMaterial: "EAH64252901/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 1000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EAH64252901", parte: "EAH64252901", especificacion: "51NBC80", codigoMaterial: "EAH64252901/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 1000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EAH64252901", parte: "EAH64252901", especificacion: "51NBC80", codigoMaterial: "EAH64252901/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 1000, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EBC4701G483", parte: "EBC4701G483", especificacion: "4.7KF 1/10W (SMD...", codigoMaterial: "EBC4701G483/240...", fechaRecibo: "2024-04-02", fechaFabricacion: "2024-04-02", cantidadInventario: 500, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EBC62298201", parte: "EBC62298201", especificacion: "91KJ 1W (SMD 6432)", codigoMaterial: "EBC62298201/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EBC62298201", parte: "EBC62298201", especificacion: "91KJ 1W (SMD 6432)", codigoMaterial: "EBC62298201/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 0, fechaInventario: "", cantidadInventarioActual: "" },
    { codigo: "EBC62298201", parte: "EBC62298201", especificacion: "91KJ 1W (SMD 6432)", codigoMaterial: "EBC62298201/240...", fechaRecibo: "2024-02-23", fechaFabricacion: "2024-02-23", cantidadInventario: 4000, fechaInventario: "", cantidadInventarioActual: "" }
];

// Variables globales
let selectedRows = new Set();
let filteredData = [...inventoryData];

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', function() {
    loadTable();
    setupEventListeners();
});

// Cargar datos en la tabla
function loadTable(data = inventoryData) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    data.forEach((item, index) => {
        const row = document.createElement('tr');
        row.dataset.index = index;
        
        row.innerHTML = `
            <td class="checkbox-column">
                <input type="checkbox" class="row-checkbox" data-index="${index}">
            </td>
            <td>${item.codigo}</td>
            <td>${item.parte}</td>
            <td>${item.especificacion}</td>
            <td>${item.codigoMaterial}</td>
            <td>${item.fechaRecibo}</td>
            <td>${item.fechaFabricacion}</td>
            <td>${item.cantidadInventario.toLocaleString()}</td>
            <td>${item.fechaInventario || '-'}</td>
            <td>${item.cantidadInventarioActual || '-'}</td>
        `;

        if (selectedRows.has(index)) {
            row.classList.add('selected');
            row.querySelector('.row-checkbox').checked = true;
        }

        tableBody.appendChild(row);
    });

    updateTotalRows(data.length);
}

// Configurar event listeners
function setupEventListeners() {
    // Botones principales
    document.getElementById('btnConsultar').addEventListener('click', consultarInventario);
    document.getElementById('btnExportar').addEventListener('click', exportarExcel);
    document.getElementById('btnImportar').addEventListener('click', () => openModal('importModal'));
    document.getElementById('btnReiniciar').addEventListener('click', reiniciarSeleccion);
    document.getElementById('btnAplicacion').addEventListener('click', () => openModal('inventoryModal'));

    // Checkbox de seleccionar todo
    document.getElementById('selectAll').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        checkboxes.forEach((checkbox, index) => {
            checkbox.checked = this.checked;
            const row = checkbox.closest('tr');
            if (this.checked) {
                selectedRows.add(index);
                row.classList.add('selected');
            } else {
                selectedRows.delete(index);
                row.classList.remove('selected');
            }
        });
    });

    // Delegación de eventos para checkboxes individuales
    document.getElementById('tableBody').addEventListener('change', function(e) {
        if (e.target.classList.contains('row-checkbox')) {
            const index = parseInt(e.target.dataset.index);
            const row = e.target.closest('tr');
            
            if (e.target.checked) {
                selectedRows.add(index);
                row.classList.add('selected');
            } else {
                selectedRows.delete(index);
                row.classList.remove('selected');
            }

            // Actualizar el checkbox de seleccionar todo
            const allCheckboxes = document.querySelectorAll('.row-checkbox');
            const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
            document.getElementById('selectAll').checked = allCheckboxes.length === checkedBoxes.length;
        }
    });

    // Modal close buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });

    // Click fuera del modal para cerrar
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    // Formulario de aplicación de inventario
    document.getElementById('inventoryForm').addEventListener('submit', aplicarInventario);

    // Botón de carga de archivo
    document.getElementById('btnUpload').addEventListener('click', importarArchivo);
}

// Funciones principales
function consultarInventario() {
    showNotification('Consultando inventario...', 'info');
    
    // Simulación de consulta
    setTimeout(() => {
        loadTable(inventoryData);
        showNotification('Inventario actualizado correctamente', 'success');
    }, 1000);
}

function exportarExcel() {
    if (selectedRows.size === 0) {
        showNotification('Por favor seleccione al menos una fila para exportar', 'error');
        return;
    }

    showNotification('Exportando a Excel...', 'info');

    // Crear CSV con los datos seleccionados
    let csv = 'Código de material,Número de parte,Especificación,Código de material completo,Fecha de recibo,Fecha de fabricación,Cantidad de inventario,Fecha de inventario,Cantidad de inventario actual\n';
    
    selectedRows.forEach(index => {
        const item = inventoryData[index];
        csv += `"${item.codigo}","${item.parte}","${item.especificacion}","${item.codigoMaterial}","${item.fechaRecibo}","${item.fechaFabricacion}","${item.cantidadInventario}","${item.fechaInventario}","${item.cantidadInventarioActual}"\n`;
    });

    // Descargar archivo CSV
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `inventario_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
        showNotification('Archivo exportado exitosamente', 'success');
    }, 500);
}

function reiniciarSeleccion() {
    selectedRows.clear();
    document.getElementById('selectAll').checked = false;
    document.querySelectorAll('.row-checkbox').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.closest('tr').classList.remove('selected');
    });
    showNotification('Selección reiniciada', 'info');
}

function aplicarInventario(e) {
    e.preventDefault();
    
    if (selectedRows.size === 0) {
        showNotification('Por favor seleccione al menos una fila', 'error');
        return;
    }

    const fecha = document.getElementById('fechaInventario').value;
    const cantidad = document.getElementById('cantidadInventario').value;

    selectedRows.forEach(index => {
        inventoryData[index].fechaInventario = fecha;
        inventoryData[index].cantidadInventarioActual = cantidad;
    });

    loadTable(inventoryData);
    closeModal('inventoryModal');
    showNotification(`Inventario aplicado a ${selectedRows.size} registros`, 'success');
    
    // Limpiar el formulario
    document.getElementById('inventoryForm').reset();
}

function importarArchivo() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];

    if (!file) {
        showNotification('Por favor seleccione un archivo', 'error');
        return;
    }

    showNotification('Importando archivo...', 'info');

    // Simulación de lectura de archivo CSV
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const csv = e.target.result;
            const lines = csv.split('\n');
            const headers = lines[0].split(',');
            
            // Simular importación exitosa
            setTimeout(() => {
                closeModal('importModal');
                showNotification(`Archivo importado: ${lines.length - 1} registros procesados`, 'success');
                fileInput.value = '';
            }, 1500);
        } catch (error) {
            showNotification('Error al procesar el archivo', 'error');
        }
    };
    
    reader.readAsText(file);
}

// Funciones auxiliares
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function updateTotalRows(count) {
    document.getElementById('totalRows').textContent = count;
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}