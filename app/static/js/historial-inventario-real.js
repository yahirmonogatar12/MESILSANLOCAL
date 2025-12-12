// Datos de ejemplo para la tabla de inventario
const inventoryData = [
    { codigo: "0DR5D00308A", parte: "0DR5D00308A", codigoR: "0DR5D00308A/2402...", recibo: "2024-02-23", fabricacion: "2024-02-23", anterior: 1000, inventario: 0, diferencia: -1000, nota: "" },
    { codigo: "0DR5D00308A", parte: "0DR5D00308A", codigoR: "0DR5D00308A/2402...", recibo: "2024-02-23", fabricacion: "2024-02-23", anterior: 1000, inventario: 0, diferencia: -1000, nota: "" },
    { codigo: "0DR5D00308A", parte: "0DR5D00308A", codigoR: "0DR5D00308A/2402...", recibo: "2024-02-23", fabricacion: "2024-02-23", anterior: 1000, inventario: 0, diferencia: -1000, nota: "" },
    { codigo: "0DR5D00308A", parte: "0DR5D00308A", codigoR: "0DR5D00308A/2402...", recibo: "2024-02-23", fabricacion: "2024-02-23", anterior: 1000, inventario: 0, diferencia: -1000, nota: "" },
    { codigo: "0DR5D00308A", parte: "0DR5D00308A", codigoR: "0DR5D00308A/2402...", recibo: "2024-02-23", fabricacion: "2024-02-23", anterior: 1000, inventario: 0, diferencia: -1000, nota: "" },
    { codigo: "M3720103557", parte: "M3720103557", codigoR: "M3720103557/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 864, inventario: 0, diferencia: -864, nota: "" },
    { codigo: "M3720103557", parte: "M3720103557", codigoR: "M3720103557/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 864, inventario: 0, diferencia: -864, nota: "" },
    { codigo: "M3720103557", parte: "M3720103557", codigoR: "M3720103557/2503...", recibo: "2025-03-19", fabricacion: "2025-03-19", anterior: 864, inventario: 0, diferencia: -864, nota: "" },
    { codigo: "M3214000093", parte: "M3214000093", codigoR: "M3214000093/2504...", recibo: "2025-04-29", fabricacion: "2025-04-29", anterior: 700, inventario: 0, diferencia: -700, nota: "" },
    { codigo: "M3500103007", parte: "M3500103007", codigoR: "M3500103007/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M3500103007", parte: "M3500103007", codigoR: "M3500103007/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M3500103007", parte: "M3500103007", codigoR: "M3500103007/2410...", recibo: "2024-10-10", fabricacion: "2024-10-10", anterior: 500, inventario: 500, diferencia: 0, nota: "" },
    { codigo: "M3104200082", parte: "M3104200082", codigoR: "M3104200082/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M3104200082", parte: "M3104200082", codigoR: "M3104200082/2504...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M20133100051", parte: "M20133100051", codigoR: "M20133100051/250...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M20133100051", parte: "M20133100051", codigoR: "M20133100051/250...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M20133100051", parte: "M20133100051", codigoR: "M20133100051/250...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M20133100051", parte: "M20133100051", codigoR: "M20133100051/250...", recibo: "2025-04-28", fabricacion: "2025-04-28", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "EBC4701G483", parte: "EBC4701G483", codigoR: "EBC4701G483/2404...", recibo: "2024-04-02", fabricacion: "2024-04-02", anterior: 500, inventario: 0, diferencia: -500, nota: "" },
    { codigo: "M30610013492", parte: "M30610013492", codigoR: "M30610013492/250...", recibo: "2025-04-29", fabricacion: "2025-04-29", anterior: 375, inventario: 0, diferencia: -375, nota: "" },
    { codigo: "M30610013492", parte: "M30610013492", codigoR: "M30610013492/250...", recibo: "2025-04-29", fabricacion: "2025-04-29", anterior: 375, inventario: 0, diferencia: -375, nota: "" },
    { codigo: "M30610013492", parte: "M30610013492", codigoR: "M30610013492/250...", recibo: "2025-04-29", fabricacion: "2025-04-29", anterior: 375, inventario: 0, diferencia: -375, nota: "" },
];

// Cargar datos en la tabla
function loadInventoryData() {
    const tbody = document.getElementById('inventoryTableBody');
    tbody.innerHTML = '';
    
    inventoryData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.codigo}</td>
            <td>${item.parte}</td>
            <td>${item.codigoR}</td>
            <td>${item.recibo}</td>
            <td>${item.fabricacion}</td>
            <td>${item.anterior.toLocaleString()}</td>
            <td>${item.inventario}</td>
            <td>${item.diferencia.toLocaleString()}</td>
            <td>${item.nota}</td>
        `;
        tbody.appendChild(row);
    });
    
    document.getElementById('totalRows').textContent = inventoryData.length;
}

// Función para consultar inventario
function consultarInventario() {
    // Simulación de consulta
    const date = document.getElementById('inventoryDate').value;
    
    // Aquí se haría la llamada a la API
    // Por ahora solo recargamos los datos
    loadInventoryData();
    
    // Mostrar mensaje de éxito
    showNotification('Inventario consultado exitosamente');
}

// Función para exportar a Excel
function exportarExcel() {
    // Simulación de exportación
    
    // Crear datos CSV
    let csv = 'Código de material,Número de parte,Código de material r...,Fecha de recibo,Fecha de fabricación,Cantidad anterior,Cantidad de inventario,Diferencia de cantidad,Nota\n';
    
    inventoryData.forEach(item => {
        csv += `${item.codigo},${item.parte},${item.codigoR},${item.recibo},${item.fabricacion},${item.anterior},${item.inventario},${item.diferencia},${item.nota}\n`;
    });
    
    // Descargar archivo
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'inventario_' + new Date().toISOString().split('T')[0] + '.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showNotification('Archivo exportado exitosamente');
}

// Función para cambiar entre vistas
function toggleView() {
    const inventoryView = document.getElementById('inventoryView');
    const materialControlView = document.getElementById('materialControlView');
    
    if (inventoryView.classList.contains('active')) {
        inventoryView.classList.remove('active');
        materialControlView.classList.add('active');
    } else {
        inventoryView.classList.add('active');
        materialControlView.classList.remove('active');
    }
}

// Función para cambiar pestañas
function switchTab(tab) {
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'registro') {
        buttons[0].classList.add('active');
    } else {
        buttons[1].classList.add('active');
    }
    
}

// Función para mostrar notificaciones
function showNotification(message) {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #27ae60;
        color: white;
        padding: 15px 25px;
        border-radius: 4px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remover después de 3 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Estilos de animación
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Manejo de escaneo de código
document.addEventListener('DOMContentLoaded', function() {
    // Cargar datos iniciales
    loadInventoryData();
    
    // Agregar eventos a los inputs de escaneo
    const scanInputs = document.querySelectorAll('.scan-input, input[placeholder*="Escanear"]');
    scanInputs.forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const value = e.target.value;
                if (value) {
                    showNotification(`Código ${value} escaneado correctamente`);
                    // Aquí se procesaría el código escaneado
                }
            }
        });
    });
    
    // Hacer la tabla responsive con scroll horizontal en móviles
    const tableContainer = document.querySelector('.table-container');
    let isDown = false;
    let startX;
    let scrollLeft;
    
    tableContainer.addEventListener('mousedown', (e) => {
        isDown = true;
        startX = e.pageX - tableContainer.offsetLeft;
        scrollLeft = tableContainer.scrollLeft;
    });
    
    tableContainer.addEventListener('mouseleave', () => {
        isDown = false;
    });
    
    tableContainer.addEventListener('mouseup', () => {
        isDown = false;
    });
    
    tableContainer.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - tableContainer.offsetLeft;
        const walk = (x - startX) * 2;
        tableContainer.scrollLeft = scrollLeft - walk;
    });
});

// Detectar cambios en el tamaño de la ventana
window.addEventListener('resize', function() {
    // Ajustar elementos según sea necesario
});