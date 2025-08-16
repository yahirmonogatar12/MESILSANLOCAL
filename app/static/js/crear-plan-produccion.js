// ===========================================
// MÓDULO CREAR PLAN DE PRODUCCIÓN - ENCAPSULADO
// ===========================================
(function() {
    'use strict';
    
    // Variables locales (ahora encapsuladas)
    let modelosBOM = [];
    let woData = [];

        // ================================================
        // FUNCIONES NECESARIAS ANTES DE DOM READY
        // ================================================

        // Mostrar formulario de WO - FUNCIÓN CRÍTICA
        async function mostrarFormularioWO() {
            console.log('mostrarFormularioWO llamada');
            document.getElementById('woFormContainer').style.display = 'block';
            document.getElementById('btnCrearWO').style.display = 'none';
            generarCodigoWO();
            
            // Siempre cargar modelos para asegurar que estén disponibles
            console.log('Cargando modelos BOM...');
            await cargarModelosBOM();
            
            // Verificar que el dropdown esté inicializado correctamente
            setTimeout(() => {
                const dropdown = document.getElementById('woDropdownList');
                const input = document.getElementById('woModelo');
                if (dropdown && input) {
                    console.log('Dropdown status check:');
                    console.log('- Dropdown exists:', !!dropdown);
                    console.log('- Dropdown display:', dropdown.style.display);
                    console.log('- Dropdown z-index:', dropdown.style.zIndex);
                    console.log('- Dropdown items:', dropdown.children.length);
                    console.log('- Input exists:', !!input);
                } else {
                    console.error('Dropdown o input no encontrados');
                }
            }, 200);
        }

        // Generar código de WO automáticamente
        function generarCodigoWO() {
            const hoy = new Date();
            const year = hoy.getFullYear().toString().slice(-2);
            const month = (hoy.getMonth() + 1).toString().padStart(2, '0');
            const day = hoy.getDate().toString().padStart(2, '0');
            
            // Generar número secuencial (simplificado, en producción se obtendría del servidor)
            const secuencial = Math.floor(Math.random() * 9999).toString().padStart(4, '0');
            const codigoWO = `WO-${year}${month}${day}-${secuencial}`;
            
            document.getElementById('woCodigoWO').value = codigoWO;
        }

        // Asignaciones globales inmediatas para onclick handlers
        window.mostrarFormularioWO = mostrarFormularioWO;

        // Función de inicialización explícita para carga dinámica
        function initCrearPlanProduccion() {
            console.log('🚀 Inicializando Crear Plan de Producción...');
            cargarModelosBOM();
            configurarEventos();
            
            // Asegurar que las fechas se configuren después de que los elementos estén disponibles
            setTimeout(() => {
                establecerFechaActual();
                // Consultar WOs del día actual después de establecer las fechas
                setTimeout(consultarWOs, 200);
            }, 50);
            
            console.log('✅ Crear Plan de Producción inicializado correctamente');
        }

        // Mantener compatibilidad con carga directa
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📥 DOMContentLoaded - Crear Plan de Producción');
            initCrearPlanProduccion();
        });

        // Hacer la función disponible globalmente para carga dinámica
        window.initCrearPlanProduccion = initCrearPlanProduccion;

        // Configurar eventos de botones
        function configurarEventos() {
            console.log('Configurando eventos...');
            document.getElementById('btnCrearWO').addEventListener('click', mostrarFormularioWO);
            document.getElementById('btnCancelarWO').addEventListener('click', ocultarFormularioWO);
            document.getElementById('btnGuardarWO').addEventListener('click', crearNuevaWO);
            document.getElementById('btnConsultar').addEventListener('click', consultarWOs);
            document.getElementById('btnRegistrar').addEventListener('click', mostrarFormularioWO); // Mismo que crear WO
            document.getElementById('btnCancelar').addEventListener('click', cancelarOperacion); // Nueva función inteligente
            document.getElementById('btnExportar').addEventListener('click', exportarExcel);
            
            // Eventos para checkboxes maestros
            document.getElementById('checkAll1').addEventListener('change', toggleAllCheckboxes);
            document.getElementById('checkAll2').addEventListener('change', toggleAllCheckboxes);
            console.log('Eventos configurados exitosamente');
        }

        // Establecer fecha actual por defecto
        function establecerFechaActual() {
            const hoy = new Date().toISOString().split('T')[0];
            
            // Establecer fechas en formulario WO
            const fechaInput = document.getElementById('woFechaOperacion');
            if (fechaInput) {
                fechaInput.value = hoy;
            }
            
            // Establecer fechas en filtros (ambas al día actual)
            const fechaDesde = document.getElementById('fechaDesde');
            const fechaHasta = document.getElementById('fechaHasta');
            
            if (fechaDesde && fechaHasta) {
                fechaDesde.value = hoy;
                fechaHasta.value = hoy;
            }
        }

        // Cargar modelos únicos de BOM
        async function cargarModelosBOM() {
            try {
                console.log('Cargando modelos desde /api/bom/modelos...');
                const response = await fetch('/api/bom/modelos', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
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
                    mostrarMensaje(`${modelosBOM.length} modelos cargados desde Control de BOM`, 'success');
                } else {
                    console.warn('No se encontraron modelos en la respuesta');
                    modelosBOM = [];
                    llenarDropdownModelos();
                    mostrarMensaje('No se encontraron modelos en Control de BOM', 'warning');
                }
            } catch (error) {
                console.error('Error cargando modelos BOM:', error);
                mostrarMensaje('Error cargando modelos de BOM: ' + error.message, 'error');
                modelosBOM = [];
                llenarDropdownModelos();
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
                item.className = 'bom-dropdown-item';
                item.setAttribute('data-value', modelo);
                item.textContent = modelo;
                item.onclick = function() { seleccionarModeloWO(modelo); };
                dropdownList.appendChild(item);
            });
            
            console.log(` ${modelosBOM.length} modelos cargados en dropdown WO`);
        }

        // Ocultar formulario de WO
        function ocultarFormularioWO() {
            document.getElementById('woFormContainer').style.display = 'none';
            document.getElementById('btnCrearWO').style.display = 'inline-block';
            limpiarFormularioWO();
        }

        // Limpiar formulario
        function limpiarFormularioWO() {
            document.getElementById('woCodigoWO').value = '';
            document.getElementById('woCodigoPO').value = '';
            document.getElementById('woModelo').value = '';
            document.getElementById('woOrdenProceso').value = '';
            document.getElementById('woCantidad').value = '';
            
            // Ocultar dropdown de modelos
            const dropdownList = document.getElementById('woDropdownList');
            if (dropdownList) {
                dropdownList.style.display = 'none';
            }
            
            establecerFechaActual();
        }

        // Función para el botón Cancelar de la barra de herramientas
        function cancelarOperacion() {
            const formularioVisible = document.getElementById('woFormContainer').style.display !== 'none';
            
            if (formularioVisible) {
                // Si hay un formulario abierto, ocultarlo
                ocultarFormularioWO();
                mostrarMensaje('Operación cancelada', 'success');
            } else {
                // Si no hay formulario abierto, limpiar filtros y recargar datos
                establecerFechaActual();
                cargarWOs();
                mostrarMensaje('Filtros restablecidos', 'success');
            }
        }

        // Crear nueva WO
        async function crearNuevaWO() {
            const codigoWO = document.getElementById('woCodigoWO').value.trim();
            // codigoPO ahora es opcional para WO independientes
            const codigoPO = document.getElementById('woCodigoPO').value.trim() || 'SIN-PO';
            const modelo = document.getElementById('woModelo').value;
            const cantidad = parseInt(document.getElementById('woCantidad').value);
            const fechaOperacion = document.getElementById('woFechaOperacion').value;

            // Validaciones
            if (!codigoWO) {
                mostrarMensaje('Por favor genere un código de WO', 'error');
                return;
            }
            if (!modelo) {
                mostrarMensaje('Por favor seleccione un modelo', 'error');
                return;
            }
            if (!cantidad || cantidad <= 0) {
                mostrarMensaje('Por favor ingrese una cantidad válida', 'error');
                return;
            }
            if (!fechaOperacion) {
                mostrarMensaje('Por favor seleccione una fecha de operación', 'error');
                return;
            }

            // Preparar datos - codigo_po es opcional para WO independientes
            const data = {
                codigo_wo: codigoWO,
                codigo_po: codigoPO, // Si está vacío, se usará 'SIN-PO' por defecto
                modelo: modelo,
                cantidad_planeada: cantidad,
                fecha_operacion: fechaOperacion
            };

            try {
                // Deshabilitar botón durante la creación
                const btnGuardar = document.getElementById('btnGuardarWO');
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Registrando...';

                const response = await fetch('/api/wo/crear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    mostrarMensaje(`WO creada exitosamente: ${result.data.codigo_wo}`, 'success');
                    ocultarFormularioWO();
                    // Recargar la tabla dinámicamente
                    await cargarWOs();
                } else {
                    mostrarMensaje('Error creando WO: ' + result.error, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error de conexión al crear WO', 'error');
            } finally {
                // Rehabilitar botón
                const btnGuardar = document.getElementById('btnGuardarWO');
                btnGuardar.disabled = false;
                btnGuardar.textContent = 'Registrar';
            }
        }

        // Función para mostrar mensajes
        function mostrarMensaje(mensaje, tipo) {
            // Crear el elemento de mensaje
            const msgDiv = document.createElement('div');
            msgDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                z-index: 10000;
                max-width: 400px;
                background-color: ${tipo === 'success' ? '#27ae60' : '#e74c3c'};
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            msgDiv.textContent = mensaje;
            
            document.body.appendChild(msgDiv);
            
            // Eliminar después de 4 segundos
            setTimeout(() => {
                if (document.body.contains(msgDiv)) {
                    document.body.removeChild(msgDiv);
                }
            }, 4000);
        }

        // Función para filtrar modelos en el dropdown de WO con carga si es necesario
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
            
            const items = dropdownList.querySelectorAll('.bom-dropdown-item');
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
                dropdownList.style.display = 'none';
            }
        }

        // Función para mostrar dropdown de WO con carga directa desde MySQL
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
            
            // Hacer consulta directa a MySQL para obtener modelos frescos
            try {
                console.log('Cargando modelos directamente desde MySQL...');
                const response = await fetch('/api/bom/modelos', {
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
                    dropdownList.innerHTML = '<div class="bom-dropdown-item" style="color: #f39c12;">No hay modelos disponibles</div>';
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
                dropdownList.innerHTML = '<div class="bom-dropdown-item" style="color: #e74c3c;">Error cargando modelos</div>';
                dropdownList.style.display = 'block';
            }
            
            console.log('=== fin mostrarDropdownWO() ===');
        }

        // Función auxiliar para llenar dropdown directamente
        function llenarDropdownModelosDirecto(dropdownList) {
            dropdownList.innerHTML = '';
            
            modelosBOM.forEach(modelo => {
                const item = document.createElement('div');
                item.className = 'bom-dropdown-item';
                item.setAttribute('data-value', modelo);
                item.textContent = modelo;
                item.onclick = function() { seleccionarModeloWO(modelo); };
                dropdownList.appendChild(item);
            });
            
            console.log(`Dropdown llenado con ${modelosBOM.length} modelos`);
        }

        // Función para seleccionar un modelo del dropdown de WO
        function seleccionarModeloWO(modelo) {
            const searchInput = document.getElementById('woModelo');
            const dropdownList = document.getElementById('woDropdownList');
            
            searchInput.value = modelo;
            dropdownList.style.display = 'none';
            
            console.log('Modelo seleccionado para WO:', modelo);
        }

        // Event listener para cerrar dropdown cuando se hace clic fuera
        document.addEventListener('click', function(event) {
            const woSearchContainer = document.querySelector('.bom-search-container');
            const woDropdownList = document.getElementById('woDropdownList');
            
            if (woSearchContainer && woDropdownList && !woSearchContainer.contains(event.target)) {
                woDropdownList.style.display = 'none';
            }
        });

        // Función de prueba para verificar modelos
        function testModelos() {
            console.log('=== TEST MODELOS ===');
            console.log('modelosBOM array:', modelosBOM);
            console.log('modelosBOM length:', modelosBOM.length);
            
            const dropdownList = document.getElementById('woDropdownList');
            console.log('Dropdown element:', dropdownList);
            console.log('Dropdown innerHTML length:', dropdownList ? dropdownList.innerHTML.length : 'null');
            
            if (modelosBOM.length === 0) {
                console.log('Recargando modelos...');
                cargarModelosBOM();
            } else {
                console.log('Forzando mostrar dropdown...');
                mostrarDropdownWO();
            }
            
            alert(`Modelos cargados: ${modelosBOM.length}. Ver consola para más detalles.`);
        }

        // Cargar WOs existentes
        async function cargarWOs() {
            try {
                mostrarCargando(true);
                const response = await fetch('/api/wo/listar');
                const result = await response.json();
                
                if (result.success) {
                    woData = result.data;
                    renderizarTablaWOs(woData);
                    actualizarContador(woData.length);
                } else {
                    console.error('Error cargando WOs:', result.error);
                    mostrarMensaje('Error cargando WOs: ' + result.error, 'error');
                    mostrarSinDatos();
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error de conexión al cargar WOs', 'error');
                mostrarSinDatos();
            } finally {
                mostrarCargando(false);
            }
        }

        // Consultar WOs por fechas
        async function consultarWOs() {
            const fechaDesde = document.getElementById('fechaDesde').value;
            const fechaHasta = document.getElementById('fechaHasta').value;

            try {
                mostrarCargando(true);
                const params = new URLSearchParams();
                if (fechaDesde) params.append('fecha_desde', fechaDesde);
                if (fechaHasta) params.append('fecha_hasta', fechaHasta);

                const response = await fetch(`/api/wo/listar?${params.toString()}`);
                const result = await response.json();
                
                if (result.success) {
                    woData = result.data;
                    renderizarTablaWOs(woData);
                    actualizarContador(woData.length);
                } else {
                    console.error('Error consultando WOs:', result.error);
                    mostrarMensaje('Error consultando WOs: ' + result.error, 'error');
                    mostrarSinDatos();
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error de conexión al consultar WOs', 'error');
                mostrarSinDatos();
            } finally {
                mostrarCargando(false);
            }
        }

        // Función para consultar POs (función auxiliar para compatibilidad)
        async function consultarPOs() {
            try {
                mostrarCargando(true);
                
                const response = await fetch('/api/po/listar');
                const result = await response.json();
                
                if (result.success) {
                    console.log('POs disponibles:', result.data);
                    mostrarMensaje(`${result.data.length} POs encontradas`, 'success');
                    // Esta función es para compatibilidad, redirecciona a WOs
                    consultarWOs();
                } else {
                    console.error('Error cargando POs:', result.error);
                    mostrarMensaje('Error cargando POs: ' + result.error, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error de conexión al consultar POs', 'error');
            } finally {
                mostrarCargando(false);
            }
        }

        // Renderizar tabla de WOs
        function renderizarTablaWOs(wos) {
            const tbody = document.querySelector('#bomTable tbody');
            
            if (!wos || wos.length === 0) {
                mostrarSinDatos();
                return;
            }

            tbody.innerHTML = '';
            
            wos.forEach((wo, index) => {
                const row = document.createElement('tr');
                row.id = `row${index + 1}`;
                
                row.innerHTML = `
                    <td>${index === 0 ? '▶' : ''}</td>
                    <td><input type="checkbox" id="check${index + 1}"></td>
                    <td>${wo.codigo_wo || ''}</td>
                    <td>${formatearFecha(wo.fecha_operacion) || ''}</td>
                    <td>${wo.codigo_modelo || ''}</td>
                    <td>${wo.nombre_modelo || wo.modelo || ''}</td>
                    <td>${wo.cantidad_planeada || 0}</td>
                    <td class="po-cell">
                        <span class="po-display">${wo.codigo_po || 'SIN-PO'}</span>
                        <input type="text" class="po-edit" value="${wo.codigo_po || ''}" style="display: none;">
                    </td>
                    <td class="acciones-cell">
                        <button class="btn-edit-po" onclick="editarPO('${wo.codigo_wo}', this)" title="Editar PO">EDIT</button>
                        <button class="btn-save-po" onclick="guardarPO('${wo.codigo_wo}', this)" style="display: none;" title="Guardar PO">SAVE</button>
                        <button class="btn-cancel-po" onclick="cancelarEditarPO(this)" style="display: none;" title="Cancelar">CANCEL</button>
                    </td>
                    <td>${wo.modificador || ''}</td>
                    <td>${formatearFechaCompleta(wo.fecha_modificacion) || ''}</td>
                    <td>${index === 0 ? '▲' : ''}</td>
                `;
                
                tbody.appendChild(row);
            });
        }

        // Mostrar sin datos
        function mostrarSinDatos() {
            const tbody = document.querySelector('#bomTable tbody');
            tbody.innerHTML = `
                <tr>
                    <td colspan="13" class="no-data">No se encontraron Work Orders</td>
                </tr>
            `;
        }

        // Mostrar estado de carga
        function mostrarCargando(mostrar) {
            const tbody = document.querySelector('#bomTable tbody');
            if (!tbody) {
                console.warn('Elemento #bomTable tbody no encontrado');
                return;
            }
            
            if (mostrar) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="13" class="bom-loading">Cargando Work Orders...</td>
                    </tr>
                `;
            }
        }

        // Formatear fecha (YYYY-MM-DD)
        function formatearFecha(fechaStr) {
            if (!fechaStr) return '';
            const fecha = new Date(fechaStr);
            return fecha.toISOString().split('T')[0];
        }

        // Formatear fecha completa (YYYY-MM-DD HH:mm:ss)
        function formatearFechaCompleta(fechaStr) {
            if (!fechaStr) return '';
            const fecha = new Date(fechaStr);
            return fecha.toISOString().replace('T', ' ').substring(0, 19);
        }

        // Actualizar contador de resultados
        function actualizarContador(cantidad) {
            const contador = document.getElementById('bomResultCounter');
            contador.textContent = `Total Rows : ${cantidad}`;
        }

        // Toggle de todos los checkboxes
        function toggleAllCheckboxes(event) {
            const isChecked = event.target.checked;
            const checkboxes = document.querySelectorAll('#bomTable tbody input[type="checkbox"]');
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        }

        // Exportar a Excel
        async function exportarExcel() {
            if (!woData || woData.length === 0) {
                mostrarMensaje('No hay datos para exportar', 'error');
                return;
            }

            try {
                const fechaDesde = document.getElementById('fechaDesde').value;
                const fechaHasta = document.getElementById('fechaHasta').value;
                
                const params = new URLSearchParams();
                params.append('formato', 'excel');
                if (fechaDesde) params.append('fecha_desde', fechaDesde);
                if (fechaHasta) params.append('fecha_hasta', fechaHasta);

                const response = await fetch(`/api/wo/exportar?${params.toString()}`);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `work_orders_${new Date().toISOString().split('T')[0]}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    mostrarMensaje('Excel exportado exitosamente', 'success');
                } else {
                    mostrarMensaje('Error al exportar Excel', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                mostrarMensaje('Error de conexión al exportar Excel', 'error');
            }
        }

// Hacer todas las funciones disponibles globalmente
window.initCrearPlanProduccion = initCrearPlanProduccion;
window.consultarWOs = consultarWOs;
window.cancelarOperacion = cancelarOperacion;
window.exportarExcel = exportarExcel;
window.ocultarFormularioWO = ocultarFormularioWO;
window.filtrarModelosWO = filtrarModelosWO;
window.mostrarDropdownWO = mostrarDropdownWO;
window.crearNuevaWO = crearNuevaWO;
        // ================================================
        // FUNCIONES PARA EDICIÓN DE PO
        // ================================================
        
        // Función para iniciar edición de PO
        function editarPO(codigoWO, button) {
            const row = button.closest('tr');
            const poCell = row.querySelector('.po-cell');
            const display = poCell.querySelector('.po-display');
            const input = poCell.querySelector('.po-edit');
            const btnEdit = row.querySelector('.btn-edit-po');
            const btnSave = row.querySelector('.btn-save-po');
            const btnCancel = row.querySelector('.btn-cancel-po');
            
            // Mostrar input y ocultar display
            display.style.display = 'none';
            input.style.display = 'inline-block';
            input.focus();
            
            // Cambiar botones
            btnEdit.style.display = 'none';
            btnSave.style.display = 'inline-block';
            btnCancel.style.display = 'inline-block';
        }
        
        // Función para guardar PO editado
        async function guardarPO(codigoWO, button) {
            const row = button.closest('tr');
            const poCell = row.querySelector('.po-cell');
            const display = poCell.querySelector('.po-display');
            const input = poCell.querySelector('.po-edit');
            const nuevoPO = input.value.trim() || 'SIN-PO';
            
            try {
                // Enviar actualización al servidor
                const response = await fetch('/api/wo/actualizar-po', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        codigo_wo: codigoWO,
                        codigo_po: nuevoPO
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Actualizar display
                    display.textContent = nuevoPO;
                    display.style.display = 'inline-block';
                    input.style.display = 'none';
                    
                    // Restaurar botones
                    const btnEdit = row.querySelector('.btn-edit-po');
                    const btnSave = row.querySelector('.btn-save-po');
                    const btnCancel = row.querySelector('.btn-cancel-po');
                    
                    btnEdit.style.display = 'inline-block';
                    btnSave.style.display = 'none';
                    btnCancel.style.display = 'none';
                    
                    mostrarMensaje(`PO actualizado exitosamente: ${nuevoPO}`, 'success');
                } else {
                    mostrarMensaje('Error actualizando PO: ' + result.error, 'error');
                }
            } catch (error) {
                console.error('Error guardando PO:', error);
                mostrarMensaje('Error guardando PO: ' + error.message, 'error');
            }
        }
        
        // Función para cancelar edición de PO
        function cancelarEditarPO(button) {
            const row = button.closest('tr');
            const poCell = row.querySelector('.po-cell');
            const display = poCell.querySelector('.po-display');
            const input = poCell.querySelector('.po-edit');
            
            // Restaurar valor original
            input.value = display.textContent === 'SIN-PO' ? '' : display.textContent;
            
            // Mostrar display y ocultar input
            display.style.display = 'inline-block';
            input.style.display = 'none';
            
            // Restaurar botones
            const btnEdit = row.querySelector('.btn-edit-po');
            const btnSave = row.querySelector('.btn-save-po');
            const btnCancel = row.querySelector('.btn-cancel-po');
            
            btnEdit.style.display = 'inline-block';
            btnSave.style.display = 'none';
            btnCancel.style.display = 'none';
        }

window.mostrarFormularioWO = mostrarFormularioWO;
window.seleccionarModeloWO = seleccionarModeloWO;
window.editarPO = editarPO;
window.guardarPO = guardarPO;
window.cancelarEditarPO = cancelarEditarPO;

console.log('Crear Plan de Producción - Módulo inicializado');

})(); // Fin del IIFE - Cierre del módulo encapsulado