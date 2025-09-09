// ===========================================
// MÓDULO CONTROL DE EMBARQUE - ENCAPSULADO
// ===========================================
(function() {
    'use strict';
    
    // Variables locales para el sistema PO (ahora encapsuladas)
    let posData = [];

    // Variables para control de peticiones AJAX
    let currentPORequest = null;
    let currentModelosRequest = null;

    // Variable local para almacenar modelos BOM (encapsulada)
    let modelosBOM = [];

// ===========================================
// FUNCIONES AUXILIARES PARA EL NUEVO ESTILO
// ===========================================

// Función para cancelar peticiones AJAX pendientes
function cancelarPeticionesAJAX() {
    if (currentPORequest) {
        currentPORequest.abort();
        currentPORequest = null;
        console.log('Petición PO cancelada');
    }
    
    if (currentModelosRequest) {
        currentModelosRequest.abort();
        currentModelosRequest = null;
        console.log('Petición modelos cancelada');
    }
}

// Toggle para checkbox de seleccionar todo en POs
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#embarqueTable tbody input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
}

// Actualizar contador de resultados
function actualizarContador() {
    // Como solo manejamos POs ahora, simplemente usamos posData.length
    const total = posData.length;
    document.getElementById('embarqueResultCounter').textContent = `Total registros: ${total}`;
}

// Funciones de utilidad necesarias para consultarPOs
function mostrarCargando(mensaje = 'Consultando Purchase Orders...') {
    const modal = document.getElementById('smdLoadingModal');
    const title = document.getElementById('smdLoadingTitle');
    const text = document.getElementById('smdLoadingText');
    
    if (title) title.textContent = mensaje;
    if (text) text.textContent = 'Procesando datos';
    if (modal) {
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    }
}

function ocultarCargando() {
    const modal = document.getElementById('smdLoadingModal');
    if (modal) {
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

function mostrarToast(mensaje, tipo = 'info') {
    const iconos = {
        success: 'success',
        error: 'error',
        warning: 'warning',
        info: 'info'
    };

    Swal.fire({
        icon: iconos[tipo] || 'info',
        title: mensaje,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
    });
}

// ===========================================
// FUNCIONES PRINCIPALES ORIGINALES
// ===========================================

// Configurar fechas por defecto
function configurarFechasPorDefecto() {
    const hoy = new Date();
    
    // Configurar para consultar solo el día actual
    document.getElementById('fechaDesde').value = hoy.toISOString().split('T')[0];
    document.getElementById('fechaHasta').value = hoy.toISOString().split('T')[0];
}

// Consultar Purchase Orders
async function consultarPOs() {
    try {
        // Cancelar petición anterior si existe
        if (currentPORequest) {
            currentPORequest.abort();
        }
        
        // Crear nuevo AbortController
        currentPORequest = new AbortController();
        
        mostrarCargando('Consultando Purchase Orders...');
        
        // Temporalmente simplificar para debugging
        const estado = document.getElementById('estadoFilter')?.value || '';
        const url = `/api/po/listar${estado ? `?estado=${estado}` : ''}`;
        
        console.log('🔍 Consultando URL:', url);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: currentPORequest.signal  // Agregar señal de cancelación
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            posData = result.data || [];
            actualizarTablaPOs();
        } else {
            throw new Error(result.error || 'Error desconocido');
        }
        
    } catch (error) {
        // No mostrar error si la petición fue cancelada
        if (error.name === 'AbortError') {
            console.log('Petición PO cancelada por el usuario');
            return;
        }
        
        console.error('Error consultando POs:', error);
        mostrarToast('Error consultando Purchase Orders: ' + error.message, 'error');
        posData = [];
        actualizarTablaPOs();
    } finally {
        currentPORequest = null;
        ocultarCargando();
    }
}

// Actualizar tabla de POs
function actualizarTablaPOs() {
    const tbody = document.querySelector('#embarqueTable tbody');
    if (!tbody) {
        console.error('Elemento #embarqueTable tbody no encontrado');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (posData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="16" class="no-data">No hay Purchase Orders registradas</td></tr>';
        return;
    }
    
    posData.forEach(po => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="checkbox-custom row-select" data-po="${po.codigo_po}"></td>
            <td>${po.codigo_po}</td>
            <td>${po.nombre_po || '-'}</td>
            <td>${formatearFecha(po.fecha_registro)}</td>
            <td>${po.cliente || '-'}</td>
            <td>${po.modelo || '-'}</td>
            <td>${po.nombre_modelo || po.modelo || '-'}</td>
            <td>${po.proveedor || '-'}</td>
            <td>${po.total_cantidad_entregada || 0}</td>
            <td>${po.cantidad_entregada || 0}</td>
            <td>${obtenerBadgeEstado(po.estado, 'PO')}</td>
            <td>${po.codigo_entrega || 'N/A'}</td>
            <td>${po.fecha_entrega ? formatearFecha(po.fecha_entrega) : 'N/A'}</td>
            <td>${po.cantidad_entregada || 0}</td>
            <td>${po.usuario_creacion || 'Sistema'}</td>
            <td>${po.modificado ? formatearFecha(po.modificado) : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
    
    // Actualizar contador
    actualizarContador();
}

// ===========================================
// FUNCIONES AUXILIARES
// ===========================================

// Formatear fecha
function formatearFecha(fechaStr) {
    if (!fechaStr) return '-';
    const fecha = new Date(fechaStr);
    return fecha.toLocaleDateString('es-ES') + ' ' + fecha.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

// Obtener badge de estado
function obtenerBadgeEstado(estado, tipo) {
    const colores = {
        // Estados PO
        'PLAN': 'secondary',
        'PREPARACION': 'warning', 
        'EMBARCADO': 'info',
        'EN_TRANSITO': 'primary',
        'ENTREGADO': 'success',
        // Estados WO
        'CREADA': 'secondary',
        'PLANIFICADA': 'warning',
        'EN_PRODUCCION': 'primary',
        'CERRADA': 'success'
    };
    
    const color = colores[estado] || 'secondary';
    return `<span style="background-color: #${color === 'secondary' ? '95a5a6' : color === 'warning' ? 'f39c12' : color === 'info' ? '3498db' : color === 'primary' ? '2980b9' : '27ae60'}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 8px;">${estado.replace('_', ' ')}</span>`;
}

// ===========================================
// FUNCIONES DE INTERFAZ - BOOTSTRAP MODALS
// ===========================================

// Configurar fechas por defecto
function configurarFechasPorDefecto() {
    const hoy = new Date();
    const fechaInicio = new Date(hoy.getTime() - 7 * 24 * 60 * 60 * 1000); // 7 días atrás
    
    // Configurar fecha por defecto en modal WO
    const fechaOperacionInput = document.querySelector('#formCrearWO input[name="fecha_operacion"]');
    if (fechaOperacionInput) {
        fechaOperacionInput.value = hoy.toISOString().split('T')[0];
    }
}

// Inicializar modal de crear PO
// ===========================================
// FUNCIONES DE MODELOS BOM (COPIADAS DE PLAN DE PRODUCCIÓN)
// ===========================================

// Cargar modelos únicos de BOM
async function cargarModelosBOM() {
    try {
        // Cancelar petición anterior si existe
        if (currentModelosRequest) {
            currentModelosRequest.abort();
        }
        
        // Crear nuevo AbortController
        currentModelosRequest = new AbortController();
        
        console.log('Cargando modelos desde /api/raw/modelos...');
        const response = await fetch('/api/raw/modelos', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: currentModelosRequest.signal  // Agregar señal de cancelación
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Respuesta recibida:', data);
        
        if (data.success && Array.isArray(data.data) && data.data.length > 0) {
            // Los modelos vienen en data.data como array de strings
            modelosBOM = data.data.filter(modelo => modelo && modelo.trim() !== '');
            console.log('Modelos procesados:', modelosBOM);
            llenarDropdownModelos();
            console.log(`${modelosBOM.length} modelos cargados desde Control de BOM`);
        } else {
            console.warn('No se encontraron modelos en la respuesta');
            modelosBOM = [];
            llenarDropdownModelos();
            console.log('No se encontraron modelos en Control de BOM');
        }
    } catch (error) {
        // No procesar si la petición fue cancelada
        if (error.name === 'AbortError') {
            console.log('Petición de modelos cancelada por el usuario');
            return;
        }
        
        console.error('Error cargando modelos BOM:', error);
        console.error('Detalles del error:', {
            message: error.message,
            stack: error.stack
        });
        
        // Fallback: intentar con endpoint anterior si el nuevo falla
        try {
            console.log('Intentando con endpoint alternativo /listar_modelos_bom...');
            const fallbackResponse = await fetch('/listar_modelos_bom', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: currentModelosRequest.signal  // Usar la misma señal de cancelación
            });
            
            if (fallbackResponse.ok) {
                const fallbackData = await fallbackResponse.json();
                console.log('Respuesta de endpoint alternativo:', fallbackData);
                
                if (Array.isArray(fallbackData) && fallbackData.length > 0) {
                    modelosBOM = fallbackData.map(item => item.modelo || item).filter(modelo => modelo && modelo.trim() !== '');
                    llenarDropdownModelos();
                    console.log('Fallback exitoso con', modelosBOM.length, 'modelos');
                    return; // Exit successfully
                }
            }
        } catch (fallbackError) {
            console.error('Error en fallback:', fallbackError);
        }
        
        // Si todo falla
        modelosBOM = [];
        llenarDropdownModelos();
    } finally {
        currentModelosRequest = null;
    }
}

// Cargar modelos desde RAW (part_no) sin fallback
async function cargarModelosRAW() {
    try {
        if (currentModelosRequest) {
            currentModelosRequest.abort();
        }
        currentModelosRequest = new AbortController();

        const response = await fetch('/api/raw/modelos', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            signal: currentModelosRequest.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.success && Array.isArray(data.data)) {
            modelosBOM = data.data.filter(m => m && m.trim() !== '');
        } else {
            modelosBOM = [];
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        console.error('Error cargando modelos RAW:', error);
        modelosBOM = [];
    } finally {
        currentModelosRequest = null;
    }
}

// Llenar dropdown de modelos
function llenarDropdownModelos() {
    const dropdownList = document.getElementById('woDropdownList');
    
    if (!dropdownList) {
        console.error('Element woDropdownList not found in llenarDropdownModelos');
        return;
    }
    
    dropdownList.innerHTML = '';
    
    modelosBOM.forEach(modelo => {
        const item = document.createElement('div');
        item.className = 'embarque-dropdown-item';
        item.setAttribute('data-value', modelo);
        item.textContent = modelo;
        item.onclick = function() { seleccionarModeloWO(modelo); };
        dropdownList.appendChild(item);
    });
    
    console.log(`🔍 ${modelosBOM.length} modelos cargados en dropdown WO`);
}

// Función para filtrar modelos en el dropdown de WO
async function filtrarModelosWO() {
    const searchInput = document.getElementById('woModelo');
    const dropdownList = document.getElementById('woDropdownList');
    const searchTerm = searchInput.value.toLowerCase();
    
    // Si no hay modelos cargados, cargarlos primero
    if (modelosBOM.length === 0) {
        console.log('No hay modelos en memoria, cargando...');
        await mostrarDropdownWO();
        return;
    }
    
    // Mostrar el dropdown
    dropdownList.style.display = 'block';
    
    const items = dropdownList.querySelectorAll('.embarque-dropdown-item');
    let hasVisibleItems = false;
    
    items.forEach(item => {
        const modeloText = item.textContent.toLowerCase();
        if (modeloText.includes(searchTerm)) {
            item.classList.remove('hidden');
            hasVisibleItems = true;
        } else {
            item.classList.add('hidden');
        }
    });
    
    // Si no hay coincidencias, ocultar el dropdown
    if (!hasVisibleItems && searchTerm.length > 0) {
        // Mantener abierto y mostrar mensaje de "Sin coincidencias"
        // Eliminar mensajes previos
        const prev = dropdownList.querySelector('#po-no-results');
        if (prev) prev.remove();
        const msg = document.createElement('div');
        msg.id = 'po-no-results';
        msg.className = 'embarque-dropdown-item';
        msg.textContent = 'Sin coincidencias';
        msg.style.cssText = 'color:#f39c12; cursor: default;';
        dropdownList.appendChild(msg);
        dropdownList.style.display = 'block';
    } else {
        const prev = dropdownList.querySelector('#po-no-results');
        if (prev) prev.remove();
    }
}

// Función para mostrar dropdown de WO
async function mostrarDropdownWO() {
    console.log('=== mostrarDropdownWO() llamada ===');
    const dropdownList = document.getElementById('woDropdownList');
    const searchInput = document.getElementById('woModelo');
    
    if (!dropdownList) {
        console.error('Element woDropdownList not found');
        return;
    }
    
    if (!searchInput) {
        console.error('Element woModelo not found');
        return;
    }
    
    console.log('Elementos encontrados OK');
    console.log('Modelos disponibles en memoria:', modelosBOM.length);
    
    // Si no hay modelos en memoria, cargarlos dinámicamente
    if (modelosBOM.length === 0) {
        console.log('No hay modelos en memoria, cargando dinámicamente...');
        try {
            const response = await fetch('/api/raw/modelos', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Respuesta de modelos:', data);
            
            if (data.success && Array.isArray(data.data) && data.data.length > 0) {
                // Actualizar array local
                modelosBOM = data.data.filter(modelo => modelo && modelo.trim() !== '');
                console.log('Modelos actualizados:', modelosBOM.length);
                
                // Llenar dropdown inmediatamente
                llenarDropdownModelosDirecto(dropdownList);
                
                // Mostrar dropdown
                dropdownList.style.display = 'block';
                dropdownList.style.zIndex = '10000';
                dropdownList.style.position = 'absolute';
                
                console.log('Dropdown llenado con', modelosBOM.length, 'modelos');
            } else {
                console.warn('No se encontraron modelos o respuesta inválida');
                dropdownList.innerHTML = '<div class="embarque-dropdown-item" style="color: #f39c12;">No hay modelos disponibles</div>';
                dropdownList.style.display = 'block';
            }
        } catch (error) {
            console.error('Error cargando modelos desde MySQL:', error);
            console.error('Detalles del error:', {
                message: error.message,
                stack: error.stack
            });
            
            // Fallback: intentar con endpoint anterior si el nuevo falla
            try {
                console.log('Intentando con endpoint alternativo /listar_modelos_bom...');
                const fallbackResponse = await fetch('/listar_modelos_bom', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (fallbackResponse.ok) {
                    const fallbackData = await fallbackResponse.json();
                    console.log('Respuesta de endpoint alternativo:', fallbackData);
                    
                    if (Array.isArray(fallbackData) && fallbackData.length > 0) {
                        modelosBOM = fallbackData.map(item => item.modelo || item).filter(modelo => modelo && modelo.trim() !== '');
                        llenarDropdownModelosDirecto(dropdownList);
                        dropdownList.style.display = 'block';
                        dropdownList.style.zIndex = '10000';
                        dropdownList.style.position = 'absolute';
                        console.log('Fallback exitoso con', modelosBOM.length, 'modelos');
                        return; // Exit successfully
                    }
                }
            } catch (fallbackError) {
                console.error('Error en fallback:', fallbackError);
            }
            
            // Si todo falla, mostrar error
            dropdownList.innerHTML = '<div class="embarque-dropdown-item" style="color: #e74c3c;">Error cargando modelos</div>';
            dropdownList.style.display = 'block';
        }
    } else {
        // Si ya hay modelos, mostrar el dropdown normalmente
        dropdownList.style.display = 'block';
        dropdownList.style.zIndex = '10000';
        dropdownList.style.position = 'absolute';
        
        if (searchInput.value.trim() === '') {
            // Si el input está vacío, mostrar todos los modelos
            const items = dropdownList.querySelectorAll('.embarque-dropdown-item');
            console.log('Items en dropdown:', items.length);
            items.forEach(item => {
                item.classList.remove('hidden');
            });
            
            // Si no hay items, llenar el dropdown
            if (items.length === 0 && modelosBOM.length > 0) {
                console.log('Dropdown vacío, llenando con modelos...');
                llenarDropdownModelos();
            }
        }
    }
    
    console.log('Dropdown configurado - display:', dropdownList.style.display);
    console.log('=== fin mostrarDropdownWO() ===');
}

// Función auxiliar para llenar dropdown directamente
function llenarDropdownModelosDirecto(dropdownList) {
    dropdownList.innerHTML = '';
    
    modelosBOM.forEach(modelo => {
        const item = document.createElement('div');
        item.className = 'embarque-dropdown-item';
        item.setAttribute('data-value', modelo);
        item.textContent = modelo;
        item.onclick = function() { seleccionarModeloWO(modelo); };
        dropdownList.appendChild(item);
    });
    
    console.log(`${modelosBOM.length} modelos cargados en dropdown WO`);
}

// Función para seleccionar un modelo del dropdown de WO
function seleccionarModeloWO(modelo) {
    const searchInput = document.getElementById('woModelo');
    const dropdownList = document.getElementById('woDropdownList');
    
    searchInput.value = modelo;
    dropdownList.style.display = 'none';
    
    console.log('Modelo seleccionado para embarque:', modelo);
}

// Funciones para dropdown de modelos en formulario de PO
async function mostrarDropdownPO() {
    console.log('=== mostrarDropdownPO() llamada ===');
    const dropdownList = document.getElementById('poDropdownList');
    const searchInput = document.getElementById('poModelo');
    
    if (!dropdownList) {
        console.error('Element poDropdownList not found');
        return;
    }
    
    if (!searchInput) {
        console.error('Element poModelo not found');
        return;
    }
    
    console.log('Elementos encontrados OK');
    console.log('Modelos disponibles en memoria:', modelosBOM.length);
    
    // Si no hay modelos en memoria, cargarlos dinámicamente
    if (modelosBOM.length === 0) {
        console.log('No hay modelos en memoria, cargando dinámicamente...');
        try {
            const response = await fetch('/api/raw/modelos', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Respuesta de modelos:', data);
            
            if (data.success && Array.isArray(data.data) && data.data.length > 0) {
                modelosBOM = data.data.filter(modelo => modelo && modelo.trim() !== '');
                console.log('Modelos actualizados:', modelosBOM.length);
                
                llenarDropdownModelosDirectoPO(dropdownList);
                
                dropdownList.style.display = 'block';
                dropdownList.style.zIndex = '10000';
                dropdownList.style.position = 'absolute';
                
                console.log('Dropdown PO llenado con', modelosBOM.length, 'modelos');
            } else {
                console.warn('No se encontraron modelos o respuesta inválida');
                dropdownList.innerHTML = '<div class="embarque-dropdown-item" style="color: #f39c12;">No hay modelos disponibles</div>';
                dropdownList.style.display = 'block';
            }
        } catch (error) {
            console.error('Error cargando modelos desde MySQL:', error);
            dropdownList.innerHTML = '<div class="embarque-dropdown-item" style="color: #e74c3c;">Error cargando modelos</div>';
            dropdownList.style.display = 'block';
        }
    } else {
        dropdownList.style.display = 'block';
        dropdownList.style.zIndex = '10000';
        dropdownList.style.position = 'absolute';
        
        if (searchInput.value.trim() === '') {
            const items = dropdownList.querySelectorAll('.embarque-dropdown-item');
            console.log('Items en dropdown PO:', items.length);
            items.forEach(item => {
                item.classList.remove('hidden');
            });
            
            if (items.length === 0 && modelosBOM.length > 0) {
                console.log('Dropdown PO vacío, llenando con modelos...');
                llenarDropdownModelosDirectoPO(dropdownList);
            }
        }
    }
    
    console.log('=== fin mostrarDropdownPO() ===');
}

function llenarDropdownModelosDirectoPO(dropdownList) {
    dropdownList.innerHTML = '';
    
    modelosBOM.forEach(modelo => {
        const item = document.createElement('div');
        item.className = 'embarque-dropdown-item';
        item.setAttribute('data-value', modelo);
        item.textContent = modelo;
        item.onclick = function() { seleccionarModeloPO(modelo); };
        dropdownList.appendChild(item);
    });
    
    console.log(`${modelosBOM.length} modelos cargados en dropdown PO`);
}

function seleccionarModeloPO(modelo) {
    const searchInput = document.getElementById('poModelo');
    const dropdownList = document.getElementById('poDropdownList');
    
    searchInput.value = modelo;
    dropdownList.style.display = 'none';
    
    console.log('Modelo seleccionado para PO:', modelo);
}

async function filtrarModelosPO() {
    const searchInput = document.getElementById('poModelo');
    const dropdownList = document.getElementById('poDropdownList');
    const searchTerm = searchInput.value.toLowerCase();
    
    if (modelosBOM.length === 0) {
        console.log('No hay modelos en memoria, cargando...');
        await mostrarDropdownPO();
        return;
    }
    
    dropdownList.style.display = 'block';
    
    const items = dropdownList.querySelectorAll('.embarque-dropdown-item');
    let hasVisibleItems = false;
    
    items.forEach(item => {
        const modeloText = item.textContent.toLowerCase();
        if (modeloText.includes(searchTerm)) {
            item.classList.remove('hidden');
            hasVisibleItems = true;
        } else {
            item.classList.add('hidden');
        }
    });
    
    if (!hasVisibleItems && searchTerm.length > 0) {
        dropdownList.style.display = 'none';
    }
}

// ===========================================
// FUNCIONES DE MODAL
// ===========================================

function inicializarDrawerCrearPO() {
    const drawer = document.getElementById('crearPODrawer');
    const overlay = document.getElementById('drawerOverlayPO');
    
    if (drawer && overlay) {
        // Prevenir cierre del drawer al hacer click en el contenido
        drawer.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Cerrar drawer con tecla ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && drawer.classList.contains('open')) {
                cerrarDrawerPO();
            }
        });
        
        console.log('✅ Drawer crear PO inicializado correctamente');
    } else {
        console.log('⚠️ Elementos del drawer PO no encontrados en DOM');
    }
}

// Inicializar modal de crear WO
function inicializarModalCrearWO() {
    const modal = document.getElementById('modalCrearWO');
    if (modal) {
        // Prevenir cierre del modal al hacer click en el contenido
        const yahirModal = modal.querySelector('.yahir-modal');
        if (yahirModal) {
            yahirModal.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }
    }
}

// Abrir drawer para crear PO (reemplaza abrirModalCrearPO)
function abrirDrawerPO() {
    const drawer = document.getElementById('crearPODrawer');
    const overlay = document.getElementById('drawerOverlayPO');
    
    if (drawer && overlay) {
        // Configurar fecha por defecto
        const fechaHoy = new Date().toISOString().split('T')[0];
        const fechaRegistroInput = document.getElementById('fechaRegistroPO');
        if (fechaRegistroInput && !fechaRegistroInput.value) {
            fechaRegistroInput.value = fechaHoy;
        }
        
        // Mostrar drawer
        drawer.classList.add('open');
        overlay.classList.add('active');
        
        console.log('✅ Drawer PO abierto correctamente');
    } else {
        console.error('❌ No se encontraron elementos del drawer PO');
    }
}

// Cerrar drawer de PO
function cerrarDrawerPO() {
    const drawer = document.getElementById('crearPODrawer');
    const overlay = document.getElementById('drawerOverlayPO');
    
    if (drawer && overlay) {
        drawer.classList.remove('open');
        overlay.classList.remove('active');
        
        // Limpiar formulario
        const form = document.getElementById('formCrearPO');
        if (form) {
            form.reset();
        }
        
        console.log('✅ Drawer PO cerrado');
    }
}

// Abrir modal para crear WO desde PO
function abrirModalCrearWO(codigoPO) {
    const form = document.getElementById('formCrearWO');
    const codigoPoInput = form.querySelector('input[name="codigo_po"]');
    if (codigoPoInput) {
        codigoPoInput.value = codigoPO;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('modalCrearWO'), {
        backdrop: 'static',  // Evita cerrar al hacer click fuera
        keyboard: true      // Permite cerrar con ESC
    });
    modal.show();
}

// Abrir modal para cambiar estado
function abrirModalCambiarEstado(codigo, tipo) {
    const form = document.getElementById('formCambiarEstado');
    const codigoInput = form.querySelector('input[name="codigo"]');
    const tipoInput = form.querySelector('input[name="tipo"]');
    
    if (codigoInput) codigoInput.value = codigo;
    if (tipoInput) tipoInput.value = tipo;
    
    const selectEstado = form.querySelector('select[name="estado"]');
    if (selectEstado) {
        selectEstado.innerHTML = '';
        
        // Cargar opciones según el tipo
        const estados = tipo === 'PO' 
            ? ['PLAN', 'PREPARACION', 'EMBARCADO', 'EN_TRANSITO', 'ENTREGADO']
            : ['CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA'];
        
        estados.forEach(estado => {
            const option = document.createElement('option');
            option.value = estado;
            option.textContent = estado.replace('_', ' ');
            selectEstado.appendChild(option);
        });
    }
    
    const modal = new bootstrap.Modal(document.getElementById('modalCambiarEstado'));
    modal.show();
}

// ===========================================
// FUNCIONES CRUD
// ===========================================

// Crear nueva Purchase Order
async function crearPO() {
    try {
        const form = document.getElementById('formCrearPO');
        const formData = new FormData(form);
        const submitBtn = document.querySelector('.drawer-footer .btn-primary') || document.querySelector('[onclick="crearPO()"]');
        
        const data = {
            nombre_po: formData.get('nombre_po'),
            fecha_registro: formData.get('fecha_registro'),
            modelo: formData.get('modelo'),
            proveedor: formData.get('proveedor') || '',
            total_cantidad_entregada: parseInt(formData.get('total_cantidad_entregada')) || 0,
            fecha_entrega: formData.get('fecha_entrega'),
            cantidad_entregada: parseInt(formData.get('cantidad_entregada')) || 0,
            codigo_entrega: formData.get('codigo_entrega') || '',
            cliente: formData.get('cliente') || formData.get('proveedor') || 'Cliente General',
            estado: 'PLAN'
        };
        
        // Validaciones básicas
        if (!data.nombre_po) {
            mostrarToast('El nombre de PO es obligatorio', 'warning');
            return;
        }
        
        if (!data.fecha_registro) {
            mostrarToast('La fecha de registro es obligatoria', 'warning');
            return;
        }

        if (!data.modelo) {
            mostrarToast('Debe seleccionar un modelo', 'warning');
            return;
        }

        // Validar que al menos cliente o proveedor esté lleno
        if (!formData.get('cliente') && !formData.get('proveedor')) {
            mostrarToast('Debe especificar al menos el cliente o el proveedor', 'warning');
            return;
        }
        
        // Activar estado de loading en el botón
        const originalHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="yahir-loading"></div> Creando PO...';
        
        // Mostrar modal de loading personalizado
        mostrarModalLoading('Creando Purchase Order...', 'Procesando información y generando código PO');
        
        const response = await fetch('/api/po/crear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        // Verificar si la respuesta es válida
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Verificar el tipo de contenido
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const textResponse = await response.text();
            console.error('❌ Respuesta no es JSON:', textResponse);
            throw new Error('El servidor no devolvió JSON válido');
        }
        
        const result = await response.json();
        
        if (result.success) {
            ocultarModalLoading();
            mostrarToastModerno(`PO ${result.data.codigo_po} creada exitosamente`, 'success');
            
            // Cerrar drawer en lugar de modal
            cerrarDrawerPO();
            
            // Recargar tabla
            await consultarPOs();
        } else {
            throw new Error(result.error || 'Error creando PO');
        }
    } catch (error) {
        console.error('Error creando PO:', error);
        ocultarModalLoading();
        mostrarToastModerno('Error creando PO: ' + error.message, 'error');
    } finally {
        // Restaurar botón
        const submitBtn = document.querySelector('.drawer-footer .btn-primary') || document.querySelector('[onclick="crearPO()"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-save me-1"></i>Crear PO';
        }
    }
}

// Convertir PO a WO
async function convertirPOaWO() {
    try {
        const form = document.getElementById('formCrearWO');
        const formData = new FormData(form);
        const submitBtn = document.querySelector('[onclick="convertirPOaWO()"]');
        
        const data = {
            modelo: formData.get('modelo'),
            cantidad_planeada: parseInt(formData.get('cantidad_planeada')),
            fecha_operacion: formData.get('fecha_operacion')
        };
        
        const codigoPO = formData.get('codigo_po');
        
        if (!data.modelo || !data.cantidad_planeada || !data.fecha_operacion) {
            mostrarToastModerno('Todos los campos son obligatorios', 'warning');
            return;
        }

        if (data.cantidad_planeada < 1) {
            mostrarToastModerno('La cantidad planeada debe ser mayor a 0', 'warning');
            return;
        }
        
        // Activar estado de loading en el botón
        const originalHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="yahir-loading"></div> Convirtiendo...';
        
        // Mostrar modal de loading personalizado
        mostrarModalLoading('Convirtiendo PO → WO', `Creando Work Order desde PO ${codigoPO}`);
        
        const response = await fetch(`/api/po/${codigoPO}/convertir-wo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            ocultarModalLoading();
            mostrarToastModerno(`WO ${result.data.wo.codigo_wo} creada desde PO ${codigoPO}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('modalCrearWO')).hide();
            form.reset();
            await consultarWOs(); // Recargar tabla WOs
        } else {
            throw new Error(result.error || 'Error convirtiendo PO → WO');
        }
    } catch (error) {
        console.error('Error convirtiendo PO → WO:', error);
        ocultarModalLoading();
        mostrarToastModerno('Error convirtiendo PO → WO: ' + error.message, 'error');
    } finally {
        // Restaurar botón
        const submitBtn = document.querySelector('[onclick="convertirPOaWO()"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-cogs"></i> Crear WO';
        }
    }
}

// Actualizar estado (PO o WO)
async function actualizarEstado() {
    try {
        const form = document.getElementById('formCambiarEstado');
        const formData = new FormData(form);
        
        const codigo = formData.get('codigo');
        const tipo = formData.get('tipo');
        const estado = formData.get('estado');
        
        if (!estado) {
            mostrarToast('Debe seleccionar un estado', 'warning');
            return;
        }
        
        mostrarCargando('Actualizando estado...');
        
        const endpoint = tipo === 'PO' ? `/api/po/${codigo}/estado` : `/api/wo/${codigo}/estado`;
        
        const response = await fetch(endpoint, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ estado })
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarToast(`Estado actualizado a ${estado}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('modalCambiarEstado')).hide();
            
            // Recargar tabla correspondiente
            if (tipo === 'PO') {
                await consultarPOs();
            } else {
                await consultarWOs();
            }
        } else {
            throw new Error(result.error || 'Error actualizando estado');
        }
    } catch (error) {
        console.error('Error actualizando estado:', error);
        mostrarToast('Error actualizando estado: ' + error.message, 'error');
    } finally {
        ocultarCargando();
    }
}

function exportarDatos() {
    const tabActiva = document.querySelector('.embarque-tab.active').textContent;
    
    if (tabActiva.includes('Purchase Orders')) {
        if (posData.length === 0) {
            mostrarToast('No hay POs para exportar', 'warning');
            return;
        }
        mostrarToast('Exportando Purchase Orders...', 'info');
    } else {
        if (wosData.length === 0) {
            mostrarToast('No hay WOs para exportar', 'warning'); 
            return;
        }
        mostrarToast('Exportando Work Orders...', 'info');
    }
}

// ===========================================
// INICIALIZACIÓN
// ===========================================

// Función de inicialización explícita para carga dinámica
function initControlEmbarque() {
    console.log('🚀 Inicializando Control de Embarque...');
    
    // Configurar fechas por defecto
    configurarFechasPorDefecto();
    
    // Cargar modelos desde RAW (part_no)
    cargarModelosRAW();
    
    // Inicializar drawer de crear PO
    inicializarDrawerCrearPO();
    
    // Inicializar modal de crear WO
    inicializarModalCrearWO();
    
    // Cargar datos iniciales
    consultarPOs();
    
    console.log('✅ Control de Embarque - Sistema PO → WO completamente funcional');
}

// Mantener compatibilidad con carga directa
document.addEventListener('DOMContentLoaded', function() {
    console.log('📥 DOMContentLoaded - Control de Embarque');
    initControlEmbarque();
});

// Hacer la función disponible globalmente para carga dinámica
window.initControlEmbarque = initControlEmbarque;

// ===============================================
// FUNCIONES DE MODALES LOADING MODERNOS
// ===============================================

function mostrarModalLoading(titulo, mensaje) {
    // Crear modal de loading si no existe
    let loadingModal = document.getElementById('yahirLoadingModal');
    if (!loadingModal) {
        loadingModal = document.createElement('div');
        loadingModal.id = 'yahirLoadingModal';
        loadingModal.innerHTML = `
            <div class="yahir-modal-backdrop">
                <div class="yahir-modal" style="width: 400px; min-height: 200px;">
                    <div class="yahir-modal-header" style="background: linear-gradient(135deg, #667eea, #764ba2);">
                        <h3 class="yahir-modal-title" id="loadingTitle">
                            <i class="fas fa-spinner fa-spin"></i>Procesando...
                        </h3>
                    </div>
                    <div class="yahir-modal-body" style="text-align: center; padding: 40px 30px;">
                        <div style="margin-bottom: 20px;">
                            <div class="yahir-loading" style="width: 40px; height: 40px; margin: 0 auto 20px auto;"></div>
                        </div>
                        <p id="loadingMessage" style="margin: 0; color: #a0a9c0; font-size: 14px;">
                            Procesando información...
                        </p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(loadingModal);
    }
    
    // Actualizar contenido
    document.getElementById('loadingTitle').innerHTML = `<i class="fas fa-spinner fa-spin"></i>${titulo}`;
    document.getElementById('loadingMessage').textContent = mensaje;
    
    // Mostrar modal
    loadingModal.style.display = 'block';
    
    return loadingModal;
}

function ocultarModalLoading() {
    const loadingModal = document.getElementById('yahirLoadingModal');
    if (loadingModal) {
        loadingModal.style.display = 'none';
    }
}

function mostrarToastModerno(mensaje, tipo = 'info', duracion = 3000) {
    // Crear toast container si no existe
    let toastContainer = document.getElementById('yahirToastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'yahirToastContainer';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        `;
        document.body.appendChild(toastContainer);
    }
    
    // Crear toast
    const toast = document.createElement('div');
    const iconMap = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    const colorMap = {
        success: 'linear-gradient(135deg, #48bb78, #38a169)',
        error: 'linear-gradient(135deg, #e53e3e, #c53030)',
        warning: 'linear-gradient(135deg, #ed8936, #dd6b20)',
        info: 'linear-gradient(135deg, #667eea, #764ba2)'
    };
    
    toast.style.cssText = `
        background: ${colorMap[tipo]};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        min-width: 300px;
        animation: slideInRight 0.3s ease-out;
        pointer-events: auto;
        cursor: pointer;
    `;
    
    toast.innerHTML = `
        <i class="${iconMap[tipo]}" style="margin-right: 12px; font-size: 16px;"></i>
        <span style="flex: 1;">${mensaje}</span>
        <i class="fas fa-times" style="margin-left: 15px; cursor: pointer; opacity: 0.8;"></i>
    `;
    
    // Agregar estilos de animación si no existen
    if (!document.getElementById('yahirToastStyles')) {
        const style = document.createElement('style');
        style.id = 'yahirToastStyles';
        style.textContent = `
            @keyframes slideInRight {
                from { opacity: 0; transform: translateX(100%); }
                to { opacity: 1; transform: translateX(0); }
            }
            @keyframes slideOutRight {
                from { opacity: 1; transform: translateX(0); }
                to { opacity: 0; transform: translateX(100%); }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Función para cerrar toast
    const cerrarToast = () => {
        toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    };
    
    // Event listeners
    toast.addEventListener('click', cerrarToast);
    toast.querySelector('.fa-times').addEventListener('click', (e) => {
        e.stopPropagation();
        cerrarToast();
    });
    
    // Agregar al container
    toastContainer.appendChild(toast);
    
    // Auto-cerrar
    if (duracion > 0) {
        setTimeout(cerrarToast, duracion);
    }
    
    return toast;
}

// =============================================
// FUNCIONES PARA DROPDOWN DE MODELOS EN PO
// =============================================

// Mostrar dropdown de modelos en formulario PO
async function mostrarDropdownPO() {
    console.log('=== mostrarDropdownPO() llamada ===');
    const dropdownList = document.getElementById('poDropdownList');
    const searchInput = document.getElementById('poModelo');
    
    if (!dropdownList) {
        console.error('Element poDropdownList not found');
        return;
    }
    
    if (!searchInput) {
        console.error('Element poModelo not found');
        return;
    }
    
    console.log('Elementos PO encontrados OK');
    console.log('Modelos disponibles en memoria:', modelosBOM.length);
    
    // Si no hay modelos en memoria, cargarlos dinámicamente
    if (modelosBOM.length === 0) {
        console.log('No hay modelos en memoria, cargando dinámicamente...');
        await cargarModelosRAW();
    }
    
    // Llenar dropdown con modelos
    llenarDropdownModelosPO();
    
    // Mostrar dropdown
    dropdownList.style.display = 'block';
    console.log('Dropdown PO mostrado');
}

// Llenar dropdown de modelos para PO
function llenarDropdownModelosPO() {
    const dropdownList = document.getElementById('poDropdownList');
    
    if (!dropdownList) {
        console.error('Element poDropdownList not found');
        return;
    }
    
    dropdownList.innerHTML = '';
    
    modelosBOM.forEach(modelo => {
        const item = document.createElement('div');
        item.className = 'embarque-dropdown-item';
        item.textContent = modelo;
        item.style.cssText = `
            padding: 10px;
            cursor: pointer;
            border-bottom: 1px solid #34495e;
            color: #ecf0f1;
            font-size: 12px;
            transition: background-color 0.3s;
        `;
        item.onmouseover = function() { this.style.backgroundColor = '#3498db'; };
        item.onmouseout = function() { this.style.backgroundColor = 'transparent'; };
        item.onclick = () => seleccionarModeloPO(modelo);
        dropdownList.appendChild(item);
    });
    
    console.log(`Dropdown PO llenado con ${modelosBOM.length} modelos`);
    
    // Aplicar estilos al dropdown
    dropdownList.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background-color: #2c3e50;
        border: 1px solid #34495e;
        border-top: none;
        border-radius: 0 0 4px 4px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
    `;
}

// Event listeners para cerrar dropdowns cuando se hace clic fuera
document.addEventListener('click', function(event) {
    const embarqueSearchContainer = document.querySelector('.embarque-search-container');
    const woDropdownList = document.getElementById('woDropdownList');
    
    if (embarqueSearchContainer && !embarqueSearchContainer.contains(event.target) && woDropdownList) {
        woDropdownList.style.display = 'none';
    }
    
    const poDropdown = document.getElementById('poDropdownList');
    const poInput = document.getElementById('poModelo');
    
    if (poDropdown && poInput) {
        if (!poInput.contains(event.target) && !poDropdown.contains(event.target)) {
            poDropdown.style.display = 'none';
        }
    }
});

// Limpiar peticiones AJAX al descargar la página
window.addEventListener('beforeunload', function() {
    cancelarPeticionesAJAX();
    console.log('Limpieza de peticiones AJAX completada');
});

// Limpiar peticiones AJAX al cambiar de página
window.addEventListener('pagehide', function() {
    cancelarPeticionesAJAX();
});

// Hacer todas las funciones disponibles globalmente (solo las necesarias)
window.toggleSelectAll = toggleSelectAll;
window.consultarPOs = consultarPOs;
window.exportarDatos = exportarDatos;
window.abrirDrawerPO = abrirDrawerPO;
window.cerrarDrawerPO = cerrarDrawerPO;
window.filtrarModelosPO = filtrarModelosPO;
window.mostrarDropdownPO = mostrarDropdownPO;
window.seleccionarModeloPO = seleccionarModeloPO;
window.crearPO = crearPO;
window.convertirPOaWO = convertirPOaWO;
window.actualizarEstado = actualizarEstado;

console.log('Control de embarque - Sistema PO inicializado');

})(); // Fin del IIFE - Cierre del módulo encapsulado
