// material-management.js
function setupMaterialManagement() {
    // Todo el código JavaScript optimizado que te proporcioné anteriormente
    // (el que contiene las plantillas y la lógica)
    document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.app-sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const overlay = document.querySelector('.overlay');
    const mainContent = document.querySelector('.app-content');
    
    // Toggle sidebar on mobile
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    });
    
    // Close sidebar when clicking on overlay
    overlay.addEventListener('click', function() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
    });
    
    // Activar tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Plantillas comunes
    const formTemplate = `
        <div class="form-container">
            <div class="form-row">
                <div class="form-group">
                    <label for="formaMaterial">Forma de material</label>
                    <select id="formaMaterial">
                        <option>OriginCode</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="cliente">Cliente</label>
                    <select id="cliente">
                        <option>Seleccionar</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="codigoMaterial">Código de material</label>
                    <input id="codigoMaterial" type="text" class="form_global">
                </div>
                <div class="form-group">
                    <label for="fechaFab">Fecha fabricación</label>
                    <input id="fechaFab" type="date">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="origenMaterial">Material importación/local</label>
                    <select id="origenMaterial">
                        <option>Customer Supply</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="cantidadActual">Cantidad actual</label>
                    <input id="cantidadActual" type="number">
                </div>
                <div class="form-group">
                    <label for="fechaRecibo">Fecha de recibo</label>
                    <input id="fechaRecibo" type="date">
                </div>
                <div class="form-group">
                    <label for="loteMaterial">No. lote material</label>
                    <input id="loteMaterial" type="text">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="codRecibido">Código material recibido</label>
                    <input id="codRecibido" type="text">
                </div>
                <div class="form-group">
                    <label for="numParte">Número de parte</label>
                    <input id="numParte" type="text">
                </div>
                <div class="form-group">
                    <label for="propiedad">Propiedad material</label>
                    <input id="propiedad" type="text">
                </div>
                <div class="form-group"></div>
            </div>
        </div>
    `;

    const actionButtons = `
        <div class="action-buttons">
            <button type="button" class="btn btn-secondary">Guardar</button>
            <button type="button" class="btn btn-secondary">Imprimir</button>
            <button type="button" class="btn btn-secondary">Consultar</button>
            <button type="button" class="btn btn-success">Exportar a Excel</button>
        </div>
    `;

    const dataTable = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Código material</th>
                    <th>Número parte</th>
                    <th>Fecha recibo</th>
                </tr>
            </thead>
            <tbody>
                <tr class="no-data">
                    <td colspan="3">No hay datos registrados</td>
                </tr>
            </tbody>
        </table>
    `;

    // Plantillas específicas
    const templates = {
        'Entrada de Aéreo': `
            <div id="material" class="tab-pane_active">
                <h2>Entrada de Aéreo</h2>
                ${formTemplate}
                ${actionButtons}
                ${dataTable}
            </div>
        `,
        'Entrada de Contenedor': `
            <div id="material" class="tab-pane_active">
                <h2>Entrada de Contenedor</h2>
                ${formTemplate}
                ${actionButtons}
                ${dataTable}
            </div>
        `,
        'Entrada de LG': `
            <div id="material" class="tab-pane_active">
                <h2>Entrada de LG</h2>
                ${formTemplate}
                ${actionButtons}
                ${dataTable}
            </div>
        `,
        'Entrada de Local Suppliers': `
            <div id="material" class="tab-pane_active">
                <h2>Entrada de Local Suppliers</h2>
                ${formTemplate}
                ${actionButtons}
                ${dataTable}
            </div>
        `,
        'Salida de material': `
            <div id="tab-salida" class="tab-pane fade show" role="tabpanel" aria-labelledby="salida-tab">
                <form id="form-salida" class="mb-4">
                    <div class="row g-3 align-items-end">
                        <div class="form-group">
                            <label for="lote" class="form-group">Número de lote</label>
                            <input type="text" id="lote" class="form-group">
                        </div>
                        <div class="col-md-3 d-flex">
                            <div class="form-check me-3">
                                <input class="form-check-input" type="checkbox" id="verif-bom">
                                <label class="form-check-label text-light" for="verif-bom">Verificación de BOM</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="peps">
                                <label class="form-check-label text-light" for="peps">PEPS</label>
                            </div>
                        </div>
                        <div class="col-md-2">
                            <label for="modelo" class="form-label text-light">Modelo</label>
                            <select id="modelo" class="form-select">
                                <option>Seleccionar</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label for="depto-salida" class="form-label text-light">Departamento de salida</label>
                            <select id="depto-salida" class="form-select">
                                <option>Seleccionar</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label for="proceso-salida" class="form-label text-light">Proceso de salida</label>
                            <select id="proceso-salida" class="form-select">
                                <option>Seleccionar</option>
                            </select>
                        </div>
                    </div>

                    <div class="row g-3 align-items-end mt-2">
                        <div class="col-md-4">
                            <label for="cod-recibido" class="form-label text-light">Código de material recibido</label>
                            <input type="text" id="cod-recibido" class="form-group">
                        </div>
                        <div class="col-md-4 d-flex align-items-center">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="val-cod-original">
                                <label class="form-check-label text-light" for="val-cod-original">Validación de código original</label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <label for="cod-original" class="form-label text-light">Código de material original</label>
                            <input type="text" id="cod-original" class="form-group bg-primary text-white">
                        </div>
                    </div>
                </form>

                <div class="p-3 mb-4 rounded" style="background-color: #5d417e;">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label text-light">Código de material</label>
                            <input type="text" class="form-group">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label text-light">Número de parte</label>
                            <input type="text" class="form-group">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label text-light">Especificación de material</label>
                            <input type="text" class="form-group">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label text-light">Cantidad actual</label>
                            <input type="number" class="form-group">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label text-light">Número de lote de material</label>
                            <input type="text" class="form-group">
                        </div>
                    </div>
                </div>

                <div class="d-flex justify-content-end mb-3">
                    <button type="button" class="btn btn-secondary me-2">Reiniciar</button>
                    <button type="button" class="btn btn-warning">Guardar</button>
                </div>

                <ul class="nav nav-tabs" id="salidaTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="registro-tab" data-bs-toggle="tab" data-bs-target="#registro" type="button" role="tab" aria-controls="registro" aria-selected="true">Registro de salida</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="historial-tab" data-bs-toggle="tab" data-bs-target="#historial" type="button" role="tab" aria-controls="historial" aria-selected="false">Historial de salida</button>
                    </li>
                </ul>
                <div class="tab-content mt-3" id="salidaTabsContent">
                    <div class="tab-pane fade show active" id="registro" role="tabpanel" aria-labelledby="registro-tab">
                        <div class="row">
                            <div class="col-md-6">
                                <table class="table table-dark table-striped table-sm">
                                    <thead>
                                        <tr>
                                            <th>Proceso</th>
                                            <th>Código</th>
                                            <th>Número de parte</th>
                                            <th>Cant. de...</th>
                                            <th>Cant. total</th>
                                            <th>Propiedad</th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <table class="table table-dark table-striped table-sm">
                                    <thead>
                                        <tr>
                                            <th>Código d...</th>
                                            <th>Código d...</th>
                                            <th>Número...</th>
                                            <th>Cantidad</th>
                                            <th>Número...</th>
                                            <th>Propiedad</th>
                                            <th>Nivel de...</th>
                                            <th>Especif...</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td colspan="8" class="text-center text-secondary">No hay data registrado</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="historial" role="tabpanel" aria-labelledby="historial-tab"></div>
                </div>
            </div>
        `
    };

    // Manejar el contenido dinámico
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.addEventListener('click', function() {
            mainContent.innerHTML = '';
            
            // Cerrar sidebar en móviles al seleccionar un item
            if (window.innerWidth < 768) {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
            }
            
            document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            const template = templates[this.textContent.trim()];
            if (template) {
                mainContent.innerHTML = template;
            }
        });
    });
    
    // Manejar tabs del header
    document.querySelectorAll('.nav-tabs .nav-link').forEach(link => {
        link.addEventListener('click', function() {
            mainContent.innerHTML = "";
            if (this.getAttribute('href') === '#info') {
                sidebar.style.display = 'block';
            } else if (this.getAttribute('href') === '#material') {
                sidebar.style.display = 'block';
                document.querySelectorAll('.sidebar-section').forEach(sec => {
                    sec.style.display = 'none';
                });
                document.querySelector('#sidebarMaterial').closest('.sidebar-section').style.display = 'block';
            } else {
                sidebar.style.display = 'none';
            }
        });
    });
    
    // Ajustar el contenido cuando se redimensiona la ventana
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }
    });
});
}

// Ejecutar cuando el DOM esté listo
if (document.readyState !== 'loading') {
    setupMaterialManagement();
} else {
    document.addEventListener('DOMContentLoaded', setupMaterialManagement);
}