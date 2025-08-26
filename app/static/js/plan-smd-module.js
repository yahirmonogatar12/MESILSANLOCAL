/**
 * Plan SMD Module
 * Módulo JavaScript encapsulado para manejo del Plan SMD
 * Evita conflictos de variables globales usando IIFE
 */
(function() {
    'use strict';
    
    // ===============================
    // ENDPOINTS (privados al módulo)
    // ===============================
    const PLAN_SMD_API = {
        workOrders: "/api/work-orders", // GET: q, estado, desde, hasta
        inventarioPorModelo: (modelo) => `/api/inventario/modelo/${encodeURIComponent(modelo)}` , // GET
        guardarPlan: "/api/plan-smd" // POST [{...renglón...}]
    };

    // ===============================
    // STATE & HELPERS (privados)
    // ===============================
    const $ = (id) => document.getElementById(id);
    let queue = [];     // WO seleccionadas para plan
    let plan = [];      // renglones del plan generado

    const fmtDate = (s) => {
        if (!s) return "—";
        try {
            const d = new Date(s);
            if (Number.isNaN(d.getTime())) return s;
            const pad = (n) => String(n).padStart(2, "0");
            return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
        } catch { return s; }
    };
    
    const num = (v) => typeof v === 'number' ? v : (v ? Number(v) : 0);

    const showLoading = (msg = "Procesando…") => { 
        $("smdLoadingText").textContent = msg; 
        $("smdLoadingModal").style.display = "flex"; 
    };
    
    const hideLoading = () => { 
        $("smdLoadingModal").style.display = "none"; 
    };
    
    const alertMsg = (m) => { 
        $("smdAlertMsg").textContent = m; 
        $("smdAlertModal").style.display = "flex"; 
    };

    async function fetchJSON(url) {
        const res = await fetch(url, { headers: { "Accept": "application/json" } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    // ===============================
    // WORK ORDERS – carga y render
    // ===============================
    function renderWorkOrders(rows) {
        const tbody = $("smdWoTbody");
        tbody.innerHTML = "";
        if (!rows || rows.length === 0) {
            tbody.innerHTML = `<tr><td class="smd-no-data" colspan="8">Sin resultados</td></tr>`;
            $("smdWoCounter").textContent = `0 resultados`;
            return;
        }
        $("smdWoCounter").textContent = `${rows.length} resultado${rows.length!==1? 's':''}`;

        for (const r of rows) {
            const tr = document.createElement("tr");
            tr.dataset.woId = r.id;
            tr.innerHTML = `
                <td><button class="smd-btn" type="button" aria-label="Agregar a cola">➕</button></td>
                <td>${r.codigo_wo||'—'}</td>
                <td>${r.codigo_po||'—'}</td>
                <td>${(r.nombre_modelo? r.nombre_modelo+" · ":"")+(r.modelo||'')}</td>
                <td>${r.codigo_modelo||'—'}</td>
                <td>${num(r.cantidad_planeada||0).toLocaleString()}</td>
                <td>${fmtDate(r.fecha_operacion)}</td>
                <td><span class="smd-badge ${r.estado||''}">${r.estado||'—'}</span></td>
            `;
            tr.querySelector("button").addEventListener("click", () => addToQueue(r));
            tbody.appendChild(tr);
        }
    }

    async function loadWorkOrders() {
        const q = encodeURIComponent($("smdQuery").value.trim());
        const estado = $("smdEstado").value;
        const desde = $("smdFechaDesde").value;
        const hasta = $("smdFechaHasta").value;

        const params = new URLSearchParams();
        if (q) params.set("q", q);
        
        // Manejar filtro de estado
        if (estado === "TODOS") {
            // No agregar filtro de estado para mostrar todos
            params.set("incluir_planificadas", "true");
        } else if (estado) {
            // Filtrar por estado específico
            params.set("estado", estado);
        } else {
            // Por defecto, solo mostrar WO con estado CREADA
            params.set("estado", "CREADA");
        }
        
        if (desde) params.set("desde", desde);
        if (hasta) params.set("hasta", hasta);

        showLoading("Consultando WO…");
        try {
            const url = `${PLAN_SMD_API.workOrders}?${params.toString()}`;
            const data = await fetchJSON(url);
            renderWorkOrders(Array.isArray(data) ? data : (data.rows||[]));
        } catch (e) { 
            console.error(e); 
            alertMsg("No fue posible cargar las WO."); 
        }
        finally { hideLoading(); }
    }

    // ===============================
    // COLA de pendientes
    // ===============================
    function addToQueue(wo) {
        if (queue.find(x => x.id === wo.id)) { 
            alertMsg("Esta WO ya está en la cola."); 
            return; 
        }
        queue.push(wo);
        renderQueue();
    }
    
    function removeFromQueue(id) {
        queue = queue.filter(x => x.id !== id);
        renderQueue();
    }
    
    function renderQueue() {
        const tbody = $("smdQueueTbody");
        tbody.innerHTML = "";
        if (!queue.length) {
            tbody.innerHTML = `<tr><td class="smd-no-data" colspan="6">Agrega WO con el botón ➕ de la tabla superior.</td></tr>`;
        }
        queue.forEach(wo => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><button class="smd-btn warn" type="button">✖</button></td>
                <td>${wo.codigo_wo||'—'}</td>
                <td>${(wo.nombre_modelo? wo.nombre_modelo+" · ":"")+(wo.modelo||'')}</td>
                <td>${wo.codigo_modelo||'—'}</td>
                <td>${num(wo.cantidad_planeada||0)}</td>
                <td>${fmtDate(wo.fecha_operacion)}</td>
            `;
            tr.querySelector("button").addEventListener("click", () => removeFromQueue(wo.id));
            tbody.appendChild(tr);
        });
        $("smdQueueCounter").textContent = `${queue.length} WO en cola`;
    }

    // ===============================
    // GENERADOR DE PLAN
    // ===============================
    function newLote(prefix = "L") {
        // NOTA: Esta función ahora se usa como fallback si no hay código WO
        // El campo 'lote' ahora contiene el código WO para trazabilidad
        const d = new Date();
        const pad = (n) => String(n).padStart(2,'0');
        const base = `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}`;
        newLote.seq = (newLote.seq||0)+1;
        return `${prefix}${base}-${String(newLote.seq).padStart(3,'0')}`;
    }

    function planRowFrom(wo, invRow) {
        const qty = num(wo.cantidad);
        const fisico = num(invRow.stock_total);
        const diferencia = 0;
        const falta = Math.max(0, qty - (fisico + diferencia));
        const pct = qty ? Math.min(100, Math.round((Math.min(qty, fisico + diferencia) / qty) * 100)) : 0;
        
        return {
            linea: 'SMT A',
            lote: wo.codigo_wo || wo.wo || newLote('P'), // Usar código WO para trazabilidad
            nparte: invRow.nparte || '',
            modelo: wo.modelo || invRow.descripcion || '',
            tipo: 'Main',
            turno: 'DIA',
            ct: wo.ct || '',
            uph: wo.uph || '',
            qty,
            fisico,
            diferencia,
            falta,
            pct: pct,
            comentarios: ''
        };
    }

    function planRowFromFaltante(wo, faltante, totalFisico) {
        const qty = num(faltante);
        const fisico = num(totalFisico || 0);
        const diferencia = 0;
        return {
            linea: 'SMT A',
            lote: wo.codigo_wo || newLote('P'), // Usar código WO para trazabilidad
            nparte: wo.codigo_modelo || wo.modelo || '-',
            modelo: wo.modelo || '-',
            tipo: 'Main',
            turno: 'DIA',
            ct: '',
            uph: '',
            qty,
            fisico,
            falta: qty,
            diferencia,
            pct: qty ? 0 : 100,
            comentarios: 'Generado por faltantes'
        };
    }

    function computeShortage(wo, invRows) {
        const planQty = num(wo.cantidad_planeada || 0);
        const totalFisico = (invRows||[]).reduce((acc, r) => acc + num(r.stock_total||0), 0);
        const faltante = Math.max(0, planQty - totalFisico);
        return { planQty, totalFisico, faltante };
    }

    function renderPlan() {
        const tbody = $("smdPlanTbody");
        tbody.innerHTML = "";
        if (!plan.length) {
            tbody.innerHTML = `<tr><td class="smd-no-data" colspan="14">Genera el plan desde la lista de pendientes (izquierda).</td></tr>`;
        }

        let totalQty = 0, totalFalta = 0;
        plan.forEach((r, idx) => {
            totalQty += num(r.qty); totalFalta += num(r.falta);
            const tr = document.createElement('tr');
            const diferencia = num(r.diferencia || 0);
            const diferenciaValue = diferencia === 0 ? '' : diferencia;
            const diferenciaStyle = diferencia > 0 ? 'color: #27ae60; font-weight: bold;' : (diferencia < 0 ? 'color: #e74c3c; font-weight: bold;' : '');
            
            tr.innerHTML = `
                <td>
                    <select class="smd-inline-select" data-field="linea" data-idx="${idx}">
                        <option>SMT A</option><option>SMT B</option><option>SMT C</option><option>SMT D</option>
                    </select>
                </td>
                <td><input class="smd-inline-input" data-field="lote" data-idx="${idx}" value="${r.lote}"></td>
                <td>${r.nparte}</td>
                <td>${r.modelo}</td>
                <td>
                    <select class="smd-inline-select" data-field="tipo" data-idx="${idx}">
                        <option ${r.tipo==='Main'?'selected':''}>Main</option>
                        <option ${r.tipo==='Display'?'selected':''}>Display</option>
                    </select>
                </td>
                <td>
                    <select class="smd-inline-select" data-field="turno" data-idx="${idx}">
                        <option ${r.turno==='DIA'?'selected':''}>DIA</option>
                        <option ${r.turno==='NOCHE'?'selected':''}>NOCHE</option>
                    </select>
                </td>
                <td><input class="smd-inline-input" data-field="ct" data-idx="${idx}" value="${r.ct}"></td>
                <td><input class="smd-inline-input" data-field="uph" data-idx="${idx}" value="${r.uph}"></td>
                <td><input class="smd-inline-input" data-field="qty" data-idx="${idx}" value="${r.qty}"></td>
                <td>${r.fisico.toLocaleString()}</td>
                <td><input class="smd-inline-input" data-field="diferencia" data-idx="${idx}" value="${diferenciaValue}" style="${diferenciaStyle}" placeholder="±0"></td>
                <td data-field="falta" data-idx="${idx}">${r.falta.toLocaleString()}</td>
                <td data-field="pct" data-idx="${idx}">${r.pct}%</td>
                <td><input class="smd-inline-input smd-inline-wide" data-field="comentarios" data-idx="${idx}" value="${r.comentarios}"></td>
            `;
            tbody.appendChild(tr);
        });

        $("smdPlanCounter").textContent = `${plan.length} renglone${plan.length===1?'':'s'}`;
        $("smdChipPlanes").textContent = `WO en plan: ${queue.length}`;
        $("smdChipTotalQty").textContent = `Qty total a producir: ${totalQty.toLocaleString()}`;
        $("smdChipTotalFaltante").textContent = `Faltante total: ${totalFalta.toLocaleString()}`;

        // listeners inline
        tbody.querySelectorAll('input, select').forEach(el => {
            el.addEventListener('change', onPlanCellChange);
        });
        
        // Recalcular automáticamente todos los valores después de renderizar
        recalculateAllRows();
    }

    function recalculateAllRows() {
        plan.forEach((row, idx) => {
            const qty = num(row.qty);
            const fisico = num(row.fisico);
            const diferencia = num(row.diferencia) || 0;
            const fisicoAjustado = fisico + diferencia;
            plan[idx].falta = Math.max(0, qty - fisicoAjustado);
            plan[idx].pct = qty ? Math.min(100, Math.round((Math.min(qty, fisicoAjustado)/qty)*100)) : 0;
        });
        updateDisplayValues();
    }
    
    function updateDisplayValues() {
        plan.forEach((row, idx) => {
            const faltaCell = document.querySelector(`[data-idx="${idx}"][data-field="falta"]`);
            const pctCell = document.querySelector(`[data-idx="${idx}"][data-field="pct"]`);
            if (faltaCell) faltaCell.textContent = row.falta.toLocaleString();
            if (pctCell) pctCell.textContent = `${row.pct}%`;
        });
        
        // Actualizar totales
        let totalQty = 0, totalFalta = 0;
        plan.forEach(r => {
            totalQty += num(r.qty);
            totalFalta += num(r.falta);
        });
        $("smdChipTotalQty").textContent = `Qty total a producir: ${totalQty.toLocaleString()}`;
        $("smdChipTotalFaltante").textContent = `Faltante total: ${totalFalta.toLocaleString()}`;
    }

    function onPlanCellChange(ev) {
        const el = ev.currentTarget; 
        const idx = Number(el.dataset.idx); 
        const field = el.dataset.field; 
        if (Number.isNaN(idx) || !field) return;
        
        const val = (el.tagName === 'SELECT') ? el.value : (el.type === 'number' ? Number(el.value) : el.value);
        plan[idx][field] = (field==='qty' || field==='diferencia') ? num(val) : val;
        
        if (field==='qty' || field==='diferencia') { 
            const qty = num(plan[idx].qty), fisico = num(plan[idx].fisico), diferencia = num(plan[idx].diferencia) || 0;
            const fisicoAjustado = fisico + diferencia;
            plan[idx].falta = Math.max(0, qty - fisicoAjustado);
            plan[idx].pct = qty ? Math.min(100, Math.round((Math.min(qty, fisicoAjustado)/qty)*100)) : 0;
            updateDisplayValues();
        } else {
            renderPlan();
        }
    }

    async function generatePlanFromQueue() {
        if (!queue.length) { 
            alertMsg('Agrega WO a la cola primero.'); 
            return; 
        }
        showLoading('Generando plan con inventario…');
        try {
            const rows = [];
            const onlyShortage = document.getElementById('smdOnlyShortage').checked;
            for (const wo of queue) {
                const inv = await fetchJSON(PLAN_SMD_API.inventarioPorModelo(wo.codigo_modelo||wo.modelo||''));
                const invRows = Array.isArray(inv) ? inv : (inv.rows||[]);

                if (onlyShortage) {
                    const { faltante, totalFisico } = computeShortage(wo, invRows);
                    if (faltante > 0) rows.push(planRowFromFaltante(wo, faltante, totalFisico));
                } else {
                    if (!invRows.length) {
                        rows.push(planRowFrom(wo, { nparte: wo.codigo_modelo || (wo.modelo||'') , stock_total: 0 }));
                    } else {
                        invRows.forEach(ir => rows.push(planRowFrom(wo, ir)));
                    }
                }
            }
            plan = rows;
            renderPlan();
        } catch (e) { 
            console.error(e); 
            alertMsg('No fue posible generar el plan.'); 
        }
        finally { hideLoading(); }
    }

    // ===============================
    // CSV & PERSISTENCIA
    // ===============================
    function toCSVCell(value) {
        const s = String(value ?? '');
        const needsQuotes = /[",\n\r]/.test(s);
        const escaped = s.replace(/"/g, '""');
        return needsQuotes ? `"${escaped}"` : escaped;
    }

    function planToCSV() {
        if (!plan.length) { 
            alertMsg('No hay renglones para exportar.'); 
            return; 
        }
        const headers = ["linea","wo","nparte","modelo","tipo","turno","ct","uph","qty","fisico","falta","diferencia","pct","comentarios"];
        const fieldMap = {"wo": "lote"}; // Mapear 'wo' a 'lote' en el objeto
        const lines = [headers.join(',')];
        plan.forEach(r => {
            const row = headers.map(h => toCSVCell(r[fieldMap[h] || h]));
            lines.push(row.join(','));
        });
        const blob = new Blob([lines.join('\r\n')], {type:'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); 
        a.href = url; 
        a.download = 'plan_smd.csv'; 
        a.click(); 
        URL.revokeObjectURL(url);
    }

    async function savePlan() {
        if (!plan.length) { 
            alertMsg('No hay renglones para guardar.'); 
            return; 
        }
        showLoading('Guardando plan…');
        try {
            // Guardar el plan
            const res = await fetch(PLAN_SMD_API.guardarPlan, { 
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body: JSON.stringify(plan)
            });
            if (!res.ok) throw new Error('HTTP '+res.status);
            
            // Obtener códigos de WO únicos del plan
            const codigosWO = [...new Set(plan.map(r => r.lote).filter(lote => lote && lote.trim()))];
            
            // Actualizar estado de cada WO a 'PLANIFICADA'
            showLoading('Actualizando estado de WO…');
            const updatePromises = codigosWO.map(async (codigoWO) => {
                try {
                    const updateRes = await fetch(`/api/wo/${encodeURIComponent(codigoWO)}/estado`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            estado: 'PLANIFICADA',
                            modificador: window.usuarioLogueado || 'Sistema'
                        })
                    });
                    if (!updateRes.ok) {
                        console.warn(`Error actualizando WO ${codigoWO}: HTTP ${updateRes.status}`);
                    } else {
                        console.log(`✅ WO ${codigoWO} actualizada a PLANIFICADA`);
                    }
                } catch (err) {
                    console.warn(`Error actualizando WO ${codigoWO}:`, err);
                }
            });
            
            // Esperar a que todas las actualizaciones terminen
            await Promise.allSettled(updatePromises);
            
            alertMsg(`Plan guardado correctamente. ${codigosWO.length} WO(s) actualizadas a estado PLANIFICADA.`);
        } catch (e) { 
            console.error(e); 
            alertMsg('Error guardando el plan.'); 
        }
        finally { hideLoading(); }
    }

    // ===============================
    // CONFIGURACIÓN DE EVENTOS
    // ===============================
    function setupEventListeners() {
        // Event listeners para botones principales
        $("smdBtnConsultar").addEventListener("click", loadWorkOrders);
        $("smdBtnLimpiar").addEventListener("click", () => {
            $("smdQuery").value = ""; 
            $("smdEstado").value = ""; 
            $("smdFechaDesde").value = ""; 
            $("smdFechaHasta").value = "";
            $("smdWoTbody").innerHTML = `<tr><td class="smd-no-data" colspan="8">Usa los filtros y pulsa <b>Consultar WO</b>.</td></tr>`;
            $("smdWoCounter").textContent = `0 resultados`;
            queue = []; 
            renderQueue(); 
            plan = []; 
            renderPlan();
        });
        
        $("smdQuery").addEventListener("keydown", (ev) => { 
            if (ev.key === "Enter") loadWorkOrders(); 
        });
        
        $("smdBtnGenerarPlan").addEventListener("click", generatePlanFromQueue);
        $("smdBtnExportarCSV").addEventListener("click", planToCSV);
        $("smdBtnGuardarPlan").addEventListener("click", savePlan);
        
        // Event listener para cerrar alertas
        $("smdAlertOk").addEventListener("click", () => {
            $("smdAlertModal").style.display = "none";
        });
        
        console.log('✅ Event listeners del Plan SMD configurados');
    }

    // ===============================
    // FUNCIÓN DE INICIALIZACIÓN PRINCIPAL
    // ===============================
    function initPlanSMD() {
        console.log('🚀 Inicializando Plan SMD Module...');
        
        try {
            // Verificar que todos los elementos necesarios existen
            const requiredElements = [
                'smdQuery', 'smdEstado', 'smdFechaDesde', 'smdFechaHasta',
                'smdBtnConsultar', 'smdBtnLimpiar', 'smdBtnGenerarPlan',
                'smdBtnExportarCSV', 'smdBtnGuardarPlan', 'smdAlertOk',
                'smdWoTbody', 'smdQueueTbody', 'smdPlanTbody'
            ];
            
            for (const elementId of requiredElements) {
                if (!$(elementId)) {
                    console.error(`❌ Elemento requerido no encontrado: ${elementId}`);
                    return false;
                }
            }
            
            // Configurar todos los event listeners
            setupEventListeners();
            
            // Inicializar estado
            queue = [];
            plan = [];
            renderQueue();
            renderPlan();
            
            console.log('✅ Plan SMD Module inicializado correctamente');
            return true;
            
        } catch (error) {
            console.error('❌ Error inicializando Plan SMD Module:', error);
            return false;
        }
    }

    // ===============================
    // TESTS UNITARIOS
    // ===============================
    function runUnitTests(){
        console.log('🧪 Ejecutando tests unitarios...');
        const results = [];
        
        function expect(name, cond){ 
            if(!cond){ 
                console.error('❌', name); 
                results.push(false);
            } else { 
                console.log('✅', name);
            } 
        }

        // toCSVCell tests
        expect('CSV: sin comillas', toCSVCell('ABC') === 'ABC');
        expect('CSV: duplica comillas', toCSVCell('A"B') === '"A""B"');
        expect('CSV: envuelve con coma', toCSVCell('A,B') === '"A,B"');

        // newLote formato tests
        const l1 = newLote('T'); 
        const l2 = newLote('T');
        expect('Lote prefijo', l1.startsWith('T'));
        expect('Lote secuencia', l1 !== l2);

        // planRowFrom cálculo tests
        const wo = {cantidad_planeada: 100, modelo:'M1', codigo_modelo:'C1'};
        const inv = {nparte:'N1', stock_total: 60};
        const pr = planRowFrom(wo, inv);
        expect('planRowFrom.qty', pr.qty === 100);
        expect('planRowFrom.fisico', pr.fisico === 60);
        expect('planRowFrom.falta', pr.falta === 40);
        expect('planRowFrom.diferencia', pr.diferencia === 0);
        expect('planRowFrom.pct', pr.pct === 60);

        // planRowFromFaltante tests
        const prF = planRowFromFaltante(wo, 40, 60);
        expect('planRowFromFaltante.qty=faltante', 
            prF.qty === 40 && prF.falta === 40 && prF.fisico === 60 && 
            prF.diferencia === 0 && prF.pct === 0);

        // computeShortage tests
        const wo9301 = { cantidad_planeada: 800, modelo: '9301', codigo_modelo: '9301' };
        const inv9301 = [{ nparte: '9301-A', stock_total: 120 }, { nparte: '9301-B', stock_total: 80 }];
        const cs1 = computeShortage(wo9301, inv9301);
        expect('computeShortage 9301 => 600', cs1.faltante === 600);

        const cs2 = computeShortage({ cantidad_planeada: 100, modelo: 'X' }, [{stock_total: 50},{stock_total:60}]);
        expect('computeShortage sin faltante', cs2.faltante === 0);

        if(results.includes(false)){ 
            console.warn('⚠️ Algunas pruebas fallaron'); 
        } else {
            console.log('🎉 Todos los tests pasaron correctamente');
        }
        
        return !results.includes(false);
    }

    // ===============================
    // LIMPIEZA AL DESCARGAR PÁGINA
    // ===============================
    function cleanup() {
        console.log('🧹 Limpiando Plan SMD Module...');
        queue = [];
        plan = [];
        // Limpiar cualquier timer o listener que pueda quedar
    }

    // Event listener para limpieza
    window.addEventListener('beforeunload', cleanup);

    // ===============================
    // EXPORTACIONES GLOBALES
    // ===============================
    // Solo exportar las funciones que necesitan ser accesibles desde fuera
    window.initPlanSMD = initPlanSMD;
    window.planSMDModule = {
        init: initPlanSMD,
        runTests: runUnitTests,
        cleanup: cleanup
    };

    // ===============================
    // AUTO-INICIALIZACIÓN
    // ===============================
    // Si el DOM ya está listo, inicializar inmediatamente
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPlanSMD);
    } else {
        // DOM ya está listo, inicializar en el próximo tick
        setTimeout(initPlanSMD, 0);
    }

    console.log('📦 Plan SMD Module cargado y listo para inicializar');

})(); // Fin del IIFE
