/**
 * Modulo Historial AOI (Control de resultados / Historial de maquinas SMT).
 *
 * Extraido del <script> inline del template el 2026-05-27 (WF_004).
 * Patron IIFE con ensureModuleStyles() de fallback igual que
 * inventario-imd-terminado-module.js y otros modulos AJAX.
 *
 * APIs consumidas (todas en app/api/control_resultados/aoi.py):
 *   GET /api/shift-now   -> turno actual + fecha logica
 *   GET /api/realtime    -> tabla del turno actual
 *   GET /api/day?date=   -> tabla por dia
 *
 * Exposiciones globales (consumidas por scriptMain.js):
 *   window.inicializarHistorialAOI() -> idempotente, auto-cleanup
 *   window.limpiarHistorialAOI()
 */

(function () {
    'use strict';

    // WF_004: garantizar CSS persistente cargado.
    const STYLESHEET_ID = 'control-historial-aoi-css';
    const STYLESHEET_HREF = '/static/css/control_historial_aoi.css?v=20260527a';
    function ensureModuleStyles() {
        if (document.getElementById(STYLESHEET_ID)) return;
        const link = document.createElement('link');
        link.id = STYLESHEET_ID;
        link.rel = 'stylesheet';
        link.href = STYLESHEET_HREF;
        document.head.appendChild(link);
    }

    // Estado del modulo (vive en closure; reset en inicializarModulo()).
    let aoiIntervals = [];
    let aoiEventListeners = [];
    let isModuleInitialized = false;

    const fmt = n => new Intl.NumberFormat('es-MX').format(n);

    function paintTableByOrder(tbodyId, rows, order) {
        const tb = document.getElementById(tbodyId);
        if (!tb) return;
        tb.innerHTML = '';
        if (!rows || rows.length === 0) {
            tb.innerHTML = `<tr><td colspan="${order.length}" id="aoi-empty">Sin registros</td></tr>`;
            return;
        }
        for (const r of rows) {
            const tr = document.createElement('tr');
            for (const k of order) {
                const td = document.createElement('td');
                const v = r[k];
                td.textContent = (k === 'cantidad') ? fmt(v) : v;
                tr.appendChild(td);
            }
            tb.appendChild(tr);
        }
    }

    async function j(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(await r.text());
        return r.json();
    }

    function todayISO() {
        const d = new Date();
        const p = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
    }

    async function loadRealtime() {
        try {
            const meta = await j('/api/shift-now');
            const nowElement = document.getElementById('aoi-now');
            const shiftBadge = document.getElementById('aoi-shift-badge');
            const shiftTitle = document.getElementById('aoi-shift-title');

            if (nowElement) nowElement.textContent = new Date(meta.now).toLocaleString();
            if (shiftBadge) shiftBadge.textContent = `${meta.shift} - ${meta.shift_date}`;
            if (shiftTitle) shiftTitle.textContent = `${meta.shift} | ${meta.shift_date}`;

            const data = await j('/api/realtime');
            paintTableByOrder('aoi-rt-body', data.rows, ['linea', 'modelo', 'lado', 'cantidad']);
            const total = data.rows.reduce((s, r) => s + (+r.cantidad || 0), 0);
            const totalElement = document.getElementById('aoi-rt-total');
            if (totalElement) totalElement.textContent = 'Total turno: ' + fmt(total);
        } catch (error) {
            console.error('Error cargando datos en tiempo real:', error);
        }
    }

    async function loadDay(d) {
        try {
            const dayTitle = document.getElementById('aoi-day-title');
            if (dayTitle) dayTitle.textContent = d;

            const data = await j('/api/day?date=' + encodeURIComponent(d));
            paintTableByOrder('aoi-day-body', data.rows, ['fecha', 'linea', 'turno', 'modelo', 'lado', 'cantidad']);
            const total = data.rows.reduce((s, r) => s + (+r.cantidad || 0), 0);
            const totalElement = document.getElementById('aoi-day-total');
            if (totalElement) totalElement.textContent = 'Total dia: ' + fmt(total);
        } catch (error) {
            console.error('Error cargando datos del dia:', error);
        }
    }

    function addManagedEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            aoiEventListeners.push({ element, event, handler });
        }
    }

    function addManagedInterval(callback, interval) {
        const intervalId = setInterval(callback, interval);
        aoiIntervals.push(intervalId);
        return intervalId;
    }

    function cleanupModule() {
        aoiIntervals.forEach(id => clearInterval(id));
        aoiIntervals = [];
        aoiEventListeners.forEach(({ element, event, handler }) => {
            if (element) element.removeEventListener(event, handler);
        });
        aoiEventListeners = [];
        isModuleInitialized = false;
    }

    function inicializarModulo() {
        ensureModuleStyles();

        if (isModuleInitialized) {
            // Re-entrada (tab cambio, reinyeccion AJAX): limpiar listeners viejos.
            cleanupModule();
        }
        isModuleInitialized = true;

        const btnRefresh = document.getElementById('aoi-btn-refresh');
        const btnQuery = document.getElementById('aoi-btn-query');
        const dateInput = document.getElementById('aoi-date');

        addManagedEventListener(btnRefresh, 'click', loadRealtime);
        addManagedEventListener(btnQuery, 'click', () => {
            const d = dateInput ? dateInput.value : '';
            if (d) loadDay(d);
        });

        if (dateInput && !dateInput.value) {
            dateInput.value = todayISO();
        }

        loadRealtime();
        addManagedInterval(loadRealtime, 15000);
    }

    // Expose para scriptMain.js (window.cargarContenidoDinamico callback).
    window.inicializarHistorialAOI = inicializarModulo;
    window.limpiarHistorialAOI = cleanupModule;

    // Cleanup en navegacion completa.
    window.addEventListener('beforeunload', cleanupModule);

    // Callback opcional para sistemas de templates.
    if (typeof window.onTemplateLoaded === 'function') {
        window.onTemplateLoaded('historial_aoi_ajax');
    }
})();
