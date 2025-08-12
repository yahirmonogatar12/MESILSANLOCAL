//  Panel Lateral de Edición para Materiales
//  Sistema moderno con animaciones para editar materiales

// 🆕 Función global para forzar inicialización (útil para AJAX)
window.initializeMaterialDrawer = function() {
    if (!window.materialEditDrawer) {
        console.log(' Inicializando Panel de Edición de Materiales...');
        window.materialEditDrawer = new MaterialEditDrawer();
        console.log(' Panel de Edición de Materiales inicializado');
    }
    
    if (!window.materialRegistroDrawer) {
        console.log(' Inicializando Panel de Registro de Materiales...');
        window.materialRegistroDrawer = new MaterialRegistroDrawer();
        console.log(' Panel de Registro de Materiales inicializado');
    }
    
    return true;
};

// Funciones globales para compatibilidad y carga AJAX
window.abrirPanelEdicion = function(btn) {
    console.log(' Intentando abrir panel de edición...');
    
    // Asegurar que el drawer esté inicializado
    if (!window.materialEditDrawer) {
        console.log(' MaterialEditDrawer no inicializado, inicializando ahora...');
        window.initializeMaterialDrawer();
        
        // Esperar un momento para que se inicialice
        setTimeout(() => {
            if (window.materialEditDrawer) {
                const row = btn.closest('tr');
                if (row) {
                    window.materialEditDrawer.abrirPanelEdicion(row);
                }
            }
        }, 100);
        return;
    }
    
    const row = btn.closest('tr');
    if (window.materialEditDrawer && row) {
        window.materialEditDrawer.abrirPanelEdicion(row);
    } else {
        console.error('❌ MaterialEditDrawer no está inicializado o no se encontró la fila');
    }
};

window.cerrarDrawer = function() {
    if (window.materialEditDrawer) {
        window.materialEditDrawer.cerrarDrawer();
    } else {
        console.error('❌ MaterialEditDrawer no está inicializado');
    }
};

window.guardarEdicion = function() {
    if (window.materialEditDrawer) {
        window.materialEditDrawer.guardarEdicion();
    } else {
        console.error('❌ MaterialEditDrawer no está inicializado');
    }
};

class MaterialEditDrawer {
    constructor() {
        this.createDrawerHTML();
        this.bindEvents();
        this.currentEditingData = null;
    }

    createDrawerHTML() {
        const drawerHTML = `
        <!-- 🎨 Panel Lateral de Edición -->
        <div id="editDrawer" class="material-edit-drawer">
            <div class="drawer-header">
                <h3><i class="fas fa-edit me-2"></i>Editar Material</h3>
                <button type="button" class="btn-close-drawer" onclick="materialEditDrawer.cerrarDrawer()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            
            <div class="drawer-body">
                <form id="editMaterialForm">
                    <input type="hidden" id="editCodigoMaterialOriginal" name="codigo_material_original">
                    
                    <!-- Información Principal -->
                    <div class="form-section">
                        <h5><i class="fas fa-info-circle me-2"></i>Información Principal</h5>
                        
                        <div class="form-group">
                            <label for="editCodigoMaterial" class="form-label">
                                <i class="fas fa-barcode me-1"></i>Código de Material <span class="required">*</span>
                            </label>
                            <input type="text" class="form-control" id="editCodigoMaterial" name="codigoMaterial" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="editNumeroParte" class="form-label">
                                <i class="fas fa-hashtag me-1"></i>Número de Parte
                            </label>
                            <input type="text" class="form-control" id="editNumeroParte" name="numeroParte">
                        </div>
                        
                        <div class="form-group">
                            <label for="editPropiedadMaterial" class="form-label">
                                <i class="fas fa-tag me-1"></i>Propiedad de Material
                            </label>
                            <input type="text" class="form-control" id="editPropiedadMaterial" name="propiedadMaterial">
                        </div>
                        
                        <div class="form-group">
                            <label for="editClassification" class="form-label">
                                <i class="fas fa-layer-group me-1"></i>Clasificación
                            </label>
                            <input type="text" class="form-control" id="editClassification" name="classification">
                        </div>
                    </div>
                    
                    <!-- Especificaciones -->
                    <div class="form-section">
                        <h5><i class="fas fa-cogs me-2"></i>Especificaciones</h5>
                        
                        <div class="form-group">
                            <label for="editEspecificacionMaterial" class="form-label">
                                <i class="fas fa-file-alt me-1"></i>Especificación de Material
                            </label>
                            <input type="text" class="form-control" id="editEspecificacionMaterial" name="especificacionMaterial">
                        </div>
                        
                        <div class="form-group">
                            <label for="editUnidadEmpaque" class="form-label">
                                <i class="fas fa-box me-1"></i>Unidad de Empaque
                            </label>
                            <input type="text" class="form-control" id="editUnidadEmpaque" name="unidadEmpaque">
                        </div>
                        
                        <div class="form-group">
                            <label for="editUbicacionMaterial" class="form-label">
                                <i class="fas fa-map-marker-alt me-1"></i>Ubicación de Material
                            </label>
                            <input type="text" class="form-control" id="editUbicacionMaterial" name="ubicacionMaterial">
                        </div>
                        
                        <div class="form-group">
                            <label for="editVendedor" class="form-label">
                                <i class="fas fa-user-tie me-1"></i>Vendedor
                            </label>
                            <input type="text" class="form-control" id="editVendedor" name="vendedor">
                        </div>
                    </div>
                    
                    <!-- Características MSL -->
                    <div class="form-section">
                        <h5><i class="fas fa-thermometer-half me-2"></i>Características MSL</h5>
                        
                        <div class="form-group">
                            <label for="editNivelMsl" class="form-label">
                                <i class="fas fa-thermometer-half me-1"></i>Nivel de MSL
                            </label>
                            <input type="text" class="form-control" id="editNivelMsl" name="nivelMsl">
                        </div>
                        
                        <div class="form-group">
                            <label for="editEspesorMsl" class="form-label">
                                <i class="fas fa-ruler me-1"></i>Espesor de MSL
                            </label>
                            <input type="text" class="form-control" id="editEspesorMsl" name="espesorMsl">
                        </div>
                    </div>
                    
                    <!-- Configuraciones -->
                    <div class="form-section">
                        <h5><i class="fas fa-sliders-h me-2"></i>Configuraciones</h5>
                        
                        <div class="form-group">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="editProhibidoSacar" name="prohibidoSacar">
                                <label class="form-check-label" for="editProhibidoSacar">
                                    <i class="fas fa-ban me-1 text-danger"></i>Prohibido Sacar
                                </label>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="editReparable" name="reparable">
                                <label class="form-check-label" for="editReparable">
                                    <i class="fas fa-tools me-1 text-success"></i>Reparable
                                </label>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="drawer-footer">
                <button type="button" class="btn btn-secondary" onclick="materialEditDrawer.cerrarDrawer()">
                    <i class="fas fa-times me-1"></i>Cancelar
                </button>
                <button type="button" class="btn btn-primary" onclick="materialEditDrawer.guardarEdicion()">
                    <i class="fas fa-save me-1"></i>Guardar Cambios
                </button>
            </div>
        </div>

        <!-- Overlay -->
        <div id="drawerOverlay" class="drawer-overlay" onclick="materialEditDrawer.cerrarDrawer()"></div>
        `;

        // Inyectar HTML al final del body
        document.body.insertAdjacentHTML('beforeend', drawerHTML);

        // Inyectar estilos CSS
        this.injectStyles();
    }

    injectStyles() {
        const styles = `
        <style>
        /* 🎨 Estilos del Panel Lateral de Edición - Estilo del Sistema */
        .material-edit-drawer {
            position: fixed;
            right: -450px;
            top: 0;
            bottom: 0;
            width: 450px;
            background: #4a5568;
            box-shadow: -5px 0 25px rgba(0, 0, 0, 0.3);
            transition: right 0.4s ease;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            border-left: 2px solid #2d3748;
        }

        .material-edit-drawer.open {
            right: 0;
        }

        .drawer-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .drawer-overlay.active {
            display: block;
            opacity: 1;
        }

        .drawer-header {
            background-color: #2d3748;
            color: #e2e8f0;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #1a202c;
        }

        .drawer-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 400;
            color: #e2e8f0;
        }

        .btn-close-drawer {
            background: none;
            border: none;
            color: #e2e8f0;
            font-size: 18px;
            cursor: pointer;
            padding: 8px;
            border-radius: 0;
            transition: background-color 0.3s ease;
            width: 36px;
            height: 36px;
        }

        .btn-close-drawer:hover {
            background-color: #1a202c;
        }

        .drawer-body {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #3a4556;
        }

        .form-section {
            background: #4a5568;
            border-radius: 0;
            padding: 20px;
            margin-bottom: 15px;
            border-bottom: 2px solid #2d3748;
        }

        .form-section h5 {
            color: #cbd5e0;
            margin-bottom: 15px;
            font-size: 14px;
            font-weight: 400;
            padding-bottom: 8px;
            border-bottom: 1px solid #2d3748;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-label {
            color: #cbd5e0;
            margin-bottom: 5px;
            font-size: 13px;
            font-weight: 400;
            display: block;
        }

        .form-label .required {
            color: #5e9ed6;
        }

        .form-control {
            background-color: #2d3748;
            border: 1px solid #5e9ed6;
            color: #e2e8f0;
            padding: 8px 12px;
            border-radius: 0;
            font-size: 14px;
            height: 36px;
            width: 100%;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        .form-control:focus {
            outline: none;
            border-color: #63b3ed;
            box-shadow: 0 0 0 1px #63b3ed;
        }

        .form-control::placeholder {
            color: #718096;
        }

        .form-check-input {
            margin-right: 8px;
            background-color: #2d3748;
            border: 1px solid #5e9ed6;
        }

        .form-check-input:checked {
            background-color: #5e9ed6;
            border-color: #5e9ed6;
        }

        .form-check-label {
            color: #cbd5e0;
            font-size: 13px;
            font-weight: 400;
            cursor: pointer;
        }

        .drawer-footer {
            background: #2d3748;
            padding: 20px;
            border-top: 2px solid #1a202c;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .drawer-footer .btn {
            padding: 8px 24px;
            border-radius: 0;
            font-size: 14px;
            font-weight: 400;
            transition: all 0.3s ease;
            border: none;
            height: 36px;
            cursor: pointer;
        }

        .drawer-footer .btn-secondary {
            background-color: #4a5568;
            color: #e2e8f0;
            border: 1px solid #2d3748;
        }

        .drawer-footer .btn-secondary:hover {
            background-color: #2d3748;
        }

        .drawer-footer .btn-primary {
            background-color: #5e9ed6;
            color: #1a202c;
            border: 1px solid #5e9ed6;
        }

        .drawer-footer .btn-primary:hover {
            background-color: #63b3ed;
            border-color: #63b3ed;
        }

        .drawer-footer .btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            background-color: #1a202c;
        }

        /* Scroll personalizado */
        .drawer-body::-webkit-scrollbar {
            width: 8px;
        }

        .drawer-body::-webkit-scrollbar-track {
            background: #2d3748;
        }

        .drawer-body::-webkit-scrollbar-thumb {
            background: #4a5568;
            border-radius: 0;
        }

        .drawer-body::-webkit-scrollbar-thumb:hover {
            background: #5e9ed6;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .material-edit-drawer {
                width: 100%;
                right: -100%;
            }
        }

        /* Animaciones */
        @keyframes slideInFromRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .material-edit-drawer.open {
            animation: slideInFromRight 0.4s ease;
        }
        </style>
        `;

        document.head.insertAdjacentHTML('beforeend', styles);
    }

    bindEvents() {
        // El sistema ahora genera los botones directamente en la tabla
        // No necesitamos agregar botones automáticamente
        console.log(' Sistema de panel lateral listo - botones generados en tabla');
    }

    addEditButtonsToTable() {
        // Buscar tabla de materiales y agregar botones de editar
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    this.checkForNewTableRows();
                }
            });
        });

        // Observar cambios en el DOM para detectar cuando se carga la tabla
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Verificar si ya existe la tabla
        setTimeout(() => {
            this.checkForNewTableRows();
        }, 1000);
    }

    checkForNewTableRows() {
        // Buscar todas las filas de la tabla que no tengan botón de editar
        const tableRows = document.querySelectorAll('table tbody tr:not([data-edit-added])');
        
        tableRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length > 0) {
                // Agregar botón de editar en la última celda
                const lastCell = cells[cells.length - 1];
                
                // Crear botón de editar
                const editButton = document.createElement('button');
                editButton.className = 'btn btn-sm btn-outline-primary ms-2';
                editButton.innerHTML = '<i class="fas fa-edit"></i>';
                editButton.title = 'Editar Material';
                editButton.onclick = () => this.abrirPanelEdicion(row);
                
                lastCell.appendChild(editButton);
                row.setAttribute('data-edit-added', 'true');
            }
        });
    }

    abrirPanelEdicion(row) {
        const cells = row.querySelectorAll('td');
        
        if (cells.length < 13) {
            this.showError('Error: No se pueden obtener todos los datos de la fila');
            return;
        }

        // Extraer datos de la fila (ahora con 14 columnas incluyendo Acciones)
        this.currentEditingData = {
            codigoMaterialOriginal: cells[0]?.textContent?.trim() || '',
            codigoMaterial: cells[0]?.textContent?.trim() || '',
            numeroParte: cells[1]?.textContent?.trim() || '',
            propiedadMaterial: cells[2]?.textContent?.trim() || '',
            classification: cells[3]?.textContent?.trim() || '',
            especificacionMaterial: cells[4]?.textContent?.trim() || '',
            unidadEmpaque: cells[5]?.textContent?.trim() || '',
            ubicacionMaterial: cells[6]?.textContent?.trim() || '',
            vendedor: cells[7]?.textContent?.trim() || '',
            prohibidoSacar: cells[8]?.querySelector('input[type="checkbox"]')?.checked || false,
            reparable: cells[9]?.querySelector('input[type="checkbox"]')?.checked || false,
            nivelMsl: cells[10]?.textContent?.trim() || '',
            espesorMsl: cells[11]?.textContent?.trim() || ''
        };

        // Llenar el formulario
        this.llenarFormulario(this.currentEditingData);

        // Mostrar el drawer
        document.getElementById('editDrawer').classList.add('open');
        document.getElementById('drawerOverlay').classList.add('active');

        console.log('🔧 Panel de edición abierto para:', this.currentEditingData.codigoMaterial);
    }

    llenarFormulario(data) {
        // Llenar campos de texto
        document.getElementById('editCodigoMaterialOriginal').value = data.codigoMaterialOriginal;
        document.getElementById('editCodigoMaterial').value = data.codigoMaterial;
        document.getElementById('editNumeroParte').value = data.numeroParte;
        document.getElementById('editPropiedadMaterial').value = data.propiedadMaterial;
        document.getElementById('editClassification').value = data.classification;
        document.getElementById('editEspecificacionMaterial').value = data.especificacionMaterial;
        document.getElementById('editUnidadEmpaque').value = data.unidadEmpaque;
        document.getElementById('editUbicacionMaterial').value = data.ubicacionMaterial;
        document.getElementById('editVendedor').value = data.vendedor;
        document.getElementById('editNivelMsl').value = data.nivelMsl;
        document.getElementById('editEspesorMsl').value = data.espesorMsl;

        // Llenar checkboxes
        document.getElementById('editProhibidoSacar').checked = data.prohibidoSacar;
        document.getElementById('editReparable').checked = data.reparable;
    }

    cerrarDrawer() {
        document.getElementById('editDrawer').classList.remove('open');
        document.getElementById('drawerOverlay').classList.remove('active');
        this.currentEditingData = null;
    }

    async guardarEdicion() {
        try {
            // Obtener datos del formulario
            const formData = new FormData(document.getElementById('editMaterialForm'));
            const nuevos_datos = {};

            // Convertir FormData a objeto
            for (let [key, value] of formData.entries()) {
                if (key !== 'codigo_material_original') {
                    nuevos_datos[key] = value;
                }
            }

            // Procesar checkboxes
            nuevos_datos.prohibidoSacar = document.getElementById('editProhibidoSacar').checked;
            nuevos_datos.reparable = document.getElementById('editReparable').checked;

            const codigo_material_original = document.getElementById('editCodigoMaterialOriginal').value;

            // Validar datos requeridos
            if (!codigo_material_original) {
                throw new Error('Código de material original requerido');
            }

            if (!nuevos_datos.codigoMaterial) {
                throw new Error('Código de material es requerido');
            }

            // Mostrar indicador de carga
            this.showLoadingButton(true);

            console.log('📤 Enviando actualización:', { codigo_material_original, nuevos_datos });

            // Enviar al servidor
            const response = await fetch('/actualizar_material_completo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    codigo_material_original: codigo_material_original,
                    nuevos_datos: nuevos_datos
                })
            });

            const result = await response.json();

            if (result.success) {
                // Actualizar la tabla
                this.actualizarFilaEnTabla(codigo_material_original, nuevos_datos);
                
                // Cerrar drawer
                this.cerrarDrawer();
                
                // Mostrar mensaje de éxito
                this.showSuccess(result.message);
                
                console.log(' Material actualizado exitosamente');
            } else {
                throw new Error(result.error || 'Error desconocido al actualizar');
            }

        } catch (error) {
            console.error('❌ Error al guardar cambios:', error);
            this.showError('Error al guardar: ' + error.message);
        } finally {
            this.showLoadingButton(false);
        }
    }

    actualizarFilaEnTabla(codigoOriginal, nuevos_datos) {
        // Buscar la fila en la tabla
        const rows = document.querySelectorAll('table tbody tr');
        
        for (let row of rows) {
            const firstCell = row.querySelector('td');
            if (firstCell && firstCell.textContent.trim() === codigoOriginal) {
                const cells = row.querySelectorAll('td');
                
                // Actualizar cada celda (14 columnas total, la última es Acciones)
                if (cells[0]) cells[0].textContent = nuevos_datos.codigoMaterial || '';
                if (cells[1]) cells[1].textContent = nuevos_datos.numeroParte || '';
                if (cells[2]) cells[2].textContent = nuevos_datos.propiedadMaterial || '';
                if (cells[3]) cells[3].textContent = nuevos_datos.classification || '';
                if (cells[4]) cells[4].textContent = nuevos_datos.especificacionMaterial || '';
                if (cells[5]) cells[5].textContent = nuevos_datos.unidadEmpaque || '';
                if (cells[6]) cells[6].textContent = nuevos_datos.ubicacionMaterial || '';
                if (cells[7]) cells[7].textContent = nuevos_datos.vendedor || '';
                
                // Actualizar checkboxes
                const prohibidoCheckbox = cells[8]?.querySelector('input[type="checkbox"]');
                if (prohibidoCheckbox) {
                    prohibidoCheckbox.checked = nuevos_datos.prohibidoSacar;
                }
                
                const reparableCheckbox = cells[9]?.querySelector('input[type="checkbox"]');
                if (reparableCheckbox) {
                    reparableCheckbox.checked = nuevos_datos.reparable;
                }
                
                if (cells[10]) cells[10].textContent = nuevos_datos.nivelMsl || '';
                if (cells[11]) cells[11].textContent = nuevos_datos.espesorMsl || '';
                // cells[12] es fecha de registro - no la actualizamos
                // cells[13] es la columna de Acciones - no la tocamos
                
                // Efecto visual de actualización
                row.style.background = 'linear-gradient(90deg, #d4edda, transparent)';
                setTimeout(() => {
                    row.style.background = '';
                }, 2000);
                
                break;
            }
        }
    }

    showLoadingButton(loading) {
        const saveButton = document.querySelector('.drawer-footer .btn-primary');
        
        if (loading) {
            saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Guardando...';
            saveButton.disabled = true;
        } else {
            saveButton.innerHTML = '<i class="fas fa-save me-1"></i>Guardar Cambios';
            saveButton.disabled = false;
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type) {
        const toastClass = type === 'success' ? 'bg-success' : 'bg-danger';
        const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white ${toastClass} border-0 position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 11000; min-width: 300px;';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${icon} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Usar Bootstrap Toast si está disponible
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
            bsToast.show();
        } else {
            // Fallback sin Bootstrap
            toast.style.display = 'block';
            setTimeout(() => {
                toast.remove();
            }, 5000);
        }
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

//  Panel Lateral de Registro para Materiales
class MaterialRegistroDrawer {
    constructor() {
        this.createDrawerHTML();
        this.bindEvents();
    }

    createDrawerHTML() {
        const drawerHTML = `
        <!-- 🎨 Panel Lateral de Registro -->
        <div id="registroDrawer" class="material-edit-drawer">
            <div class="drawer-header">
                <h3><i class="fas fa-plus-circle me-2"></i>Registrar Nuevo Material</h3>
                <button type="button" class="btn-close-drawer" onclick="materialRegistroDrawer.cerrarDrawer()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            
            <div class="drawer-body">
                <form id="registroMaterialForm">
                    <!-- Información Principal -->
                    <div class="form-section">
                        <h5><i class="fas fa-info-circle me-2"></i>Información Principal</h5>
                        
                        <div class="form-group">
                            <label for="regCodigoMaterial" class="form-label">
                                <i class="fas fa-barcode me-1"></i>Código de Material <span class="required">*</span>
                            </label>
                            <input type="text" class="form-control" id="regCodigoMaterial" name="codigoMaterial" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="regNumeroParte" class="form-label">
                                <i class="fas fa-hashtag me-1"></i>Número de Parte <span class="required">*</span>
                            </label>
                            <input type="text" class="form-control" id="regNumeroParte" name="numeroParte" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="regPropiedadMaterial" class="form-label">
                                <i class="fas fa-tag me-1"></i>Propiedad de Material <span class="required">*</span>
                            </label>
                            <select class="form-control" id="regPropiedadMaterial" name="propiedadMaterial" required>
                                <option value="">Seleccionar propiedad</option>
                                <option value="PART">PART</option>
                                <option value="ETC">ETC</option>
                                <option value="PCB">PCB</option>
                                <option value="SMD">SMD</option>
                                <option value="COMMON USE">COMMON USE</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="regClassification" class="form-label">
                                <i class="fas fa-layer-group me-1"></i>Clasificación
                            </label>
                            <input type="text" class="form-control" id="regClassification" name="classification" placeholder="Ej: CHIP RESISTOR, CAPACITOR, etc.">
                        </div>
                    </div>
                    
                    <!-- Especificaciones -->
                    <div class="form-section">
                        <h5><i class="fas fa-cogs me-2"></i>Especificaciones</h5>
                        
                        <div class="form-group">
                            <label for="regEspecificacionMaterial" class="form-label">
                                <i class="fas fa-file-alt me-1"></i>Especificación de Material
                            </label>
                            <input type="text" class="form-control" id="regEspecificacionMaterial" name="especificacionMaterial" placeholder="Ej: 120J 1/4W (SMD 3216)">
                        </div>
                        
                        <div class="form-group">
                            <label for="regUnidadEmpaque" class="form-label">
                                <i class="fas fa-box me-1"></i>Unidad de Empaque
                            </label>
                            <input type="number" class="form-control" id="regUnidadEmpaque" name="unidadEmpaque" value="0" min="0">
                        </div>
                        
                        <div class="form-group">
                            <label for="regUbicacionMaterial" class="form-label">
                                <i class="fas fa-map-marker-alt me-1"></i>Ubicación de Material
                            </label>
                            <input type="text" class="form-control" id="regUbicacionMaterial" name="ubicacionMaterial" placeholder="Ubicación en almacén">
                        </div>
                        
                        <div class="form-group">
                            <label for="regVendedor" class="form-label">
                                <i class="fas fa-user-tie me-1"></i>Vendedor
                            </label>
                            <input type="text" class="form-control" id="regVendedor" name="vendedor" placeholder="Nombre del vendedor">
                        </div>
                    </div>
                    
                    <!-- Características MSL -->
                    <div class="form-section">
                        <h5><i class="fas fa-thermometer-half me-2"></i>Características MSL</h5>
                        
                        <div class="form-group">
                            <label for="regNivelMsl" class="form-label">
                                <i class="fas fa-thermometer-half me-1"></i>Nivel de MSL
                            </label>
                            <select class="form-control" id="regNivelMsl" name="nivelMSL">
                                <option value="">Seleccionar nivel</option>
                                <option value="1">Nivel 1</option>
                                <option value="2">Nivel 2</option>
                                <option value="3">Nivel 3</option>
                                <option value="4">Nivel 4</option>
                                <option value="5">Nivel 5</option>
                                <option value="6">Nivel 6</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="regEspesorMsl" class="form-label">
                                <i class="fas fa-ruler me-1"></i>Espesor de MSL
                            </label>
                            <input type="text" class="form-control" id="regEspesorMsl" name="espesorMSL" placeholder="Ej: 0.5mm">
                        </div>
                    </div>
                    
                    <!-- Configuraciones -->
                    <div class="form-section">
                        <h5><i class="fas fa-sliders-h me-2"></i>Configuraciones</h5>
                        
                        <div class="form-group">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="regProhibidoSacar" name="prohibidoSacar">
                                <label class="form-check-label" for="regProhibidoSacar">
                                    <i class="fas fa-ban me-1 text-danger"></i>Prohibido Sacar
                                </label>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="regReparable" name="reparable">
                                <label class="form-check-label" for="regReparable">
                                    <i class="fas fa-tools me-1 text-success"></i>Reparable
                                </label>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="drawer-footer">
                <button type="button" class="btn btn-secondary" onclick="materialRegistroDrawer.cerrarDrawer()">
                    <i class="fas fa-times me-1"></i>Cancelar
                </button>
                <button type="button" class="btn btn-primary" onclick="materialRegistroDrawer.guardarRegistro()">
                    <i class="fas fa-save me-1"></i>Registrar Material
                </button>
            </div>
        </div>

        <!-- Overlay para registro -->
        <div id="registroDrawerOverlay" class="drawer-overlay" onclick="materialRegistroDrawer.cerrarDrawer()"></div>
        `;

        // Inyectar HTML al final del body
        document.body.insertAdjacentHTML('beforeend', drawerHTML);
    }

    bindEvents() {
        // Vincular el evento submit del formulario
        const form = document.getElementById('registroMaterialForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.guardarRegistro();
            });
        }
    }

    abrirPanelRegistro() {
        // Limpiar formulario
        this.limpiarFormulario();
        
        // Mostrar el drawer
        document.getElementById('registroDrawer').classList.add('open');
        document.getElementById('registroDrawerOverlay').classList.add('active');

        console.log(' Panel de registro abierto');
    }

    cerrarDrawer() {
        document.getElementById('registroDrawer').classList.remove('open');
        document.getElementById('registroDrawerOverlay').classList.remove('active');
    }

    limpiarFormulario() {
        const form = document.getElementById('registroMaterialForm');
        if (form) {
            form.reset();
            // Restablecer valores por defecto
            document.getElementById('regUnidadEmpaque').value = '0';
        }
    }

    async guardarRegistro() {
        try {
            // Obtener datos del formulario
            const formData = new FormData(document.getElementById('registroMaterialForm'));
            const nuevoItem = {};

            // Convertir FormData a objeto
            for (let [key, value] of formData.entries()) {
                nuevoItem[key] = value;
            }

            // Procesar checkboxes
            nuevoItem.prohibidoSacar = document.getElementById('regProhibidoSacar').checked ? 1 : 0;
            nuevoItem.reparable = document.getElementById('regReparable').checked ? 1 : 0;

            // Validar campos requeridos
            if (!nuevoItem.codigoMaterial) {
                throw new Error('Código de material es requerido');
            }
            if (!nuevoItem.numeroParte) {
                throw new Error('Número de parte es requerido');
            }
            if (!nuevoItem.propiedadMaterial) {
                throw new Error('Propiedad de material es requerida');
            }

            // Mostrar indicador de carga
            this.showLoadingButton(true);

            console.log('📤 Enviando nuevo material:', nuevoItem);

            // Enviar al servidor
            const response = await fetch('/guardar_material', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(nuevoItem)
            });

            const result = await response.json();

            if (result.success) {
                // Cerrar drawer y limpiar formulario
                this.cerrarDrawer();
                this.limpiarFormulario();
                
                // Mostrar mensaje de éxito
                this.showSuccess(result.message || "Material registrado exitosamente! Haga clic en 'Consultar' para ver los datos actualizados.");
                
                console.log(' Material registrado exitosamente');
            } else {
                throw new Error(result.error || 'Error desconocido al registrar');
            }

        } catch (error) {
            console.error('❌ Error al registrar material:', error);
            this.showError('Error al registrar: ' + error.message);
        } finally {
            this.showLoadingButton(false);
        }
    }

    showLoadingButton(loading) {
        const saveButton = document.querySelector('#registroDrawer .btn-primary');
        
        if (loading) {
            saveButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Registrando...';
            saveButton.disabled = true;
        } else {
            saveButton.innerHTML = '<i class="fas fa-save me-1"></i>Registrar Material';
            saveButton.disabled = false;
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type) {
        const toastClass = type === 'success' ? 'bg-success' : 'bg-danger';
        const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white ${toastClass} border-0 position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 11000; min-width: 300px;';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${icon} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Usar Bootstrap Toast si está disponible
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
            bsToast.show();
        } else {
            // Fallback sin Bootstrap
            toast.style.display = 'block';
            setTimeout(() => {
                toast.remove();
            }, 5000);
        }
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// 🆕 También inicializar si ya está cargado el DOM (para AJAX)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.initializeMaterialDrawer);
} else {
    window.initializeMaterialDrawer();
}

// 🚀 Inicializar el sistema cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log(' Inicializando Panel de Edición de Materiales via DOMContentLoaded...');
    window.initializeMaterialDrawer();
});
