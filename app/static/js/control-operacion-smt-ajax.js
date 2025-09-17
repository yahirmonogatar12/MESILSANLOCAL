// Control de Operación Línea SMT - Integración con Plan SMD
(function() {
  console.log('Inicializando Control de Operacion Linea SMT AJAX...');
  
  // Variables globales
  let currentPlanData = [];
  let filteredPlanData = [];
  let selectedPlanId = null;
  let currentRunId = null;
  let isFiltered = false; // Nueva variable para controlar el estado de filtro
  let autoRefreshInterval = null;
  let isInitialized = false;
  // Datos cacheados para matching BOM <-> Historial
  let lastHistoryDataNorm = [];
  let historyMatchKeys = new Set();
  let lastBomData = [];
  let lastBomTableBody = null;
  let maskCheckOk = false;

  function parseSlotNumber(v){
    try{
      if (v === null || typeof v === 'undefined') return null;
      const s = String(v).trim();
      if (!s) return null;
      const m = s.match(/\d+/);
      return m ? Number(m[0]) : null;
    }catch(_){ return null; }
  }

  function normalizeCode(v){
    return String(v || '').trim().toUpperCase();
  }

  function parseMounterNumber(v){
    try{
      const s = String(v ?? '').trim();
      if (!s) return null;
      const m = s.match(/\d+/);
      return m ? Number(m[0]) : null;
    }catch(_){ return null; }
  }

  function parseMounterFromEquipment(equipment){
    try{
      const s = String(equipment ?? '');
      const m = s.match(/m\s*(\d+)/i);
      return m ? Number(m[1]) : null;
    }catch(_){ return null; }
  }

  function parseSideFromBaseFeeder(v){
    try{
      const s = String(v ?? '').toUpperCase();
      if (!s) return null;
      if (s.includes('F')) return 'FRONT';
      if (s.includes('R')) return 'REAR';
      return null;
    }catch(_){ return null; }
  }

  function makeKey(slot, code, mounter, side){
    const sn = parseSlotNumber(slot);
    const cn = normalizeCode(code);
    const mn = parseMounterNumber(mounter);
    const sd = side ? String(side).toUpperCase() : '';
    return sn !== null && cn && mn !== null && sd ? `${sn}|${cn}|${mn}|${sd}` : '';
  }

  function rebuildHistoryMatchIndex(){
    historyMatchKeys = new Set();
    lastHistoryDataNorm.forEach(it => {
      const key = makeKey(it.slot, it.part, it.mounter, it.side);
      if (key) historyMatchKeys.add(key);
    });
  }
      
      // Elementos del DOM
      const elements = {
        tableBody: null,
        placeholder: null,
        dateFrom: null,
        dateTo: null,
        selLine: null,
        btnSearch: null
      };
      
      // FunciÃ³n para obtener elementos del DOM
      function getElements() {
        elements.tableBody = document.getElementById('tbody-plan-data');
        elements.placeholder = document.getElementById('plan-placeholder');
        elements.dateFrom = document.getElementById('dateFrom');
        elements.dateTo = document.getElementById('dateTo');
        elements.selLine = document.getElementById('selLine');
        elements.btnSearch = document.getElementById('btn-search');
        elements.chkShowPlanned = document.getElementById('chk-show-planned');
        
        return elements.tableBody && elements.placeholder;
      }
      
      // Función para mostrar notificaciones toast sutiles
      function showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        // Crear el elemento toast
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Iconos por tipo - estilo más técnico/industrial
        const icons = {
          success: '✓',
          error: '✗', 
          warning: '⚠',
          info: '●'
        };
        
        // Títulos por tipo - más técnicos
        const titles = {
          success: 'OPERACIÓN EXITOSA',
          error: 'ERROR DE SISTEMA',
          warning: 'ADVERTENCIA DEL SISTEMA', 
          info: 'INFORMACIÓN DEL SISTEMA'
        };

        toast.innerHTML = `
          <div class="toast-header">
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span>${titles[type] || titles.info}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
          </div>
          <div class="toast-body">${message}</div>
        `;

        // Agregar al contenedor
        container.appendChild(toast);

        // Mostrar con animación
        setTimeout(() => {
          toast.classList.add('show');
        }, 100);

        // Auto-remover después del tiempo especificado
        setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => {
            if (toast.parentElement) {
              toast.remove();
            }
          }, 300);
        }, duration);

        return toast;
      }

      // Función para mostrar alertas de éxito
      function showSuccess(message, duration = 3000) {
        return showToast(message, 'success', duration);
      }

      // Función para mostrar alertas de error  
      function showError(message, duration = 5000) {
        return showToast(message, 'error', duration);
      }

      // Función para mostrar alertas de advertencia
      function showWarning(message, duration = 4000) {
        return showToast(message, 'warning', duration);
      }

      // Función para mostrar alertas de información
      function showInfo(message, duration = 3000) {
        return showToast(message, 'info', duration);
      }

      // Función de recarga rápida para después de operaciones START/END
      async function recargaRapida() {
        try {
          // Solo recargar si es necesario mantener la vista actualizada
          if (isFiltered && selectedPlanId) {
            // En modo focus, consultar solo el plan específico
            const response = await fetch(`/api/plan-smd/list?plan_id=${selectedPlanId}`);
            if (response.ok) {
              const data = await response.json();
              if (data.success && data.rows && data.rows.length > 0) {
                const planActualizado = data.rows[0];
                filteredPlanData = [planActualizado];
                renderPlanData(filteredPlanData);
                aplicarSeleccionPersistida();
              }
            }
          }
          // Si no está en modo focus, no recargar automáticamente para mantener velocidad
        } catch (error) {
          console.warn('Error en recarga rapida:', error);
          // En caso de error, hacer recarga completa
          setTimeout(() => cargarDatosPlanSMD(), 500);
        }
      }

      // FunciÃ³n para cargar datos del plan SMD
      async function cargarDatosPlanSMD() {
        if (!getElements()) {
          console.warn('Elementos no encontrados, reintentando...');
          setTimeout(cargarDatosPlanSMD, 1000);
          return;
        }
        
        try {
          // Filtros de búsqueda
          const params = new URLSearchParams();
          const lotEl = document.getElementById('lotNo');
          if (lotEl && lotEl.value) params.set('q', lotEl.value.trim());
          if (elements.selLine && elements.selLine.value && elements.selLine.value !== 'ALL') { 
            params.set('linea', elements.selLine.value); 
          }
          
          // Lógica para mostrar pendientes: ignorar fechas y solo mostrar PLANEADOS
          if (elements.chkShowPlanned && elements.chkShowPlanned.checked) {
            params.set('solo_pendientes', 'true');
          } else {
            // Solo aplicar filtros de fecha si NO está marcado "Mostrar Pendientes"
            if (elements.dateFrom && elements.dateFrom.value) params.set('desde', elements.dateFrom.value);
            if (elements.dateTo && elements.dateTo.value) params.set('hasta', elements.dateTo.value);
          }

        const url = `/api/plan-smd/list?${params}`;
        
        elements.placeholder.textContent = 'Loading data...';
        elements.placeholder.style.display = 'grid';
        
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const rows = Array.isArray(data) ? data : (data.rows || []);
        currentPlanData = rows;
        
        // Datos recibidos: ${rows.length} planes
        
        // Verificar si hay búsqueda por LOT NO para activar modo focus automáticamente
        const lotNoInput = document.getElementById('lotNo');
        const lotNoValue = lotNoInput && lotNoInput.value ? lotNoInput.value.trim() : '';
        
        if (rows.length > 0) { 
          elements.placeholder.style.display = 'none'; 
          
          // Si hay búsqueda por LOT NO y encontramos resultados, activar modo focus automáticamente
          if (lotNoValue && rows.length > 0) {
            // Buscar el plan que coincida con el LOT NO
            const planPorLote = rows.find(p => p.lote && p.lote.toLowerCase().includes(lotNoValue.toLowerCase()));
            if (planPorLote) {
              selectedPlanId = planPorLote.id;
              localStorage.setItem('smtSelectedPlanId', String(selectedPlanId));
              isFiltered = true;
              filteredPlanData = [planPorLote];
              renderPlanData(filteredPlanData);
              aplicarSeleccionPersistida();
              return; // Salir aquí porque ya renderizamos en modo focus
            }
          }
        } else { 
          elements.placeholder.textContent = 'No hay planes con esos filtros'; 
          elements.placeholder.style.display = 'grid'; 
        }
        
        // Si estamos en modo enfoque, mantener el filtro activo sin renderizar todos primero
        if (isFiltered && selectedPlanId) {
          let planSeleccionado = rows.find(p => p.id === selectedPlanId);
          
          // Si el plan no está en los datos filtrados, hacer una consulta específica para obtenerlo
          if (!planSeleccionado) {
            try {
              const planResponse = await fetch(`/api/plan-smd/list?plan_id=${selectedPlanId}`);
              if (planResponse.ok) {
                const planData = await planResponse.json();
                if (planData.success && planData.rows && planData.rows.length > 0) {
                  planSeleccionado = planData.rows[0];
                }
              }
            } catch (error) {
              console.error('❌ Error consultando plan específico:', error);
            }
          }
          
          if (planSeleccionado) {
            filteredPlanData = [planSeleccionado];
            renderPlanData(filteredPlanData);
          } else {
            // Si el plan seleccionado ya no existe, salir del modo enfoque
            isFiltered = false;
            renderPlanData(rows);
          }
        } else {
          // Renderizar todos los datos normalmente
          renderPlanData(rows);
        }
        
        aplicarSeleccionPersistida();
        
      } catch (error) {
          console.error('Error cargando datos:', error);
          elements.placeholder.textContent = `Error loading data: ${error.message}`;
          elements.placeholder.style.display = 'grid';
        }
      }
      
      // Función para filtrar por plan específico (modo enfoque)
      function filtrarPorPlan(planId) {
        const planSeleccionado = currentPlanData.find(p => p.id === planId);
        if (!planSeleccionado) {
          console.warn('Plan no encontrado para filtrar');
          return;
        }
        
        isFiltered = true;
        filteredPlanData = [planSeleccionado];
        renderPlanData(filteredPlanData);
      }
      
      // Función para mostrar todos los planes (salir del modo enfoque)
      function mostrarTodosLosDatos() {
        isFiltered = false;
        filteredPlanData = [];
        
        // Limpiar el campo de búsqueda para mostrar realmente todos los planes
        const lotEl = document.getElementById('lotNo');
        if (lotEl) {
          lotEl.value = '';
        }
        
        // Recargar datos sin filtros para mostrar todos los planes
        cargarDatosPlanSMD();
        
        // Limpiar historial de materiales y BOM - mostrar mensaje inicial
        setTimeout(() => {
          mostrarMensajeInicialHistorial();
          mostrarMensajeInicialBom();
        }, 500);
      }
      
      // FunciÃ³n para renderizar los datos en la tabla
      function renderPlanData(data) {
        // aplica después de render
        if (!elements.tableBody) return;
        
        // Limpiar tabla
        elements.tableBody.innerHTML = '';
        
        data.forEach((item, index) => {
          const row = document.createElement('tr');
          row.setAttribute('data-plan-id', String(item.id||''));
          // Calcular el total del plan como lo que ya se produjo + lo que falta
          const totalPlan = (item.producido || 0) + (item.falta || 0);
          const pct = Math.min(100, Math.round(((item.producido || 0) / (totalPlan || 1)) * 100));
          const falta = item.falta || 0;
          
          let statusClass = 'pending';
          let statusText = 'PLANEADO';
          
          // Lógica simplificada: priorizar run_status sobre estatus
          
          // Primero verificar run_status (más específico)
          if (item.run_status === 'RUNNING') {
            statusClass = 'partial';
            statusText = 'INICIADO';
          } else if (item.run_status === 'PAUSED') {
            statusClass = 'warning';
            statusText = 'PAUSADO';
          } else if (item.run_status === 'ENDED') {
            statusClass = 'completed';
            statusText = 'FINALIZADO';
          }
          // Si no hay run_status activo, usar estatus de trazabilidad
          else if (item.estatus === 'FINALIZADO') {
            statusClass = 'completed';
            statusText = 'FINALIZADO';
          } else if (item.estatus === 'INICIADO') {
            statusClass = 'partial';
            statusText = 'INICIADO';
          } else if (item.estatus === 'PLANEADO') {
            statusClass = 'pending';
            statusText = 'PLANEADO';
          }
          
          // Fallback basado en progreso
          else {
            if (pct >= 100) {
              statusClass = 'completed';
              statusText = 'COMPLETADO';
            } else if (pct > 0) {
              statusClass = 'partial';
              statusText = 'EN PROCESO';
            } else {
              statusClass = 'pending';
              statusText = 'PLANEADO';
            }
          }
          
          // Event listener para doble click (modo enfoque)
          row.addEventListener('dblclick', () => { 
            selectedPlanId = item.id; 
            try{ 
              localStorage.setItem('smtSelectedPlanId', String(selectedPlanId||'')); 
            }catch(e){} 
            
            // Activar modo enfoque en lugar de solo resaltar
            filtrarPorPlan(selectedPlanId);
          });
          
          // Event listener para click simple (modo focus con historial)
          row.addEventListener('click', function(e) {
            // Evitar que se active si se hace clic en el checkbox
            if (e.target.type === 'checkbox') {
              return;
            }
            
            // Remover clase focus de otras filas
            const allRows = document.querySelectorAll('#tbody-plan-data tr');
            allRows.forEach(r => {
              r.classList.remove('focused-row');
            });
            
            // Agregar clase focus a la fila actual
            row.classList.add('focused-row');
            
            // Guardar selección en localStorage
            try {
              localStorage.setItem('smtSelectedPlanId', item.id);
            } catch(e) {
              console.warn('No se pudo guardar selección:', e);
            }
            
            // Obtener la línea del item y cargar historial
            const lineaItem = item.linea;
            const nParteItem = item.nparte || item.modelo || '';
            
          // Mapear línea a formato esperado y cargar historial
          if (lineaItem) {
              // Resetear validación de Metal Mask al cambiar el foco
              maskCheckOk = false;
              // Si estamos en modo focus, cargar historial filtrado por línea
              cargarHistorialMaterial(lineaItem, 0);
              
              // También cargar el BOM List si tenemos NParte
              if (nParteItem) {
                cargarBomList(lineaItem, nParteItem, 0);
              }
            }
          });
          
          // Agregar cursor pointer para indicar que es clickeable
          row.style.cursor = 'pointer';
          row.style.transition = 'all 0.2s ease';
          
          // Agregar clase especial si tiene run activo
          if (item.run_status === 'RUNNING') {
            row.classList.add('run-active');
          } else if (item.run_status === 'PAUSED') {
            row.classList.add('run-paused');
          } else if (item.estatus === 'FINALIZADO' || item.run_status === 'ENDED') {
            row.classList.add('run-completed');
          }
          
          row.innerHTML = `
            <td>${item.linea || ''}</td>
            <td class="mono">${item.lote || ''}</td>
            <td class="mono">${item.nparte || ''}</td>
            <td>${item.modelo || ''}</td>
            <td>${item.tipo || ''}</td>
            <td><span class="status-tag ${statusClass}">${item.turno || ''}</span></td>
            <td>${item.ct || ''}</td>
            <td>${item.uph || ''}</td>
            <td class="mono" data-type="quantity">${item.falta || 0}</td>
            <td class="mono" data-type="quantity" data-status="${statusClass === 'completed' ? 'active' : statusClass === 'partial' ? 'warning' : 'error'}">${item.producido || 0}</td>
            <td class="mono" data-type="quantity">${falta}</td>
            <td><span class="status-tag ${statusClass}">${pct}%</span></td>
            <td><div class="progress-bar"><span style="width:${pct}%"></span></div></td>
            <td class="mono" data-type="date">${item.fecha_creacion ? item.fecha_creacion.substring(0, 16) : ''}</td>
            <td><span class="status-tag ${statusClass}">${statusText}</span></td>
            <td>${item.comentarios || ''}</td>
          `;
          
          elements.tableBody.appendChild(row);
        });
      }
      
      // Aplicar selección persistida tras renderizar
      function aplicarSeleccionPersistida() {
        try {
          const saved = Number(localStorage.getItem('smtSelectedPlanId')) || null;
          if (!saved) return;
          
          // Si hay un plan guardado, solo marcarlo como seleccionado (sin activar modo enfoque automáticamente)
          const planGuardado = currentPlanData.find(p => p.id === saved);
          if (planGuardado) {
            selectedPlanId = saved;
            // NO activar automáticamente el modo enfoque al cargar la página
            // El usuario debe hacer doble clic para activar el modo enfoque
          }
        } catch(e) { 
          console.warn('No se pudo aplicar selección persistida', e); 
        }
      }
      
      // Función para configurar las fechas por defecto (México - Monterrey)
      function setupDefaultDates() {
        // Obtener elementos directamente para asegurar que existen
        const dateFromEl = document.getElementById('dateFrom');
        const dateToEl = document.getElementById('dateTo');
        
        if (dateFromEl && dateToEl) {
          // Crear fecha actual en zona horaria de México (UTC-6)
          const mexicoTime = new Date().toLocaleString("en-CA", {
            timeZone: "America/Monterrey",
            year: "numeric",
            month: "2-digit", 
            day: "2-digit"
          });
          
          // SIEMPRE establecer la fecha actual de México (sobreescribir cualquier valor previo)
          dateFromEl.value = mexicoTime;
          dateToEl.value = mexicoTime;
        } else {
          // Reintentar en 500ms
          setTimeout(setupDefaultDates, 500);
        }
      }
      
      // Función para agregar estilos CSS dinámicamente
      function addFocusStyles() {
        // Verificar si ya existen los estilos
        if (document.getElementById('smt-focus-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'smt-focus-styles';
        style.textContent = `
          /* Estilos para modo focus */
          #tbody-plan-data tr {
            cursor: pointer;
            transition: all 0.2s ease;
          }
          
          #tbody-plan-data tr.focused-row td {
            background-color: #3498DB !important;
            color: #FFFFFF !important;
            font-weight: 500;
            border-color: #2980B9 !important;
          }

          #tbody-plan-data tr.focused-row:hover td {
            background-color: #2980B9 !important;
          }
          
          #tbody-plan-data tr.focused-row .status-tag {
            background-color: rgba(255, 255, 255, 0.2) !important;
            color: #FFFFFF !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
          }
          
          /* Estilos para contenedores de tabla - APLICAR A TODAS LAS TABLAS */
          div.table,
          .panel-body .table,
          #tbl-mch,
          #tbl-solder,
          #tbl-metalmask,
          #tbl-squeegee {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: block !important;
            position: relative !important;
          }
          #tbl-bom {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: auto !important;
            display: block !important;
            position: relative !important;
          }
          #panel-bom .panel-body {
            /* Evitar scroll vertical en el body del panel para que viva en #tbl-bom */
            max-height: none !important;
            overflow-y: visible !important;
            overflow-x: auto !important;
          }
          
          
          .panel-body {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
          }
          
          div.section-table-container {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: block !important;
            position: relative !important;
          }
          
          /* Asegurar que TODAS las tablas usen todo el ancho disponible */
          .section-table,
          #tbl-bom table,
          #tbl-mch table,
          #tbl-solder table,
          #tbl-metalmask table,
          #tbl-squeegee table,
          .panel .table table {
            width: 100% !important;
            table-layout: fixed !important;
          }

          /* Ajustes de ancho de columnas para BOM */
          #panel-bom table th:nth-child(4),
          #panel-bom table td:nth-child(4) {
            width: 20% !important;   /* Description más ancho */
            min-width: 320px;
            white-space: nowrap;
          }
          #panel-bom table th:nth-child(6),
          #panel-bom table td:nth-child(6) {
            width: 70px !important;  /* Qty más angosto */
            max-width: 70px;
            white-space: nowrap;
            text-align: center;
          }
          
          /* Forzar scroll en cualquier contenedor que tenga el tbody del historial */
          #materialHistoryTableBody-Control\\ de\\ operacion\\ de\\ linea\\ SMT {
            /* Asegurar que el tbody sea visible */
          }
          
          /* Contenedor padre del tbody del historial */
          table:has(#materialHistoryTableBody-Control\\ de\\ operacion\\ de\\ linea\\ SMT) {
            width: 100% !important;
          }
          
          /* Selectores específicos para TODOS los paneles - SCROLL UNIVERSAL */
          #panel-mch .panel-body,
          #panel-bom .panel-body,
          #panel-solder .panel-body,
          #panel-metalmask .panel-body,
          #panel-squeegee .panel-body {
            overflow-y: auto !important;
            overflow-x: hidden !important;
          }
          
          #panel-mch .table,
          #panel-bom .table,
          #panel-solder .table,
          #panel-metalmask .table,
          #panel-squeegee .table {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: block !important;
            position: relative !important;
          }
          
          div:has(table tbody[id*="materialHistory"]) {
            max-height: 400px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
          }
          
          /* Estilos para el scrollbar - APLICAR A TODAS LAS TABLAS */
          .section-table-container::-webkit-scrollbar,
          .panel-body::-webkit-scrollbar,
          .table::-webkit-scrollbar,
          #tbl-mch::-webkit-scrollbar,
          #tbl-bom::-webkit-scrollbar,
          #tbl-solder::-webkit-scrollbar,
          #tbl-metalmask::-webkit-scrollbar,
          #tbl-squeegee::-webkit-scrollbar,
          div.table::-webkit-scrollbar {
            width: 8px;
            height: 8px;
          }
          
          .section-table-container::-webkit-scrollbar-track,
          .panel-body::-webkit-scrollbar-track,
          .table::-webkit-scrollbar-track,
          #tbl-mch::-webkit-scrollbar-track,
          #tbl-bom::-webkit-scrollbar-track,
          #tbl-solder::-webkit-scrollbar-track,
          #tbl-metalmask::-webkit-scrollbar-track,
          #tbl-squeegee::-webkit-scrollbar-track,
          div.table::-webkit-scrollbar-track {
            background: #40424F;
            border-radius: 4px;
          }
          
          .section-table-container::-webkit-scrollbar-thumb,
          .panel-body::-webkit-scrollbar-thumb,
          .table::-webkit-scrollbar-thumb,
          #tbl-mch::-webkit-scrollbar-thumb,
          #tbl-bom::-webkit-scrollbar-thumb,
          #tbl-solder::-webkit-scrollbar-thumb,
          #tbl-metalmask::-webkit-scrollbar-thumb,
          #tbl-squeegee::-webkit-scrollbar-thumb,
          div.table::-webkit-scrollbar-thumb {
            background: #666;
            border-radius: 4px;
          }
          
          .section-table-container::-webkit-scrollbar-thumb:hover,
          .panel-body::-webkit-scrollbar-thumb:hover,
          .table::-webkit-scrollbar-thumb:hover,
          #tbl-mch::-webkit-scrollbar-thumb:hover,
          #tbl-bom::-webkit-scrollbar-thumb:hover,
          #tbl-solder::-webkit-scrollbar-thumb:hover,
          #tbl-metalmask::-webkit-scrollbar-thumb:hover,
          #tbl-squeegee::-webkit-scrollbar-thumb:hover,
          div.table::-webkit-scrollbar-thumb:hover {
            background: #888;
          }
          
          /* Estilos para BOM List */
          .bom-pending {
            border: 1px solid #E74C3C !important;
          }
          
          .bom-matched {
            border: 1px solid #27AE60 !important;
          }
          
          .status-indicator {
            padding: 2px 4px;
            border-radius: 2px;
            font-weight: 600;
            display: inline-block;
          }
          
          .status-indicator.bom-pending {
            background-color: rgba(231, 76, 60, 0.15);
            color: #E74C3C;
            border: 1px solid #E74C3C;
          }
          
          .status-indicator.bom-matched {
            background-color: rgba(39, 174, 96, 0.15);
            color: #27AE60;
            border: 1px solid #27AE60;
          }

          /* Colorear texto de toda la fila del BOM según estado */
          #panel-bom table tbody tr.bom-pending td {
            color: #E74C3C !important;
          }
          #panel-bom table tbody tr.bom-matched td {
            color: #27AE60 !important;
          }

          /* Overlay Metal Mask scan */
          .mm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display:flex; align-items:center; justify-content:center; z-index: 9999; }
          .mm-dialog { width: 460px; background:#2f3241; border:1px solid #3e6ea1; border-radius:6px; padding:16px; box-shadow:0 10px 30px rgba(0,0,0,.4); }
          .mm-dialog h3 { margin:0 0 8px 0; font-size:16px; color:#e4e7ef; }
          .mm-row { display:flex; gap:10px; align-items:center; margin:12px 0; }
          .mm-row label { width:140px; color:#cfd6e4; }
          .mm-row input { flex:1; padding:8px; background:#1f2330; color:#e4e7ef; border:1px solid #3e6ea1; border-radius:4px; }
          .mm-actions { display:flex; gap:10px; justify-content:flex-end; margin-top:10px; }
          .mm-actions .btn { padding:8px 12px; border-radius:4px; border:1px solid transparent; cursor:pointer; }
          .btn-primary { background:#6741d9; color:#fff; border-color:#4f32a6; }
          .btn-danger { background:#c0392b; color:#fff; border-color:#962d22; }
          .mm-result { margin-top:10px; font-size:12px; }
          .mm-ok { color:#2ecc71; }
          .mm-ng { color:#e74c3c; }
        `;
        document.head.appendChild(style);
      }
      
      // FunciÃ³n para configurar event listeners
      function setupEventListeners() {
        if (!getElements()) return;
        
        // Agregar estilos CSS
        addFocusStyles();
        
        // Configurar event listeners para historial de material
        const btnExportarHistorial = document.getElementById('btnExportarHistorial-Control de operacion de linea SMT');
        if (btnExportarHistorial) {
          btnExportarHistorial.addEventListener('click', function() {
            console.log('Exportar historial clicked');
            exportarHistorialMaterial();
          });
        }

        // Configurar event listeners para exportar BOM
        const btnExportarBom = document.getElementById('btnExportarBom-Control de operacion de linea SMT');
        if (btnExportarBom) {
          btnExportarBom.addEventListener('click', function() {
            console.log('Exportar BOM clicked');
            exportarBomList();
          });
        }

        // Función para detectar y configurar botones de Excel Export automáticamente
        function configurarBotonesExcel() {
          // Buscar botones en el panel BOM
          const bomButtons = document.querySelectorAll(`
            #panel-bom .btn[title*="Excel"],
            #panel-bom .btn[onclick*="excel"],
            #panel-bom .excel-export,
            #panel-bom button[title*="Export"],
            #panel-bom .btn:contains("Excel"),
            #panel-bom .btn[data-export="excel"]
          `);
          
          bomButtons.forEach(btn => {
            // Remover event listeners anteriores
            btn.removeAttribute('onclick');
            btn.addEventListener('click', function(e) {
              e.preventDefault();
              e.stopPropagation();
              console.log('Exportar BOM Excel (auto-detectado)');
              exportarBomList();
            });
          });

          // Buscar botones en el panel Material History
          const historyButtons = document.querySelectorAll(`
            #panel-mch .btn[title*="Excel"],
            #panel-mch .btn[onclick*="excel"],
            #panel-mch .excel-export,
            #panel-mch button[title*="Export"],
            #panel-mch .btn:contains("Excel"),
            #panel-mch .btn[data-export="excel"]
          `);
          
          historyButtons.forEach(btn => {
            // Remover event listeners anteriores
            btn.removeAttribute('onclick');
            btn.addEventListener('click', function(e) {
              e.preventDefault();
              e.stopPropagation();
              console.log('Exportar History Excel (auto-detectado)');
              exportarHistorialMaterial();
            });
          });

          console.log(`Botones Excel configurados: ${bomButtons.length} BOM, ${historyButtons.length} History`);
        }

        // Ejecutar configuración de botones después de un pequeño delay
        setTimeout(configurarBotonesExcel, 1000);
        
        // Re-ejecutar cuando se cargue contenido dinámico
        const observer = new MutationObserver(function(mutations) {
          let shouldReconfig = false;
          mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
              mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1 && 
                    (node.classList?.contains('btn') || 
                     node.querySelector?.('.btn') ||
                     node.id?.includes('panel-'))) {
                  shouldReconfig = true;
                }
              });
            }
          });
          
          if (shouldReconfig) {
            setTimeout(configurarBotonesExcel, 500);
          }
        });

        if (document.querySelector('#panel-bom, #panel-mch')) {
          observer.observe(document.querySelector('#panel-bom, #panel-mch') || document.body, {
            childList: true,
            subtree: true
          });
        }

        // Abrir cuadro de escaneo para MetalMask
        const btnMM = document.getElementById('btn-metalmask-regist');
        if (btnMM) {
          btnMM.addEventListener('click', () => {
            showMetalMaskScanDialog();
          });
        }
        
        const lineaDropdown = document.getElementById('linea-Control de operacion de linea SMT');
        if (lineaDropdown) {
          lineaDropdown.addEventListener('change', function() {
            console.log('Línea cambiada a:', this.value);
            onLineaChange();
          });
        }
        
        // No cargar historial automáticamente - solo cuando se seleccione un plan
        // Mostrar mensaje inicial en lugar de cargar datos automáticamente
        setTimeout(function() {
            mostrarMensajeInicialHistorial();
            mostrarMensajeInicialBom();
        }, 1000);
        
        if (elements.btnSearch) {
          elements.btnSearch.addEventListener('click', () => {
            // Salir del modo enfoque cuando se presiona Search
            if (isFiltered) {
              isFiltered = false;
              filteredPlanData = [];
              // Limpiar historial y BOM cuando se sale del modo focus
              setTimeout(() => {
                mostrarMensajeInicialHistorial();
                mostrarMensajeInicialBom();
              }, 300);
            }
            
            // Limpiar campos Lot No y Lot No Info para búsqueda general
            const lotNoEl = document.getElementById('lotNo');
            const lotNoInfoEl = document.getElementById('lotNoInfo');
            if (lotNoEl) lotNoEl.value = '';
            if (lotNoInfoEl) lotNoInfoEl.value = '';
            
            // Asegurar que las fechas siempre estén en el día actual
            setupDefaultDates();
            
            // Hacer búsqueda con los filtros aplicados
            cargarDatosPlanSMD();
          });
        }
        
        // Botón para limpiar LOT NO
        const btnClearLot = document.getElementById('btn-clear-lot');
        if (btnClearLot) {
          btnClearLot.addEventListener('click', () => {
            const lotNoField = document.getElementById('lotNo');
            if (lotNoField) {
              lotNoField.value = '';
              // Salir del modo focus y recargar todos los datos
              if (isFiltered) {
                isFiltered = false;
                filteredPlanData = [];
                cargarDatosPlanSMD();
                // Limpiar historial y BOM cuando se sale del modo focus
                setTimeout(() => {
                  mostrarMensajeInicialHistorial();
                  mostrarMensajeInicialBom();
                }, 300);
              }
            }
          });
        }
        
        // Event listener para campo LOT NO - activar búsqueda y modo focus al presionar Enter
        const lotNoField = document.getElementById('lotNo');
        if (lotNoField) {
          lotNoField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
              e.preventDefault(); // Evitar submit del form si existe
              
              // Si hay valor, buscar y activar modo focus
              const lotValue = lotNoField.value.trim();
              if (lotValue) {
                // Forzar búsqueda inmediata
                cargarDatosPlanSMD();
              }
            }
          });
          
          // También agregar listener para cuando se limpia el campo
          lotNoField.addEventListener('input', (e) => {
            const lotValue = e.target.value.trim();
            // Si se vació el campo, salir del modo focus
            if (!lotValue && isFiltered) {
              isFiltered = false;
              filteredPlanData = [];
              cargarDatosPlanSMD();
              // Limpiar historial y BOM cuando se sale del modo focus
              setTimeout(() => {
                mostrarMensajeInicialHistorial();
                mostrarMensajeInicialBom();
              }, 300);
            }
          });
        }
        
        // Cambio en fechas
        if (elements.dateFrom) {
          elements.dateFrom.addEventListener('change', () => {
            console.log('ðŸ“… Fecha desde cambiada:', elements.dateFrom.value);
            cargarDatosPlanSMD();
          });
        }
        
        if (elements.dateTo) {
          elements.dateTo.addEventListener('change', () => {
            console.log('ðŸ“… Fecha hasta cambiada:', elements.dateTo.value);
            cargarDatosPlanSMD();
          });
        }
        
        // Checkbox "Mostrar Planeadas"
        if (elements.chkShowPlanned) {
          elements.chkShowPlanned.addEventListener('change', () => {
            console.log('Mostrar planeadas:', elements.chkShowPlanned.checked);
            cargarDatosPlanSMD();
          });
        }
        
        // Otros botones
        const btnStart = document.getElementById('btn-start');
        const btnEnd = document.getElementById('btn-end');
        const btnStop = document.getElementById('btn-stop');
        
        if (btnStart) {
          btnStart.addEventListener('click', async () => {
            if (!selectedPlanId) { 
              showError('SELECCIÓN REQUERIDA → Selecciona un plan (doble clic en fila)');
              return; 
            }
            // Validaciones previas: BOM y Metal Mask
            if (!bomAllMatched()) {
              showError('BOM NO VERIFICADO → Aún hay componentes NG');
              return;
            }
            if (!maskCheckOk) {
              showError('METAL MASK NO DISPONIBLE → Escanea y valida disponibilidad');
              return;
            }
            
            // Deshabilitar botón inmediatamente
            btnStart.disabled = true;
            btnStart.textContent = 'Starting...';
            btnStart.classList.add('processing');
            
            try {
              // Encontrar el plan seleccionado en los datos actuales
              const datosActuales = isFiltered ? filteredPlanData : currentPlanData;
              const planSeleccionado = datosActuales.find(p => p.id === selectedPlanId);
              if (!planSeleccionado) {
                showError('PLAN NO ENCONTRADO → Actualiza los datos del sistema');
                return;
              }
              
              // Validaciones rápidas
              if (planSeleccionado.run_status === 'RUNNING') {
                showWarning(`PROCESO YA ACTIVO → ${planSeleccionado.lote}`);
                return;
              }
              
              const linea = planSeleccionado.linea;
              if (!linea) {
                showError('LÍNEA NO ASIGNADA → Configura línea para el plan');
                return;
              }
              
              // Iniciar run directamente (sin verificación de línea para velocidad)
              const resp = await fetch('/api/plan-run/start', { 
                method: 'POST', 
                headers: {'Content-Type':'application/json'}, 
                body: JSON.stringify({ plan_id: selectedPlanId, linea, lot_prefix: 'I' }) 
              });
              const data = await resp.json();
              
              if (!data.success) {
                showError(data.error || 'No se pudo iniciar el run');
                return;
              }
              
              // Actualizar estado local inmediatamente
              currentRunId = data.run.id; 
              // Mapear plan->run para soportar múltiples activos
              try { const map = JSON.parse(localStorage.getItem('smtRunMap')||'{}'); map[String(selectedPlanId)] = Number(currentRunId); localStorage.setItem('smtRunMap', JSON.stringify(map)); } catch(_){}
              // Legacy single key
              localStorage.setItem('smtRunId', String(currentRunId));
              
              // Actualizar UI inmediatamente
              const lotNoInput = document.getElementById('lotNo'); 
              const lotInfo = document.getElementById('lotNoInfo');
              if (lotNoInput) lotNoInput.value = data.run.lot_no; 
              if (lotInfo) lotInfo.value = `Iniciado: ${data.run.lot_no}`;
              
              // Actualizar la fila en la tabla sin recargar todo
              const filaActual = document.querySelector(`tr[data-plan-id="${selectedPlanId}"]`);
              if (filaActual) {
                const estatusCell = filaActual.querySelector('td:nth-child(15)');
                if (estatusCell) {
                  estatusCell.innerHTML = '<span class="status-tag partial">INICIADO</span>';
                }
              }
              
              // Notificación removida por solicitud del usuario
            } catch(e){ 
              showError('Error al iniciar run: ' + e.message);
            } finally {
              // Rehabilitar botón
              btnStart.disabled = false;
              btnStart.textContent = 'Start(Re-Start)';
              btnStart.classList.remove('processing');
            }
          });
        }
        
        if (btnEnd) {
          btnEnd.addEventListener('click', async () => {
            // Deshabilitar botón inmediatamente
            btnEnd.disabled = true;
            btnEnd.textContent = 'Ending...';
            btnEnd.classList.add('processing');
            
            try { 
              if (!selectedPlanId) {
                showError('SELECCIÓN REQUERIDA → Doble clic en el plan a finalizar');
                return;
              }
              const datos = (isFiltered ? filteredPlanData : currentPlanData) || [];
              const planRow = datos.find(x => x && Number(x.id) === Number(selectedPlanId));
              if (!planRow) {
                showError('PLAN NO ENCONTRADO → Actualiza la lista');
                return;
              }
              const ok = window.confirm(`Finalizar plan:\nLinea: ${planRow.linea||''}\nLot: ${planRow.lote||''}\nNParte: ${planRow.nparte||''}\n¿Confirmar?`);
              if (!ok) { return; }
              let rid = null;
              try { const map = JSON.parse(localStorage.getItem('smtRunMap')||'{}'); rid = map[String(selectedPlanId)] || null; } catch(_) {}
              if (!rid && planRow.run_id) rid = Number(planRow.run_id);
              if (!rid) {
                try {
                  const r1 = await fetch(`/api/plan-smd/list?plan_id=${selectedPlanId}`);
                  const j1 = await r1.json();
                  const row1 = Array.isArray(j1) ? j1[0] : (j1.rows && j1.rows[0]);
                  if (row1 && row1.run_id) rid = Number(row1.run_id);
                } catch(_) {}
              }
              if (!rid) {
                showError('NO HAY PROCESO ACTIVO para el plan seleccionado');
                return; 
              }
              
              // Finalizar run
              const resp = await fetch('/api/plan-run/end', { 
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body: JSON.stringify({ run_id: rid, plan_id: selectedPlanId }) 
              });
              const data = await resp.json(); 
              
              if (!data.success) {
                showError(data.error || 'No se pudo finalizar el run');
                return;
              }
              
              // Identificar el plan afectado y actualizar UI en sitio
              const endedPlanId = (data && data.run && data.run.plan_id) ? Number(data.run.plan_id) : (selectedPlanId || null);
              if (endedPlanId) {
                const fila = document.querySelector(`tr[data-plan-id="${endedPlanId}"]`);
                if (fila) {
                  // Estatus visual
                  const tdEstatus = fila.children[14];
                  if (tdEstatus) tdEstatus.innerHTML = '<span class="status-tag completed">FINALIZADO</span>';
                  fila.classList.remove('run-active','run-paused');
                  fila.classList.add('run-completed');
                }
                // Actualizar cache local para que el refresco en vivo respete el estado
                const all = Array.isArray(currentPlanData) ? currentPlanData : [];
                const it = all.find(x => Number(x.id) === Number(endedPlanId));
                if (it) { it.run_status = 'ENDED'; it.estatus = 'FINALIZADO'; }
                // remover mapeo plan->run al finalizar
                try { const map = JSON.parse(localStorage.getItem('smtRunMap')||'{}'); delete map[String(endedPlanId)]; localStorage.setItem('smtRunMap', JSON.stringify(map)); } catch(_){}
              }

              // Limpiar estado local inmediatamente
              localStorage.removeItem('smtRunId'); 
              currentRunId = null;
              
              // Limpiar campos de UI inmediatamente
              const lotNoInput = document.getElementById('lotNo'); 
              const lotInfo = document.getElementById('lotNoInfo');
              if (lotNoInput) lotNoInput.value = '';
              if (lotInfo) lotInfo.value = '';
              
              // Notificación removida por solicitud del usuario
            } catch(e){ 
              showError('Error al finalizar run: ' + e.message); 
            } finally {
              // Rehabilitar botón
              btnEnd.disabled = false;
              btnEnd.textContent = 'End';
              btnEnd.classList.remove('processing');
            }
          });
        }
        
        if (btnStop) {
          btnStop.addEventListener('click', () => {
            console.log('Stop clicked');
          });
        }
      }
      
      // FunciÃ³n principal de inicializaciÃ³n
      function inicializar() {
        if (isInitialized) {
          console.log('Ya inicializado, omitiendo...');
          return;
        }
        
        console.log('Inicializando Control de Operacion SMT AJAX...');
        isInitialized = true;
        
        // Configurar event listeners primero
        setupEventListeners();
        
        // Configurar fechas por defecto ANTES de cargar datos
        setTimeout(() => {
          setupDefaultDates();
          
          // Cargar datos DESPUÉS de configurar las fechas
          setTimeout(() => {
            cargarDatosPlanSMD();
          }, 200);
        }, 100);
      }
      
      // Función para verificar estado
      window.verificarControlOperacionSMTAjax = function() {
        const container = document.getElementById('app-mes-front-isolated');
        const table = document.getElementById('tbody-plan-data');
        const tbody = elements.tableBody;
        
        console.log('- Container:', !!container);
        console.log('- Table:', !!table);
        console.log('- Tbody:', !!tbody);
        console.log('- Datos cargados:', currentPlanData.length);
        
        return !!(container && table && tbody);
      };
      
      // Exponer funciones globalmente para uso en botones
      window.mostrarTodosLosDatos = mostrarTodosLosDatos;
      window.filtrarPorPlan = filtrarPorPlan;
      window.controlOperacionSMTAjax = true;
      
      // Auto-inicialización simplificada
      console.log('Módulo SMT cargado correctamente');
      
      // Inicializar siempre
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializar);
      } else {
        setTimeout(inicializar, 100);
      }
      
      // Configuración adicional cuando la ventana esté completamente cargada
      window.addEventListener('load', () => {
        setTimeout(setupDefaultDates, 200);
      });
      
      // Observador de mutaciones para detectar carga dinÃ¡mica
      if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function(mutations) {
          mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
              const container = document.getElementById('app-mes-front-isolated');
              if (container && !isInitialized) {
                console.log('ðŸ” Detectado contenido dinÃ¡mico, inicializando...');
                setTimeout(inicializar, 300);
              }
            }
          });
        });
        
        observer.observe(document.body, {
          childList: true,
          subtree: true
        });
      }
      
      // Callback para sistemas de templates
      if (typeof window.onTemplateLoaded === 'function') {
        window.onTemplateLoaded('control_operacion_linea_smt_ajax');
      }

      // ==========================
      // INTEGRACIÓN CON SISTEMA DE HISTORIAL DE MATERIAL
      // ==========================
      function getFocusedPlan(){
          if (Array.isArray(filteredPlanData) && filteredPlanData.length > 0) return filteredPlanData[0];
          return (currentPlanData||[]).find(p => p && Number(p.id) === Number(selectedPlanId));
      }

      function requiredUsesForPlan(){
          const p = getFocusedPlan();
          if (!p) return 0;
          const candidates = [p.falta, p.qty, p.cantidad_total, p.cantidad, p.total];
          for (const v of candidates){ const n = Number(v||0); if (!isNaN(n) && n>0) return n; }
          return 0;
      }

      function bomAllMatched(){
          if (!lastBomData || lastBomData.length === 0) return false;
          for (const it of lastBomData){
              const side = (it.tabla_tipo ? String(it.tabla_tipo).toUpperCase() : '') ||
                           parseSideFromBaseFeeder(it.base_feeder || it.feeder_info || '');
              const key = makeKey(it.slot, it.material_code, it.mounter, side);
              if (!key || !historyMatchKeys.has(key)) return false;
          }
          return true;
      }

      async function consultMaskInfo(code){
          const r = await fetch(`/api/masks/info?code=${encodeURIComponent(code)}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const j = await r.json();
          if (!j.success || !j.found) throw new Error(j.error || 'No encontrada');
          return j.data;
      }

      function showMetalMaskScanDialog(){
          const overlay = document.createElement('div');
          overlay.className = 'mm-overlay';
          overlay.innerHTML = `
            <div class="mm-dialog">
              <h3>Registrar Metal Mask</h3>
              <div class="mm-row">
                <label>Metal Mask S/N</label>
                <input id=\"mm-scan-input\" placeholder=\"Ej. MM1-2-001\" />
              </div>
              <div class=\"mm-actions\">
                <button class=\"btn btn-primary\" id=\"mm-scan-ok\">Regist</button>
                <button class=\"btn btn-danger\" id=\"mm-scan-cancel\">Close</button>
              </div>
              <div class=\"mm-result\" id=\"mm-scan-result\"></div>
            </div>`;
          document.body.appendChild(overlay);

          const inp = overlay.querySelector('#mm-scan-input');
          const btnOk = overlay.querySelector('#mm-scan-ok');
          const btnCancel = overlay.querySelector('#mm-scan-cancel');
          const res = overlay.querySelector('#mm-scan-result');
          setTimeout(()=> inp && inp.focus(), 50);

          const close = ()=> overlay.remove();
          btnCancel.addEventListener('click', close);
          overlay.addEventListener('click', (e)=>{ if (e.target === overlay) close(); });

          async function doScan(){
              const code = (inp.value||'').trim();
              if (!code){ res.textContent='Ingrese el S/N a validar'; res.className='mm-result mm-ng'; return; }
              res.textContent = 'Consultando...'; res.className='mm-result';
              try{
                  const data = await consultMaskInfo(code);
                  const used = Number(data.used_count||0);
                  const maxc = Number(data.max_count||0);
                  const allowance = Number(data.allowance||0);
                  const available = Math.max(0, (maxc + allowance) - used);
                  const required = requiredUsesForPlan();
                  const ok = available >= (required>0?required:1);
                  maskCheckOk = ok;
                  const now = new Date().toISOString().slice(0,16).replace('T',' ');
                  res.innerHTML = ok
                    ? `<span class="mm-ok">Disponible ✓</span> Usos disp.: <b>${available}</b> / Requeridos: <b>${required}</b>`
                    : `<span class="mm-ng">No disponible ✗</span> Usos disp.: <b>${available}</b> / Requeridos: <b>${required}</b>`;

                  // Append row into MetalMask history table
                  try{
                      let tbody = document.querySelector('#panel-metalmask table tbody');
                      if (!tbody){ const t = document.querySelector('#panel-metalmask table'); tbody = document.createElement('tbody'); t && t.appendChild(tbody); }
                      if (tbody){
                          const tr = document.createElement('tr');
                          tr.innerHTML = `<td style=\"padding:6px; font-size:10px;\">${now}</td>
                                          <td style=\"padding:6px; font-size:10px;\">${data.management_no||code}</td>
                                          <td style=\"padding:6px; font-size:10px; color:${ok?'#27AE60':'#E74C3C'};\">${available}</td>`;
                          tbody.prepend(tr);
                      }
                  }catch(_){ }
              }catch(err){
                  maskCheckOk = false;
                  res.textContent = 'Error consultando máscara: ' + err.message;
                  res.className = 'mm-result mm-ng';
              }
          }

          btnOk.addEventListener('click', doScan);
          inp.addEventListener('keypress', (e)=>{ if (e.key==='Enter') doScan(); });
      }
      
      // Función para mapear línea a equipo SMT y sus máquinas
      function mapearLineaAEquipo(linea) {
          const mapeoLineas = {
              '1LINE': 'SMT A',
              '2LINE': 'SMT B', 
              '3LINE': 'SMT C',
              '4LINE': 'SMT D',
              // También mapear valores directos
              'SMT A': 'SMT A',
              'SMT B': 'SMT B',
              'SMT C': 'SMT C',
              'SMT D': 'SMT D'
          };
          return mapeoLineas[linea] || linea;
      }
      
      // Función para obtener todas las máquinas de una línea SMT
      function obtenerMaquinasDeLinea(linea) {
          const maquinasPorLinea = {
              '1LINE': ['L1 m1', 'L1 m2', 'L1 m3', '1line'],
              '2LINE': ['L2 m1', 'L2 m2', 'L2 m3', '2line'],
              '3LINE': ['L3 m1', 'L3 m2', 'L3 m3', '3line'],
              '4LINE': ['L4 m1', 'L4 m2', 'L4 m3', '4line'],
              'SMT A': ['L1 m1', 'L1 m2', 'L1 m3', '1line'],
              'SMT B': ['L2 m1', 'L2 m2', 'L2 m3', '2line'],
              'SMT C': ['L3 m1', 'L3 m2', 'L3 m3', '3line'],
              'SMT D': ['L4 m1', 'L4 m2', 'L4 m3', '4line']
          };
          return maquinasPorLinea[linea] || [];
      }
      
      // Función para cargar datos del historial de cambio de material
      async function cargarHistorialMaterial(lineaSeleccionada = null, intentos = 0) {
          console.log('Cargando historial de material para línea:', lineaSeleccionada);
          
          let tableBody = document.getElementById('materialHistoryTableBody-Control de operacion de linea SMT');
          
          // Fallback: template aislado (#tbl-mch table)
          if (!tableBody) {
              const mchTable = document.querySelector('#tbl-mch table');
              if (mchTable) {
                  tableBody = mchTable.querySelector('tbody');
                  if (!tableBody) {
                      tableBody = document.createElement('tbody');
                      mchTable.appendChild(tableBody);
                  }
              }
          }
          
          if (!tableBody) {
              const maxIntentos = 20;
              if (intentos < maxIntentos) {
                  console.warn(`Tabla no encontrada (intento ${intentos + 1}/${maxIntentos}), reintentando en 300ms...`);
                  setTimeout(() => cargarHistorialMaterial(lineaSeleccionada, intentos + 1), 300);
                  return;
              }
              console.error('No se encontró el tbody objetivo para historial de material tras varios intentos');
              return;
          }
          
          try {
              // Obtener la línea seleccionada del dropdown si no se proporciona
              if (!lineaSeleccionada) {
                  const lineaDropdown = document.getElementById('linea-Control de operacion de linea SMT');
                  lineaSeleccionada = lineaDropdown ? lineaDropdown.value : 'Todos';
                  console.log('Línea obtenida del dropdown:', lineaSeleccionada);
              } else {
                  console.log('Usando línea del parámetro:', lineaSeleccionada);
              }
              
              // Si es "Todos", usar el endpoint original
              if (lineaSeleccionada === 'Todos') {
                  const url = '/api/historial-cambio-material-maquina';
                  console.log('Cargando historial de material (todos) desde:', url);
                  
                  const response = await fetch(url);
                  if (!response.ok) {
                      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                  }
                  
                  const result = await response.json();
                  
                  if (!result.success) {
                      throw new Error(result.error || 'Error en la respuesta del API');
                  }
                  
                  const data = result.data || [];
                  renderizarTablaHistorial(data, tableBody, lineaSeleccionada);
                  return;
              }
              
              // Para líneas específicas, usar el nuevo endpoint
              const equipoSMT = mapearLineaAEquipo(lineaSeleccionada);
              const url = `/api/historial_smt_latest_v2?linea=${encodeURIComponent(equipoSMT)}`;
              
              console.log('Mapeo de línea:');
              console.log('  - Línea original:', lineaSeleccionada);
              console.log('  - Equipo SMT mapeado:', equipoSMT);
              console.log('  - URL construida:', url);
              console.log('Cargando historial de material para línea:', lineaSeleccionada, '(', equipoSMT, ') desde:', url);
              
              const response = await fetch(url);
              if (!response.ok) {
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
              }
              
              const result = await response.json();
              const data = result.data || [];
              
              // Renderizar datos en la tabla del historial de material
              console.log('Renderizando datos en la tabla del historial de material...');
              renderizarTablaHistorial(data, tableBody, lineaSeleccionada);
              
          } catch (error) {
              console.error('Error cargando historial de material:', error);
              if (tableBody) {
                  tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: #E74C3C;">Error cargando datos</td></tr>';
              }
          }
      }
      
      // Función auxiliar para renderizar la tabla de historial
      function renderizarTablaHistorial(data, tableBody, lineaFiltro = null) {
          // Verificar que tableBody existe
          if (!tableBody) {
              console.error('TableBody es null, no se puede renderizar la tabla');
              return;
          }
          
          // Limpiar tabla
          tableBody.innerHTML = '';
          
          if (data.length === 0) {
              tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #95A5A6;">No hay datos disponibles</td></tr>';
              return;
          }
          
          // Filtrar datos por línea si se especifica una línea y estamos en modo focus
          let dataFiltrada = data;
          if (lineaFiltro && isFiltered && selectedPlanId) {
              const maquinasPermitidas = obtenerMaquinasDeLinea(lineaFiltro);
              console.log(`Filtrando historial para línea: ${lineaFiltro}`);
              console.log('Máquinas permitidas:', maquinasPermitidas);
              
              dataFiltrada = data.filter(item => {
                  const maquina = item.maquina || item.equipment || item.Equipment || item.machine || '';
                  const coincide = maquinasPermitidas.some(maq => 
                      maquina.toLowerCase().includes(maq.toLowerCase()) ||
                      maq.toLowerCase().includes(maquina.toLowerCase())
                  );
                  if (coincide) {
                      console.log(`✓ Incluido: ${maquina} (coincide con ${maquinasPermitidas.find(m => 
                          maquina.toLowerCase().includes(m.toLowerCase()) || 
                          m.toLowerCase().includes(maquina.toLowerCase()))})`);
                  }
                  return coincide;
              });
              
              console.log(`Datos filtrados: ${dataFiltrada.length} de ${data.length} registros`);
          }
          
          // Normalizar datos e indexar para matching BOM (incluye mounter desde Equipment y lado FRONT/REAR desde Base Feeder)
          lastHistoryDataNorm = dataFiltrada.map(item => {
              const equipment = item.maquina || item.equipment || item.Equipment || item.machine || '';
              const baseFeederVal = item.FeederBase || item.feederbase || item.BaseFeeder || item.base_feeder || item.Feeder || item.feeder || '';
              return {
                  slot: item.SlotNo || item.slot_no || item.slotno || item.SlotNumber || '',
                  part: item.PartName || item.warehousing || item.Warehousing || item.part_name || item.Material || '',
                  mounter: parseMounterFromEquipment(equipment),
                  side: parseSideFromBaseFeeder(baseFeederVal)
              };
          });
          rebuildHistoryMatchIndex();

          // Renderizar filas filtradas
          const maxRows = 1000; // Permitir hasta 1000 registros
          const dataToShow = dataFiltrada.slice(0, maxRows);
          
          dataToShow.forEach((item, index) => {
              const row = document.createElement('tr');
              
              // Debug: Ver los campos disponibles en el primer elemento
              if (index === 0) {
                  console.log('Campos disponibles en el API de historial:', Object.keys(item));
                  console.log('Datos del primer elemento:', item);
              }
              
              // Mapear campos del API a los campos esperados por la tabla
              const equipment = item.maquina || item.equipment || item.Equipment || item.machine || '';
              const slotNo = item.SlotNo || item.slot_no || item.slotno || item.SlotNumber || '';
              const baseFeeder = item.FeederBase || item.feederbase || item.BaseFeeder || item.base_feeder || item.Feeder || item.feeder || '';
              const registDate = item.fecha_formateada || item.regist_date || item.RegistDate || item.ScanDate || item.fecha || '';
              const warehousing = item.PartName || item.warehousing || item.Warehousing || item.part_name || item.Material || '';
              const registQuantity = item.Quantity || item.regist_quantity || item.RegistQuantity || item.quantity || 0;
              const currentQuantity = item.Quantity || item.current_quantity || item.CurrentQuantity || item.quantity || 0;
              
              row.innerHTML = `
                  <td style="padding: 6px; font-size: 10px;">${equipment}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${slotNo}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${baseFeeder}</td>
                  <td style="padding: 6px; font-size: 10px;">${registDate}</td>
                  <td style="padding: 6px; font-size: 10px;">${warehousing}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: right;">${registQuantity}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: right;">${currentQuantity}</td>
              `;
              
              // Efecto hover
              row.addEventListener('mouseenter', () => {
                  row.style.backgroundColor = '#485563';
              });
              row.addEventListener('mouseleave', () => {
                  row.style.backgroundColor = index % 2 === 0 ? '#40424F' : '#44475A';
              });
              
              tableBody.appendChild(row);
          });
          
          // Actualizar footer con el total de filas (template legacy)
          const footer = document.getElementById('materialHistoryFooter-Control de operacion de linea SMT');
          if (footer) {
              const totalOriginal = data.length;
              const totalFiltrado = dataFiltrada.length;
              const mostrados = Math.min(totalFiltrado, maxRows);
              
              if (lineaFiltro && isFiltered && selectedPlanId && totalFiltrado < totalOriginal) {
                  footer.textContent = `Total Rows : ${mostrados} (${totalFiltrado} de ${totalOriginal} - Filtrado por ${lineaFiltro})`;
              } else {
                  footer.textContent = `Total Rows : ${mostrados}${totalFiltrado > maxRows ? ` (mostrando ${maxRows})` : ''}`;
              }
          }
          // Actualizar footer alternativo (template aislado)
          const panelFooter = document.querySelector('#panel-mch .footer-row');
          if (panelFooter) {
              const totalOriginal = data.length;
              const totalFiltrado = dataFiltrada.length;
              const mostrados = Math.min(totalFiltrado, maxRows);
              
              if (lineaFiltro && isFiltered && selectedPlanId && totalFiltrado < totalOriginal) {
                  panelFooter.textContent = `Total Rows : ${mostrados} (${totalFiltrado} de ${totalOriginal} - Filtrado por ${lineaFiltro})`;
              } else {
                  panelFooter.textContent = `Total Rows : ${mostrados}${totalFiltrado > maxRows ? ` (mostrando ${maxRows})` : ''}`;
              }
          }
          
          // Aplicar scroll después de renderizar
          setTimeout(() => {
              // Buscar contenedor para aplicar scroll
              let container = tableBody.closest('.section-table-container');
              
              if (!container) {
                  container = tableBody.closest('div.table');
              }
              
              if (!container) {
                  container = tableBody.closest('.panel-body');
              }
              
              if (!container) {
                  let parent = tableBody.parentElement;
                  while (parent && parent.tagName !== 'DIV') {
                      parent = parent.parentElement;
                  }
                  container = parent;
              }
              
              if (container) {
                  // Aplicar estilos de scroll
                  container.style.setProperty('max-height', '400px', 'important');
                  container.style.setProperty('overflow-y', 'auto', 'important');
                  const esBom = container.id === 'tbl-bom' || container.closest('#panel-bom');
                  container.style.setProperty('overflow-x', esBom ? 'auto' : 'hidden', 'important');
                  container.style.setProperty('display', 'block', 'important');
              }
          }, 500);

          // Re-render del BOM para aplicar coincidencias si ya está cargado
          try {
              if (lastBomData && lastBomData.length && lastBomTableBody) {
                  renderizarTablaBom(lastBomData, lastBomTableBody);
              }
          } catch (e) {
              console.warn('No se pudo refrescar BOM tras historial:', e);
          }
      }
      
      // Función para exportar historial de material a Excel
      async function exportarHistorialMaterial() {
          try {
              console.log('Exportando historial de material...');
              showInfo('Preparando exportación de Material Changed History...');
              
              // Si hay datos cargados en lastHistoryDataNorm, usar esos datos
              let dataToExport = [];
              
              if (lastHistoryDataNorm && lastHistoryDataNorm.length > 0) {
                  // Usar datos ya normalizados y mostrados en pantalla
                  const tableBody = document.getElementById('materialHistoryTableBody-Control de operacion de linea SMT') ||
                                  document.querySelector('#tbl-mch table tbody');
                  
                  if (tableBody) {
                      const rows = tableBody.querySelectorAll('tr');
                      rows.forEach(row => {
                          const cells = row.querySelectorAll('td');
                          if (cells.length >= 7 && !cells[0].getAttribute('colspan')) {
                              dataToExport.push({
                                  equipment: cells[0].textContent.trim(),
                                  slot_no: cells[1].textContent.trim(),
                                  base_feeder: cells[2].textContent.trim(),
                                  regist_date: cells[3].textContent.trim(),
                                  warehousing: cells[4].textContent.trim(),
                                  regist_quantity: cells[5].textContent.trim(),
                                  current_quantity: cells[6].textContent.trim()
                              });
                          }
                      });
                  }
              }
              
              // Si no hay datos en pantalla, consultar API
              if (dataToExport.length === 0) {
                  const url = '/api/historial-cambio-material-maquina';
                  const response = await fetch(url);
                  
                  if (!response.ok) {
                      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                  }
                  
                  const result = await response.json();
                  
                  if (!result.success) {
                      throw new Error(result.error || 'Error en la respuesta del API');
                  }
                  
                  dataToExport = result.data || [];
              }
              
              if (dataToExport.length === 0) {
                  showWarning('No hay datos para exportar en Material Changed History');
                  return;
              }
              
              // Crear Excel usando SheetJS (si está disponible) o CSV como fallback
              if (typeof XLSX !== 'undefined') {
                  // Crear Excel usando SheetJS
                  const wsData = [
                      ['Equipment', 'Slot No', 'Base Feeder', 'Regist Date', 'Warehousing', 'Regist Quantity', 'Current Quantity'],
                      ...dataToExport.map(row => [
                          row.equipment || '',
                          row.slot_no || '',
                          row.base_feeder || '',
                          row.regist_date || '',
                          row.warehousing || '',
                          row.regist_quantity || 0,
                          row.current_quantity || 0
                      ])
                  ];
                  
                  const ws = XLSX.utils.aoa_to_sheet(wsData);
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, ws, 'Material History');
                  
                  // Configurar anchos de columna
                  ws['!cols'] = [
                      { width: 15 }, // Equipment
                      { width: 10 }, // Slot No
                      { width: 12 }, // Base Feeder
                      { width: 15 }, // Regist Date
                      { width: 20 }, // Warehousing
                      { width: 12 }, // Regist Quantity
                      { width: 12 }  // Current Quantity
                  ];
                  
                  const filename = `Material_Changed_History_${new Date().toISOString().slice(0, 10)}.xlsx`;
                  XLSX.writeFile(wb, filename);
                  showSuccess(`Archivo Excel exportado: ${filename}`);
              } else {
                  // Fallback a CSV
                  const headers = ['Equipment', 'Slot No', 'Base Feeder', 'Regist Date', 'Warehousing', 'Regist Quantity', 'Current Quantity'];
                  const csvContent = [
                      headers.join(','),
                      ...dataToExport.map(row => [
                          `"${row.equipment || ''}"`,
                          `"${row.slot_no || ''}"`,
                          `"${row.base_feeder || ''}"`,
                          `"${row.regist_date || ''}"`,
                          `"${row.warehousing || ''}"`,
                          row.regist_quantity || 0,
                          row.current_quantity || 0
                      ].join(','))
                  ].join('\n');
                  
                  // Crear archivo y descargar
                  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
                  const link = document.createElement('a');
                  const filename = `Material_Changed_History_${new Date().toISOString().slice(0, 10)}.csv`;
                  
                  if (link.download !== undefined) {
                      const url = URL.createObjectURL(blob);
                      link.setAttribute('href', url);
                      link.setAttribute('download', filename);
                      link.style.visibility = 'hidden';
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                      showSuccess(`Archivo CSV exportado: ${filename}`);
                  }
              }
              
          } catch (error) {
              console.error('Error exportando historial:', error);
              showError('Error al exportar Material Changed History: ' + error.message);
          }
      }

      // Función para exportar BOM List a Excel
      async function exportarBomList() {
          try {
              console.log('Exportando BOM List...');
              showInfo('Preparando exportación de BOM List...');
              
              // Verificar si hay datos de BOM cargados
              if (!lastBomData || lastBomData.length === 0) {
                  showWarning('No hay datos de BOM para exportar. Selecciona un plan primero.');
                  return;
              }
              
              // Preparar datos para exportación con información de matching
              const dataToExport = lastBomData.map(item => {
                  // Determinar match usando la misma lógica que en renderizarTablaBom
                  const bomSlot = item.slot;
                  const bomCode = item.material_code;
                  const bomMounter = item.mounter;
                  const bomSide = (item.tabla_tipo ? String(item.tabla_tipo).toUpperCase() : '') ||
                                  parseSideFromBaseFeeder(item.base_feeder || item.feeder_info || '');
                  const k = makeKey(bomSlot, bomCode, bomMounter, bomSide);
                  const isMatched = k && historyMatchKeys.has(k);
                  
                  return {
                      mounter: item.mounter || '',
                      slot: item.slot || '',
                      material_code: item.material_code || '',
                      description: item.description || '',
                      feeder_info: item.feeder_info || '',
                      qty: item.qty || 0,
                      type: item.tabla_tipo || '',
                      status: isMatched ? 'PASS' : 'NG',
                      verification_pass: isMatched ? 'YES' : 'NO'
                  };
              });
              
              // Crear Excel usando SheetJS (si está disponible) o CSV como fallback
              if (typeof XLSX !== 'undefined') {
                  // Crear Excel usando SheetJS
                  const wsData = [
                      ['Mounter', 'Slot', 'Material Code', 'Description', 'Feeder Info', 'Qty', 'Type', 'Status', 'Verification Pass'],
                      ...dataToExport.map(row => [
                          row.mounter,
                          row.slot,
                          row.material_code,
                          row.description,
                          row.feeder_info,
                          row.qty,
                          row.type,
                          row.status,
                          row.verification_pass
                      ])
                  ];
                  
                  const ws = XLSX.utils.aoa_to_sheet(wsData);
                  const wb = XLSX.utils.book_new();
                  XLSX.utils.book_append_sheet(wb, ws, 'BOM List');
                  
                  // Configurar anchos de columna
                  ws['!cols'] = [
                      { width: 12 }, // Mounter
                      { width: 8 },  // Slot
                      { width: 20 }, // Material Code
                      { width: 30 }, // Description
                      { width: 12 }, // Feeder Info
                      { width: 8 },  // Qty
                      { width: 10 }, // Type
                      { width: 10 }, // Status
                      { width: 15 }  // Verification Pass
                  ];
                  
                  const filename = `BOM_List_${new Date().toISOString().slice(0, 10)}.xlsx`;
                  XLSX.writeFile(wb, filename);
                  showSuccess(`Archivo Excel exportado: ${filename}`);
              } else {
                  // Fallback a CSV
                  const headers = ['Mounter', 'Slot', 'Material Code', 'Description', 'Feeder Info', 'Qty', 'Type', 'Status', 'Verification Pass'];
                  const csvContent = [
                      headers.join(','),
                      ...dataToExport.map(row => [
                          `"${row.mounter}"`,
                          `"${row.slot}"`,
                          `"${row.material_code}"`,
                          `"${row.description}"`,
                          `"${row.feeder_info}"`,
                          row.qty,
                          `"${row.type}"`,
                          `"${row.status}"`,
                          `"${row.verification_pass}"`
                      ].join(','))
                  ].join('\n');
                  
                  // Crear archivo y descargar
                  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
                  const link = document.createElement('a');
                  const filename = `BOM_List_${new Date().toISOString().slice(0, 10)}.csv`;
                  
                  if (link.download !== undefined) {
                      const url = URL.createObjectURL(blob);
                      link.setAttribute('href', url);
                      link.setAttribute('download', filename);
                      link.style.visibility = 'hidden';
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                      showSuccess(`Archivo CSV exportado: ${filename}`);
                  }
              }
              
              // Estadísticas de exportación
              const matched = dataToExport.filter(item => item.status === 'PASS').length;
              const pending = dataToExport.length - matched;
              showInfo(`Exportación completada: ${dataToExport.length} elementos (${matched} verificados, ${pending} pendientes)`);
              
          } catch (error) {
              console.error('Error exportando BOM:', error);
              showError('Error al exportar BOM List: ' + error.message);
          }
      }
      
      // Función para manejar cambio de línea
      function onLineaChange() {
          const linea = document.getElementById('linea-Control de operacion de linea SMT');
          if (linea) {
              console.log('Línea seleccionada:', linea.value);
              cargarHistorialMaterial(linea.value, 0);
          }
      }
      
      // Función para mostrar mensaje inicial en el historial
      function mostrarMensajeInicialHistorial() {
          const tableBody = document.getElementById('materialHistoryTableBody-Control de operacion de linea SMT');
          if (!tableBody) {
              // Buscar tabla alternativa
              const mchTable = document.querySelector('#tbl-mch table tbody');
              if (mchTable) {
                  mchTable.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 30px; color: #95A5A6; font-style: italic;">Selecciona un plan para ver el historial de materiales</td></tr>';
              }
              return;
          }
          
          tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 30px; color: #95A5A6; font-style: italic;">Selecciona un plan para ver el historial de materiales</td></tr>';
          
          // Actualizar footer
          const footer = document.getElementById('materialHistoryFooter-Control de operacion de linea SMT');
          if (footer) {
              footer.textContent = 'Total Rows : 0';
          }
          const panelFooter = document.querySelector('#panel-mch .footer-row');
          if (panelFooter) {
              panelFooter.textContent = 'Total Rows : 0';
          }
      }

      // ==========================
      // INTEGRACIÓN CON SISTEMA DE BOM LIST
      // ==========================
      
      // Función para cargar datos del BOM SMT basado en línea y modelo
      async function cargarBomList(linea, modelCode, intentos = 0) {
          console.log('Cargando BOM List para:', { linea, modelCode });
          
          let tableBody = document.querySelector('#panel-bom table tbody');
          
          // Crear tbody si no existe
          if (!tableBody) {
              const bomTable = document.querySelector('#panel-bom table');
              if (bomTable) {
                  tableBody = document.createElement('tbody');
                  bomTable.appendChild(tableBody);
              }
          }
          
          if (!tableBody) {
              const maxIntentos = 10;
              if (intentos < maxIntentos) {
                  console.warn(`Tabla BOM no encontrada (intento ${intentos + 1}/${maxIntentos}), reintentando...`);
                  setTimeout(() => cargarBomList(linea, modelCode, intentos + 1), 300);
                  return;
              }
              console.error('No se encontró la tabla BOM tras varios intentos');
              return;
          }
          
          try {
              // Construir URL del endpoint
              const equipoSMT = mapearLineaAEquipo(linea);
              const url = `/api/bom-smt-data?linea=${encodeURIComponent(equipoSMT)}&model_code=${encodeURIComponent(modelCode)}`;
              
              console.log('Cargando BOM desde:', url);
              
              const response = await fetch(url);
              if (!response.ok) {
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
              }
              
              const result = await response.json();
              
              if (!result.success) {
                  throw new Error(result.error || 'Error en la respuesta del API');
              }
              
              const data = result.data || [];
              console.log(`BOM cargado: ${data.length} elementos`);
              
              // Guardar para aplicar matching con historial y re-renders
              lastBomData = data;
              lastBomTableBody = tableBody;
              
              // Renderizar datos en la tabla BOM (aplicará matching si existe historial)
              renderizarTablaBom(lastBomData, lastBomTableBody);
              
          } catch (error) {
              console.error('Error cargando BOM:', error);
              if (tableBody) {
                  tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px; color: #E74C3C;">Error cargando datos del BOM</td></tr>';
              }
          }
      }
      
      // Función para renderizar la tabla del BOM
      function renderizarTablaBom(data, tableBody) {
          if (!tableBody) {
              console.error('TableBody del BOM es null');
              return;
          }
          
          // Limpiar tabla
          tableBody.innerHTML = '';
          
          if (data.length === 0) {
              tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px; color: #95A5A6;">No hay datos de BOM disponibles</td></tr>';
              return;
          }
          
          // Renderizar filas con lógica de match (slot + material_code + mounter + side)
          data.forEach((item, index) => {
              const row = document.createElement('tr');
              
              // Determinar match: slot + material_code + mounter presentes en historial
              const bomSlot = item.slot;
              const bomCode = item.material_code;
              const bomMounter = item.mounter;
              // Intentar obtener lado desde tipo explícito o desde feeder info como respaldo
              const bomSide = (item.tabla_tipo ? String(item.tabla_tipo).toUpperCase() : '') ||
                              parseSideFromBaseFeeder(item.base_feeder || item.feeder_info || '');
              const k = makeKey(bomSlot, bomCode, bomMounter, bomSide);
              const isMatched = k && historyMatchKeys.has(k);
              const statusClass = isMatched ? 'bom-matched' : 'bom-pending';
              row.className = statusClass;
              
              row.innerHTML = `
                  <td style="padding: 6px; font-size: 10px;">${item.mounter || ''}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${item.slot || ''}</td>
                  <td style="padding: 6px; font-size: 10px;">${item.material_code || ''}</td>
                  <td style="padding: 6px; font-size: 10px;">${item.description || ''}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${item.feeder_info || ''}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${item.qty || 0}</td>
                  <td style="padding: 6px; font-size: 10px; text-align: center;">${item.tabla_tipo || ''}</td>
                  <td style="padding: 6px; font-size: 10px;">
                      <span class="status-indicator ${statusClass}">
                          ${isMatched ? 'PASS' : 'NG'}
                      </span>
                  </td>
              `;
              
              // Efecto hover
              row.addEventListener('mouseenter', () => {
                  row.style.backgroundColor = '#485563';
              });
              row.addEventListener('mouseleave', () => {
                  row.style.backgroundColor = index % 2 === 0 ? '#40424F' : '#44475A';
              });
              
              tableBody.appendChild(row);
          });
          
          // Actualizar footer del BOM (usando coincidencias calculadas)
          const bomFooter = document.querySelector('#panel-bom .footer-row');
          if (bomFooter) {
              let matched = 0;
              data.forEach(it => {
                  const side = (it.tabla_tipo ? String(it.tabla_tipo).toUpperCase() : '') ||
                               parseSideFromBaseFeeder(it.base_feeder || it.feeder_info || '');
                  const key = makeKey(it.slot, it.material_code, it.mounter, side);
                  if (key && historyMatchKeys.has(key)) matched++;
              });
              const pending = Math.max(0, data.length - matched);
              bomFooter.textContent = `Total: ${data.length} | Pendientes: ${pending} | Verificados: ${matched}`;
          }
          
          // Aplicar scroll después de renderizar
          setTimeout(() => {
              // Usar siempre el contenedor específico del BOM para el scroll interno
              let bomContainer = document.getElementById('tbl-bom');
              if (!bomContainer) {
                  // Fallback: contenedor .table más cercano
                  bomContainer = tableBody.closest('#panel-bom .table') || tableBody.closest('#tbl-bom');
              }
              if (bomContainer) {
                  // Aplicar estilos de scroll al BOM (contenedor interno)
                  bomContainer.style.setProperty('max-height', '400px', 'important');
                  bomContainer.style.setProperty('overflow-y', 'auto', 'important');
                  bomContainer.style.setProperty('overflow-x', 'auto', 'important');
                  bomContainer.style.setProperty('display', 'block', 'important');
                  console.log('Scroll interno aplicado al BOM:', bomContainer);
              }
          }, 500);
      }
      
      // Función para mostrar mensaje inicial en el BOM
      function mostrarMensajeInicialBom() {
          const tableBody = document.querySelector('#panel-bom table tbody');
          if (!tableBody) return;
          
          tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 30px; color: #95A5A6; font-style: italic;">Selecciona un plan para ver el BOM</td></tr>';
          
          // Actualizar footer del BOM
          const bomFooter = document.querySelector('#panel-bom .footer-row');
          if (bomFooter) {
              bomFooter.textContent = 'Total: 0 | Pendientes: 0 | Verificados: 0';
          }
      }

      // Exponer funciones para uso externo
      window.cargarHistorialMaterialPorLinea = cargarHistorialMaterial;
      window.exportarHistorialMaterial = exportarHistorialMaterial;
      window.exportarBomList = exportarBomList;
      window.onLineaChange = onLineaChange;
      window.mostrarMensajeInicialHistorial = mostrarMensajeInicialHistorial;
      window.cargarBomList = cargarBomList;
      window.mostrarMensajeInicialBom = mostrarMensajeInicialBom;
      
      // Funciones adicionales para compatibilidad con botones externos
      window.exportBomToExcel = exportarBomList;
      window.exportHistoryToExcel = exportarHistorialMaterial;
      window.exportBOMList = exportarBomList;
      window.exportMaterialHistory = exportarHistorialMaterial;



      // ==========================
      // Actualización en tiempo real
      // ==========================
      (function setupLiveRefresh(){
        const REFRESH_MS = 15000; // 15s por defecto
        let liveTimer = null;

        function buildListUrlFromUI(){
          const params = new URLSearchParams();
          const lotEl = document.getElementById('lotNo');
          const selLine = document.getElementById('selLine');
          const chk = document.getElementById('chk-show-planned');
          const d1 = document.getElementById('dateFrom');
          const d2 = document.getElementById('dateTo');
          if (lotEl && lotEl.value) params.set('q', lotEl.value.trim());
          if (selLine && selLine.value && selLine.value !== 'ALL') params.set('linea', selLine.value);
          if (chk && chk.checked){
            params.set('solo_pendientes','true');
          } else {
            if (d1 && d1.value) params.set('desde', d1.value);
            if (d2 && d2.value) params.set('hasta', d2.value);
          }
          return `/api/plan-smd/list?${params.toString()}`;
        }

        function computeStatus(item){
          const total = (item.producido||0) + (item.falta||0);
          const pct = Math.min(100, Math.round(((item.producido || 0) / (total || 1)) * 100));
          let statusClass = 'pending';
          if (item.run_status === 'RUNNING') statusClass = 'partial';
          else if (item.run_status === 'PAUSED') statusClass = 'warning';
          else if (item.run_status === 'ENDED' || item.estatus === 'FINALIZADO' || pct >= 100) statusClass = 'completed';
          else if (pct > 0) statusClass = 'partial';
          return { pct, statusClass };
        }

        function updateRowLive(item){
          // Mantener mapeo plan->run para soportar múltiples activos
          try {
            if (item && item.id) {
              const key = String(item.id);
              const map = JSON.parse(localStorage.getItem('smtRunMap')||'{}');
              if (item.run_status === 'RUNNING' && item.run_id) {
                map[key] = Number(item.run_id);
                localStorage.setItem('smtRunMap', JSON.stringify(map));
              } else if (item.run_status === 'ENDED') {
                if (key in map) { delete map[key]; localStorage.setItem('smtRunMap', JSON.stringify(map)); }
              }
            }
          } catch(_){}
          const row = document.querySelector(`tr[data-plan-id="${item.id}"]`);
          if (!row) return;
          const { pct, statusClass } = computeStatus(item);
          // celdas: 9: Qty, 10: Producido, 11: Falta, 12: %, 13: progress, 15: Estatus
          const tdProducido = row.children[9];
          const tdFalta = row.children[10];
          const tdPct = row.children[11];
          const tdProg = row.children[12];
          const tdEstatus = row.children[14];
          if (tdProducido) tdProducido.textContent = String(item.producido || 0);
          if (tdFalta) tdFalta.textContent = String(item.falta || 0);
          if (tdPct) tdPct.innerHTML = `<span class="status-tag ${statusClass}">${pct}%</span>`;
          if (tdProg) {
            const span = tdProg.querySelector('span');
            if (span) span.style.width = `${pct}%`;
          }
          if (tdEstatus) tdEstatus.innerHTML = `<span class="status-tag ${statusClass}">${item.run_status==='RUNNING'?'INICIADO': (item.estatus || 'PLANEADO')}</span>`;
          row.classList.remove('run-active','run-paused','run-completed');
          if (item.run_status === 'RUNNING') row.classList.add('run-active');
          else if (item.run_status === 'PAUSED') row.classList.add('run-paused');
          else if (item.estatus === 'FINALIZADO' || item.run_status === 'ENDED') row.classList.add('run-completed');
        }

        async function liveTick(){
          try{
            // Si hay un plan filtrado, traer solo ese
            if (typeof selectedPlanId !== 'undefined' && selectedPlanId){
              const r = await fetch(`/api/plan-smd/list?plan_id=${selectedPlanId}`);
              const j = await r.json();
              const rows = Array.isArray(j) ? j : (j.rows||[]);
              rows.forEach(updateRowLive);
              return;
            }
            // Si no, refrescar todos los visibles con los filtros actuales
            const url = buildListUrlFromUI();
            const r = await fetch(url);
            const j = await r.json();
            const rows = Array.isArray(j) ? j : (j.rows||[]);
            rows.forEach(updateRowLive);
          }catch(e){
            console.warn('Live refresh error:', e);
          }
        }

        function start(){
          if (liveTimer) return;
          liveTimer = setInterval(liveTick, REFRESH_MS);
        }
        function stop(){
          if (liveTimer) clearInterval(liveTimer);
          liveTimer = null;
        }

        document.addEventListener('visibilitychange', ()=>{
          if (document.hidden) stop(); else start();
        });
        // Exponer por si se desea controlar
        window.startSmtLiveRefresh = start;
        window.stopSmtLiveRefresh = stop;

        // Arrancar tras un pequeño delay para permitir el primer render
        setTimeout(start, 1200);
      })();

})();






