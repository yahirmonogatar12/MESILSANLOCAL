// Control de Operación Línea SMT - Integración con Plan SMD
(function() {
  console.log('🚀 Inicializando Control de Operación Línea SMT AJAX...');
  
  // Variables globales
  let currentPlanData = [];
  let filteredPlanData = [];
  let selectedPlanId = null;
  let currentRunId = null;
  let isFiltered = false; // Nueva variable para controlar el estado de filtro
  let autoRefreshInterval = null;
  let isInitialized = false;
      
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
          console.warn('⚠️ Error en recarga rápida:', error);
          // En caso de error, hacer recarga completa
          setTimeout(() => cargarDatosPlanSMD(), 500);
        }
      }

      // FunciÃ³n para cargar datos del plan SMD
      async function cargarDatosPlanSMD() {
        if (!getElements()) {
          console.warn('âš ï¸ Elementos no encontrados, reintentando...');
          setTimeout(cargarDatosPlanSMD, 1000);
          return;
        }
        
        try {
          // Filtros de búsqueda
          const params = new URLSearchParams();
          const lotEl = document.getElementById('lotNo');
          if (lotEl && lotEl.value) params.set('q', lotEl.value.trim());
          if (elements.selLine && elements.selLine.value && elements.selLine.value !== 'ALL') { 
            console.log('🔍 Filtro de línea aplicado:', elements.selLine.value);
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
        console.log('📡 URL de consulta:', url);
        
        elements.placeholder.textContent = 'Loading data...';
        elements.placeholder.style.display = 'grid';
        
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const rows = Array.isArray(data) ? data : (data.rows || []);
        currentPlanData = rows;
        
        console.log(`📊 Datos recibidos: ${rows.length} planes`);
        if (rows.length > 0) {
          console.log('📋 Líneas encontradas:', [...new Set(rows.map(r => r.linea))]);
        }
        
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
              // Requerir selección explícita para evitar finalizar el plan equivocado
              if (!selectedPlanId) {
                showError('SELECCIÓN REQUERIDA → Doble clic en el plan a finalizar');
                return;
              }
              // Confirmación con detalles del plan
              const datos = (isFiltered ? filteredPlanData : currentPlanData) || [];
              const planRow = datos.find(x => x && Number(x.id) === Number(selectedPlanId));
              if (!planRow) {
                showError('PLAN NO ENCONTRADO → Actualiza la lista y vuelve a intentar');
                return;
              }
              const confirmMsg = `Finalizar plan:\nLinea: ${planRow.linea || ''}\nLot: ${planRow.lote || ''}\nNParte: ${planRow.nparte || ''}.\n¿Confirmar?`;
              if (!window.confirm(confirmMsg)) { return; }
              // Resolver run_id del plan seleccionado
              let ridMap = null;
              try { const map = JSON.parse(localStorage.getItem('smtRunMap')||'{}'); ridMap = map[String(selectedPlanId)]||null; } catch(_){}
              if (!ridMap) {
                const row2 = datos.find(x => x && Number(x.id) === Number(selectedPlanId));
                ridMap = row2 && row2.run_id ? Number(row2.run_id) : null;
              }
              if (!ridMap) {
                try{
                  const respRun = await fetch(`/api/plan-smd/list?plan_id=${selectedPlanId}`);
                  const jr = await respRun.json();
                  const rr = Array.isArray(jr)? jr[0] : (jr.rows && jr.rows[0]);
                  if (rr && rr.run_id) ridMap = Number(rr.run_id);
                }catch(_){/* ignore */}
              }
              if (ridMap) currentRunId = ridMap;
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
          console.error('âŒ Error cargando datos:', error);
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
          
          row.addEventListener('dblclick', () => { 
            selectedPlanId = item.id; 
            try{ 
              localStorage.setItem('smtSelectedPlanId', String(selectedPlanId||'')); 
            }catch(e){} 
            
            // Activar modo enfoque en lugar de solo resaltar
            filtrarPorPlan(selectedPlanId);
          });
          
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
      
      // FunciÃ³n para configurar event listeners
      function setupEventListeners() {
        if (!getElements()) return;
        if (elements.btnSearch) {
          elements.btnSearch.addEventListener('click', () => {
            // Salir del modo enfoque cuando se presiona Search
            if (isFiltered) {
              isFiltered = false;
              filteredPlanData = [];
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
            console.log('📋 Mostrar planeadas:', elements.chkShowPlanned.checked);
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
            console.log('â¸ï¸ Stop clicked');
          });
        }
      }
      
      // FunciÃ³n principal de inicializaciÃ³n
      function inicializar() {
        if (isInitialized) {
          console.log('âš ï¸ Ya inicializado, omitiendo...');
          return;
        }
        
        console.log('âœ… Inicializando Control de OperaciÃ³n SMT AJAX...');
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
      
      // Auto-inicialización
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
