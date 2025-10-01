/**
 * Plan Main Loader - Carga datos de la tabla plan_main MySQL
 * Sistema para cargar y mostrar datos de producción en la tabla principal
 */
(function() {
    "use strict";

    // Variables globales
    let isInitialized = false;
    let planMainData = [];
    let filteredData = [];
    let currentFilters = {};
    let selectedRowId = null;
    let autoRefreshTimer = null;
    let isAutoRefreshing = false;

    // Referencias DOM
    const elements = {
        tableBody: null,
        tableContainer: null,
        loadingIndicator: null
    };

    /**
     * Configuración de endpoints API
     */
    const API_CONFIG = {
        baseUrl: '/api/plan-main',
        endpoints: {
            list: '/list',
            detail: '/detail',
            update: '/update',
            delete: '/delete'
        }
    };

    /**
     * Cargar datos de la tabla plan_main
     */
    async function cargarDatosPlanMain(filtros = {}) {
        // Mostrar indicador de carga (si ya hay contenido lo sustituye temporalmente)
        mostrarIndicadorCarga(true);
        
        try {
            // Construir parámetros de consulta usando los nombres que espera tu backend
            const params = new URLSearchParams();
            
            // Filtro de búsqueda general (q)
            if (filtros.q && filtros.q.trim()) {
                params.set("q", filtros.q.trim());
            }
            
            // Filtro de línea (linea) - compatible con tu backend
            if (filtros.linea && filtros.linea !== "Todos" && filtros.linea !== "ALL") {
                params.set("linea", filtros.linea);
            }
            
            // Filtros de fecha (desde/hasta) - compatible con tu backend
            if (filtros.desde) {
                params.set("desde", filtros.desde);
            }
            if (filtros.hasta) {
                params.set("hasta", filtros.hasta);
            }
            
            // Filtro solo pendientes
            if (filtros.solo_pendientes) {
                params.set("solo_pendientes", "true");
            }
            
            // Realizar petición al endpoint existente
            const url = "/api/plan-main/list?" + params.toString();
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status} - ${response.statusText}`);
            }

            const responseData = await response.json();
            
            // Tu backend devuelve directamente un array
            let datos = [];
            if (Array.isArray(responseData)) {
                datos = responseData;
            } else if (responseData.data && Array.isArray(responseData.data)) {
                datos = responseData.data;
            } else if (responseData.rows && Array.isArray(responseData.rows)) {
                datos = responseData.rows;
            } else {
                datos = [];
            }
            
            // Actualizar datos globales
            planMainData = datos;
            currentFilters = filtros;
            
            // Renderizar tabla
            renderizarTablaPrincipal(datos);
            
            // Actualizar estadísticas
            actualizarEstadisticas(datos);
            
            return datos;
            
        } catch (error) {
            mostrarError("Error al cargar los datos: " + error.message);
            
            // Mostrar mensaje de error en la tabla
            const tableBody = elements.tableBody;
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr class="message-row">
                        <td colspan="16" style="display: table-cell; text-align: center; padding: 30px; color: #e74c3c;">
                            <i class="fas fa-exclamation-triangle" style="font-size: 24px; margin-bottom: 10px;"></i><br>
                            Error al cargar los datos<br>
                            <small style="color: #95a5a6;">${error.message}</small>
                        </td>
                    </tr>
                `;
            }
            
            return [];
            
        } finally {
            mostrarIndicadorCarga(false);
        }
    }

    /**
     * Actualizar producido de un plan (incremento o set)
     * options: { increment: number } o { set: number }
     */
    // PRODUCCION DESHABILITADA: la actualización de 'produced_count' se realiza externamente.
    // Esta función queda como stub para evitar llamadas al endpoint de producción.
    async function actualizarProducido(/* lotNo, options = {} */) {
        mostrarInfo('El producido se actualiza automáticamente desde el sistema externo.');
        return false;
    }

    function iniciarAutoRefresh(intervalMs = 15000) {
        detenerAutoRefresh();
        let ciclos = 0;
        autoRefreshTimer = setInterval(async () => {
            if (isAutoRefreshing) return;
            isAutoRefreshing = true;
            try {
                ciclos++;
                // Cada 8 ciclos (~2 minutos si 15s) hacer recarga completa para capturar nuevos planes
                if (ciclos % 8 === 0) {
                    const filtros = obtenerFiltrosActuales();
                    await cargarDatosPlanMain(filtros);
                } else {
                    await refrescarSoloProducido();
                }
            } catch (e) {
                // Auto refresh fallo
            } finally {
                isAutoRefreshing = false;
            }
        }, intervalMs);
    }

    // Refrescar solo columnas de producido/falta/porcentaje para cada fila renderizada
    async function refrescarSoloProducido() {
        try {
            const lotesVisibles = Array.from(document.querySelectorAll('tbody tr[data-plan-id]'))
                .map(tr => {
                    const id = tr.getAttribute('data-plan-id');
                    const plan = planMainData.find(p => String(p.id) === String(id));
                    return plan ? (plan.lote || plan.lot_no) : null;
                })
                .filter(Boolean);
            if (lotesVisibles.length === 0) return;

            // Reusar filtros actuales pero sólo traer mismos lotes (si backend soporta filtro q parcial)
            // Para minimizar impacto: pedir nuevamente la lista completa y mapear.
            const filtros = obtenerFiltrosActuales();
            const nuevos = await cargarDatosPlanMainLigero(filtros);
            if (!nuevos || nuevos.length === 0) return;

            // Index por lot_no
            const index = {};
            nuevos.forEach(p => { index[p.lote || p.lot_no] = p; });

            lotesVisibles.forEach(lot => {
                const planNuevo = index[lot];
                if (!planNuevo) return;
                // Actualizar cache planMainData
                const idx = planMainData.findIndex(p => (p.lote||p.lot_no) === lot);
                if (idx >= 0) {
                    planMainData[idx].producido = planNuevo.producido;
                    planMainData[idx].falta = planNuevo.falta;
                    planMainData[idx].estatus = planNuevo.estatus; // Por si cambió a TERMINADO
                }
                // Actualizar DOM
                const tr = Array.from(document.querySelectorAll('tbody tr[data-plan-id]'))
                    .find(r => (planMainData.find(p=>String(p.id)===r.getAttribute('data-plan-id'))||{}).lote === lot);
                if (!tr) return;
                const planCache = planMainData[idx];
                if (!planCache) return;
                const planCount = parseInt(planCache.qty)||0;
                const producido = parseInt(planCache.producido)||0;
                const falta = Math.max(0, planCount - producido);
                const porcentaje = planCount>0? Math.round((producido/planCount)*100):0;
                // Columnas: asumimos orden original -> Qty(10) Producido(11) Falta(12) % (13) barra(14) estado(16)
                const tds = tr.querySelectorAll('td');
                // Orden real de columnas (0..15):
                // 0 chk,1 id,2 linea,3 lote,4 nparte,5 modelo,6 process,7 ct,8 uph,
                // 9 qty,10 producido,11 falta,12 porcentaje,13 barra,14 fecha,15 estado
                if (tds.length >= 16) {
                    tds[9].textContent = planCount.toLocaleString();
                    tds[10].textContent = producido.toLocaleString();
                    tds[11].textContent = falta.toLocaleString();
                    tds[12].textContent = porcentaje + '%';
                    const barSpan = tds[13].querySelector('.progress-bar span');
                    if (barSpan) barSpan.style.width = porcentaje + '%';
                    const statusTag = tds[15].querySelector('.status-tag');
                    if (statusTag) {
                        let rawStatus = (planCache.estatus || planCache.status || 'PLAN').toUpperCase();
                        let statusClass = 'pending';
                        let extraClass = '';
                        let statusText = 'PLANEADO';
                        if (rawStatus === 'EN PROGRESO' || rawStatus === 'RUNNING') { statusClass = 'partial'; extraClass=' running'; statusText = '▶ EN PROGRESO'; }
                        else if (rawStatus === 'PAUSADO' || rawStatus === 'PAUSED') { statusClass = 'partial'; extraClass=' paused'; statusText = '⏸ PAUSADO'; }
                        else if (rawStatus === 'TERMINADO' || rawStatus === 'FINALIZADO' || porcentaje >= 100) { statusClass = 'completed'; statusText = 'TERMINADO'; }
                        statusTag.className = 'status-tag ' + statusClass + extraClass;
                        statusTag.textContent = statusText;
                    }
                } else {
                    // Si por alguna razón la estructura cambió, forzar recarga completa en siguiente ciclo
                }
            });
        } catch (e) {
            // Refresco incremental fallo
        }
    }

    async function cargarDatosPlanMainLigero(filtros) {
        try {
            const params = new URLSearchParams();
            if (filtros.q && filtros.q.trim()) params.set('q', filtros.q.trim());
            if (filtros.linea && filtros.linea !== 'Todos' && filtros.linea !== 'ALL') params.set('linea', filtros.linea);
            if (filtros.desde) params.set('desde', filtros.desde);
            if (filtros.hasta) params.set('hasta', filtros.hasta);
            if (filtros.solo_pendientes) params.set('solo_pendientes', 'true');
            const url = '/api/plan-main/list?' + params.toString();
            const resp = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }});
            if (!resp.ok) return [];
            const json = await resp.json();
            if (Array.isArray(json)) return json;
            if (json.rows && Array.isArray(json.rows)) return json.rows;
            return [];
        } catch { return []; }
    }

    function detenerAutoRefresh() {
        if (autoRefreshTimer) {
            clearInterval(autoRefreshTimer);
            autoRefreshTimer = null;
        }
    }

    // Eliminada función obtenerCtUphRaw: ahora CT y UPH llegan directamente del endpoint /api/plan-main/list

    /**
     * Renderizar datos en la tabla principal
     */
    function renderizarTablaPrincipal(datos) {
        const tableBody = elements.tableBody || document.getElementById("tbody-plan-data");
        
        if (!tableBody) {
            return;
        }

        // Limpiar tabla
        tableBody.innerHTML = "";

        if (!datos || datos.length === 0) {
            tableBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="16" style="display: table-cell; text-align: center; padding: 30px; color: #95a5a6;">
                        <i class="fas fa-inbox" style="font-size: 24px; margin-bottom: 10px;"></i><br>
                        No hay datos disponibles
                        <br><small>Ajuste los filtros de búsqueda</small>
                    </td>
                </tr>
            `;
            return;
        }

            // Renderizar filas
        datos.forEach((plan, index) => {
            // DEBUG: Ver exactamente qué datos llegan
            if (index === 0) {

            }
            
            const row = document.createElement("tr");
            row.setAttribute("data-plan-id", plan.id);
            row.className = "plan-row";            // Calcular progreso y estado - usando campos exactos de tu API
            const planCount = parseInt(plan.qty) || 0;  // Tu API envía 'qty' 
            const arrayCount = parseInt(plan.array_count) || 0;
            const xOut = parseInt(plan.x_out) || 0;
            const producido = plan.producido || (arrayCount - xOut);  // Tu API envía 'producido'
            const falta = plan.falta || Math.max(0, planCount - producido);  // Tu API envía 'falta'
            const porcentaje = planCount > 0 ? Math.round((producido / planCount) * 100) : 0;
            
            // Determinar clase de estado con nuevos estados
            let rawStatus = (plan.estatus || plan.status || 'PLAN').toUpperCase();
            let statusClass = 'pending';
            let statusText = 'PLANEADO';
            let pausedSeconds = plan.paused_at || 0;
            let pausedInfo = '';
            
            if (pausedSeconds > 0) {
                const hours = Math.floor(pausedSeconds / 3600);
                const minutes = Math.floor((pausedSeconds % 3600) / 60);
                const seconds = pausedSeconds % 60;
                pausedInfo = ` (⏸ ${hours}h ${minutes}m ${seconds}s)`;
            }
            
            if (rawStatus === 'EN PROGRESO' || rawStatus === 'RUNNING') { 
                statusClass = 'partial running'; 
                statusText = '▶ EN PROGRESO' + pausedInfo; 
            }
            else if (rawStatus === 'PAUSADO' || rawStatus === 'PAUSED') { 
                statusClass = 'partial paused'; 
                statusText = '⏸ PAUSADO' + pausedInfo; 
            }
            else if (rawStatus === 'TERMINADO' || rawStatus === 'FINALIZADO' || rawStatus === 'COMPLETED' || porcentaje >= 100) { 
                statusClass = 'completed'; 
                statusText = 'TERMINADO' + (pausedSeconds > 0 ? pausedInfo : ''); 
            }
            else if (rawStatus === 'PLAN') { 
                statusClass = 'pending'; 
                statusText = 'PLANEADO'; 
            }
            
            // Formatear fechas - usando campos exactos de tu API
            const fechaTrabajo = (plan.fecha_inicio || plan.working_date) ? formatearFecha(plan.fecha_inicio || plan.working_date) : "";
            const fechaCreado = plan.created_at ? formatearFechaHora(plan.created_at) : "";
            
            // Construir HTML de la fila - EXACTAMENTE como el HTML original
            row.innerHTML = `
                <td style="text-align: center; width: 30px;">
                    <input type="checkbox" class="table-checkbox" value="${plan.id}">
                </td>
                <td class="mono" title="ID: ${plan.id}">${plan.id}</td>
                <td title="Línea: ${plan.linea || ''}">${plan.linea || ''}</td>
                <td title="Lote: ${plan.lote || ''}">${plan.lote || ''}</td>
                <td title="No. Parte: ${plan.nparte || ''}">${plan.nparte || ''}</td>
                <td title="Modelo: ${plan.modelo || ''}">${plan.modelo || ''}</td>
                <td title="Proceso: ${plan.process || ''}">${plan.process || ''}</td>
                <td class="mono ct-cell" title="CT: ${plan.ct != null ? plan.ct : 0}">
                    ${plan.ct != null ? plan.ct : 0}
                </td>
                <td class="mono uph-cell" title="UPH: ${plan.uph != null ? plan.uph : '-'}">
                    ${plan.uph != null ? plan.uph : '-'}
                </td>
                <td class="mono" title="Cantidad planificada">${planCount.toLocaleString()}</td>
                <td class="mono" title="Producido">${producido.toLocaleString()}</td>
                <td class="mono" title="Falta">${falta.toLocaleString()}</td>
                <td class="mono" title="Porcentaje completado">${porcentaje}%</td>
                <td title="Progreso visual">
                    <div class="progress-bar" style="width: 80px;">
                        <span style="width: ${porcentaje}%"></span>
                    </div>
                </td>
                <td title="Fecha de trabajo">${fechaTrabajo}</td>
                <td title="Estado: ${statusText}${pausedSeconds > 0 ? ' | Tiempo pausado total: ' + pausedSeconds + ' segundos' : ''}">
                    <span class="status-tag ${statusClass}">${statusText}</span>
                </td>
            `;
            
            // Eliminada carga asíncrona: CT y UPH ya vienen en los datos del plan

            // Agregar eventos
            agregarEventosFila(row, plan);
            
            // Agregar clase según estado
            if (plan.status === "RUNNING") {
                row.classList.add("run-active");
            } else if (plan.status === "PAUSED") {
                row.classList.add("run-paused");
            } else if (plan.status === "COMPLETED") {
                row.classList.add("run-completed");
            }
            
            tableBody.appendChild(row);
        });


        
        // No restaurar selección en modo focus
        if (!document.querySelector('.data-table.focus-mode') && selectedRowId) {
            const sel = document.querySelector(`tr[data-plan-id="${selectedRowId}"]`);
            if (sel) sel.classList.add('focused-row');
        }
    }

    /**
     * Agregar eventos a una fila de la tabla
     */
    function agregarEventosFila(row, planData) {
        // Click en la fila para seleccionar
        row.addEventListener("click", function(e) {
            // No seleccionar si se hizo click en el checkbox
            if (e.target.type === "checkbox") {
                return;
            }
            
            seleccionarFila(row, planData);
        });
        
        // Doble click para abrir detalles
        row.addEventListener("dblclick", function() {
            abrirDetallesPlan(planData);
        });
        
        // Hover efectos
        row.addEventListener("mouseenter", function() {
            if (!row.classList.contains("focused-row")) {
                row.style.backgroundColor = "#485563";
            }
        });
        
        row.addEventListener("mouseleave", function() {
            if (!row.classList.contains("focused-row")) {
                row.style.backgroundColor = "";
            }
        });
    }

    /**
     * Seleccionar una fila
     */
    function seleccionarFila(row, planData) {
        // Remover selección anterior
        document.querySelectorAll(".plan-row").forEach(r => {
            r.classList.remove("focused-row");
        });
        
        // Agregar nueva selección
        row.classList.add("focused-row");
        selectedRowId = planData.id;
        

        
        // Disparar evento personalizado
        const evento = new CustomEvent("planSelected", {
            detail: { plan: planData }
        });
        document.dispatchEvent(evento);
        
        // Guardar en localStorage para persistencia
        localStorage.setItem("selectedPlanMainId", planData.id);
    }

    /**
     * Activar modo focus (doble clic en fila)
     */
    function abrirDetallesPlan(planData) {

        activarModoFocus(planData);
    }

    /**
     * Activar modo focus - mostrar solo un plan
     */
    function activarModoFocus(planData) {

        
        // Actualizar campo de número de lote
        const numeroLoteField = document.getElementById("numeroLote-Control de operacion de linea Main");
        if (numeroLoteField) {
            numeroLoteField.value = planData.lote || planData.lot_no || "";
        }
        
        // Guardar estado del modo focus
        localStorage.setItem("modoFocusActivo", "true");
        localStorage.setItem("planFocusData", JSON.stringify(planData));
        
        // Renderizar solo el plan seleccionado
    renderizarTablaPrincipal([planData]);
    const table = document.querySelector('.data-table');
    if (table) table.classList.add('focus-mode');
    // Limpiar selección previa
    selectedRowId = null;
    document.querySelectorAll('.plan-row').forEach(r=>r.classList.remove('focused-row'));
        
    }

    /**
     * Desactivar modo focus - mostrar todos los planes
     */
    function desactivarModoFocus() {

        
        // Limpiar localStorage
        localStorage.removeItem("modoFocusActivo");
        localStorage.removeItem("planFocusData");
        
        // Recargar todos los datos
        const filtros = obtenerFiltrosActuales();
    cargarDatosPlanMain(filtros);
    const table = document.querySelector('.data-table');
    if (table) table.classList.remove('focus-mode');
    // Permitir que se pueda volver a seleccionar
    selectedRowId = null;

    }

    /**
     * Verificar si el modo focus está activo
     */
    function esModoFocusActivo() {
        return localStorage.getItem("modoFocusActivo") === "true";
    }

    /**
     * Actualizar título para mostrar modo focus (DESHABILITADO)
     */
    function actualizarTituloModoFocus(planData) {
        // Función deshabilitada - no mostrar cambios en título

    }

    /**
     * Restaurar título original (DESHABILITADO)
     */
    function restaurarTituloOriginal() {
        // Función deshabilitada - no restaurar título

    }

    // Funciones del botón salir focus eliminadas - se usa botón Consultar

    /**
     * Mostrar/ocultar indicador de carga
     */
    function mostrarIndicadorCarga(mostrar) {
        const tableBody = elements.tableBody || document.getElementById("tbody-plan-data");
        if (!tableBody) return;

        const table = tableBody.closest('table');
        if (table) table.setAttribute('aria-busy', mostrar ? 'true' : 'false');
        if (mostrar) {
            tableBody.innerHTML = `
                <tr class="loading-row">
                    <td colspan="16" style="display: table-cell; text-align:center; padding:28px;">
                        <div style="display:inline-flex; align-items:center; gap:12px;">
                            <div class="plan-loading-spinner" style="width:32px; height:32px; border-width:3px;"></div>
                            <span class="plan-loading-text" style="font-size:13px; letter-spacing:.5px; color:#bcd4e6;">Cargando datos...</span>
                        </div>
                    </td>
                </tr>`;
        }
    }

    /**
     * Actualizar estadísticas
     */
    function actualizarEstadisticas(datos) {
        const stats = calcularEstadisticas(datos);
        
        // Actualizar elementos de estadísticas si existen
        const statsContainer = document.querySelector(".stats-container");
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Total Planes:</span>
                    <span class="stat-value">${stats.total}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">En Progreso:</span>
                    <span class="stat-value">${stats.enProgreso}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Completados:</span>
                    <span class="stat-value">${stats.completados}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Pendientes:</span>
                    <span class="stat-value">${stats.pendientes}</span>
                </div>
            `;
        }
        

    }

    /**
     * Calcular estadísticas de los datos
     */
    function calcularEstadisticas(datos) {
        if (!datos || datos.length === 0) {
            return { total: 0, enProgreso: 0, completados: 0, pendientes: 0 };
        }
        
        return datos.reduce((stats, plan) => {
            stats.total++;
            
            const planCount = parseInt(plan.plan_count) || 0;
            const arrayCount = parseInt(plan.array_count) || 0;
            const xOut = parseInt(plan.x_out) || 0;
            const producido = arrayCount - xOut;
            const porcentaje = planCount > 0 ? (producido / planCount) * 100 : 0;
            
            if (plan.status === "COMPLETED" || porcentaje >= 100) {
                stats.completados++;
            } else if (plan.status === "RUNNING" || porcentaje > 0) {
                stats.enProgreso++;
            } else {
                stats.pendientes++;
            }
            
            return stats;
        }, { total: 0, enProgreso: 0, completados: 0, pendientes: 0 });
    }

    /**
     * Configurar eventos de la interfaz
     */
    function configurarEventos() {

        
        // Verificar si hay modo focus activo al cargar
        verificarModoFocusAlInicio();
        
        // Botón consultar
        const btnConsultar = document.getElementById("btnConsultar-Control de operacion de linea Main");
        if (btnConsultar) {
            btnConsultar.addEventListener("click", async () => {

                // Mostrar loader en el tbody de inmediato mientras consultamos
                mostrarIndicadorCarga(true);
                
                // Limpiar el campo número de lote antes de consultar
                const numeroLoteField = document.getElementById("numeroLote-Control de operacion de linea Main");
                if (numeroLoteField) {

                    numeroLoteField.value = "";
                }
                
                // Si está en modo focus, desactivarlo antes de consultar
                if (esModoFocusActivo()) {

                    desactivarModoFocus();
                } else {

                    // Obtener filtros DESPUÉS de limpiar el campo
                    const filtros = obtenerFiltrosActuales();

                    await cargarDatosPlanMain(filtros);
                }
            });
        }

        // Botón Exportar (tabla principal filtrada)
        const btnExportar = document.getElementById("btnExportarMain-Control de operacion de linea Main");
        if (btnExportar) {
            btnExportar.addEventListener('click', () => {
                try { exportarTablaFiltrada(); } catch (e) { /* Error exporting CSV */ }
            });
        }
        
        // Campo de número de lote con Enter
        const numeroLote = document.getElementById("numeroLote-Control de operacion de linea Main");
        if (numeroLote) {
            numeroLote.addEventListener("keypress", async (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    mostrarIndicadorCarga(true);
                    const filtros = { q: numeroLote.value };
                    await cargarDatosPlanMain(filtros);
                }
            });
        }
        
        // Selector de línea
        const selectorLinea = document.getElementById("linea-Control de operacion de linea Main");
        if (selectorLinea) {
            selectorLinea.addEventListener("change", async () => {
                mostrarIndicadorCarga(true);
                const filtros = obtenerFiltrosActuales();
                await cargarDatosPlanMain(filtros);
            });
        }
        
        // Checkbox "seleccionar todo"
        const checkboxTodos = document.querySelector("th input[type='checkbox']");
        if (checkboxTodos) {
            checkboxTodos.addEventListener("change", function() {
                const checkboxes = document.querySelectorAll("tbody input[type='checkbox']");
                checkboxes.forEach(cb => cb.checked = this.checked);
            });
        }

        // Botones de control de estado
        const btnIniciar = document.getElementById("btnIniciar-Control de operacion de linea Main");
        const btnFin = document.getElementById("btnFin-Control de operacion de linea Main");
        const btnPausa = document.getElementById("btnPausa-Control de operacion de linea Main");
        const loteInput = document.getElementById("numeroLote-Control de operacion de linea Main");

        function crearModalMotivo({titulo, etiqueta, onConfirm}) {
            let overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:9999;font-family:inherit;';
            let modal = document.createElement('div');
            modal.style.cssText = 'background:#1f2a33;padding:18px 20px;border:1px solid #20688C;width:420px;max-width:90%;border-radius:6px;box-shadow:0 4px 18px rgba(0,0,0,.6);';
            modal.innerHTML = `
                <h3 style="margin:0 0 10px;font-size:16px;color:#e0e0e0;letter-spacing:.5px;">${titulo}</h3>
                <label style="display:block;font-size:12px;color:#9bb8c9;margin-bottom:6px;">${etiqueta}</label>
                <textarea id="motivoCampo" style="width:100%;height:90px;resize:vertical;background:#132028;color:#e0e0e0;border:1px solid #2c5364;padding:6px;font-size:12px;border-radius:4px;"></textarea>
                <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px;">
                    <button id="btnCancelarModal" style="background:#444;padding:6px 14px;border:0;color:#ddd;border-radius:4px;cursor:pointer;">Cancelar</button>
                    <button id="btnAceptarModal" style="background:#1d6fa5;padding:6px 16px;border:0;color:#fff;border-radius:4px;font-weight:600;cursor:pointer;">Aceptar</button>
                </div>`;
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            setTimeout(()=>document.getElementById('motivoCampo').focus(),50);
            function cerrar(){ overlay.remove(); }
            document.getElementById('btnCancelarModal').onclick = () => { cerrar(); };
            document.getElementById('btnAceptarModal').onclick = () => {
                const texto = document.getElementById('motivoCampo').value.trim();
                if (!texto) { document.getElementById('motivoCampo').focus(); return; }
                onConfirm(texto, cerrar);
            };
        }

        function setButtonsLoading(action, loading) {
            const ids = {
                'EN PROGRESO': 'btnIniciar-Control de operacion de linea Main',
                'PAUSADO': 'btnPausa-Control de operacion de linea Main',
                'TERMINADO': 'btnFin-Control de operacion de linea Main'
            };
            const texts = {
                'EN PROGRESO': 'Iniciando...',
                'PAUSADO': 'Pausando...',
                'TERMINADO': 'Finalizando...'
            };
            const allIds = [
                'btnIniciar-Control de operacion de linea Main',
                'btnPausa-Control de operacion de linea Main',
                'btnFin-Control de operacion de linea Main'
            ];
            const activeId = ids[action];
            const activeBtn = activeId ? document.getElementById(activeId) : null;
            // Disable/Enable all
            allIds.forEach(id => {
                const b = document.getElementById(id);
                if (!b) return;
                if (loading) {
                    b.disabled = true;
                    b.style.opacity = '0.7';
                    b.style.cursor = 'not-allowed';
                } else {
                    b.disabled = false;
                    b.style.opacity = '';
                    b.style.cursor = '';
                }
            });
            // Set text for active button
            if (activeBtn) {
                if (loading) {
                    if (!activeBtn.dataset.originalText) activeBtn.dataset.originalText = activeBtn.textContent;
                    activeBtn.textContent = texts[action] || 'Procesando...';
                } else {
                    activeBtn.textContent = activeBtn.dataset.originalText || activeBtn.textContent;
                    delete activeBtn.dataset.originalText;
                }
            }
        }

        async function actualizarStatus(nuevo, extraPayload = {}) {
            const lotNo = loteInput?.value?.trim();
            if (!lotNo) { return; }
            try {
                setButtonsLoading(nuevo, true);
                const payload = Object.assign({ lot_no: lotNo, status: nuevo }, extraPayload);
                const resp = await fetch('/api/plan/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();
                if (resp.status === 409) {
                    // Conflicto de línea
                    mostrarError(`Ya hay un plan EN PROGRESO en la línea (${data.line}). (${data.lot_no_en_progreso})`);
                    return;
                }
                if (!resp.ok || !data.success) {
                    // Error actualizando status
                    let mensaje = 'No se pudo actualizar el estado';
                    if (data) {
                        switch (data.error_code) {
                            case 'NOT_FOUND':
                                mensaje = 'El plan no existe (lot_no no encontrado)'; break;
                            case 'LINE_CONFLICT':
                                mensaje = `Ya existe un plan EN PROGRESO en la misma línea (${data.line})`; break;
                            case 'NO_ROWS_UPDATED':
                                mensaje = 'No se modificó ninguna fila (sin cambios o lot_no incorrecto)'; break;
                            case 'UPDATE_EXCEPTION':
                                mensaje = 'Error en la ejecución del UPDATE: ' + (data.error||''); break;
                            case 'UNHANDLED_EXCEPTION':
                                mensaje = 'Error inesperado: ' + (data.error||''); break;
                            default:
                                if (data.error) mensaje = 'STATUS ERROR: ' + data.error;
                        }
                    }
                    mostrarError(mensaje);
                    return;
                }
                const filtros = obtenerFiltrosActuales();
                await cargarDatosPlanMain(filtros);
                const plan = planMainData.find(p => (p.lote||p.lot_no) === lotNo);
                if (plan) activarModoFocus(plan);
            } catch (e) {
                // Excepción actualizando status
            } finally {
                setButtonsLoading(nuevo, false);
            }
        }

        if (btnIniciar) btnIniciar.addEventListener('click', () => actualizarStatus('EN PROGRESO'));
        if (btnPausa) btnPausa.addEventListener('click', () => {
            crearModalMotivo({
                titulo: 'Motivo de Pausa',
                etiqueta: 'Describe la causa de la pausa:',
                onConfirm: (motivo, cerrar) => { cerrar(); actualizarStatus('PAUSADO', { pause_reason: motivo }); }
            });
        });
        if (btnFin) btnFin.addEventListener('click', () => {
            // Determinar si está incompleto para pedir motivo
            const lotNo = loteInput?.value?.trim();
            if (!lotNo) { actualizarStatus('TERMINADO'); return; }
            const plan = planMainData.find(p => (p.lote||p.lot_no) === lotNo);
            const qty = plan ? (parseInt(plan.qty)||parseInt(plan.plan_count)||0) : 0;
            const producido = plan ? (parseInt(plan.producido)||parseInt(plan.produced_count)||0) : 0;
            if (qty > 0 && producido < qty) {
                crearModalMotivo({
                    titulo: 'Motivo de Terminación Incompleta',
                    etiqueta: `Producción incompleta (${producido}/${qty}). Indica motivo:`,
                    onConfirm: (motivo, cerrar) => { cerrar(); actualizarStatus('TERMINADO', { end_reason: motivo }); }
                });
            } else {
                actualizarStatus('TERMINADO');
            }
        });
    }

    function exportarTablaFiltrada() {
        // Usar los datos cargados (filtrados). Si hay focus, exportar todos los filtrados, no solo el de focus
        const datos = Array.isArray(planMainData) ? planMainData.slice() : [];
        if (!datos.length) {
            mostrarInfo('No hay datos para exportar');
            return;
        }
        // Construir filas con las mismas columnas visibles (excepto checkbox y barra gráfica)
        const headers = ['Línea','Lote','NParte','Modelo','Proceso','CT','UPH','Qty','Producido','Falta','%','Fecha Trabajo','Estado'];
        const rows = [headers];
        datos.forEach(plan => {
            const planCount = parseInt(plan.qty) || 0;
            const producido = parseInt(plan.producido || plan.produced_count || 0) || 0;
            const falta = Math.max(0, planCount - producido);
            const porcentaje = planCount>0 ? Math.round((producido/planCount)*100) : 0;
            let rawStatus = (plan.estatus || plan.status || 'PLAN').toUpperCase();
            let statusText = 'PLANEADO';
            if (rawStatus === 'EN PROGRESO' || rawStatus === 'RUNNING') statusText = 'EN PROGRESO';
            else if (rawStatus === 'PAUSADO' || rawStatus === 'PAUSED') statusText = 'PAUSADO';
            else if (rawStatus === 'TERMINADO' || rawStatus === 'FINALIZADO' || porcentaje >= 100) statusText = 'TERMINADO';
            const fechaTrabajo = plan.fecha_inicio || plan.working_date || '';
            rows.push([
                safeCell(plan.linea || plan.line || ''),
                safeCell(plan.lote || plan.lot_no || ''),
                safeCell(plan.nparte || plan.part_no || ''),
                safeCell(plan.modelo || plan.model_code || ''),
                safeCell(plan.process || ''),
                numCell(plan.ct),
                numCell(plan.uph),
                numCell(planCount),
                numCell(producido),
                numCell(falta),
                numCell(porcentaje),
                safeCell(fechaTrabajo),
                safeCell(statusText)
            ]);
        });
        const csv = toCSV(rows);
        const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth()+1).padStart(2,'0');
        const d = String(now.getDate()).padStart(2,'0');
        const hh = String(now.getHours()).padStart(2,'0');
        const mm = String(now.getMinutes()).padStart(2,'0');
        const ss = String(now.getSeconds()).padStart(2,'0');
        a.href = url;
        a.download = `plan_main_export_${y}${m}${d}_${hh}${mm}${ss}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function toCSV(rows) {
        return rows.map(r => r.map(csvEscape).join(',')).join('\r\n');
    }
    function csvEscape(val) {
        if (val === null || val === undefined) return '';
        const s = String(val);
        if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
        return s;
    }
    function safeCell(v) { return v == null ? '' : String(v); }
    function numCell(v) { const n = Number(v); return isFinite(n) ? String(n) : ''; }

    /**
     * Obtener filtros actuales de la interfaz
     */
    function obtenerFiltrosActuales() {
        return {
            q: document.getElementById("numeroLote-Control de operacion de linea Main")?.value || "",
            linea: document.getElementById("linea-Control de operacion de linea Main")?.value || "Todos",
            desde: document.getElementById("fechaDesde-Control de operacion de linea Main")?.value || "",
            hasta: document.getElementById("fechaHasta-Control de operacion de linea Main")?.value || ""
        };
    }

    /**
     * Verificar modo focus al inicio de la aplicación
     */
    function verificarModoFocusAlInicio() {
        if (esModoFocusActivo()) {
            const planDataString = localStorage.getItem("planFocusData");
            if (planDataString) {
                try {
                    const planData = JSON.parse(planDataString);
                    // Restaurando modo focus
                    
                    // Restaurar estado visual
                    actualizarTituloModoFocus(planData);
                    
                    // Actualizar campo de lote
                    const numeroLoteField = document.getElementById("numeroLote-Control de operacion de linea Main");
                    if (numeroLoteField) {
                        numeroLoteField.value = planData.lote || planData.lot_no || "";
                    }
                    
                    // Cargar solo ese plan
                    renderizarTablaPrincipal([planData]);
                    
                } catch (error) {
                    // Error restaurando modo focus
                    desactivarModoFocus();
                }
            } else {
                desactivarModoFocus();
            }
        }
    }

    /**
     * Formatear fecha - Corregido para formato ISO YYYY-MM-DD
     */
    function formatearFecha(fecha) {
        if (!fecha) return "";
        try {
            // Si la fecha viene en formato ISO (2025-09-22)
            let date;
            if (typeof fecha === 'string' && fecha.includes('-')) {
                // Formato ISO: 2025-09-22
                const [year, month, day] = fecha.split('-');
                date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
            } else {
                date = new Date(fecha);
            }
            
            // Verificar que la fecha es válida
            if (isNaN(date.getTime())) {
                return fecha; // Devolver original si no se puede parsear
            }
            
            return date.toLocaleDateString("es-MX", {
                day: "2-digit",
                month: "2-digit", 
                year: "numeric"
            });
        } catch (e) {
            // Error formateando fecha
            return fecha;
        }
    }

    /**
     * Formatear fecha y hora
     */
    function formatearFechaHora(fechaHora) {
        if (!fechaHora) return "";
        try {
            const date = new Date(fechaHora);
            return date.toLocaleString("es-MX", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch (e) {
            return fechaHora;
        }
    }

    // Funciones de utilidad para mensajes
    function mostrarInfo(mensaje) {
        // INFO:
        // Aquí se puede implementar notificaciones visuales
    }

    function mostrarError(mensaje) {
        // ERROR:
        // Aquí se puede implementar notificaciones de error
    }

    function mostrarExito(mensaje) {
        // ÉXITO:
        // Aquí se puede implementar notificaciones de éxito
    }

    /**
     * Inicializar el sistema
     */
    function inicializar() {
        if (isInitialized) {
            // Sistema ya inicializado
            return;
        }

        // Inicializando Plan Main Loader...
        
        // Verificar elementos DOM necesarios
        elements.tableBody = document.getElementById("tbody-plan-data");
        elements.tableContainer = document.querySelector(".main-table-container");
        
        if (!elements.tableBody) {
            // No se encontró el tbody principal
            return;
        }

        isInitialized = true;
        
        // Configurar eventos
        configurarEventos();
        
        // Restaurar selección persistida
        const savedSelectedId = localStorage.getItem("selectedPlanMainId");
        if (savedSelectedId) {
            selectedRowId = savedSelectedId;
        }
        
        // Cargar datos iniciales
        setTimeout(() => {
            // Fijar fechas por defecto a hoy
            try {
                const hoy = new Date();
                const iso = hoy.toISOString().slice(0,10);
                const fDesde = document.getElementById("fechaDesde-Control de operacion de linea Main");
                const fHasta = document.getElementById("fechaHasta-Control de operacion de linea Main");
                if (fDesde && !fDesde.value) fDesde.value = iso;
                if (fHasta && !fHasta.value) fHasta.value = iso;
            } catch {}
            const filtrosIniciales = obtenerFiltrosActuales();
            cargarDatosPlanMain(filtrosIniciales);
        }, 500);
        iniciarAutoRefresh();
        
        // Plan Main Loader inicializado correctamente
    }

    /**
     * Funciones públicas
     */
    window.planMainLoader = {
        cargarDatos: cargarDatosPlanMain,
        obtenerDatos: () => planMainData,
        obtenerSeleccionado: () => {
            if (selectedRowId) {
                return planMainData.find(p => p.id == selectedRowId);
            }
            return null;
        },
        refrescar: () => {
            const filtros = obtenerFiltrosActuales();
            return cargarDatosPlanMain(filtros);
        },
        limpiarSeleccion: () => {
            selectedRowId = null;
            localStorage.removeItem("selectedPlanMainId");
            document.querySelectorAll(".plan-row").forEach(r => {
                r.classList.remove("focused-row");
            });
        },
    // producir deshabilitado (stub)
    producir: actualizarProducido,
        iniciarAutoRefresh,
        detenerAutoRefresh
    };

    // Agregar estilos CSS dinámicos para animaciones
    const style = document.createElement("style");
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    .plan-loading-spinner { width:40px; height:40px; border:4px solid #3498db; border-top:4px solid transparent; border-radius:50%; animation: spin 0.9s linear infinite; }
    .plan-loading-text { letter-spacing:0.5px; font-weight:500; color:#bcd4e6; }
        /* Asegurar que filas especiales no queden ocultas por reglas de ocultar columnas 1 y 2 */
        .data-table tr.loading-row td,
        .data-table tr.message-row td,
        .data-table tr.empty-row td { display: table-cell !important; }
        .data-table tr.loading-row td { padding: 28px !important; text-align: center; }
        
        .plan-row {
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .stats-container {
            display: flex;
            gap: 20px;
            padding: 10px;
            background: #34334E;
            border: 1px solid #20688C;
            margin-bottom: 10px;
        }
        
        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }
        
        .stat-label {
            font-size: 11px;
            color: #95A5A6;
        }
        
        .stat-value {
            font-size: 14px;
            font-weight: bold;
            color: #E0E0E0;
        }
    `;
    document.head.appendChild(style);

    // Auto-inicialización
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", inicializar);
    } else {
        setTimeout(inicializar, 100);
    }

    // Observer para detectar cambios en el DOM
    if (typeof MutationObserver !== "undefined") {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === 1 && 
                            (node.id === "tbody-plan-data" || node.querySelector("#tbody-plan-data"))) {
                            if (!isInitialized) {
                                setTimeout(inicializar, 100);
                            }
                        }
                    }
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Exposición global de funciones
    window.PlanMainLoader = {
        cargarDatos: cargarDatosPlanMain,
        activarModoFocus: activarModoFocus,
        desactivarModoFocus: desactivarModoFocus,
        esModoFocusActivo: esModoFocusActivo,
        obtenerPlanSeleccionado: () => {
            if (esModoFocusActivo()) {
                const planDataString = localStorage.getItem("planFocusData");
                return planDataString ? JSON.parse(planDataString) : null;
            }
            return null;
        }
    };

    // Plan Main Loader cargado exitosamente

})();