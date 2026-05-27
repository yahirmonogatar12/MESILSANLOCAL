// ====== Cargar CSS persistente (WF_004) ======
// Idempotente: solo inyecta el <link> si no existe ya en el DOM.
(function ensureAssyModuleStyles(){
  const STYLESHEET_ID = "control-plan-assy-css";
  const STYLESHEET_HREF = "/static/css/control_plan_assy.css?v=20260526a";
  if (!document.getElementById(STYLESHEET_ID)) {
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }
})();

// ====== plan-assy-core.js (loadPlans, edit/cancel, createModalsInBody, initializePlanEventListeners) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

// loadPlans: fetch + render. Despacha a renderTableWithVisualGroups (grupos) o
// renderTableByLines (vista lineas) segun currentViewMode (definido en plan-assy-groups.js).
// Esta funcion era el "override" que en plan.js original vivia al final (linea 4608)
// y reemplazaba la version plana. Aqui ya es la unica version.
async function loadPlans() {
  try {
    showTableBodyLoading('assy-tableBody', 'Cargando planes...', 22);

    setDefaultDateFilters();
    const fs = document.getElementById("assy-filter-start")?.value;
    const fe = document.getElementById("assy-filter-end")?.value;
    let url = "/api/plan";
    const params = [];
    if (fs) params.push(`start=${encodeURIComponent(fs)}`);
    if (fe) params.push(`end=${encodeURIComponent(fe)}`);
    if (params.length) url += `?${params.join("&")}`;

    let res = await axios.get(url);
    let data = Array.isArray(res.data) ? res.data.slice() : [];

    // Guardar copia profunda de los datos originales para recuperar al reorganizar
    originalPlansData = data.map(plan => ({ ...plan }));

    // Aplicar orden guardado (si existe) antes de renderizar
    data = applySavedOrderToData(data, fs, fe);

    // Renderizar segun el modo de vista actual
    if (typeof currentViewMode !== 'undefined' && currentViewMode === 'lines') {
      // En modo lineas, poblar el filtro y renderizar por lineas
      if (typeof populateLineFilter === 'function') populateLineFilter(data);
      const lineFilter = document.getElementById('assy-line-filter');
      const selectedLine = lineFilter ? lineFilter.value : '';
      if (typeof renderTableByLines === 'function') renderTableByLines(selectedLine);
    } else {
      // Vista por grupos visuales (default)
      if (typeof renderTableWithVisualGroups === 'function') {
        renderTableWithVisualGroups(data);
      } else {
        console.error('renderTableWithVisualGroups no esta disponible - verifica que plan-assy-groups.js se cargo antes de plan-assy-core.js');
      }
    }
  } catch (error) {
    alert("Error al cargar planes: " + (error.response?.data?.error || error.message));
    let tbody = document.getElementById("assy-tableBody");
    if (tbody) {
      tbody.innerHTML = `<tr class="message-row"><td colspan="22" style="display: table-cell; text-align: center; padding: 20px; color: #888;">Error al cargar los datos</td></tr>`;
    }
  }
}

async function openEditModal(lotNo) {
  try {
    // Mostrar modal inmediatamente con loading
    const modal = document.getElementById("assy-editModal");
    const form = document.getElementById("assy-editForm");

    // CRÍTICO: Limpiar tanto display como visibility
    modal.style.display = "flex";
    modal.style.visibility = "visible";

    // Ocultar el formulario mientras carga
    form.style.display = "none";

    showTableLoading('assy-modal-content', 'Cargando datos del plan...');

    // Hacer la consulta a la API
    let res = await axios.get("/api/plan");
    let plan = res.data.find(p => p.lot_no === lotNo);

    if (!plan) {
      hideTableLoading('assy-modal-content');
      modal.style.display = "none";
      return alert("Plan no encontrado");
    }

    // Llenar el formulario con los datos
    form.lot_no.value = plan.lot_no;

    // Set turno based on routing
    const turnoSel = form.elements["turno"];
    if (turnoSel) {
      turnoSel.value = routingToTurno(plan.routing) || "DIA";
    }

    form.plan_count.value = plan.plan_count;
    form.wo_code.value = plan.wo_code || "";
    form.po_code.value = plan.po_code || "";
    form.line.value = plan.line;
    await loadPlanBomRevisionOptions(
      plan.part_no,
      plan.assigned_bom_rev,
      document.getElementById('assy-edit-assigned-bom-rev')
    );

    // *** NUEVO: Cambiar botón según estado del plan ***
    const cancelBtn = document.getElementById('assy-cancelBtn');
    if (cancelBtn) {
      if (plan.status === 'CANCELADO') {
        // Plan cancelado - mostrar botón PLANEAR en verde
        cancelBtn.textContent = 'Planear';
        cancelBtn.style.background = '#27ae60'; // Verde
        cancelBtn.dataset.action = 'reactivar';
      } else {
        // Plan activo - mostrar botón CANCELAR en rojo
        cancelBtn.textContent = 'Cancelar plan';
        cancelBtn.style.background = '#e74c3c'; // Rojo
        cancelBtn.dataset.action = 'cancelar';
      }
    }

    // Pequeoa pausa para mejor UX (monimo 500ms para que se vea el loading)
    await new Promise(resolve => setTimeout(resolve, 300));

    // Ocultar loading y mostrar formulario con animacion suave
    hideTableLoading('assy-modal-content');
    form.style.display = "block";
    form.style.opacity = "0";
    form.style.transform = "translateY(10px)";

    // Animacion de entrada
    setTimeout(() => {
      form.style.transition = "all 0.3s ease";
      form.style.opacity = "1";
      form.style.transform = "translateY(0)";
    }, 50);

  } catch (error) {
    hideTableLoading('assy-modal-content');
    document.getElementById("assy-editModal").style.display = "none";
    alert("Error al cargar datos del plan: " + (error.response?.data?.error || error.message));
  }
}

// Guardar edicion
// ========= PLAN EDIT FORM HANDLERS (Ahora manejados por Event Delegation) =========

/**
 * Manejar submit del formulario de edicion de plan
 */
async function handleEditPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn?.textContent || 'Guardar';

  try {
    // Cambiar el boton a estado de carga
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Validando...';
      submitBtn.style.backgroundColor = '#6c757d';
      submitBtn.style.cursor = 'not-allowed';
    }

    // *** VALIDACIÓN: Verificar conflictos de línea/horario ***
    const conflicto = validarConflictoLineaHorario(data);
    if (conflicto) {
      // Mostrar modal de advertencia con el conflicto
      showWarningModal(conflicto.mensaje);
      
      // Re-habilitar botón
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        submitBtn.style.backgroundColor = '';
        submitBtn.style.cursor = '';
      }
      return; // Detener el guardado
    }

    if (submitBtn) {
      submitBtn.innerHTML = 'Actualizando...';
    }

    showTableLoading('assy-modal-content', 'Buscando Work Order y datos actualizados en RAW...');

    // Buscar datos actualizados en la tabla RAW antes de guardar
    try {
      // El formulario no tiene part_no, pero tiene wo_code
      // Primero buscar el WO para obtener el part_no (modelo)
      const woCode = data.wo_code;

      if (woCode && woCode !== 'SIN-WO') {
        // Buscar el WO en la tabla work_orders
        const woResponse = await axios.get(`/api/work_orders?include_import_status=1&q=${encodeURIComponent(woCode)}`);

        if (woResponse.data && woResponse.data.length > 0) {
          // Filtrar exactamente el WO que coincide con wo_code
          const woData = woResponse.data.find(wo => wo.codigo_wo === woCode);

          if (woData) {
            const partNo = woData.modelo; // El campo en work_orders se llama 'modelo'

            if (partNo) {
              // Buscar en RAW con timeout de 5 segundos
              let rawResponse = null;
              try {
                const timeoutPromise = new Promise((_, reject) => {
                  setTimeout(() => reject(new Error('Timeout: La peticion tardo mos de 5 segundos')), 5000);
                });

                const axiosPromise = axios.get(`/api/raw/search?part_no=${encodeURIComponent(partNo)}`, {
                  timeout: 5000,
                  headers: {
                    'Content-Type': 'application/json'
                  }
                });

                rawResponse = await Promise.race([axiosPromise, timeoutPromise]);
              } catch (axiosError) {
                console.error('Error al buscar datos en RAW:', axiosError.message);
                rawResponse = null;
              }

              if (rawResponse && rawResponse.status === 200) {
                if (rawResponse.data && rawResponse.data.length > 0) {
                  const rawData = rawResponse.data[0];

                  // Actualizar datos desde RAW
                  data.part_no = partNo;
                  data.uph = rawData.uph || 0;
                  data.ct = rawData.ct || 0;
                  data.project = rawData.project || '';
                  data.model_code = rawData.model_code || rawData.model || '';
                } else {
                  // Actualizar al menos el part_no
                  data.part_no = partNo;
                }
              } else {
                // Actualizar al menos el part_no aunque falle la bosqueda en RAW
                data.part_no = partNo;
              }
            }
          }
        }
      }
    } catch (rawError) {
      console.error('Error al buscar datos en RAW:', rawError.message);
    }

    showTableLoading('assy-modal-content', 'Actualizando plan...');

    const updateResponse = await axios.post("/api/plan/update", data);

    // Mostrar modal de oxito
    showSuccessModal(`Plan ${data.lot_no} actualizado exitosamente`);

    document.getElementById("assy-editModal").style.display = "none";
    await loadPlans();
    await saveGroupSequences({ silent: true });
  } catch (error) {
    console.error('Error en handleEditPlanSubmit:', error);
    alert("Error actualizando plan: " + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar boton
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
      submitBtn.style.backgroundColor = '';
      submitBtn.style.cursor = '';
    }
    hideTableLoading('assy-modal-content');
  }
}

/**
 * Manejar cancelacion de plan
 */
async function handleCancelPlan() {
  const form = document.getElementById("assy-editForm");
  if (!form) return;

  const lot = form.lot_no.value;
  if (!lot) return;
  
  const cancelBtn = document.getElementById("assy-cancelBtn");
  const action = cancelBtn?.dataset.action || 'cancelar';
  
  // Determinar acción y mensaje según el estado
  const esCancelar = action === 'cancelar';
  const confirmMsg = esCancelar 
    ? `¿Cancelar plan ${lot}?` 
    : `¿Reactivar plan ${lot}?`;
  const nuevoEstado = esCancelar ? 'CANCELADO' : 'PLAN';
  const loadingMsg = esCancelar ? 'Cancelando plan...' : 'Reactivando plan...';
  const successMsg = esCancelar 
    ? `Plan ${lot} cancelado exitosamente` 
    : `Plan ${lot} reactivado exitosamente`;
  
  if (!confirm(confirmMsg)) return;

  const originalText = cancelBtn?.textContent || (esCancelar ? 'Cancelar plan' : 'Planear');

  try {
    // Cambiar el boton a estado de carga
    if (cancelBtn) {
      cancelBtn.disabled = true;
      cancelBtn.innerHTML = esCancelar ? 'Cancelando...' : 'Reactivando...';
      cancelBtn.style.backgroundColor = '#6c757d';
      cancelBtn.style.cursor = 'not-allowed';
    }

    showTableLoading('plan-editModal-content', loadingMsg);

    await axios.post("/api/plan/update", { lot_no: lot, status: nuevoEstado });

    // Mostrar modal de éxito
    showSuccessModal(successMsg);

    document.getElementById("assy-editModal").style.display = "none";
    await loadPlans();
    await saveGroupSequences({ silent: true });
  } catch (error) {
    alert(`Error ${esCancelar ? 'cancelando' : 'reactivando'} plan: ` + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar boton
    if (cancelBtn) {
      cancelBtn.disabled = false;
      cancelBtn.innerHTML = originalText;
      cancelBtn.style.backgroundColor = '';
      cancelBtn.style.cursor = '';
    }
    hideTableLoading('plan-editModal-content');
  }
}

function validarConflictoLineaHorario(nuevoPlan) {
  // console.log(' Validando conflictos de línea/horario para:', nuevoPlan);
  
  // *** CORRECCIÓN: Obtener planes desde visualGroups ***
  const todosLosPlanes = [];
  visualGroups.groups.forEach(group => {
    todosLosPlanes.push(...group.plans);
  });
  
  // Crear array de planes con sus horarios calculados
  const planesConHorario = [];
  
  todosLosPlanes.forEach(plan => {
    // Excluir el propio plan si es edición y planes cancelados
    if (plan.lot_no === nuevoPlan.lot_no || plan.status === 'CANCELADO') {
      return;
    }
    
    // Obtener cálculos del plan (si ya están calculados)
    const calc = planningCalculations.get(plan.lot_no);
    
    planesConHorario.push({
      lot_no: plan.lot_no,
      line: plan.line,
      fecha: plan.working_date,
      inicio: calc?.startTime || null,
      model_code: plan.model_code,
      group_no: calc?.groupNumber || plan.group_no
    });
  });
  
  // console.log(` Comparando contra ${planesConHorario.length} planes activos`);
  
  // Para el nuevo plan, necesitamos calcular su hora de inicio
  // Buscar en qué grupo estaría y calcular su posición
  let horaInicioNuevoPlan = nuevoPlan.inicio || currentConfig.shiftStart;
  
  // Si el nuevo plan tiene target_group o group_no, calcular su inicio basado en ese grupo
  const grupoDestino = parseInt(nuevoPlan.target_group || nuevoPlan.group_no || 0);
  if (grupoDestino > 0 && visualGroups.groups && visualGroups.groups.length >= grupoDestino) {
    // El nuevo plan iría al inicio del grupo (asumiendo que sería el primer plan)
    // Por simplicidad, usamos el inicio del turno
    horaInicioNuevoPlan = currentConfig.shiftStart;
  }
  
 // console.log(` Hora de inicio del nuevo plan: ${horaInicioNuevoPlan}`);
  
  // Buscar conflictos: misma línea Y misma hora de inicio
  for (const planExistente of planesConHorario) {
    // Comparar línea
    const mismaLinea = planExistente.line === nuevoPlan.line;
    
    // Comparar fecha
    const mismaFecha = planExistente.fecha === (nuevoPlan.fecha || nuevoPlan.working_date);
    
    // Comparar hora de inicio (solo si el plan existente tiene hora calculada)
    const mismoInicio = planExistente.inicio && planExistente.inicio === horaInicioNuevoPlan;
    
    if (mismaLinea && mismaFecha && mismoInicio) {
      // console.log(' Conflicto detectado:', { planExistente, nuevoPlan, grupoDestino, horaInicioNuevoPlan });
      
      return {
        planConflicto: planExistente,
        mensaje: `⚠️ CONFLICTO DETECTADO\n\n` +
                `Ya existe un plan en la misma línea y horario:\n\n` +
                `Línea: ${planExistente.line}\n` +
                `Fecha: ${planExistente.fecha}\n` +
                `Hora Inicio: ${planExistente.inicio}\n` +
                `Modelo: ${planExistente.model_code}\n` +
                `Lot No: ${planExistente.lot_no}\n` +
                `Grupo: ${planExistente.group_no || 'Sin asignar'}\n\n` +
                `No se puede crear/editar un plan con el mismo horario en la misma línea.`
      };
    }
  }
  
  // console.log(' No se detectaron conflictos');
  return null;
}

async function handleNewPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  
  // 🎯 Renombrar target_group a group_no para enviarlo al backend
  if (data.target_group && data.target_group !== '0') {
    data.group_no = parseInt(data.target_group); // El backend espera group_no
  }
  delete data.target_group; // Eliminar campo temporal

  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn?.textContent || 'Registrar';

  try {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Validando...';
      submitBtn.style.cursor = 'not-allowed';
    }

    // *** NUEVA LÓGICA: Si hay conflicto, mover al final del grupo con conflicto ***
    const conflicto = validarConflictoLineaHorario(data);
    if (conflicto) {
 // console.log(' Conflicto detectado, buscando grupo del plan conflictivo...');
      
      // Buscar en qué grupo está el plan con conflicto
      const planConflictivo = conflicto.planConflicto;
      let grupoDestino = null;
      
      // Buscar el grupo del plan conflictivo en visualGroups
      for (let i = 0; i < visualGroups.groups.length; i++) {
        const group = visualGroups.groups[i];
        const planEnGrupo = group.plans.find(p => p.lot_no === planConflictivo.lot_no);
        if (planEnGrupo) {
          grupoDestino = i + 1; // Los grupos son 1-indexed
          // console.log(` Plan conflictivo ${planConflictivo.lot_no} encontrado en GRUPO ${grupoDestino}`);
          break;
        }
      }
      
      if (grupoDestino) {
        // Asignar el nuevo plan al final de ese grupo
        data.group_no = grupoDestino;
 // console.log(` Asignando nuevo plan al GRUPO ${grupoDestino} (al final del grupo con conflicto)`);
        
        // Mostrar notificación informativa (no bloqueante)
 // console.log(`ℹ Plan agregado al final del GRUPO ${grupoDestino} debido a conflicto de horario en línea ${data.line}`);
      } else {
 console.warn(' No se encontró el grupo del plan conflictivo, continuando sin asignación automática');
      }
    }
    
    if (submitBtn) {
      submitBtn.textContent = 'Guardando...';
    }

    // Crear el plan en el backend (ahora incluye group_no)
    const response = await axios.post("/api/plan", data);
    const newPlan = response.data;

    // Mostrar modal de éxito
    showSuccessModal('Plan registrado exitosamente');

    document.getElementById("assy-modal").style.display = "none";
    form.reset();
    
    // Recargar planes - ahora el plan ya viene con su grupo asignado desde la BD
    await loadPlans();
    await saveGroupSequences({ silent: true });
    
    // Ya no necesitamos mover manualmente porque el plan ya tiene group_no en la BD
    // El renderTableWithVisualGroups() respetará el group_no del backend
    
  } catch (error) {
    alert("Error registrando plan: " + (error.response?.data?.error || error.message));
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
      submitBtn.style.cursor = '';
    }
  }
}

function createModalsInBody() {
  // console.log('??? Creando modales dinomicamente en el body...');

  // Verificar que los estilos CSS eston cargados
  const testDiv = document.createElement('div');
  testDiv.className = 'modal-overlay';
  testDiv.style.display = 'none';
  document.body.appendChild(testDiv);
  const computedStyle = window.getComputedStyle(testDiv);
  // console.log('?? Estilos CSS de modal-overlay:', { position: computedStyle.position, zIndex: computedStyle.zIndex, display: computedStyle.display });
  document.body.removeChild(testDiv);

  // Modal de Nuevo Plan
  if (!document.getElementById('assy-modal')) {
    // console.log('?? Creando modal plan-modal');
    const planModal = document.createElement('div');
    planModal.id = 'assy-modal';
    planModal.className = 'modal-overlay';

    // IMPORTANTE: Agregar estilos inline como fallback
    planModal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.6);
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    planModal.innerHTML = `
      <div id="assy-modal-content" style="
        background: #34334E; 
        border-radius: 8px; 
        padding: 20px; 
        width: 90%;
        max-width: 500px; 
        max-height: 90vh;
        overflow-y: auto;
        color: lightgray;
        box-sizing: border-box;
        margin: 10px;
      ">
        <h3 style="margin: 0 0 15px 0; color: #ecf0f1; font-size: clamp(16px, 4vw, 20px); text-align: center;">Registrar Plan</h3>
        <form id="assy-form" style="display: flex; flex-direction: column; gap: 12px;">
          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Fecha:</label>
          <input type="date" name="working_date" required class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Part No:</label>
          <input type="text" name="part_no" required class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Line:</label>
          <input type="text" name="line" required class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Turno:</label>
          <select name="turno" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="DIA" selected>DIA</option>
            <option value="TIEMPO EXTRA">TIEMPO EXTRA</option>
            <option value="NOCHE">NOCHE</option>
          </select>

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Plan Count:</label>
          <input type="number" name="plan_count" value="0" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">WO Code:</label>
          <input type="text" name="wo_code" value="SIN-WO" placeholder="SIN-WO" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">PO Code:</label>
          <input type="text" name="po_code" value="SIN-PO" placeholder="SIN-PO" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Asignar a Grupo:</label>
          <select name="target_group" id="target-group-select" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="">📋 Automático (al final)</option>
          </select>

          <div class="form-actions" style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
            <button type="submit" class="plan-btn plan-btn-add" style="flex: 1; min-width: 120px; background: #27ae60; color: white; border: none; padding: 12px 10px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Registrar</button>
            <button type="button" id="assy-closeModalBtn" class="assy-btn" style="flex: 1; min-width: 120px; background: #666; color: white; border: none; padding: 12px 10px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); touch-action: manipulation;">Cancelar</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(planModal);
  }

  // Modal de Editar Plan
  if (!document.getElementById('assy-editModal')) {
    // console.log('?? Creando modal plan-editModal');
    const editModal = document.createElement('div');
    editModal.id = 'assy-editModal';
    editModal.className = 'modal-overlay';

    // IMPORTANTE: Agregar estilos inline como fallback
    editModal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.6);
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    editModal.innerHTML = `
      <div id="assy-modal-content" style="
        background: #34334E; 
        border-radius: 8px; 
        padding: 20px; 
        width: 90%;
        max-width: 500px; 
        max-height: 90vh;
        overflow-y: auto;
        color: lightgray;
        box-sizing: border-box;
        margin: 10px;
      ">
        <h3 style="margin: 0 0 15px 0; color: #ecf0f1; font-size: clamp(16px, 4vw, 20px); text-align: center;">Editar Plan</h3>
        <form id="assy-editForm" style="display: flex; flex-direction: column; gap: 12px;">
          <input type="hidden" name="lot_no">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Turno:</label>
          <select name="turno" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="DIA">DIA</option>
            <option value="TIEMPO EXTRA">TIEMPO EXTRA</option>
            <option value="NOCHE">NOCHE</option>
          </select>

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Plan Count:</label>
          <input type="number" name="plan_count" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">WO Code:</label>
          <input type="text" name="wo_code" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">PO Code:</label>
          <input type="text" name="po_code" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Line:</label>
          <input type="text" name="line" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Revision BOM:</label>
          <select name="assigned_bom_rev" id="assy-edit-assigned-bom-rev" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="">Automatico - revision vigente</option>
          </select>

          <div class="form-actions-with-gap" style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button type="submit" class="plan-btn plan-btn-add" style="flex: 1; min-width: 100px; background: #27ae60; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Guardar</button>
              <button type="button" class="assy-btn" style="flex: 1; min-width: 100px; background: #666; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); touch-action: manipulation;">Cerrar</button>
            </div>
            <button type="button" id="assy-cancelBtn" class="plan-btn plan-btn-danger" style="width: 100%; background: #e74c3c; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Cancelar plan</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(editModal);
  }

  // Modal de Reprogramar
  if (!document.getElementById('reschedule-modal')) {
    // console.log('?? Creando modal reschedule-modal');
    const rescheduleModal = document.createElement('div');
    rescheduleModal.id = 'reschedule-modal';
    rescheduleModal.className = 'modal-overlay';

    // IMPORTANTE: Agregar estilos inline como fallback
    rescheduleModal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.6);
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    rescheduleModal.innerHTML = `
      <div class="modal-content" style="background: #34334E; border-radius: 8px; width: 90%; max-width: 1200px; max-height: 90%; padding: 20px; color: lightgray; overflow: auto;">
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 class="reschedule-title" style="margin: 0; color: #9b59b6;">Reprogramar Planes</h3>
          <button id="reschedule-closeModalBtn" class="btn-close-line" style="background: #666; border: none; color: white; font-size: 24px; cursor: pointer; width: 30px; height: 30px; border-radius: 4px;">&times;</button>
        </div>

        <div class="reschedule-filters" style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
          <label style="font-size: 11px; color: #ecf0f1;">Fecha Desde:</label>
          <input type="date" id="reschedule-date-from" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
          <label style="font-size: 11px; color: #ecf0f1;">Fecha Hasta:</label>
          <input type="date" id="reschedule-date-to" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
          <label style="font-size: 11px; color: #ecf0f1;">Nueva Fecha:</label>
          <input type="date" id="reschedule-new-date" class="assy-input" required style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
          <button id="reschedule-search-btn" class="plan-btn reschedule-search-btn" style="background-color: #8e44ad; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 12px;">Buscar Pendientes</button>
          <button id="reschedule-submit-btn" class="plan-btn plan-btn-add" style="background-color: #8e44ad; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 12px;">Reprogramar Seleccionados</button>
        </div>

        <div class="modal-table-container" style="overflow-x: auto; margin-bottom: 20px;">
          <table class="modal-table" style="width: 100%; border-collapse: collapse; background: #2B2D3E;">
            <thead>
              <tr style="background: #1e1e2e;">
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;"><input type="checkbox" id="reschedule-select-all"></th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">LOT NO</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Fecha Actual</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Part No</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Line</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Plan Count</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Input</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Pendiente</th>
                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Status</th>
              </tr>
            </thead>
            <tbody id="reschedule-tableBody" style="color: lightgray;"></tbody>
          </table>
        </div>

        <div class="modal-status" style="padding: 10px; text-align: center; color: #95a5a6; font-size: 12px;">
          <span id="reschedule-status">Seleccione una fecha para buscar planes con input pendiente</span>
        </div>
      </div>
    `;
    document.body.appendChild(rescheduleModal);
  }

  if (!document.getElementById('assy-scan-lots-modal')) {
    // console.log('?? Creando modal scan-lots-modal');
    const scanLotsModal = document.createElement('div');
    scanLotsModal.id = 'assy-scan-lots-modal';
    scanLotsModal.className = 'modal-overlay';
    scanLotsModal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.6);
      justify-content: center;
      align-items: center;
      z-index: 10000;
    `;

    scanLotsModal.innerHTML = `
      <div class="modal-content" id="scan-lots-modal-content" style="background:#34334E; border-radius:8px; width:94%; max-width:1350px; max-height:90%; padding:20px; color:lightgray; overflow:auto;">
        <div class="modal-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
          <h3 style="margin:0; color:#f39c12;">Lotes SCAN sin asignar</h3>
          <button id="scan-lots-closeModalBtn" class="plan-btn modal-close-btn" style="background:#666; border:none; color:white; font-size:24px; cursor:pointer; width:30px; height:30px; border-radius:4px; display:flex; align-items:center; justify-content:center; padding:0; line-height:1;">×</button>
        </div>

        <div class="modal-filters" style="display:flex; gap:10px; align-items:center; margin-bottom:20px; flex-wrap:wrap;">
          <label style="font-size:11px; color:#ecf0f1;">Fecha Desde:</label>
          <input type="date" id="scan-lots-date-from" class="assy-input" style="background:#2B2D3E; color:lightgray; border:1px solid #20688C; padding:6px 8px; border-radius:4px; font-size:12px; width:140px;">

          <label style="font-size:11px; color:#ecf0f1;">Fecha Hasta:</label>
          <input type="date" id="scan-lots-date-to" class="assy-input" style="background:#2B2D3E; color:lightgray; border:1px solid #20688C; padding:6px 8px; border-radius:4px; font-size:12px; width:140px;">

          <label style="font-size:11px; color:#ecf0f1;">Linea:</label>
          <input type="text" id="scan-lots-line" class="assy-input" placeholder="M2" style="background:#2B2D3E; color:lightgray; border:1px solid #20688C; padding:6px 8px; border-radius:4px; font-size:12px; width:80px;">

          <label style="font-size:11px; color:#ecf0f1;">Part No:</label>
          <input type="text" id="scan-lots-part-no" class="assy-input" placeholder="EBR..." style="background:#2B2D3E; color:lightgray; border:1px solid #20688C; padding:6px 8px; border-radius:4px; font-size:12px; width:160px;">

          <button id="scan-lots-search-btn" class="assy-btn" style="background-color:#d35400; color:white; border:none; padding:7px 14px; border-radius:4px; cursor:pointer; font-size:12px;">Buscar</button>
        </div>

        <div class="modal-table-container" style="overflow-x:auto; margin-bottom:20px;">
          <table class="modal-table" style="width:100%; border-collapse:collapse; background:#2B2D3E;">
            <thead>
              <tr style="background:#1e1e2e;">
                <th style="padding:10px; text-align:left; border-bottom:2px solid #20688C; color:#ecf0f1;">Linea</th>
                <th style="padding:10px; text-align:left; border-bottom:2px solid #20688C; color:#ecf0f1;">Part No</th>
                <th style="padding:10px; text-align:right; border-bottom:2px solid #20688C; color:#ecf0f1;">Cantidad</th>
                <th style="padding:10px; text-align:left; border-bottom:2px solid #20688C; color:#ecf0f1;">Rango</th>
                <th style="padding:10px; text-align:left; border-bottom:2px solid #20688C; color:#ecf0f1;">Lot No destino</th>
                <th style="padding:10px; text-align:center; border-bottom:2px solid #20688C; color:#ecf0f1;">Accion</th>
              </tr>
            </thead>
            <tbody id="scan-lots-tableBody" style="color:lightgray;"></tbody>
          </table>
        </div>

        <div class="modal-status" style="padding:10px; text-align:center; color:#95a5a6; font-size:12px;">
          <span id="scan-lots-status">Busque grupos SCAN por numero de parte para asignarlos a un plan compatible</span>
        </div>
      </div>
    `;
    document.body.appendChild(scanLotsModal);
  }

  // console.log('? Modales creados dinomicamente en el body');
}

// Funcion de inicializacion de event listeners usando event delegation
function initializePlanEventListeners() {
  // console.log('?? initializePlanEventListeners llamada');

  // IMPORTANTE: Siempre crear modales dinomicamente en el body
  // Esto asegura que los modales siempre eston al nivel correcto del DOM
  createModalsInBody();

  // IMPORTANTE: Usar proteccion para evitar agregar listeners duplicados
  // Solo agregar listeners una vez, ya que eston en document.body
  if (document.body.dataset.planListenersAttached === 'true') {
    // console.log('? Listeners ya eston configurados, saltando re-inicializacion de listeners');
    // console.log('?? Los modales fueron creados/verificados en el body');
    return;
  }

  // console.log('?? Configurando event listeners con event delegation...');

  // ========== EVENT LISTENER DE CLICKS (Event Delegation) ==========
  document.body.addEventListener('click', function (e) {
    const target = e.target;

    // ========== BOTONES DE MODALES ==========

    // Abrir modal Nuevo Plan
    if (target.id === 'assy-openModalBtn' || target.closest('#assy-openModalBtn')) {
      e.preventDefault();
 // console.log(' Click en plan-openModalBtn detectado');

      // Asegurar que el modal existe antes de abrirlo
      if (!document.getElementById('assy-modal')) {
 // console.log(' Modal no existe, creándolo...');
        createModalsInBody();
      }

      // Llenar el selector de grupos antes de abrir el modal
      populateGroupSelector();

      // Llenar el campo de fecha con la fecha de hoy
      const dateInput = document.querySelector('#assy-form input[name="working_date"]');
      if (dateInput) {
        const today = getTodayInNuevoLeon(); // Formato YYYY-MM-DD
        dateInput.value = today;
        // console.log(' Fecha del día establecida:', today);
      }

      const modal = document.getElementById('assy-modal');
      if (modal) {
        // FORZAR estilos inline para sobrescribir cualquier CSS conflictivo
        modal.style.cssText = `
          display: flex !important;
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          width: 100% !important;
          height: 100% !important;
          background: rgba(0,0,0,0.6) !important;
          justify-content: center !important;
          align-items: center !important;
          z-index: 10000 !important;
          opacity: 1 !important;
          visibility: visible !important;
        `;
        // console.log(' Modal plan-modal abierto con estilos forzados');
      } else {
        console.error(' Modal plan-modal no encontrado después de crearlo');
      }
      return;
    }

    // Cerrar modal Nuevo Plan
    if (target.id === 'assy-closeModalBtn' || target.closest('#assy-closeModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('assy-modal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    // Abrir modal Work Orders
    if (target.id === 'assy-wo-openModalBtn' || target.closest('#assy-wo-openModalBtn')) {
      e.preventDefault();
      // console.log('?? Click en wo-openModalBtn detectado');

      // Crear modal WO si no existe
      if (typeof createWorkOrdersModal === 'function') {
        createWorkOrdersModal();
        // console.log('? Modal WO creado/verificado');
      }

      const modal = document.getElementById('wo-modal');
      if (modal) {
        // FORZAR estilos inline para sobrescribir cualquier CSS conflictivo
        modal.style.cssText = `
          display: flex !important;
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          width: 100% !important;
          height: 100% !important;
          background: rgba(0,0,0,0.6) !important;
          justify-content: center !important;
          align-items: center !important;
          z-index: 10000 !important;
          opacity: 1 !important;
          visibility: visible !important;
        `;
        // console.log('? Modal wo-modal abierto con estilos forzados');
        if (typeof loadWorkOrders === 'function') loadWorkOrders();
      } else {
        console.error('? Modal wo-modal no encontrado despuos de crearlo');
      }
      return;
    }

    if (target.id === 'assy-scan-lots-openModalBtn' || target.closest('#assy-scan-lots-openModalBtn')) {
      e.preventDefault();
      // console.log('?? Click en scan-lots-openModalBtn detectado');

      if (!document.getElementById('assy-scan-lots-modal')) {
        createModalsInBody();
      }

      setDefaultScanLotsDates();
      const modal = document.getElementById('assy-scan-lots-modal');
      if (modal) {
        modal.style.cssText = `
          display: flex !important;
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          width: 100% !important;
          height: 100% !important;
          background: rgba(0,0,0,0.6) !important;
          justify-content: center !important;
          align-items: center !important;
          z-index: 10000 !important;
          opacity: 1 !important;
          visibility: visible !important;
        `;
        loadScanLots();
      }
      return;
    }

    if (target.id === 'scan-lots-closeModalBtn' || target.closest('#scan-lots-closeModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('assy-scan-lots-modal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    if (target.id === 'scan-lots-search-btn' || target.closest('#scan-lots-search-btn')) {
      e.preventDefault();
      loadScanLots();
      return;
    }

    if (target.classList.contains('scan-assign-btn') || target.closest('.scan-assign-btn')) {
      e.preventDefault();
      assignScanLot(target.closest('.scan-assign-btn'), false);
      return;
    }

    if (target.classList.contains('scan-extend-assign-btn') || target.closest('.scan-extend-assign-btn')) {
      e.preventDefault();
      assignScanLot(target.closest('.scan-extend-assign-btn'), true);
      return;
    }

    if (target.classList.contains('scan-create-plan-btn') || target.closest('.scan-create-plan-btn')) {
      e.preventDefault();
      createPlanForScanLot(target.closest('.scan-create-plan-btn'));
      return;
    }

    // Abrir modal Reprogramar
    if (target.id === 'assy-reschedule-openModalBtn' || target.closest('#assy-reschedule-openModalBtn')) {
      e.preventDefault();
      // console.log('?? Click en reschedule-openModalBtn detectado');

      // Asegurar que el modal existe antes de abrirlo
      if (!document.getElementById('reschedule-modal')) {
        // console.log('?? Modal no existe, creondolo...');
        createModalsInBody();
      }

      const modal = document.getElementById('reschedule-modal');
      if (modal) {
        // FORZAR estilos inline para sobrescribir cualquier CSS conflictivo
        modal.style.cssText = `
          display: flex !important;
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          width: 100% !important;
          height: 100% !important;
          background: rgba(0,0,0,0.6) !important;
          justify-content: center !important;
          align-items: center !important;
          z-index: 10000 !important;
          opacity: 1 !important;
          visibility: visible !important;
        `;

        // console.log('? Modal reschedule-modal abierto con estilos forzados');
        if (typeof setDefaultRescheduleDates === 'function') setDefaultRescheduleDates();
      } else {
        console.error('? Modal reschedule-modal no encontrado despuos de crearlo');
      }
      return;
    }

    // Cerrar modal Reprogramar
    if (target.id === 'reschedule-closeModalBtn' || target.closest('#reschedule-closeModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('reschedule-modal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    // Boton Buscar Pendientes del modal Reprogramar
    if (target.id === 'reschedule-search-btn' || target.closest('#reschedule-search-btn')) {
      e.preventDefault();
      if (typeof loadPendingPlans === 'function') loadPendingPlans();
      return;
    }

    // Boton Reprogramar Seleccionados
    if (target.id === 'reschedule-submit-btn' || target.closest('#reschedule-submit-btn')) {
      e.preventDefault();
      if (typeof reschedulePendingPlans === 'function') reschedulePendingPlans();
      return;
    }

    // ========== MODAL DE EDICIoN ==========

    // Boton Cerrar modal Editar (el boton "Cerrar" dentro del form)
    if (target.closest('#assy-editForm button[type="button"]') &&
      target.textContent.includes('Cerrar')) {
      e.preventDefault();
      const modal = document.getElementById('assy-editModal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    // Boton Cancelar Plan (boton rojo)
    if (target.id === 'assy-cancelBtn' || target.closest('#assy-cancelBtn')) {
      e.preventDefault();
      if (typeof handleCancelPlan === 'function') handleCancelPlan();
      return;
    }

    // ========== BOTONES DE ACCIONES ==========

    // Auto acomodo
    if (target.id === 'assy-auto-arrange-btn' || target.closest('#assy-auto-arrange-btn')) {
      e.preventDefault();
      autoArrangePlans();
      return;
    }

    // Exportar a Excel
    if (target.id === 'assy-export-excel-btn' || target.closest('#assy-export-excel-btn')) {
      e.preventDefault();
      exportarExcel();
      return;
    }

    // Guardar secuencias
    if (target.id === 'assy-save-sequences-btn' || target.closest('#assy-save-sequences-btn')) {
      e.preventDefault();
      saveGroupSequences();
      return;
    }

    // Calcular tiempos
    if (target.id === 'calc-times-btn' || target.closest('#calc-times-btn')) {
      e.preventDefault();
      reloadTableWithCurrentData();
      return;
    }

    // Toggle vista por lineas
    if (target.id === 'assy-toggle-view-btn' || target.closest('#assy-toggle-view-btn')) {
      e.preventDefault();
      toggleViewMode();
      return;
    }
  });

  // ========== EVENT LISTENER DE CHANGE PARA LINE-FILTER ==========
  document.body.addEventListener('change', function (e) {
    const target = e.target;
    
    // Filtro de lineas
    if (target.id === 'assy-line-filter') {
      renderTableByLines(target.value);
      return;
    }
  });

  // ========== EVENT LISTENERS DE SUBMIT ==========
  document.body.addEventListener('submit', function (e) {
    // Submit del form de editar plan
    if (e.target.id === 'assy-editForm') {
      e.preventDefault();
      if (typeof window.handleEditPlanSubmit === 'function') {
        window.handleEditPlanSubmit(e.target);
      }
      return;
    }

    // Submit del form de nuevo plan
    if (e.target.id === 'assy-form') {
      e.preventDefault();
      if (typeof window.handleNewPlanSubmit === 'function') {
        window.handleNewPlanSubmit(e.target);
      }
      return;
    }
  });

  // ========== EVENT LISTENER DE CHANGE ==========
  document.body.addEventListener('change', function (e) {
    const target = e.target;

    // Selector de nomero de grupos
    if (target.id === 'assy-groups-count') {
      reloadTableWithCurrentData();
      return;
    }

    // Checkbox "Seleccionar todos" del modal Reprogramar
    if (target.id === 'reschedule-select-all') {
      if (typeof toggleAllReschedule === 'function') toggleAllReschedule(target);
      return;
    }
  });

  // ========== EVENT LISTENER DE DOBLE CLICK ==========
  // Remover listener anterior si existe para evitar duplicados
  if (document.body.dblclickHandler) {
    document.body.removeEventListener('dblclick', document.body.dblclickHandler);
  }
  
  // Crear y almacenar el handler
  document.body.dblclickHandler = function (e) {
 // console.log(' Doble click detectado en:', e.target);
    
    // Verificar si el doble click fue en una fila de la tabla de planes
    const row = e.target.closest('tr.assy-row');
    
    if (!row) {
      // console.log(' No se encontró tr.assy-row');
      return;
    }
    
    // Verificar que la fila pertenece al contenedor ASSY, no al de IMD
    const assyContainer = row.closest('#plan-main-assy-unique-container');
    if (!assyContainer) {
 // console.log(' Fila no pertenece a ASSY, ignorando...');
      return;
    }
    
    // console.log(' Fila encontrada:', row);

    const lotNo = row.dataset.lot;
 // console.log(' Lot No:', lotNo);
    
    if (lotNo && typeof openEditModal === 'function') {
      // console.log(' Abriendo modal de edición para:', lotNo);
      openEditModal(lotNo);
    } else {
      // console.log(' No se puede abrir modal. lotNo:', lotNo, 'openEditModal existe:', typeof openEditModal === 'function');
    }
  };
  
  // Agregar el listener
  document.body.addEventListener('dblclick', document.body.dblclickHandler);

  // Marcar como inicializado
  document.body.dataset.planListenersAttached = 'true';
  // console.log(' Event listeners configurados correctamente');
}

// Event listeners para nuevos controles
document.addEventListener('DOMContentLoaded', initializePlanEventListeners);

// Exponer funciones globalmente para que puedan ser llamadas despuos de cargar contenido dinomico
window.assyInitializePlanEventListeners = initializePlanEventListeners;
window.assyCreateModalsInBody = createModalsInBody;
window.assyLoadPlans = loadPlans;
// assyExportarExcel se exporta en plan-assy-excel.js (definicion vive ahi)

// Tambion ejecutar inmediatamente si el DOM ya esto listo (para scripts defer)
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  initializePlanEventListeners();
}

window.debugGroups = function () {
  try {
    const rows = [...document.querySelectorAll('#assy-tableBody tr.assy-row')];
    const perGroup = {};
    rows.forEach(r => { const gi = parseInt(r.dataset.groupIndex) || 0; const lot = r.dataset.lot; (perGroup[gi] = perGroup[gi] || []).push(lot); });
    return { visualGroups: visualGroups.groups.map((g, i) => ({ g: i + 1, lots: g.plans.map(p => p.lot_no) })), domRows: perGroup };
  } catch (e) { console.warn(e); }
}

