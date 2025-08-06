// 🎯 Panel Lateral de Edición para Materiales
// 📝 Sistema moderno con animaciones para editar materiales

// 🆕 Función global para forzar inicialización (útil para AJAX)
window.initializeMaterialDrawer = function() {
    if (!window.materialEditDrawer) {
        console.log('🎯 Inicializando Panel de Edición de Materiales...');
        window.materialEditDrawer = new MaterialEditDrawer();
        console.log('✅ Panel de Edición de Materiales inicializado');
        return true;
    }
    return false;
};

// Funciones globales para compatibilidad y carga AJAX
window.abrirPanelEdicion = function(btn) {
    console.log('🎯 Intentando abrir panel de edición...');
    
    // Asegurar que el drawer esté inicializado
    if (!window.materialEditDrawer) {
        console.log('⚠️ MaterialEditDrawer no inicializado, inicializando ahora...');
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

        // Inyectar estilos CSS desde archivo externo
        this.injectStyles();
    }

    injectStyles() {
        const styles = `
        <style>
        /* 🎨 Estilos del Panel Lateral de Edición */
        .material-edit-drawer {
            position: fixed;
            right: -450px;
            top: 0;
            bottom: 0;
            width: 450px;
            background: #ffffff;
            box-shadow: -5px 0 25px rgba(0, 0, 0, 0.15);
            transition: right 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .drawer-overlay.active {
            display: block;
            opacity: 1;
        }

        .drawer-header {
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            color: white;
            padding: 20px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .drawer-header h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }

        .btn-close-drawer {
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 5px;
            border-radius: 50%;
            transition: background-color 0.3s ease;
        }

        .btn-close-drawer:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }

        .drawer-body {
            flex: 1;
            overflow-y: auto;
            padding: 25px;
            background: #f8f9fa;
        }

        .form-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border-left: 4px solid #4a90e2;
        }

        .form-section h5 {
            color: #4a90e2;
            margin-bottom: 20px;
            font-size: 16px;
            font-weight: 600;
            padding-bottom: 10px;
            border-bottom: 1px solid #e9ecef;
        }

        .form-group {
            margin-bottom: 18px;
        }

        .form-label {
            font-weight: 500;
            color: #495057;
            margin-bottom: 8px;
            display: block;
        }

        .form-label .required {
            color: #dc3545;
        }

        .form-control {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px 15px;
            font-size: 14px;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
            width: 100%;
        }

        .form-control:focus {
            border-color: #4a90e2;
            outline: 0;
            box-shadow: 0 0 0 0.2rem rgba(74, 144, 226, 0.15);
        }

        .form-check-input {
            margin-right: 8px;
            transform: scale(1.1);
        }

        .form-check-input:checked {
            background-color: #4a90e2;
            border-color: #4a90e2;
        }

        .form-check-label {
            font-weight: 500;
            cursor: pointer;
        }

        .drawer-footer {
            background: white;
            padding: 20px 25px;
            border-top: 1px solid #e9ecef;
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
        }

        .drawer-footer .btn {
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
            border: none;
        }

        .drawer-footer .btn-secondary {
            background-color: #6c757d;
            color: white;
        }

        .drawer-footer .btn-secondary:hover {
            background-color: #5a6268;
            transform: translateY(-1px);
        }

        .drawer-footer .btn-primary {
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            color: white;
        }

        .drawer-footer .btn-primary:hover {
            background: linear-gradient(135deg, #357abd 0%, #2968a3 100%);
            transform: translateY(-1px);
            box-shadow: 0 5px 15px rgba(74, 144, 226, 0.3);
        }

        .drawer-footer .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Scroll personalizado */
        .drawer-body::-webkit-scrollbar {
            width: 6px;
        }

        .drawer-body::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        .drawer-body::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 3px;
        }

        .drawer-body::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
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
            animation: slideInFromRight 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        </style>
        `;

        // Verificar si ya se cargó el CSS con estilos similares a control_bom.css
        if (!document.querySelector('link[href*="material-edit-drawer-bom.css"]')) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = '/static/css/material-edit-drawer-bom.css';
            document.head.appendChild(link);
        }
    }

    bindEvents() {
        // El sistema ahora genera los botones directamente en la tabla
        // No necesitamos agregar botones automáticamente
        console.log('🎯 Sistema de panel lateral listo - botones generados en tabla');
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
                
                console.log('✅ Material actualizado exitosamente');
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

// 🆕 También inicializar si ya está cargado el DOM (para AJAX)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.initializeMaterialDrawer);
} else {
    window.initializeMaterialDrawer();
}

// 🚀 Inicializar el sistema cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Inicializando Panel de Edición de Materiales via DOMContentLoaded...');
    window.initializeMaterialDrawer();
});
