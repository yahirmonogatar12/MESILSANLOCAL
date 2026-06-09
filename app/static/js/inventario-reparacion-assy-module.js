/**
 * Modulo de Inventario reparacion ASSY (solo lectura / reportes).
 * Lee la tabla compartida pcb_inventory_scan_prod (area='REPARACION') via las
 * APIs del blueprint app/api/control_resultados/inventario_reparacion_assy.py.
 *
 * Gemelo de inventario-reparacion-smd-module.js. Prefijo de IDs 'repa-' para
 * coexistir sin colisiones con el modulo SMD ('rep-'). Incluye la columna extra
 * linea_salida_pcb en Detalle de movimientos.
 *
 * 3 vistas: 's' = Stock actual, 'm' = Movimientos, 'd' = Resumen por defecto.
 */
(function () {
    'use strict';

    // WF_004 capa 2: garantizar el CSS persistente. MainTemplate.html ya lo
    // declara, pero si el modulo se sirve fuera del template, inyectar el
    // <link> de forma idempotente.
    const STYLESHEET_ID = 'inventario-reparacion-assy-css';
    const STYLESHEET_HREF = '/static/css/inventario_reparacion_assy.css?v=20260605a';
    function ensureModuleStyles() {
        if (document.getElementById(STYLESHEET_ID)) return;
        const link = document.createElement('link');
        link.id = STYLESHEET_ID;
        link.rel = 'stylesheet';
        link.href = STYLESHEET_HREF;
        document.head.appendChild(link);
    }

    // ---- Estado privado del modulo (se resetea en cada init AJAX) ----
    let datosOriginalesRepa = { s: [], m: [], d: [] };
    let filtrosRepa = { s: {}, m: {}, d: {} };
    let cargados = { s: false, m: false, d: false };

    // ---- Utilidades ----
    function fmt(v) { return (v === undefined || v === null || v === '') ? '-' : v; }
    function qs(sel) { return document.querySelector(sel); }
    function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }
    function esc(v) { return (v === undefined || v === null) ? '' : String(v); }

    function todayISO() {
        const now = new Date();
        const local = new Date(now.getTime() - (now.getTimezoneOffset() * 60000));
        return local.toISOString().split('T')[0];
    }

    // ============================================================
    // FILTROS DE CABECERA (texto, busqueda "contiene", case-insensitive)
    // ============================================================
    function toggleFiltroRepA(tabla, columna) {
        const filtroDiv = document.getElementById(`filtro-repa-${tabla}-${columna}`);
        const filterBtn = document.querySelector(`button[onclick="toggleFiltroRepA('${tabla}', '${columna}')"]`);
        if (!filtroDiv) return;

        document.querySelectorAll('.header-filter-repa').forEach(f => {
            if (f.id !== `filtro-repa-${tabla}-${columna}`) f.style.display = 'none';
        });
        document.querySelectorAll('.filter-btn-repa').forEach(b => {
            if (b !== filterBtn) b.classList.remove('active');
        });

        if (filtroDiv.style.display === 'none' || !filtroDiv.style.display) {
            filtroDiv.style.display = 'block';
            if (filterBtn) filterBtn.classList.add('active');
            const input = filtroDiv.querySelector('.filter-input-repa');
            if (input) setTimeout(() => input.focus(), 100);
        } else {
            filtroDiv.style.display = 'none';
            if (filterBtn) filterBtn.classList.remove('active');
        }
    }

    function aplicarFiltroTextoRepA(tabla, columna, valor) {
        if (valor.trim() === '') {
            delete filtrosRepa[tabla][columna];
        } else {
            filtrosRepa[tabla][columna] = valor.trim();
        }
        aplicarTodosFiltrosRepA(tabla);
    }

    function aplicarTodosFiltrosRepA(tabla) {
        let datos = [...datosOriginalesRepa[tabla]];
        Object.keys(filtrosRepa[tabla]).forEach(columna => {
            const filtro = (filtrosRepa[tabla][columna] || '').toLowerCase();
            datos = datos.filter(fila => {
                const celda = (fila[columna] === undefined || fila[columna] === null) ? '' : String(fila[columna]).toLowerCase();
                return celda.includes(filtro);
            });
        });
        renderTabla(tabla, datos);
    }

    function limpiarTodosFiltrosRepA(tabla) {
        filtrosRepa[tabla] = {};
        document.querySelectorAll(`#repa-${tabla}-table .header-filter-repa input`).forEach(i => { i.value = ''; });
        document.querySelectorAll(`#repa-${tabla}-table .header-filter-repa`).forEach(f => { f.style.display = 'none'; });
        document.querySelectorAll(`#repa-${tabla}-table .filter-btn-repa`).forEach(b => b.classList.remove('active'));
        renderTabla(tabla, datosOriginalesRepa[tabla]);
    }

    // ============================================================
    // RENDER DE TABLAS
    // ============================================================
    function renderTabla(tabla, datos) {
        const tbody = document.querySelector(`#repa-${tabla}-table tbody`);
        if (!tbody) return;
        tbody.innerHTML = '';

        datos.forEach(fila => {
            const tr = document.createElement('tr');

            if (tabla === 's') {
                const stock = parseInt(fila.stock_actual || 0, 10);
                const stockCls = stock > 0 ? 'stock-pos' : (stock < 0 ? 'stock-neg' : 'stock-zero');
                tr.innerHTML = `
                    <td title="${esc(fila.pcb_part_no)}">${fmt(fila.pcb_part_no)}</td>
                    <td title="${esc(fila.modelo)}">${fmt(fila.modelo)}</td>
                    <td>${fmt(fila.proceso)}</td>
                    <td>${fmt(fila.total_entrada)}</td>
                    <td>${fmt(fila.total_salida)}</td>
                    <td>${fmt(fila.total_scrap)}</td>
                    <td class="${stockCls}">${fmt(fila.stock_actual)}</td>`;
            } else if (tabla === 'm') {
                const tipo = fila.tipo_movimiento;
                const chip = tipo === 'ENTRADA' ? 'ok-repa' : (tipo === 'SCRAP' ? 'ng-repa' : (tipo === 'SALIDA' ? 'warn-repa' : ''));
                tr.innerHTML = `
                    <td>${fmt(fila.inventory_date)}</td>
                    <td>${fmt(fila.hora)}</td>
                    <td><span class="${chip}">${fmt(tipo)}</span></td>
                    <td title="${esc(fila.scanned_original)}">${fmt(fila.scanned_original)}</td>
                    <td title="${esc(fila.pcb_part_no)}">${fmt(fila.pcb_part_no)}</td>
                    <td title="${esc(fila.modelo)}">${fmt(fila.modelo)}</td>
                    <td>${fmt(fila.proceso)}</td>
                    <td title="${esc(fila.defect_type)}">${fmt(fila.defect_type)}</td>
                    <td title="${esc(fila.component_location)}">${fmt(fila.component_location)}</td>
                    <td>${fmt(fila.etapa_deteccion)}</td>
                    <td title="${esc(fila.linea_salida_pcb)}">${fmt(fila.linea_salida_pcb)}</td>
                    <td>${fmt(fila.qty)}</td>
                    <td>${fmt(fila.array_count)}</td>
                    <td title="${esc(fila.scanned_by)}">${fmt(fila.scanned_by)}</td>
                    <td title="${esc(fila.comentarios)}">${fmt(fila.comentarios)}</td>`;
            } else if (tabla === 'd') {
                tr.innerHTML = `
                    <td title="${esc(fila.defect_type)}">${fmt(fila.defect_type)}</td>
                    <td>${fmt(fila.etapa_deteccion)}</td>
                    <td>${fmt(fila.registros)}</td>
                    <td>${fmt(fila.qty_total)}</td>`;
            }
            tbody.appendChild(tr);
        });

        const statusEl = qs(`#repa-${tabla}-status`);
        if (statusEl) {
            const total = datosOriginalesRepa[tabla].length;
            const fil = datos.length;
            statusEl.textContent = total === fil ? `${total} registros` : `${fil} de ${total} registros`;
        }
    }

    // ============================================================
    // CONSTRUCCION DE QUERY STRINGS (filtros del panel -> params API)
    // ============================================================
    function paramsStock() {
        const p = new URLSearchParams();
        const parte = qs('#repa-s-parte');
        const proceso = qs('#repa-s-proceso');
        const incluir = qs('#repa-s-incluir-cero');
        if (parte && parte.value.trim()) p.append('numero_parte', parte.value.trim());
        if (proceso && proceso.value) p.append('proceso', proceso.value);
        if (incluir && incluir.checked) p.append('include_zero', '1');
        return p;
    }

    function paramsMovimientos() {
        const p = new URLSearchParams();
        const desde = qs('#repa-m-desde');
        const hasta = qs('#repa-m-hasta');
        const parte = qs('#repa-m-parte');
        const proceso = qs('#repa-m-proceso');
        const tipo = qs('#repa-m-tipo');
        if (desde && desde.value) p.append('fecha_inicio', desde.value);
        if (hasta && hasta.value) p.append('fecha_fin', hasta.value);
        if (parte && parte.value.trim()) p.append('numero_parte', parte.value.trim());
        if (proceso && proceso.value) p.append('proceso', proceso.value);
        if (tipo && tipo.value) p.append('tipo_movimiento', tipo.value);
        return p;
    }

    function paramsDefectos() {
        const p = new URLSearchParams();
        const desde = qs('#repa-d-desde');
        const hasta = qs('#repa-d-hasta');
        const proceso = qs('#repa-d-proceso');
        if (desde && desde.value) p.append('fecha_inicio', desde.value);
        if (hasta && hasta.value) p.append('fecha_fin', hasta.value);
        if (proceso && proceso.value) p.append('proceso', proceso.value);
        return p;
    }

    // ============================================================
    // CARGA DE DATOS POR VISTA
    // ============================================================
    async function cargar(tabla, url, paramsFn, labelSingular, labelPlural) {
        const loading = qs(`#repa-${tabla}-loading`);
        const status = qs(`#repa-${tabla}-status`);
        if (loading) loading.style.display = 'block';
        if (status) status.textContent = 'Cargando...';
        try {
            const p = paramsFn();
            const r = await fetch(url + (p.toString() ? `?${p.toString()}` : ''));
            const data = await r.json();
            if (data.status === 'error') {
                if (status) status.textContent = 'Error: ' + (data.message || 'desconocido');
                return;
            }
            const rows = data.items || [];
            datosOriginalesRepa[tabla] = rows;
            filtrosRepa[tabla] = {};
            cargados[tabla] = true;
            renderTabla(tabla, rows);
            if (status) status.textContent = `${rows.length} ${rows.length === 1 ? labelSingular : labelPlural}`;
        } catch (e) {
            console.error('[REPA] error cargando ' + tabla, e);
            if (status) status.textContent = 'Error de conexion';
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    const S = {
        load: () => cargar('s', '/api/reparacion_assy/stock', paramsStock, 'parte', 'partes'),
        clear: () => {
            ['repa-s-parte'].forEach(id => { const el = qs('#' + id); if (el) el.value = ''; });
            const proc = qs('#repa-s-proceso'); if (proc) proc.value = '';
            const inc = qs('#repa-s-incluir-cero'); if (inc) inc.checked = false;
            datosOriginalesRepa.s = [];
            const tb = qs('#repa-s-table tbody'); if (tb) tb.innerHTML = '';
            limpiarTodosFiltrosRepA('s');
            const st = qs('#repa-s-status'); if (st) st.textContent = 'Limpio';
        }
    };

    const M = {
        load: () => cargar('m', '/api/reparacion_assy/movimientos', paramsMovimientos, 'movimiento', 'movimientos'),
        clear: () => {
            ['repa-m-desde', 'repa-m-hasta', 'repa-m-parte'].forEach(id => { const el = qs('#' + id); if (el) el.value = ''; });
            ['repa-m-proceso', 'repa-m-tipo'].forEach(id => { const el = qs('#' + id); if (el) el.value = ''; });
            datosOriginalesRepa.m = [];
            const tb = qs('#repa-m-table tbody'); if (tb) tb.innerHTML = '';
            limpiarTodosFiltrosRepA('m');
            const st = qs('#repa-m-status'); if (st) st.textContent = 'Listo para consultar';
        }
    };

    const D = {
        load: () => cargar('d', '/api/reparacion_assy/defectos', paramsDefectos, 'defecto', 'defectos'),
        clear: () => {
            ['repa-d-desde', 'repa-d-hasta'].forEach(id => { const el = qs('#' + id); if (el) el.value = ''; });
            const proc = qs('#repa-d-proceso'); if (proc) proc.value = '';
            datosOriginalesRepa.d = [];
            const tb = qs('#repa-d-table tbody'); if (tb) tb.innerHTML = '';
            limpiarTodosFiltrosRepA('d');
            const st = qs('#repa-d-status'); if (st) st.textContent = 'Limpio';
        }
    };

    // ============================================================
    // EXPORT EXCEL (descarga blob desde los endpoints /export del backend)
    // ============================================================
    async function exportar(tabla, baseUrl, paramsFn) {
        const status = qs(`#repa-${tabla}-status`);
        try {
            const p = paramsFn();
            const url = baseUrl + '/export' + (p.toString() ? `?${p.toString()}` : '');
            const r = await fetch(url, { method: 'GET', credentials: 'same-origin' });
            if (!r.ok) throw new Error('Status ' + r.status);
            const blob = await r.blob();

            let filename = `reparacion_assy_${tabla}_${todayISO()}.xlsx`;
            const disp = r.headers.get('content-disposition');
            if (disp) {
                const m = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disp);
                if (m && m[1]) filename = m[1].replace(/['"]/g, '');
            }

            const a = document.createElement('a');
            a.href = window.URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            if (status) status.textContent = 'Exportacion completada';
        } catch (e) {
            console.error('[REPA] error exportando ' + tabla, e);
            if (status) status.textContent = 'Error al exportar';
        }
    }

    // ============================================================
    // EVENTOS - EVENT DELEGATION (un solo listener en body, idempotente)
    // ============================================================
    function configurarEventos() {
        // Estado inicial del DOM recien inyectado (cada re-inyeccion AJAX).
        // Fecha "desde" por defecto = hoy en Movimientos y Resumen por defecto.
        // El usuario puede cambiarla libremente; el backend respeta lo que llegue.
        ['repa-m-desde', 'repa-d-desde'].forEach(id => {
            const el = qs('#' + id);
            if (el && !el.value) el.value = todayISO();
        });
        const mStatus = qs('#repa-m-status');
        if (mStatus) mStatus.textContent = 'Listo para consultar';

        if (document.body.dataset.repaListenersAttached) return;

        document.body.addEventListener('click', function (e) {
            const t = e.target;

            // --- Pestañas ---
            const tab = t.closest('.tab-repa');
            if (tab && document.body.contains(tab)) {
                const panel = tab.dataset.panel;
                qsa('.tab-repa').forEach(x => x.classList.remove('active'));
                qsa('.panel-repa').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                const panelEl = qs('#repa-panel-' + panel);
                if (panelEl) panelEl.classList.add('active');
                // Carga perezosa la primera vez que se abre la pestaña.
                if (panel === 'movimientos' && !cargados.m) M.load();
                if (panel === 'defectos' && !cargados.d) D.load();
                return;
            }

            // --- Botones por ID ---
            const idHandlers = {
                'repa-s-buscar': () => S.load(),
                'repa-s-limpiar': () => S.clear(),
                'repa-s-exportar': () => exportar('s', '/api/reparacion_assy/stock', paramsStock),
                'repa-m-buscar': () => M.load(),
                'repa-m-limpiar': () => M.clear(),
                'repa-m-exportar': () => exportar('m', '/api/reparacion_assy/movimientos', paramsMovimientos),
                'repa-d-buscar': () => D.load(),
                'repa-d-limpiar': () => D.clear(),
                'repa-d-exportar': () => exportar('d', '/api/reparacion_assy/defectos', paramsDefectos)
            };
            for (const id in idHandlers) {
                if (t.id === id || (t.closest && t.closest('#' + id))) {
                    idHandlers[id]();
                    return;
                }
            }

            // Cerrar filtros si el click fue fuera de un header filtrable.
            if (!t.closest('.filterable-header-repa')) {
                document.querySelectorAll('.header-filter-repa').forEach(f => f.style.display = 'none');
                document.querySelectorAll('.filter-btn-repa').forEach(b => b.classList.remove('active'));
            }
        });

        document.body.dataset.repaListenersAttached = '1';
    }

    // ============================================================
    // INICIALIZACION
    // ============================================================
    function inicializarInventarioReparacionASSY() {
        ensureModuleStyles();
        // Reset de estado del closure: esta funcion se llama en cada
        // re-inyeccion AJAX, asi que limpiamos datos/filtros/banderas.
        datosOriginalesRepa = { s: [], m: [], d: [] };
        filtrosRepa = { s: {}, m: {}, d: {} };
        cargados = { s: false, m: false, d: false };

        configurarEventos();

        // Esperar a que el DOM del template este listo antes de la primera
        // carga, para evitar el race con cargarContenidoDinamico (que aun
        // puede estar moviendo el HTML al contenedor).
        esperarDOM(['#repa-s-table tbody'], () => {
            // Fecha "desde" por defecto = hoy (Movimientos y Resumen por defecto).
            // Se setea aqui tambien por si configurarEventos corrio antes de
            // que estos inputs existieran en el DOM.
            ['repa-m-desde', 'repa-d-desde'].forEach(id => {
                const el = qs('#' + id);
                if (el && !el.value) el.value = todayISO();
            });
            S.load();  // La pestaña activa por defecto es Stock.
        });
    }

    function esperarDOM(selectores, callback, maxIntentos) {
        maxIntentos = maxIntentos || 30;
        let intentos = 0;
        (function check() {
            if (selectores.every(sel => document.querySelector(sel))) {
                callback();
            } else if (intentos < maxIntentos) {
                intentos++;
                setTimeout(check, 30);
            } else {
                console.warn('[REPA] esperarDOM: timeout, ejecutando callback de todos modos');
                callback();
            }
        })();
    }

    // Cleanup al navegar a otro modulo.
    function cleanup() {
        ['s', 'm', 'd'].forEach(t => {
            const loader = qs(`#repa-${t}-loading`);
            if (loader) loader.style.display = 'none';
        });
    }

    // ---- Exponer globalmente ----
    window.inicializarInventarioReparacionASSY = inicializarInventarioReparacionASSY;
    window.limpiarInventarioReparacionASSY = cleanup;
    window.toggleFiltroRepA = toggleFiltroRepA;
    window.aplicarFiltroTextoRepA = aplicarFiltroTextoRepA;
    window.limpiarTodosFiltrosRepA = limpiarTodosFiltrosRepA;

    window.inventarioReparacionASSYModule = {
        inicializar: inicializarInventarioReparacionASSY,
        datosOriginales: datosOriginalesRepa,
        filtros: filtrosRepa,
        S: S, M: M, D: D
    };

    // Auto-inicializacion en la primera carga.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarInventarioReparacionASSY);
    } else {
        inicializarInventarioReparacionASSY();
    }
})();
