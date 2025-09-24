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
            
            const woFormContainer = document.getElementById('woFormContainer');
            const btnCrearWO = document.getElementById('btnCrearWO');
            
            if (woFormContainer) {
                woFormContainer.style.display = 'block';
            } else {
                console.error('❌ Elemento woFormContainer no encontrado');
            }
            
            if (btnCrearWO) {
                btnCrearWO.style.display = 'none';
            } else {
                console.warn('⚠️ Elemento btnCrearWO no encontrado (puede ser normal)');
            }
            
            // Generar código WO con un pequeño delay para asegurar que el DOM esté listo
            setTimeout(() => {
                generarCodigoWO();
            }, 100);
            
            // Siempre cargar modelos para asegurar que estén disponibles
            console.log('Cargando modelos BOM...');
            // await cargarModelosBOM(); // Función no utilizada - comentada para evitar error 404
            
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
        async function generarCodigoWO() {
            console.log('🔧 Generando código WO...');
            const elemento = document.getElementById('woCodigoWO');
            
            if (!elemento) {
                console.error('❌ Elemento woCodigoWO no encontrado');
                return;
            }
            
            try {
                // Obtener código secuencial real del servidor
                const response = await fetch('/api/generar_codigo_wo');
                const data = await response.json();
                
                if (data.ok && data.codigo_wo) {
                    elemento.value = data.codigo_wo;
                    console.log('✅ Código WO generado desde servidor:', data.codigo_wo);
                } else {
                    throw new Error('Error en respuesta del servidor');
                }
            } catch (error) {
                console.error('❌ Error al generar código WO:', error);
                alert('Error al generar código WO. Por favor, intente nuevamente.');
            }
        }

        // Asignaciones globales inmediatas para onclick handlers
        window.mostrarFormularioWO = mostrarFormularioWO;

        // Función de inicialización explícita para carga dinámica
        function initCrearPlanProduccion() {
            console.log('🚀 Inicializando Crear Plan de Producción...');
            // cargarModelosBOM(); // Función no utilizada - comentada para evitar error 404
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
        // Función cargarModelosBOM comentada - no se utiliza y causaba error 404
        /*
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
        */

        // Cargar modelos (part_no) desde tabla RAW
        async function cargarModelosRAW() {
            try {
                const response = await fetch('/api/raw/modelos', {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
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
                llenarDropdownModelos();
            } catch (error) {
                console.error('Error cargando modelos RAW:', error);
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
            const woFormContainer = document.getElementById('woFormContainer');
            const btnCrearWO = document.getElementById('btnCrearWO');
            
            if (woFormContainer) {
                woFormContainer.style.display = 'none';
            } else {
                console.warn('⚠️ Elemento woFormContainer no encontrado en ocultarFormularioWO');
            }
            
            if (btnCrearWO) {
                btnCrearWO.style.display = 'inline-block';
            } else {
                console.warn('⚠️ Elemento btnCrearWO no encontrado en ocultarFormularioWO');
            }
            
            limpiarFormularioWO();
        }

        // Limpiar formulario
        function limpiarFormularioWO() {
            const elementos = [
                'woCodigoWO', 'woCodigoPO', 'woModelo', 'woOrdenProceso', 'woCantidad'
            ];
            
            elementos.forEach(id => {
                const elemento = document.getElementById(id);
                if (elemento) {
                    elemento.value = '';
                } else {
                    console.warn(`⚠️ Elemento ${id} no encontrado en limpiarFormularioWO`);
                }
            });
            
            // Ocultar dropdown de modelos
            const dropdownList = document.getElementById('woDropdownList');
            if (dropdownList) {
                dropdownList.style.display = 'none';
            }
            
            establecerFechaActual();
        }

        // Función para el botón Cancelar de la barra de herramientas
        function cancelarOperacion() {
            const woFormContainer = document.getElementById('woFormContainer');
            
            if (woFormContainer) {
                const formularioVisible = woFormContainer.style.display !== 'none';
                
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
            } else {
                console.warn('⚠️ Elemento woFormContainer no encontrado en cancelarOperacion');
                // Fallback: limpiar filtros y recargar datos
                establecerFechaActual();
                cargarWOs();
                mostrarMensaje('Filtros restablecidos', 'success');
            }
        }

        // Crear nueva WO
        async function crearNuevaWO() {
            console.log('🚀 Iniciando creación de nueva WO...');
            
            const elementoCodigoWO = document.getElementById('woCodigoWO');
            console.log('Elemento woCodigoWO:', elementoCodigoWO);
            
            if (!elementoCodigoWO) {
                console.error('❌ Elemento woCodigoWO no encontrado en crearNuevaWO');
                mostrarMensaje('Error: Elemento de código WO no encontrado', 'error');
                return;
            }
            
            const codigoWO = elementoCodigoWO.value.trim();
            console.log('Código WO obtenido:', codigoWO);
            
            // codigoPO ahora es opcional para WO independientes
            const codigoPO = document.getElementById('woCodigoPO').value.trim() || 'SIN-PO';
            const modelo = document.getElementById('woModelo').value;
            const cantidad = parseInt(document.getElementById('woCantidad').value);
            const fechaOperacion = document.getElementById('woFechaOperacion').value;

            // Validaciones
            if (!codigoWO) {
                console.error('❌ Código WO está vacío');
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
                fecha_operacion: fechaOperacion,
                usuario_creador: window.usuarioLogueado || 'Usuario no identificado'
            };

            try {
                // Deshabilitar botón durante la creación
                const btnGuardar = document.getElementById('btnGuardarWO');
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Registrando...';

                const response = await fetch('/api/work_orders', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.ok) {
                    mostrarMensaje(`WO creada exitosamente: ${data.codigo_wo}`, 'success');
                    ocultarFormularioWO();
                    // Recargar la tabla dinámicamente
                    await cargarWOs();
                } else {
                    mostrarMensaje('Error creando WO: ' + (result.message || 'Error desconocido'), 'error');
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

        // Función para filtrar modelos en el dropdown de WO
        function filtrarModelosWO() {
            const searchInput = document.getElementById('woModelo');
            const dropdownList = document.getElementById('woDropdownList');
            const searchTerm = searchInput.value.toLowerCase();
            
            // Si no hay modelos cargados, no hacer nada (evitar bucle infinito)
            if (modelosBOM.length === 0) {
                console.log('No hay modelos en memoria para filtrar');
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
            
            // Si no hay coincidencias, mantener abierto con mensaje
            const NORES_ID = 'wo-no-results';
            const old = dropdownList.querySelector('#' + NORES_ID);
            if (old) old.remove();
            if (!hasVisibleItems && searchTerm.length > 0) {
                const msg = document.createElement('div');
                msg.id = NORES_ID;
                msg.className = 'bom-dropdown-item';
                msg.textContent = 'Sin coincidencias';
                msg.style.cssText = 'color:#f39c12; cursor: default;';
                dropdownList.appendChild(msg);
                dropdownList.style.display = 'block';
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
            
            // Solo cargar modelos si no están en memoria
            if (!modelosBOM || modelosBOM.length === 0) {
                try {
                    console.log('Cargando modelos desde RAW...');
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
                    const lista = Array.isArray(data) ? data : (data && Array.isArray(data.data) ? data.data : []);
                    
                    if (lista.length > 0) {
                        // Actualizar array local
                        modelosBOM = lista.map(item => item.modelo || item).filter(modelo => modelo && modelo.trim() !== '');
                        console.log('Modelos cargados exitosamente:', modelosBOM.length);
                        
                        // Llenar dropdown
                        llenarDropdownModelosDirecto(dropdownList);
                        
                    } else {
                        console.warn('No se encontraron modelos');
                        dropdownList.innerHTML = '<div class="bom-dropdown-item" style="color: #f39c12;">No hay modelos disponibles</div>';
                    }
                } catch (error) {
                    console.error('Error cargando modelos:', error);
                    
                    // Mostrar error en dropdown
                    dropdownList.innerHTML = '<div class="bom-dropdown-item" style="color: #e74c3c;">Error cargando modelos</div>';
                }
            }
            
            // Mostrar dropdown
            dropdownList.style.display = 'block';
            dropdownList.style.zIndex = '10000';
            dropdownList.style.position = 'absolute';
            
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
                // cargarModelosBOM(); // Función no utilizada - comentada para evitar error 404
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
                // Cargar todas las WO sin filtro de estado
                const response = await fetch('/api/wo/listar?incluir_planificadas=true');
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
            const fechaDesdeEl = document.getElementById('fechaDesde');
            const fechaHastaEl = document.getElementById('fechaHasta');
            
            const fechaDesde = fechaDesdeEl ? fechaDesdeEl.value : '';
            const fechaHasta = fechaHastaEl ? fechaHastaEl.value : '';

            try {
                mostrarCargando(true);
                const params = new URLSearchParams();
                if (fechaDesde) params.append('fecha_desde', fechaDesde);
                if (fechaHasta) params.append('fecha_hasta', fechaHasta);
                // Incluir todas las WO sin filtro de estado
                params.append('incluir_planificadas', 'true');

                const response = await fetch(`/api/wo/listar?${params.toString()}`);
                
                // Verificar si la respuesta es válida
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // Verificar que el contenido sea JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const text = await response.text();
                    console.error('Respuesta no es JSON:', text.substring(0, 200));
                    throw new Error('El servidor no devolvió una respuesta JSON válida');
                }
                
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
                console.error('Error al consultar WOs:', error);
                mostrarMensaje('Error de conexión al consultar WOs: ' + error.message, 'error');
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
                
                // Verificar si la respuesta es válida
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // Verificar que el contenido sea JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const text = await response.text();
                    console.error('Respuesta no es JSON:', text.substring(0, 200));
                    throw new Error('El servidor no devolvió una respuesta JSON válida');
                }
                
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
                console.error('Error al consultar POs:', error);
                mostrarMensaje('Error de conexión al consultar POs: ' + error.message, 'error');
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
                    <td><span class="estado-badge estado-${(wo.estado || 'CREADA').toLowerCase()}">${wo.estado || 'CREADA'}</span></td>
                    <td>${formatearFecha(wo.fecha_operacion) || ''}</td>
                    <td>${wo.linea || ''}</td>
                    <td class="modelo-cell">
                        <span class="modelo-display">${wo.codigo_modelo || wo.modelo || ''}</span>
                        <input type="text" class="modelo-edit" value="${wo.codigo_modelo || wo.modelo || ''}" style="display: none;">
                    </td>
                    <td>${wo.nombre_modelo || ''}</td>
                    <td class="cantidad-cell">
                        <span class="cantidad-display">${wo.cantidad_planeada || 0}</span>
                        <input type="number" class="cantidad-edit" value="${wo.cantidad_planeada || 0}" min="1" style="display: none;">
                    </td>
                    <td class="po-cell">
                        <span class="po-display">${wo.codigo_po || 'SIN-PO'}</span>
                        <input type="text" class="po-edit" value="${wo.codigo_po || ''}" style="display: none;">
                    </td>
                    <td class="acciones-cell">
                        <button class="btn-edit-wo ${(wo.estado || 'CREADA') !== 'CREADA' ? 'disabled' : ''}" onclick="editarWO('${wo.codigo_wo}', this)" title="${(wo.estado || 'CREADA') !== 'CREADA' ? 'Solo se pueden editar WOs con estado CREADA' : 'Editar WO'}">EDIT</button>
                        <button class="btn-save-wo" onclick="guardarWO('${wo.codigo_wo}', this)" style="display: none;" title="Guardar WO">SAVE</button>
                        <button class="btn-cancel-wo" onclick="cancelarEditarWO(this)" style="display: none;" title="Cancelar">CANCEL</button>
                        <button class="btn-delete-wo ${(wo.estado || 'CREADA') !== 'CREADA' ? 'disabled' : ''}" onclick="eliminarWO('${wo.codigo_wo}', this)" title="${(wo.estado || 'CREADA') !== 'CREADA' ? 'Solo se pueden eliminar WOs con estado CREADA' : 'Eliminar WO'}" style="margin-left: 5px;">DEL</button>
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
                    <td colspan="15" class="no-data">No se encontraron Work Orders</td>
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
                        <td colspan="15" class="bom-loading">Cargando Work Orders...</td>
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
        // FUNCIONES PARA EDICIÓN DE WO
        // ================================================
        
        // Función para iniciar edición de WO
        function editarWO(codigoWO, button) {
            const row = button.closest('tr');
            
            // Verificar el estado de la WO
            const estadoBadge = row.querySelector('.estado-badge');
            const estado = estadoBadge ? estadoBadge.textContent.trim() : '';
            
            // Solo permitir edición si el estado es 'CREADA'
            if (estado !== 'CREADA') {
                alert('Solo se pueden editar órdenes de trabajo con estado CREADA');
                return;
            }
            
            // Elementos de modelo
            const modeloCell = row.querySelector('.modelo-cell');
            const modeloDisplay = modeloCell.querySelector('.modelo-display');
            const modeloInput = modeloCell.querySelector('.modelo-edit');
            
            // Elementos de cantidad
            const cantidadCell = row.querySelector('.cantidad-cell');
            const cantidadDisplay = cantidadCell.querySelector('.cantidad-display');
            const cantidadInput = cantidadCell.querySelector('.cantidad-edit');
            
            // Elementos de PO
            const poCell = row.querySelector('.po-cell');
            const poDisplay = poCell.querySelector('.po-display');
            const poInput = poCell.querySelector('.po-edit');
            
            // Botones
            const btnEdit = row.querySelector('.btn-edit-wo');
            const btnSave = row.querySelector('.btn-save-wo');
            const btnCancel = row.querySelector('.btn-cancel-wo');
            const btnDelete = row.querySelector('.btn-delete-wo');
            
            // Mostrar inputs y ocultar displays
            modeloDisplay.style.display = 'none';
            modeloInput.style.display = 'inline-block';
            cantidadDisplay.style.display = 'none';
            cantidadInput.style.display = 'inline-block';
            poDisplay.style.display = 'none';
            poInput.style.display = 'inline-block';
            
            // Enfocar primer campo
            modeloInput.focus();
            
            // Cambiar botones
            btnEdit.style.display = 'none';
            btnSave.style.display = 'inline-block';
            btnCancel.style.display = 'inline-block';
            btnDelete.style.display = 'none';
        }
        
        // Función para guardar WO editado
        async function guardarWO(codigoWO, button) {
            const row = button.closest('tr');
            
            // Obtener valores de los campos
            const modeloInput = row.querySelector('.modelo-edit');
            const cantidadInput = row.querySelector('.cantidad-edit');
            const poInput = row.querySelector('.po-edit');
            
            const nuevoModelo = modeloInput.value.trim();
            const nuevaCantidad = parseInt(cantidadInput.value) || 1;
            const nuevoPO = poInput.value.trim() || 'SIN-PO';
            
            // Validaciones
            if (!nuevoModelo) {
                mostrarMensaje('El modelo es requerido', 'error');
                modeloInput.focus();
                return;
            }
            
            if (nuevaCantidad < 1) {
                mostrarMensaje('La cantidad debe ser mayor a 0', 'error');
                cantidadInput.focus();
                return;
            }
            
            try {
                // Enviar actualización al servidor
                const response = await fetch('/api/wo/actualizar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        codigo_wo: codigoWO,
                        modelo: nuevoModelo,
                        cantidad_planeada: nuevaCantidad,
                        codigo_po: nuevoPO
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Actualizar displays
                    const modeloDisplay = row.querySelector('.modelo-display');
                    const cantidadDisplay = row.querySelector('.cantidad-display');
                    const poDisplay = row.querySelector('.po-display');
                    
                    modeloDisplay.textContent = nuevoModelo;
                    cantidadDisplay.textContent = nuevaCantidad;
                    poDisplay.textContent = nuevoPO;
                    
                    // Ocultar inputs y mostrar displays
                    modeloDisplay.style.display = 'inline-block';
                    modeloInput.style.display = 'none';
                    cantidadDisplay.style.display = 'inline-block';
                    cantidadInput.style.display = 'none';
                    poDisplay.style.display = 'inline-block';
                    poInput.style.display = 'none';
                    
                    // Restaurar botones
                    const btnEdit = row.querySelector('.btn-edit-wo');
                    const btnSave = row.querySelector('.btn-save-wo');
                    const btnCancel = row.querySelector('.btn-cancel-wo');
                    const btnDelete = row.querySelector('.btn-delete-wo');
                    
                    btnEdit.style.display = 'inline-block';
                    btnSave.style.display = 'none';
                    btnCancel.style.display = 'none';
                    btnDelete.style.display = 'inline-block';
                    
                    mostrarMensaje('WO actualizada exitosamente', 'success');
                } else {
                    mostrarMensaje('Error guardando WO: ' + result.error, 'error');
                }
                
            } catch (error) {
                console.error('Error guardando WO:', error);
                mostrarMensaje('Error guardando WO: ' + error.message, 'error');
            }
        }
        
        // Función para cancelar edición de WO
        function cancelarEditarWO(button) {
            const row = button.closest('tr');
            
            // Elementos de modelo
            const modeloCell = row.querySelector('.modelo-cell');
            const modeloDisplay = modeloCell.querySelector('.modelo-display');
            const modeloInput = modeloCell.querySelector('.modelo-edit');
            
            // Elementos de cantidad
            const cantidadCell = row.querySelector('.cantidad-cell');
            const cantidadDisplay = cantidadCell.querySelector('.cantidad-display');
            const cantidadInput = cantidadCell.querySelector('.cantidad-edit');
            
            // Elementos de PO
            const poCell = row.querySelector('.po-cell');
            const poDisplay = poCell.querySelector('.po-display');
            const poInput = poCell.querySelector('.po-edit');
            
            // Restaurar valores originales
            modeloInput.value = modeloDisplay.textContent;
            cantidadInput.value = cantidadDisplay.textContent;
            poInput.value = poDisplay.textContent === 'SIN-PO' ? '' : poDisplay.textContent;
            
            // Mostrar displays y ocultar inputs
            modeloDisplay.style.display = 'inline-block';
            modeloInput.style.display = 'none';
            cantidadDisplay.style.display = 'inline-block';
            cantidadInput.style.display = 'none';
            poDisplay.style.display = 'inline-block';
            poInput.style.display = 'none';
            
            // Restaurar botones
            const btnEdit = row.querySelector('.btn-edit-wo');
            const btnSave = row.querySelector('.btn-save-wo');
            const btnCancel = row.querySelector('.btn-cancel-wo');
            const btnDelete = row.querySelector('.btn-delete-wo');
            
            btnEdit.style.display = 'inline-block';
            btnSave.style.display = 'none';
            btnCancel.style.display = 'none';
            btnDelete.style.display = 'inline-block';
        }
        
        // Función para eliminar WO
        async function eliminarWO(codigoWO, button) {
            const row = button.closest('tr');
            
            // Verificar el estado de la WO
            const estadoBadge = row.querySelector('.estado-badge');
            const estado = estadoBadge ? estadoBadge.textContent.trim() : '';
            
            // Solo permitir eliminación si el estado es 'CREADA'
            if (estado !== 'CREADA') {
                alert('Solo se pueden eliminar órdenes de trabajo con estado CREADA');
                return;
            }
            
            if (!confirm(`¿Está seguro de eliminar la WO ${codigoWO}?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/wo/eliminar', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        codigo_wo: codigoWO
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Remover fila de la tabla
                    const row = button.closest('tr');
                    row.remove();
                    
                    // Actualizar contador
                    const tbody = document.querySelector('#bomTable tbody');
                    const filas = tbody.querySelectorAll('tr').length;
                    actualizarContador(filas);
                    
                    mostrarMensaje(`WO ${codigoWO} eliminada exitosamente`, 'success');
                } else {
                    mostrarMensaje('Error eliminando WO: ' + result.error, 'error');
                }
                
            } catch (error) {
                console.error('Error eliminando WO:', error);
                mostrarMensaje('Error eliminando WO: ' + error.message, 'error');
            }
        }

    // ================================================
    // FUNCIONES DE IMPORTACIÓN DE EXCEL
    // ================================================
    
    function importarExcel() {
        console.log('Iniciando importación de Excel...');
        const fileInput = document.getElementById('fileInputExcel');
        if (fileInput) {
            fileInput.click();
        } else {
            console.error('❌ Input de archivo no encontrado');
            alert('Error: No se pudo encontrar el selector de archivo');
        }
    }
    
    // Variable global para almacenar el archivo seleccionado
    let archivoExcelSeleccionado = null;

    function mostrarModalFechaImportacion(input) {
        if (!input.files || input.files.length === 0) {
            console.log('No se seleccionó ningún archivo');
            return;
        }
        
        const archivo = input.files[0];
        console.log('Archivo seleccionado:', archivo.name);
        
        // Validar tipo de archivo
        const extensionesPermitidas = ['.xlsx', '.xls'];
        const extension = archivo.name.toLowerCase().substring(archivo.name.lastIndexOf('.'));
        
        if (!extensionesPermitidas.includes(extension)) {
            alert('Error: Solo se permiten archivos Excel (.xlsx, .xls)');
            input.value = '';
            return;
        }
        
        // Validar tamaño del archivo (máximo 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (archivo.size > maxSize) {
            alert('Error: El archivo es demasiado grande. Máximo 10MB permitido.');
            input.value = '';
            return;
        }
        
        // Almacenar el archivo globalmente
        archivoExcelSeleccionado = archivo;
        
        // Mostrar el modal
        const modal = document.getElementById('modalFechaImportacion');
        const nombreArchivo = document.getElementById('nombreArchivoImportacion');
        const fechaInput = document.getElementById('fechaImportacionSeleccionada');
        
        // Configurar valores por defecto
        nombreArchivo.textContent = archivo.name;
        
        // Establecer fecha por defecto (mañana)
        const mañana = new Date();
        mañana.setDate(mañana.getDate() + 1);
        fechaInput.value = mañana.toISOString().split('T')[0];
        
        modal.style.display = 'block';
    }

    function cancelarImportacion() {
        const modal = document.getElementById('modalFechaImportacion');
        const fileInput = document.getElementById('fileInputExcel');
        
        modal.style.display = 'none';
        fileInput.value = '';
        archivoExcelSeleccionado = null;
    }

    function confirmarImportacionConFecha() {
        const fechaSeleccionada = document.getElementById('fechaImportacionSeleccionada').value;
        
        if (!fechaSeleccionada) {
            alert('Por favor selecciona una fecha de operación');
            return;
        }
        
        if (!archivoExcelSeleccionado) {
            alert('Error: No hay archivo seleccionado');
            return;
        }
        
        // Ocultar modal
        const modal = document.getElementById('modalFechaImportacion');
        modal.style.display = 'none';
        
        // Procesar archivo con la fecha seleccionada
        procesarArchivoExcelConFecha(archivoExcelSeleccionado, fechaSeleccionada);
    }

    function procesarArchivoExcelConFecha(archivo, fechaOperacion) {
        console.log('Procesando archivo:', archivo.name, 'con fecha:', fechaOperacion);
        
        // Mostrar indicador de carga
        const btnImportar = document.getElementById('btnImportar');
        const textoOriginal = btnImportar ? btnImportar.textContent : '';
        if (btnImportar) {
            btnImportar.textContent = 'Importando...';
            btnImportar.disabled = true;
        }
        
        // Crear FormData para enviar el archivo y la fecha
        const formData = new FormData();
        formData.append('file', archivo);
        formData.append('fecha_operacion', fechaOperacion);
        
        // Enviar archivo al servidor
        fetch('/importar_excel_plan_produccion', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('Respuesta del servidor:', data);
            
            if (data.success) {
                mostrarMensaje(`Excel importado exitosamente. Se procesaron ${data.registros_procesados || 0} registros para la fecha ${fechaOperacion}.`, 'success');
                
                // Actualizar la tabla después de la importación
                consultarWOs();
                
                // Mostrar detalles adicionales si están disponibles
                if (data.detalles) {
                    console.log('Detalles de importación:', data.detalles);
                }
            } else {
                console.error('Error en importación:', data.error);
                mostrarMensaje(`Error al importar Excel: ${data.error || 'Error desconocido'}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error en la petición:', error);
            mostrarMensaje('Error de conexión al importar el archivo. Intente nuevamente.', 'error');
        })
        .finally(() => {
            // Restaurar botón
            if (btnImportar) {
                btnImportar.textContent = textoOriginal || 'Importar Excel';
                btnImportar.disabled = false;
            }
            
            // Limpiar variables
            const fileInput = document.getElementById('fileInputExcel');
            fileInput.value = '';
            archivoExcelSeleccionado = null;
        });
    }

    function procesarArchivoExcel(input) {
        // Esta función ahora redirige al modal
        mostrarModalFechaImportacion(input);
    }

window.mostrarFormularioWO = mostrarFormularioWO;
window.seleccionarModeloWO = seleccionarModeloWO;
window.editarWO = editarWO;
window.guardarWO = guardarWO;
window.cancelarEditarWO = cancelarEditarWO;
window.eliminarWO = eliminarWO;
window.importarExcel = importarExcel;
window.procesarArchivoExcel = procesarArchivoExcel;
window.mostrarModalFechaImportacion = mostrarModalFechaImportacion;
window.cancelarImportacion = cancelarImportacion;
window.confirmarImportacionConFecha = confirmarImportacionConFecha;

console.log('Crear Plan de Producción - Módulo inicializado');

})(); // Fin del IIFE - Cierre del módulo encapsulado
