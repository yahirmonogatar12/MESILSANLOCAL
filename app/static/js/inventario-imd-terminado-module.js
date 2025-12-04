/**
 * Módulo de Inventario IMD Terminado
 * Encapsula toda la funcionalidad para gestionar el inventario de productos IMD terminados
 * Usa patrón IIFE para evitar conflictos de variables globales
 */
(function() {
    'use strict';
    
    // Variables privadas del módulo
    let datosOriginalesIMD = {
        'g': [], // Inventario general
        'u': [], // Ubicación  
        'm': []  // Movimientos
    };
    
    let filtrosIMD = {
        'g': {},
        'u': {},
        'm': {}
    };

    // Funciones utilitarias privadas
    function fmt(v) { 
        return (v === undefined || v === null || v === "") ? "-" : v; 
    }
    
    function coalesce(a, b) { 
        return (a !== undefined && a !== null) ? a : b; 
    }
    
    function qs(sel) { 
        return document.querySelector(sel); 
    }
    
    function qsa(sel) { 
        return Array.from(document.querySelectorAll(sel)); 
    }
    
    function todayISO() { 
        return new Date().toISOString().split('T')[0]; 
    }

    // Funciones para filtros IMD
    function toggleFiltroIMD(tabla, columna) {
        const filtroDiv = document.getElementById(`filtro-${tabla}-${columna}`);
        const filterBtn = document.querySelector(`button[onclick="toggleFiltroIMD('${tabla}', '${columna}')"]`);
        
        // Cerrar otros filtros
        document.querySelectorAll('.header-filter-imd').forEach(filter => {
            if (filter.id !== `filtro-${tabla}-${columna}`) {
                filter.style.display = 'none';
            }
        });
        
        // Quitar active de otros botones
        document.querySelectorAll('.filter-btn-imd').forEach(btn => {
            if (btn !== filterBtn) {
                btn.classList.remove('active');
            }
        });
        
        // Toggle del filtro actual
        if (filtroDiv.style.display === 'none' || !filtroDiv.style.display) {
            // Si tiene select, poblar opciones
            const select = filtroDiv.querySelector('.filter-select-imd');
            if (select) {
                poblarOpcionesFiltroIMD(tabla, columna);
            }
            
            filtroDiv.style.display = 'block';
            filterBtn.classList.add('active');
            
            // Enfocar el input si existe
            const input = filtroDiv.querySelector('.filter-input-imd');
            if (input) {
                setTimeout(() => input.focus(), 100);
            }
        } else {
            filtroDiv.style.display = 'none';
            filterBtn.classList.remove('active');
        }
    }

    function poblarOpcionesFiltroIMD(tabla, columna) {
        const select = document.querySelector(`#filtro-${tabla}-${columna} .filter-select-imd`);
        if (!select || !datosOriginalesIMD[tabla].length) return;
        
        // Mantener opciones fijas y agregar dinámicas según la columna
        const opcionesFijas = Array.from(select.querySelectorAll('option')).map(opt => opt.value);
        const valoresUnicos = new Set();
        
        // Obtener valores únicos de la columna
        datosOriginalesIMD[tabla].forEach(fila => {
            const valor = fila[columna];
            if (valor && valor !== '' && valor !== null && valor !== undefined) {
                valoresUnicos.add(valor.toString());
            }
        });
        
        // Agregar opciones dinámicas (solo si no existen en las fijas)
        const valoresOrdenados = Array.from(valoresUnicos).sort();
        valoresOrdenados.forEach(valor => {
            if (!opcionesFijas.includes(valor)) {
                const option = document.createElement('option');
                option.value = valor;
                option.textContent = valor;
                select.appendChild(option);
            }
        });
    }

    function aplicarFiltroIMD(tabla, columna, valor) {
        if (valor === '') {
            delete filtrosIMD[tabla][columna];
        } else {
            filtrosIMD[tabla][columna] = valor;
        }
        
        aplicarTodosFiltrosIMD(tabla);
        
        // Cerrar el filtro después de aplicar
        document.getElementById(`filtro-${tabla}-${columna}`).style.display = 'none';
        document.querySelector(`button[onclick="toggleFiltroIMD('${tabla}', '${columna}')"]`).classList.remove('active');
    }

    function aplicarFiltroTextoIMD(tabla, columna, valor) {
        if (valor.trim() === '') {
            delete filtrosIMD[tabla][columna];
        } else {
            filtrosIMD[tabla][columna] = valor.trim();
        }
        
        aplicarTodosFiltrosIMD(tabla);
    }

    function limpiarFiltroIMD(tabla, columna) {
        delete filtrosIMD[tabla][columna];
        
        // Limpiar el input
        const input = document.querySelector(`#filtro-${tabla}-${columna} .filter-input-imd`);
        if (input) input.value = '';
        
        // Limpiar el select si existe
        const select = document.querySelector(`#filtro-${tabla}-${columna} .filter-select-imd`);
        if (select) select.selectedIndex = 0;
        
        aplicarTodosFiltrosIMD(tabla);
        
        // Cerrar el filtro
        document.getElementById(`filtro-${tabla}-${columna}`).style.display = 'none';
        document.querySelector(`button[onclick="toggleFiltroIMD('${tabla}', '${columna}')"]`).classList.remove('active');
    }

    function aplicarTodosFiltrosIMD(tabla) {
        if (!datosOriginalesIMD[tabla].length) return;
        
        let datosFiltrados = [...datosOriginalesIMD[tabla]];
        
        // Aplicar cada filtro
        Object.keys(filtrosIMD[tabla]).forEach(columna => {
            const valorFiltro = filtrosIMD[tabla][columna];
            
            datosFiltrados = datosFiltrados.filter(fila => {
                const valorCelda = fila[columna];
                
                // Filtros especiales para stock
                if (columna === 'stock_total' && valorFiltro.startsWith('>')) {
                    const limite = parseInt(valorFiltro.substring(1));
                    return parseInt(valorCelda || 0) > limite;
                } else if (columna === 'stock_total' && valorFiltro === '=0') {
                    return parseInt(valorCelda || 0) === 0;
                } else {
                    // Filtro de texto - búsqueda que contiene (case-insensitive)
                    const valorTexto = (valorCelda || '').toString().toLowerCase();
                    const filtroTexto = valorFiltro.toLowerCase();
                    return valorTexto.includes(filtroTexto);
                }
            });
        });
        
        // Actualizar tabla con datos filtrados
        actualizarTablaIMD(tabla, datosFiltrados);
    }

    function actualizarTablaIMD(tabla, datos) {
        const tbody = document.querySelector(`#INVIMDPCBID_${tabla}-table tbody`);
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        datos.forEach(fila => {
            const tr = document.createElement('tr');
            
            if (tabla === 'g') {
                // Inventario General
                tr.innerHTML = `
                    <td title="${fmt(fila.modelo)}">${fmt(fila.modelo)}</td>
                    <td title="${fmt(fila.nparte)}">${fmt(fila.nparte)}</td>
                    <td>${fmt(fila.stock_total)}</td>
                    <td title="${fmt(fila.ubicaciones)}">${fmt(fila.ubicaciones)}</td>
                    <td>${fmt(fila.ultima_entrada)}</td>
                    <td>${fmt(fila.ultima_salida)}</td>
                    <td>${fmt(fila.tipo_inventario)}</td>`;
            } else if (tabla === 'u') {
                // Ubicación
                tr.innerHTML = `
                    <td>${fmt(fila.fecha || fila.fecha_registro || '')}</td>
                    <td title="${fmt(fila.modelo)}">${fmt(fila.modelo)}</td>
                    <td title="${fmt(fila.nparte)}">${fmt(fila.nparte)}</td>
                    <td>${fmt(fila.ubicacion)}</td>
                    <td>${fmt(fila.cantidad)}</td>
                    <td>${fmt(fila.tipo_inventario)}</td>
                    <td title="${fmt(fila.comentario)}">${fmt(fila.comentario)}</td>
                    <td>${fmt(fila.carro)}</td>`;
            } else if (tabla === 'm') {
                // Movimientos
                const tipoChip = fila.tipo === 'SALIDA' ? 'ng-imd' : (fila.tipo === 'ENTRADA' ? 'ok-imd' : '');
                tr.innerHTML = `
                    <td>${fmt(fila.fecha_hora || '')}</td>
                    <td><span class="${tipoChip}">${fmt(fila.tipo)}</span></td>
                    <td title="${fmt(fila.nparte)}">${fmt(fila.nparte)}</td>
                    <td title="${fmt(fila.modelo)}">${fmt(fila.modelo)}</td>
                    <td>${fmt(fila.cantidad)}</td>
                    <td>${fmt(fila.ubicacion)}</td>
                    <td>${fmt(fila.tipo_inventario)}</td>
                    <td title="${fmt(fila.comentario)}">${fmt(fila.comentario)}</td>
                    <td>${fmt(fila.carro)}</td>`;
            }
            
            tbody.appendChild(tr);
        });
        
        // Actualizar contador
        const statusElement = document.querySelector(`#INVIMDPCBID_${tabla}-status`);
        if (statusElement) {
            const total = datosOriginalesIMD[tabla].length;
            const filtrados = datos.length;
            statusElement.textContent = total === filtrados ? 
                `${total} registros` : 
                `${filtrados} de ${total} registros`;
        }
    }

    function limpiarTodosFiltrosIMD(tabla) {
        filtrosIMD[tabla] = {};
        
        // Resetear todos los selects de esta tabla
        document.querySelectorAll(`#INVIMDPCBID_${tabla}-table .header-filter-imd select`).forEach(select => {
            select.selectedIndex = 0;
        });
        
        // Resetear todos los inputs de esta tabla
        document.querySelectorAll(`#INVIMDPCBID_${tabla}-table .header-filter-imd input`).forEach(input => {
            input.value = '';
        });
        
        // Cerrar todos los filtros
        document.querySelectorAll(`#INVIMDPCBID_${tabla}-table .header-filter-imd`).forEach(filter => {
            filter.style.display = 'none';
        });
        
        // Quitar active de todos los botones
        document.querySelectorAll(`#INVIMDPCBID_${tabla}-table .filter-btn-imd`).forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Mostrar todos los datos
        actualizarTablaIMD(tabla, datosOriginalesIMD[tabla]);
    }

    function setDefaultDates(ids) {
        ids.forEach(id => { 
            const el = qs('#' + id); 
            if (el && !el.value) el.value = todayISO(); 
        });
    }

    // Función para exportar datos a Excel
    function exportarExcelIMD(datos, nombreArchivo, columnas) {
        if (!datos || datos.length === 0) {
            alert('No hay datos para exportar');
            return;
        }
        
        // Crear contenido CSV
        let csvContent = "";
        
        // Agregar cabeceras
        const headers = columnas.map(col => col.header);
        csvContent += headers.join(",") + "\n";
        
        // Agregar datos
        datos.forEach(row => {
            const values = columnas.map(col => {
                let value = row[col.key] || "";
                // Escapar comillas y comas
                if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                    value = '"' + value.replace(/"/g, '""') + '"';
                }
                return value;
            });
            csvContent += values.join(",") + "\n";
        });
        
        // Crear y descargar archivo
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", nombreArchivo + ".csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Configuración de módulos de funcionalidad
    const U = {
        url: '/api/ubicacion',
        load: async () => {
            qs('#INVIMDPCBID_u-loading').style.display = 'block'; 
            qs('#INVIMDPCBID_u-status').textContent = 'Cargando…';
            try {
                const r = await fetch(U.url); 
                const data = await r.json();
                const rows = data.items || data.data || [];
                
                // Guardar datos originales para filtros
                datosOriginalesIMD['u'] = rows;
                filtrosIMD['u'] = {}; // Resetear filtros
                
                // Usar función de actualización que soporta filtros
                actualizarTablaIMD('u', rows);
                
                qs('#INVIMDPCBID_u-status').textContent = `${rows.length} registros`;
            } catch (e) {
                qs('#INVIMDPCBID_u-status').textContent = 'Error de conexión';
            } finally { 
                qs('#INVIMDPCBID_u-loading').style.display = 'none'; 
            }
        },
        clear: () => {
            qs('#INVIMDPCBID_u-table tbody').innerHTML = '';
            qs('#INVIMDPCBID_u-status').textContent = 'Limpio';
            // Limpiar datos y filtros
            datosOriginalesIMD['u'] = [];
            limpiarTodosFiltrosIMD('u');
        }
    };

    const M = {
        url: '/api/movimientos',
        load: async () => {
            const desde = qs('#INVIMDPCBID_m-desde').value;
            const hasta = qs('#INVIMDPCBID_m-hasta').value;
            
            const p = new URLSearchParams();
            if (desde) p.append('desde', desde);
            if (hasta) p.append('hasta', hasta);

            qs('#INVIMDPCBID_m-loading').style.display = 'block'; 
            qs('#INVIMDPCBID_m-status').textContent = 'Cargando…';
            try {
                const r = await fetch(M.url + (p.toString() ? `?${p.toString()}` : '')); 
                const data = await r.json();
                const rows = data.items || data.data || [];
                
                // Guardar datos originales para filtros
                datosOriginalesIMD['m'] = rows;
                filtrosIMD['m'] = {}; // Resetear filtros
                
                // Usar función de actualización que soporta filtros
                actualizarTablaIMD('m', rows);
                
                qs('#INVIMDPCBID_m-status').textContent = `${rows.length} movimientos`;
            } catch (e) {
                qs('#INVIMDPCBID_m-status').textContent = 'Error de conexión';
            } finally { 
                qs('#INVIMDPCBID_m-loading').style.display = 'none'; 
            }
        },
        clear: () => {
            ['INVIMDPCBID_m-desde', 'INVIMDPCBID_m-hasta'].forEach(id => { 
                const el = qs('#' + id); 
                if (el) el.value = ''; 
            });
            qs('#INVIMDPCBID_m-table tbody').innerHTML = '';
            qs('#INVIMDPCBID_m-status').textContent = 'Limpio';
            // Limpiar datos y filtros
            datosOriginalesIMD['m'] = [];
            limpiarTodosFiltrosIMD('m');
        }
    };

    const G = {
        url: '/api/inventario_general',
        load: async () => {
            qs('#INVIMDPCBID_g-loading').style.display = 'block'; 
            qs('#INVIMDPCBID_g-status').textContent = 'Cargando…';
            try {
                const r = await fetch(G.url); 
                const data = await r.json();
                const rows = data.items || data.data || [];
                
                // Guardar datos originales para filtros
                datosOriginalesIMD['g'] = rows;
                filtrosIMD['g'] = {}; // Resetear filtros
                
                // Usar función de actualización que soporta filtros
                actualizarTablaIMD('g', rows);
                
                qs('#INVIMDPCBID_g-status').textContent = `${rows.length} ítems`;
            } catch (e) {
                qs('#INVIMDPCBID_g-status').textContent = 'Error de conexión';
            } finally { 
                qs('#INVIMDPCBID_g-loading').style.display = 'none'; 
            }
        },
        clear: () => {
            qs('#INVIMDPCBID_g-table tbody').innerHTML = '';
            qs('#INVIMDPCBID_g-status').textContent = 'Limpio';
            // Limpiar datos y filtros
            datosOriginalesIMD['g'] = [];
            limpiarTodosFiltrosIMD('g');
        },
        exportarExcel: () => {
            if (!datosOriginalesIMD['g'] || datosOriginalesIMD['g'].length === 0) {
                alert('No hay datos para exportar. Primero realiza una consulta.');
                return;
            }
            
            // Crear datos para Excel
            const datos = datosOriginalesIMD['g'];
            const headers = ['Modelo', 'No. Parte', 'Stock Total', 'Ubicaciones', 'Última Entrada', 'Última Salida', 'Tipo Inventario'];
            
            // Crear CSV content
            let csvContent = headers.join(',') + '\n';
            
            datos.forEach(row => {
                const fila = [
                    `"${row.modelo || ''}"`,
                    `"${row.nparte || ''}"`,
                    `"${row.stock_total || 0}"`,
                    `"${row.ubicaciones || ''}"`,
                    `"${row.ultima_entrada || ''}"`,
                    `"${row.ultima_salida || ''}"`,
                    `"${row.tipo_inventario || ''}"`
                ];
                csvContent += fila.join(',') + '\n';
            });
            
            // Crear y descargar archivo
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            
            // Nombre del archivo con fecha
            const fecha = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `inventario_imd_general_${fecha}.csv`);
            
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            qs('#INVIMDPCBID_g-status').textContent = `Exportados ${datos.length} registros a Excel`;
        }
    };

    // Configuración de eventos
    function configurarEventos() {
        // Tabs
        qsa('.tab-imd').forEach(b => {
            b.addEventListener('click', () => {
                qsa('.tab-imd').forEach(t => t.classList.remove('active'));
                qsa('.panel-imd').forEach(p => p.classList.remove('active'));
                b.classList.add('active');
                qs('#INVIMDPCBID_panel-' + b.dataset.panel).classList.add('active');
            });
        });

        // Ubicación
        if (qs('#INVIMDPCBID_u-buscar')) {
            qs('#INVIMDPCBID_u-buscar').addEventListener('click', U.load);
        }
        if (qs('#INVIMDPCBID_u-limpiar')) {
            qs('#INVIMDPCBID_u-limpiar').addEventListener('click', U.clear);
        }
        if (qs('#INVIMDPCBID_u-exportar')) {
            qs('#INVIMDPCBID_u-exportar').addEventListener('click', () => {
                const datos = datosOriginalesIMD['u'] || [];
                const columnas = [
                    { key: 'fecha', header: 'Fecha' },
                    { key: 'modelo', header: 'Modelo' },
                    { key: 'nparte', header: 'N. Parte' },
                    { key: 'ubicacion', header: 'Ubicación' },
                    { key: 'cantidad', header: 'Cantidad' },
                    { key: 'tipo_inventario', header: 'Tipo Inventario' },
                    { key: 'comentario', header: 'Comentario' },
                    { key: 'carro', header: 'Carro' },
                    { key: 'usuario', header: 'Usuario' }
                ];
                exportarExcelIMD(datos, 'ubicaciones_imd', columnas);
            });
        }

        // Movimientos
        setDefaultDates(['INVIMDPCBID_m-desde']);
        if (qs('#INVIMDPCBID_m-buscar')) {
            qs('#INVIMDPCBID_m-buscar').addEventListener('click', M.load);
        }
        if (qs('#INVIMDPCBID_m-limpiar')) {
            qs('#INVIMDPCBID_m-limpiar').addEventListener('click', M.clear);
        }
        if (qs('#INVIMDPCBID_m-exportar')) {
            qs('#INVIMDPCBID_m-exportar').addEventListener('click', () => {
                const datos = datosOriginalesIMD['m'] || [];
                const columnas = [
                    { key: 'fecha_hora', header: 'Fecha/Hora' },
                    { key: 'tipo', header: 'Tipo' },
                    { key: 'nparte', header: 'N. Parte' },
                    { key: 'modelo', header: 'Modelo' },
                    { key: 'cantidad', header: 'Cantidad' },
                    { key: 'ubicacion', header: 'Ubicación' },
                    { key: 'tipo_inventario', header: 'Tipo Inventario' },
                    { key: 'comentario', header: 'Comentario' },
                    { key: 'carro', header: 'Carro' }
                ];
                exportarExcelIMD(datos, 'movimientos_imd', columnas);
            });
        }

        // Inventario General
        if (qs('#INVIMDPCBID_g-buscar')) {
            qs('#INVIMDPCBID_g-buscar').addEventListener('click', G.load);
        }
        if (qs('#INVIMDPCBID_g-limpiar')) {
            qs('#INVIMDPCBID_g-limpiar').addEventListener('click', G.clear);
        }
        if (qs('#INVIMDPCBID_g-exportar')) {
            qs('#INVIMDPCBID_g-exportar').addEventListener('click', G.exportarExcel);
        }

        // Cerrar filtros IMD al hacer clic fuera
        document.addEventListener('click', function(event) {
            // Solo procesar si no es un click en elementos de filtro
            if (!event.target.closest('.filterable-header-imd')) {
                document.querySelectorAll('.header-filter-imd').forEach(filter => {
                    filter.style.display = 'none';
                });
                document.querySelectorAll('.filter-btn-imd').forEach(btn => {
                    btn.classList.remove('active');
                });
            }
        });
    }

    // Función de inicialización
    function inicializarInventarioIMD() {
        // Test mode with mock data when ?test=1
        function isTestMode() { 
            return window.location.search.indexOf('test=1') >= 0; 
        }
        
        if (isTestMode()) {
            (function() {
                var mock = {
                    '/api/ubicacion': { 
                        items: [
                            {fecha:'2025-08-10', modelo:'ES1D', nparte:'0DR100009MA', ubicacion:'A1-01', cantidad:120, carro:'C1', usuario:'yahir'},
                            {fecha:'2025-08-10', modelo:'US1J', nparte:'0DR100009CC', ubicacion:'B2-03', cantidad:60, carro:'C2', usuario:'admin'}
                        ]
                    },
                    '/api/movimientos': { 
                        items: [
                            {fecha_hora:'2025-08-10 08:15', tipo:'ENTRADA', nparte:'0DR100009MA', modelo:'ES1D', cantidad:120, ubicacion:'A1-01', carro:'C1', usuario:'yahir'},
                            {fecha_hora:'2025-08-10 09:10', tipo:'SALIDA', nparte:'0DR100009CC', modelo:'US1J', cantidad:20, ubicacion:'B2-03', carro:'C2', usuario:'admin'}
                        ]
                    },
                    '/api/inventario_general': { 
                        items: [
                            {modelo:'ES1D', nparte:'0DR100009MA', stock_total:1000, ubicaciones:'A1-01,C1; B1-02,C3', ultima_entrada:'2025-08-09', ultima_salida:'2025-08-10'},
                            {modelo:'US1J', nparte:'0DR100009CC', stock_total:500, ubicaciones:'B2-03,C2', ultima_entrada:'2025-08-08', ultima_salida:'2025-08-10'}
                        ]
                    }
                };
                var realFetch = window.fetch;
                window.fetch = function(url) {
                    var u = (typeof url === 'string') ? url.split('?')[0] : (url && url.url ? url.url.split('?')[0] : '');
                    if (mock[u]) {
                        return Promise.resolve(new Response(JSON.stringify(mock[u]), {status:200, headers:{'Content-Type':'application/json'}}));
                    }
                    return realFetch.apply(window, arguments);
                };
            })();
        }

        // Configurar eventos
        configurarEventos();

        // Auto-cargar al abrir
        G.load();        // Inventario general
        U.load();        // Ubicaciones
        M.load();        // Movimientos
        
        // Prepara estados
        const globalStatus = qs('#INVIMDPCBID_globalStatus');
        if (globalStatus) {
            globalStatus.textContent = 'Inventario IMD Terminado';
        }

        console.log('Módulo Inventario IMD Terminado inicializado correctamente');
    }

    // Auto-inicialización cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarInventarioIMD);
    } else {
        inicializarInventarioIMD();
    }

    // Exportar funciones que deben ser accesibles globalmente para los onclick
    window.toggleFiltroIMD = toggleFiltroIMD;
    window.aplicarFiltroTextoIMD = aplicarFiltroTextoIMD;
    window.limpiarTodosFiltrosIMD = limpiarTodosFiltrosIMD;

    // Exportar el módulo completo para uso externo
    window.inventarioIMDModule = {
        inicializar: inicializarInventarioIMD,
        datosOriginales: datosOriginalesIMD,
        filtros: filtrosIMD,
        U: U,
        M: M,
        G: G
    };

})();
