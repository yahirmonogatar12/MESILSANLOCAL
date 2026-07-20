// ====== plan-assy-scanlots.js (lotes SCAN sin asignar) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

function updateScanLotsStatus(message) {
  const statusElement = document.getElementById("scan-lots-status");
  if (statusElement) {
    statusElement.textContent = message;
  }
}

function setDefaultScanLotsDates() {
  const dateFrom = document.getElementById("scan-lots-date-from");
  const dateTo = document.getElementById("scan-lots-date-to");
  if (dateFrom && !dateFrom.value) {
    dateFrom.value = getDateInNuevoLeon(-7);
  }
  if (dateTo && !dateTo.value) {
    dateTo.value = getTodayInNuevoLeon();
  }
}

async function loadScanLots() {
  const tbody = document.getElementById("scan-lots-tableBody");
  if (!tbody) return;

  try {
    showTableBodyLoading("scan-lots-tableBody", "Cargando lotes SCAN...", 6);
    updateScanLotsStatus("Cargando lotes SCAN...");

    const dateFrom = document.getElementById("scan-lots-date-from")?.value || "";
    const dateTo = document.getElementById("scan-lots-date-to")?.value || "";
    const line = document.getElementById("scan-lots-line")?.value?.trim() || "";
    const partNo = document.getElementById("scan-lots-part-no")?.value?.trim() || "";

    const params = [];
    if (dateFrom) params.push(`date_from=${encodeURIComponent(dateFrom)}`);
    if (dateTo) params.push(`date_to=${encodeURIComponent(dateTo)}`);
    if (line) params.push(`line=${encodeURIComponent(line)}`);
    if (partNo) params.push(`part_no=${encodeURIComponent(partNo)}`);
    params.push("limit=200");

    const response = await axios.get(`/api/plan/input-main/scan-lots?${params.join("&")}`);
    scanLotsData = response.data.scan_lots || [];
    scanLotPlanOptions = response.data.plan_options || [];
    renderScanLotsTable();
    updateScanLotsStatus(`${scanLotsData.length} grupo(s) por numero de parte pendiente(s)`);
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#e74c3c;">Error al cargar lotes SCAN</td></tr>`;
    updateScanLotsStatus("Error al cargar lotes SCAN");
    alert("Error al cargar lotes SCAN: " + (error.response?.data?.error || error.message));
  }
}

function getCompatiblePlanOptions(scanLot) {
  const line = String(scanLot.linea || '').trim();
  const partNo = String(scanLot.nparte || '').trim();
  return scanLotPlanOptions.filter(plan =>
    String(plan.line || '').trim() === line &&
    String(plan.part_no || '').trim() === partNo &&
    ((parseInt(plan.plan_count) || 0) - (parseInt(plan.produced_count) || 0)) > 0
  );
}

function renderScanLotsTable() {
  const tbody = document.getElementById("scan-lots-tableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!scanLotsData.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#95a5a6;">No hay lotes SCAN pendientes en el rango seleccionado</td></tr>`;
    return;
  }

  scanLotsData.forEach(scanLot => {
    const options = getCompatiblePlanOptions(scanLot);
    const hasOptions = options.length > 0;
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid #555";
    tr.dataset.scanIndex = String(scanLotsData.indexOf(scanLot));

    const optionsHtml = hasOptions
      ? options.map(plan => {
        const pending = Math.max((parseInt(plan.plan_count) || 0) - (parseInt(plan.produced_count) || 0), 0);
        const label = `${plan.lot_no} | ${plan.part_no} | ${plan.working_date} | ${plan.status} | Pend: ${pending}`;
        return `<option value="${escapePlanHtml(plan.lot_no)}">${escapePlanHtml(label)}</option>`;
      }).join("")
      : `<option value="">Sin lote compatible</option>`;

    tr.innerHTML = `
      <td style="padding:6px; text-align:center;">${escapePlanHtml(scanLot.linea)}</td>
      <td style="padding:6px; font-size:11px;">${escapePlanHtml(scanLot.nparte)}</td>
      <td style="padding:6px; text-align:right;">${scanLot.cantidad_total || 0}</td>
      <td style="padding:6px; font-size:11px;">${escapePlanHtml(scanLot.primero)}<br>${escapePlanHtml(scanLot.ultimo)}</td>
      <td style="padding:6px; min-width:280px;">
        <select class="plan-input scan-target-lot-select" ${hasOptions ? "" : "disabled"} style="width:100%; background:#1a1b26; color:lightgray; border:1px solid #20688C; padding:6px; border-radius:4px;">
          ${optionsHtml}
        </select>
      </td>
      <td style="padding:6px; text-align:center;">
        <div style="display:flex; gap:6px; justify-content:center; flex-wrap:wrap;">
          <button class="plan-btn scan-assign-btn" ${hasOptions ? "" : "disabled"} style="padding:5px 10px; font-size:11px; background:#27ae60;">Asignar</button>
          <button class="plan-btn scan-extend-assign-btn" ${hasOptions ? "" : "disabled"} style="padding:5px 10px; font-size:11px; background:#8e44ad;">Extender + asignar</button>
          <button class="plan-btn scan-create-plan-btn" style="padding:5px 10px; font-size:11px; background:#2980b9;">Crear plan</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function getSelectedScanTargetPlan(row) {
  const targetLotNo = row?.querySelector(".scan-target-lot-select")?.value || "";
  return scanLotPlanOptions.find(plan => plan.lot_no === targetLotNo) || null;
}

async function assignScanLot(button, allowExtend = false) {
  const row = button.closest("tr");
  const scanLot = scanLotsData[parseInt(row?.dataset?.scanIndex || "-1", 10)];
  const targetLotNo = row?.querySelector(".scan-target-lot-select")?.value || "";
  const targetPlan = getSelectedScanTargetPlan(row);
  const dateFrom = document.getElementById("scan-lots-date-from")?.value || "";
  const dateTo = document.getElementById("scan-lots-date-to")?.value || "";

  if (!scanLot || !targetLotNo) {
    alert("Selecciona un grupo SCAN y un Lot No destino");
    return;
  }

  const pending = targetPlan
    ? ((parseInt(targetPlan.plan_count) || 0) - (parseInt(targetPlan.produced_count) || 0))
    : 0;
  const scanQty = parseInt(scanLot.cantidad_total) || 0;

  if (pending <= 0) {
    alert("Ese plan ya está completo. Crea un plan nuevo para estos escaneos.");
    return;
  }
  if (scanQty > pending && !allowExtend) {
    alert(`La cantidad SCAN (${scanQty}) excede el pendiente del plan (${pending}). Usa "Extender + asignar".`);
    return;
  }

  const actionText = allowExtend && scanQty > pending ? "Extender y asignar" : "Asignar";
  if (!confirm(`${actionText} ${scanQty} pieza(s) de ${scanLot.nparte} (${scanLot.linea}) al lote ${targetLotNo}?`)) {
    return;
  }

  const originalText = button.textContent;
  try {
    button.textContent = "Asignando...";
    button.disabled = true;
    updateScanLotsStatus(`Asignando grupo ${scanLot.nparte}...`);

    const response = await axios.post("/api/plan/input-main/assign-lot", {
      linea: scanLot.linea,
      nparte: scanLot.nparte,
      date_from: dateFrom,
      date_to: dateTo,
      target_lot_no: targetLotNo,
      allow_extend: allowExtend
    });

    if (response.data.success) {
      showSuccessModal(response.data.message || "Lote SCAN asignado correctamente");
      await loadScanLots();
      if (typeof loadPlans === "function") {
        await loadPlans();
        await saveGroupSequences({ silent: true });
      }
    } else {
      alert(response.data.error || "No se pudo asignar el lote SCAN");
    }
  } catch (error) {
    alert("Error asignando lote SCAN: " + (error.response?.data?.error || error.message));
  } finally {
    button.textContent = originalText;
    button.disabled = false;
    updateScanLotsStatus("Listo");
  }
}

async function createPlanForScanLot(button) {
  const row = button.closest("tr");
  const scanLot = scanLotsData[parseInt(row?.dataset?.scanIndex || "-1", 10)];
  const dateFrom = document.getElementById("scan-lots-date-from")?.value || "";
  const dateTo = document.getElementById("scan-lots-date-to")?.value || "";

  if (!scanLot) {
    alert("Selecciona un grupo SCAN");
    return;
  }

  const scanQty = parseInt(scanLot.cantidad_total) || 0;
  if (!confirm(`Crear un plan nuevo para ${scanQty} pieza(s) de ${scanLot.nparte} (${scanLot.linea})?`)) {
    return;
  }

  const originalText = button.textContent;
  try {
    button.textContent = "Creando...";
    button.disabled = true;
    updateScanLotsStatus(`Creando plan para ${scanLot.nparte}...`);

    const response = await axios.post("/api/plan/input-main/create-plan", {
      linea: scanLot.linea,
      nparte: scanLot.nparte,
      date_from: dateFrom,
      date_to: dateTo,
      working_date: dateTo
    });

    if (response.data.success) {
      showSuccessModal(response.data.message || "Plan creado correctamente");
      await loadScanLots();
      if (typeof loadPlans === "function") {
        await loadPlans();
        await saveGroupSequences({ silent: true });
      }
    } else {
      alert(response.data.error || "No se pudo crear el plan");
    }
  } catch (error) {
    alert("Error creando plan: " + (error.response?.data?.error || error.message));
  } finally {
    button.textContent = originalText;
    button.disabled = false;
    updateScanLotsStatus("Listo");
  }
}


// ====== plan-assy-groups.js (visual groups + lines view + auto-acomodo) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

function initializeVisualGroups(groupCount) {
  visualGroups.groups = [];
  for (let i = 0; i < groupCount; i++) {
    visualGroups.groups.push({
      id: i,
      name: `GRUPO ${i + 1}`,
      plans: [],
      totalTime: 0,
      isOvertime: false
    });
  }
}

// Renderizar tabla con grupos visibles
function renderTableWithVisualGroups(data) {
  const table = document.getElementById('assy-table');
  const oldTbody = document.getElementById('assy-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'assy-tableBody';

  const groupCount = parseInt(document.getElementById('assy-groups-count').value) || 6;
  initializeVisualGroups(groupCount);

  // Verificar si los datos tienen informacion de grupos guardada
  const hasGroupData = data.some(plan => plan.group_no != null && plan.sequence != null);

  if (hasGroupData) {


    // Asignar planes basondose en group_no y sequence de la base de datos
    data.forEach((plan) => {
      if (plan.group_no != null && plan.sequence != null) {
        const groupIndex = plan.group_no - 1; // Convertir de 1-indexed a 0-indexed
        if (groupIndex >= 0 && groupIndex < groupCount) {
          visualGroups.groups[groupIndex].plans.push(plan);
          visualGroups.planAssignments.set(plan.lot_no, groupIndex);
        } else {
          // Si el group_no esto fuera del rango actual, asignar al oltimo grupo
          const fallbackGroup = groupCount - 1;
          visualGroups.groups[fallbackGroup].plans.push(plan);
          visualGroups.planAssignments.set(plan.lot_no, fallbackGroup);
        }
      } else {
        // Para planes sin grupo asignado, usar distribucion automotica
        const assignedGroup = data.indexOf(plan) % groupCount;
        visualGroups.groups[assignedGroup].plans.push(plan);
        visualGroups.planAssignments.set(plan.lot_no, assignedGroup);
      }
    });

    // Ordenar los planes dentro de cada grupo por sequence
    visualGroups.groups.forEach(group => {
      group.plans.sort((a, b) => {
        const aSeq = a.sequence || 999;
        const bSeq = b.sequence || 999;
        return aSeq - bSeq;
      });
    });

  } else {


    // Asignar planes a grupos (mantener asignaciones previas si existen)
    data.forEach((plan, index) => {
      let assignedGroup = visualGroups.planAssignments.get(plan.lot_no);
      if (assignedGroup === undefined) {
        // Asignar automoticamente si no tiene asignacion previa
        assignedGroup = index % groupCount;
        visualGroups.planAssignments.set(plan.lot_no, assignedGroup);
      }
      visualGroups.groups[assignedGroup].plans.push(plan);
    });
  }

  // Renderizar cada grupo
  visualGroups.groups.forEach((group, groupIndex) => {
    // Fila de encabezado del grupo
    const groupHeaderRow = document.createElement('tr');
    groupHeaderRow.className = 'group-header-row';
    groupHeaderRow.innerHTML = `
      <td colspan="23" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>${group.name}</span>
          <div>
            <span id="group-${groupIndex}-total" style="margin-right: 10px;">Total: 0.0h</span>
            <span id="group-${groupIndex}-status" class="status-calc">CALCULANDO</span>
          </div>
        </div>
      </td>
    `;
    tbody.appendChild(groupHeaderRow);

    // Zona de drop para el grupo
    const dropZoneRow = document.createElement('tr');
    dropZoneRow.className = 'group-drop-zone';
    dropZoneRow.dataset.groupIndex = groupIndex;
    dropZoneRow.innerHTML = `
      <td colspan="23" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
        <div class="drop-zone-content">
          ${group.plans.length === 0 ? 'Arrastra planes aquo para asignarlos a este grupo' : ''}
        </div>
      </td>
    `;
    tbody.appendChild(dropZoneRow);

    // Renderizar planes del grupo
    group.plans.forEach((plan, planIndex) => {
      const globalIndex = data.findIndex(p => p.lot_no === plan.lot_no);
      const tr = document.createElement("tr");
      tr.dataset.lot = plan.lot_no;
      tr.dataset.groupIndex = groupIndex;
      tr.draggable = true;
      tr.className = 'assy-row';

      // Calcular secuencia dentro del grupo
      const groupSequence = planIndex + 1;

      tr.innerHTML = `
        <td style="background-color: #e74c3c; color: white; font-weight: bold; text-align: center;">${groupSequence}</td>
        <td>${plan.lot_no}</td>
        <td>${plan.wo_code || ""}</td>
        <td>${plan.po_code || ""}</td>
        <td>${plan.working_date}</td>
        <td>${plan.line}</td>
        <td>${routingToTurno(plan.routing)}</td>
        <td>${plan.model_code}</td>
        <td>${partNoWithBomRevision(plan)}</td>
        <td>${plan.sub_assy || ''}</td>
        <td>${plan.project}</td>
        <td>${plan.process || ""}</td>
        <td>${plan.ct || "0"}</td>
        <td>${plan.uph || "0"}</td>
        <td>${plan.plan_count}</td>
        <td>${plan.produced ?? 0}</td>
        <td>${plan.output ?? 0}</td>
        <td>${plan.entregadas_main ?? 0}</td>
        <td>${plan.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell fecha-inicio-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold;">-</td>
      `;

      tbody.appendChild(tr);
    });

    // Espacio entre grupos
    if (groupIndex < visualGroups.groups.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'group-spacer';
      spacerRow.innerHTML = `<td colspan="23" style="height: 10px; background-color: #2c2c2c;"></td>`;
      tbody.appendChild(spacerRow);
    }
  });

  // Reemplazar el tbody completo para evitar listeners duplicados
  if (oldTbody && oldTbody.parentNode) {
    oldTbody.parentNode.replaceChild(tbody, oldTbody);
  } else if (table) {
    table.appendChild(tbody);
  }

  // Configurar drag & drop para grupos sobre el nuevo tbody
  setupGroupDragDrop();

  // Calcular tiempos para grupos
  calculateGroupTimes();
  
  // *** NUEVO: Resaltar conflictos de línea/horario ***
  // Usar setTimeout para asegurar que calculateGroupTimes() termine primero
  setTimeout(() => {
    resaltarConflictosLineaHorario();
  }, 100);
}

/**
 * Función para detectar y resaltar visualmente conflictos de línea/horario
 * Marca en rojo las filas que tienen la misma línea y horario de inicio
 */
function resaltarConflictosLineaHorario() {
  // console.log(' Buscando conflictos de línea/horario para resaltar...');
  
  // *** CORRECCIÓN: Obtener planes desde visualGroups en lugar de planningData ***
  const todosLosPlanes = [];
  visualGroups.groups.forEach(group => {
    todosLosPlanes.push(...group.plans);
  });
  
  // console.log(' Total de planes en grupos:', todosLosPlanes.length);
  // console.log(' planningCalculations size:', planningCalculations.size);
  
  // Crear mapa de planes con su hora de inicio calculada
  const planesConHorario = [];
  
  todosLosPlanes.forEach(plan => {
    // Obtener cálculos del plan
    const calc = planningCalculations.get(plan.lot_no);
    
    // console.log(`Plan ${plan.lot_no}: line=${plan.line}, status=${plan.status}, calc=`, calc);
    
    // Solo considerar planes activos (no cancelados) y con hora de inicio calculada
    if (plan.status !== 'CANCELADO' && calc && calc.startTime && calc.startTime !== '--') {
      planesConHorario.push({
        lot_no: plan.lot_no,
        line: plan.line,
        fecha: plan.working_date,
        inicio: calc.startTime,
        model_code: plan.model_code,
        group_no: calc.groupNumber
      });
      // console.log(`   Agregado: ${plan.lot_no} - ${plan.line} - ${calc.startTime}`);
    }
  });
  
  // console.log(` Analizando ${planesConHorario.length} planes activos con horario calculado`);
  
  // Crear mapa de conflictos: "linea-fecha-hora" -> [lot_no1, lot_no2, ...]
  const conflictosMap = new Map();
  
  planesConHorario.forEach(plan => {
    // Crear clave única: línea + fecha + hora de inicio
    const clave = `${plan.line}-${plan.fecha}-${plan.inicio}`;
    
    if (!conflictosMap.has(clave)) {
      conflictosMap.set(clave, []);
    }
    conflictosMap.get(clave).push({
      lot_no: plan.lot_no,
      model_code: plan.model_code,
      group_no: plan.group_no
    });
  });
  
 // console.log(' Mapa de conflictos:', Array.from(conflictosMap.entries()));
  
  // Identificar claves con conflictos (más de un plan)
  const clavesConConflicto = Array.from(conflictosMap.entries())
    .filter(([clave, planes]) => planes.length > 1);
  
  if (clavesConConflicto.length === 0) {
    // console.log(' No se encontraron conflictos de línea/horario');
    return;
  }
  
 // console.log(` Se encontraron ${clavesConConflicto.length} conflictos`);
  
  // Obtener todos los lot_no que tienen conflicto
  const lotNosConConflicto = new Set();
  clavesConConflicto.forEach(([clave, planes]) => {
    const lotNos = planes.map(p => p.lot_no);
    lotNos.forEach(lotNo => lotNosConConflicto.add(lotNo));
    
    // Log detallado del conflicto
    const [linea, fecha, hora] = clave.split('-');
 // console.log(` Conflicto en Línea: ${linea}, Fecha: ${fecha}, Hora: ${hora}`);
    planes.forEach(p => {
      // console.log(`   - Lot: ${p.lot_no}, Modelo: ${p.model_code}, Grupo: ${p.group_no}`);
    });
  });
  
 // console.log(' Lot numbers con conflicto:', Array.from(lotNosConConflicto));
  
  // Resaltar filas con conflicto
  const tbody = document.getElementById('assy-tableBody');
  if (!tbody) {
    console.error(' No se encontró plan-tableBody');
    return;
  }
  
  const rows = tbody.querySelectorAll('tr.assy-row');
 // console.log(` Filas encontradas en tabla: ${rows.length}`);
  let conflictosResaltados = 0;
  
  rows.forEach(row => {
    const lotNo = row.dataset.lot;
    
    if (lotNosConConflicto.has(lotNo)) {
      // Aplicar estilos de conflicto
      row.style.backgroundColor = '#c0392b'; // Rojo oscuro
      row.style.borderLeft = '5px solid #e74c3c'; // Borde rojo brillante
      row.style.boxShadow = '0 0 10px rgba(231, 76, 60, 0.5)';
      
      // CRÍTICO: Asegurar que los eventos sigan funcionando
      row.style.pointerEvents = 'auto';
      row.style.cursor = 'pointer';
      
      // Resaltar específicamente las celdas de línea y hora de inicio
      const cells = row.querySelectorAll('td');
      if (cells.length > 0) {
        // Columna 5: Line
        if (cells[5]) {
          cells[5].style.backgroundColor = '#e74c3c';
          cells[5].style.fontWeight = 'bold';
          cells[5].style.color = '#ffffff';
        }
        // Columna 19: Inicio (hora de inicio)
        if (cells[20]) {
          cells[20].style.backgroundColor = '#e74c3c';
          cells[20].style.fontWeight = 'bold';
          cells[20].style.color = '#ffffff';
        }
      }
      
      // Agregar tooltip/title con información del conflicto
      const planInfo = planesConHorario.find(p => p.lot_no === lotNo);
      if (planInfo) {
        const clave = `${planInfo.line}-${planInfo.fecha}-${planInfo.inicio}`;
        const planesEnConflicto = conflictosMap.get(clave);
        const otrosPlanes = planesEnConflicto
          .filter(p => p.lot_no !== lotNo)
          .map(p => `${p.lot_no} (${p.model_code}, Grupo ${p.group_no})`)
          .join('\n');
        
        row.title = `⚠️ CONFLICTO: Misma línea (${planInfo.line}) y hora (${planInfo.inicio}) que:\n${otrosPlanes}`;
      }
      
      conflictosResaltados++;
    }
  });
  
  // console.log(` ${conflictosResaltados} filas resaltadas con conflicto`);
  
  // Mostrar notificación si hay conflictos
  if (conflictosResaltados > 0) {
    mostrarNotificacionConflictos(conflictosResaltados);
  }
}

/**
 * Mostrar notificación temporal sobre conflictos encontrados
 */
function mostrarNotificacionConflictos(cantidad) {
  // Remover notificación previa si existe
  const notificacionPrevia = document.getElementById('notificacion-conflictos');
  if (notificacionPrevia) {
    notificacionPrevia.remove();
  }
  
  // Crear notificación
  const notificacion = document.createElement('div');
  notificacion.id = 'notificacion-conflictos';
  notificacion.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: #e74c3c;
    color: white;
    padding: 15px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
    z-index: 9999;
    font-family: 'LG regular', sans-serif;
    font-weight: bold;
    max-width: 300px;
    animation: slideInRight 0.3s ease;
  `;
  
  notificacion.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px;">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="white" opacity="0.3"/>
        <path d="M12 8v4M12 16h.01" stroke="white" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <div>
        <div style="font-size: 14px;">⚠️ Conflictos Detectados</div>
        <div style="font-size: 12px; opacity: 0.9; margin-top: 3px;">
          ${cantidad} plan(es) con misma línea/horario
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(notificacion);
  
  // Auto-ocultar después de 8 segundos
  setTimeout(() => {
    if (notificacion.parentElement) {
      notificacion.style.animation = 'slideOutRight 0.3s ease';
      setTimeout(() => notificacion.remove(), 300);
    }
  }, 8000);
}

// Configurar drag & drop entre grupos y dentro de grupos
function setupGroupDragDrop() {
  const tbody = document.getElementById("assy-tableBody");
  let draggedElement = null;
  let draggedFromGroup = null;
  let dropIndicator = null;
  let isDraggingOverDropZone = false;

  // Crear indicador visual de insercion
  function createDropIndicator() {
    const indicator = document.createElement('tr');
    indicator.className = 'drop-indicator';
    indicator.innerHTML = `<td colspan="23" style="height: 3px; background: #3498db; border: none; padding: 0;"></td>`;
    return indicator;
  }

  // Limpiar indicador de drop
  function clearDropIndicator() {
    if (dropIndicator && dropIndicator.parentNode) {
      dropIndicator.parentNode.removeChild(dropIndicator);
    }
    dropIndicator = null;
  }

  // Eventos para filas de planes
  tbody.addEventListener('dragstart', (e) => {
    const row = e.target.closest('.assy-row');
    if (!row) return;

    draggedElement = row;
    draggedFromGroup = parseInt(row.dataset.groupIndex);
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  tbody.addEventListener('dragend', (e) => {
    const row = e.target.closest('.assy-row');
    if (row) {
      row.classList.remove('dragging');
    }
    clearDropIndicator();
    draggedElement = null;
    draggedFromGroup = null;
    isDraggingOverDropZone = false;
  });

  tbody.addEventListener('dragover', (e) => {
    e.preventDefault();

    if (!draggedElement) return;

    // Verificar si estamos sobre una zona de drop entre grupos
    const dropZone = e.target.closest('.group-drop-zone');
    if (dropZone) {
      isDraggingOverDropZone = true;
      clearDropIndicator(); // Limpiar indicador de reordenamiento
      dropZone.style.backgroundColor = '#20688C';
      dropZone.style.borderColor = '#3498db';
      return;
    }

    isDraggingOverDropZone = false;
    // limpiar estilos de todas las drop-zones si no estamos sobre una
    const allZones = tbody.querySelectorAll('.group-drop-zone');
    allZones.forEach(z => { z.style.backgroundColor = '#34495e'; z.style.borderColor = '#20688C'; });

    // Logica para reordenamiento dentro del grupo
    const targetRow = e.target.closest('.assy-row');
    if (!targetRow || targetRow === draggedElement) {
      clearDropIndicator();
      return;
    }

    const targetGroupIndex = parseInt(targetRow.dataset.groupIndex);
    const draggedGroupIndex = parseInt(draggedElement.dataset.groupIndex);

    // Solo permitir reordenamiento dentro del mismo grupo
    if (targetGroupIndex === draggedGroupIndex) {
      clearDropIndicator();

      // Crear nuevo indicador
      dropIndicator = createDropIndicator();

      // Determinar donde insertar el indicador
      const rect = targetRow.getBoundingClientRect();
      const midpoint = rect.top + rect.height / 2;

      if (e.clientY < midpoint) {
        // Insertar antes de la fila target
        targetRow.parentNode.insertBefore(dropIndicator, targetRow);
      } else {
        // Insertar despuos de la fila target
        const nextSibling = targetRow.nextSibling;
        // Verificar que el siguiente elemento no sea un header de grupo o drop zone
        if (nextSibling &&
          !nextSibling.classList.contains('group-header-row') &&
          !nextSibling.classList.contains('group-drop-zone') &&
          !nextSibling.classList.contains('group-spacer')) {
          targetRow.parentNode.insertBefore(dropIndicator, nextSibling);
        } else {
          targetRow.parentNode.insertBefore(dropIndicator, nextSibling);
        }
      }
    } else {
      clearDropIndicator();
    }
  });

  tbody.addEventListener('dragleave', (e) => {
    const dropZone = e.target.closest('.group-drop-zone');
    if (dropZone && !dropZone.contains(e.relatedTarget)) {
      dropZone.style.backgroundColor = '#34495e';
      dropZone.style.borderColor = '#20688C';
    }
  });

  tbody.addEventListener('drop', (e) => {
    e.preventDefault();

    if (!draggedElement) return;

    clearDropIndicator();

    const dropZone = e.target.closest('.group-drop-zone');

    if (dropZone && isDraggingOverDropZone) {
      // Movimiento entre grupos
      const targetGroupIndex = parseInt(dropZone.dataset.groupIndex);
      const lotNo = draggedElement.dataset.lot;

      // Actualizar asignacion
      visualGroups.planAssignments.set(lotNo, targetGroupIndex);

      // Recargar tabla con nueva asignacion
      reloadTableWithCurrentData();

      // Actualizar secuencias y fechas de inicio
      setTimeout(() => {
        updateSequenceNumbers();
      }, 100);

      // Restaurar estilos
      dropZone.style.backgroundColor = '#34495e';
      dropZone.style.borderColor = '#20688C';

      // Feedback visual
      const dropZoneContent = dropZone.querySelector('.drop-zone-content');
      const originalText = dropZoneContent.innerHTML;

      dropZoneContent.innerHTML = `? Plan ${lotNo.split('-')[2]} movido aquo`;
      dropZoneContent.classList.add('drop-zone-success');

      setTimeout(() => {
        dropZoneContent.innerHTML = originalText;
        dropZoneContent.classList.remove('drop-zone-success');
      }, 1500);

    } else {
      // Reordenamiento dentro del mismo grupo
      const targetRow = e.target.closest('.assy-row');
      if (!targetRow || targetRow === draggedElement) {
        return;
      }

      const targetGroupIndex = parseInt(targetRow.dataset.groupIndex);
      const draggedGroupIndex = parseInt(draggedElement.dataset.groupIndex);

      // Solo proceder si es el mismo grupo
      if (targetGroupIndex === draggedGroupIndex) {
        reorderWithinGroup(draggedElement, targetRow, targetGroupIndex, e.clientY);
      }
    }

    isDraggingOverDropZone = false;
  });
}

// Funcion para reordenar planes dentro del mismo grupo
function reorderWithinGroup(draggedRow, targetRow, groupIndex, clientY) {
  const lotNo = draggedRow.dataset.lot;
  const targetLotNo = targetRow.dataset.lot;



  // Obtener el grupo actual
  const currentGroup = visualGroups.groups[groupIndex];
  if (!currentGroup) {

    return;
  }

  // Encontrar ondices de los planes
  const draggedIndex = currentGroup.plans.findIndex(plan => plan.lot_no === lotNo);
  const targetIndex = currentGroup.plans.findIndex(plan => plan.lot_no === targetLotNo);

  if (draggedIndex === -1 || targetIndex === -1) {

    return;
  }



  // Determinar la nueva posicion basada en la posicion del mouse
  const rect = targetRow.getBoundingClientRect();
  const midpoint = rect.top + rect.height / 2;
  let newIndex;

  if (clientY < midpoint) {
    // Insertar antes del target
    newIndex = targetIndex;
  } else {
    // Insertar despuos del target
    newIndex = targetIndex + 1;
  }

  // Ajustar si estamos moviendo hacia adelante
  if (draggedIndex < newIndex) {
    newIndex--;
  }



  // Solo proceder si realmente hay cambio
  if (draggedIndex === newIndex) {

    return;
  }

  // Reordenar el array
  const [movedPlan] = currentGroup.plans.splice(draggedIndex, 1);
  currentGroup.plans.splice(newIndex, 0, movedPlan);



  // Re-renderizar la tabla usando los grupos ya reordenados
  renderCurrentVisualGroups();

  // Actualizar secuencias y fechas
  setTimeout(() => {
    updateSequenceNumbers();

    // Feedback visual sutil
    const movedRowAfterReload = document.querySelector(`tr[data-lot="${lotNo}"]`);
    if (movedRowAfterReload) {
      movedRowAfterReload.style.transition = 'background-color 0.3s ease';
      movedRowAfterReload.style.backgroundColor = '#27ae60';

      setTimeout(() => {
        movedRowAfterReload.style.backgroundColor = '';
        setTimeout(() => {
          movedRowAfterReload.style.transition = '';
        }, 300);
      }, 800);
    }
  }, 100);
}

// Calcular tiempos para cada grupo
function calculateGroupTimes() {
  visualGroups.groups.forEach((group, groupIndex) => {
    let totalProductiveMinutes = 0; // Solo tiempo productivo
    let currentTime = timeToMinutes(currentConfig.shiftStart);
    const groupStartTime = currentTime;

    // Filtrar planes que NO eston cancelados
    const activePlans = group.plans.filter(plan => plan.status !== 'CANCELADO');

    activePlans.forEach((plan, planIndex) => {
      const productionTime = calculateProductionTime(plan.plan_count || 0, plan.uph || 0);
      const startTime = currentTime;
      const plannedEndTime = currentTime + productionTime;

      // Verificar breaks que caen durante este plan
      let breaksDuringPlan = 0;
      currentConfig.breaks.forEach(breakInfo => {
        const breakStart = timeToMinutes(breakInfo.start);
        const breakEnd = timeToMinutes(breakInfo.end);
        const breakDuration = breakEnd - breakStart;

        // Si el break cae durante la produccion de este plan
        if (breakStart >= startTime && breakStart < plannedEndTime) {
          breaksDuringPlan += breakDuration;
        }
      });

      // Tiempo real de fin (incluyendo breaks)
      const actualEndTime = plannedEndTime + breaksDuringPlan;

      // Actualizar colculos individuales
      planningCalculations.set(plan.lot_no, {
        groupNumber: groupIndex + 1,
        productionTime: productionTime,
        startTime: minutesToTime(startTime),
        endTime: minutesToTime(actualEndTime), // Incluye breaks
        isOvertime: false, // Se calcularo despuos
        totalGroupTime: totalProductiveMinutes + productionTime
      });

      currentTime = actualEndTime; // Avanzar al tiempo real (con breaks)
      totalProductiveMinutes += productionTime; // Solo sumar tiempo productivo
    });

    // Para planes cancelados, no calcular tiempos pero mantener el registro
    group.plans.filter(plan => plan.status === 'CANCELADO').forEach(plan => {
      planningCalculations.set(plan.lot_no, {
        groupNumber: groupIndex + 1,
        productionTime: 0, // Sin tiempo de produccion
        startTime: '--',
        endTime: '--',
        isOvertime: false,
        totalGroupTime: 0,
        isCancelled: true // Marca especial para planes cancelados
      });
    });

    // Determinar si el grupo esto en overtime (mos de 9 horas productivas)
    const productiveMinutes = (currentConfig.productiveHours || 9) * 60; // 9 horas = 540 min
    group.totalTime = totalProductiveMinutes; // Solo tiempo productivo de planes activos
    group.isOvertime = totalProductiveMinutes > productiveMinutes;

    // Marcar planes individuales en overtime (solo los activos)
    let accumulatedTime = 0;
    activePlans.forEach(plan => {
      const calc = planningCalculations.get(plan.lot_no);
      if (calc) {
        accumulatedTime += calc.productionTime;
        calc.isOvertime = accumulatedTime > productiveMinutes; // Overtime cuando excede 9h productivas
      }
    });

    // Actualizar UI del grupo
    updateGroupUI(groupIndex, group);
  });

  // Actualizar filas de planes con colculos
  updatePlanRows();
}

// Actualizar UI del grupo
function updateGroupUI(groupIndex, group) {
  const totalElement = document.getElementById(`group-${groupIndex}-total`);
  const statusElement = document.getElementById(`group-${groupIndex}-status`);

  if (totalElement) {
    const hours = (group.totalTime / 60).toFixed(1);
    totalElement.textContent = `Total: ${hours}h`;
  }

  if (statusElement) {
    if (group.isOvertime) {
      statusElement.textContent = 'TIEMPO EXTRA';
      statusElement.className = 'status-extra';
    } else {
      statusElement.textContent = 'NORMAL';
      statusElement.className = 'status-normal';
    }
  }
}

// Actualizar filas de planes con colculos
function updatePlanRows() {
  const tbody = document.getElementById("assy-tableBody");
  const planRows = tbody.querySelectorAll('.assy-row');

  planRows.forEach(row => {
    const lotNo = row.dataset.lot;
    const calc = planningCalculations.get(lotNo);

    if (calc) {
      const cells = row.querySelectorAll('td');

      // Si el plan esto cancelado, mostrar tiempos como -- y marcar como cancelado
      if (calc.isCancelled) {
        if (cells[19]) cells[19].textContent = '--'; // Tiempo Productivo
        if (cells[20]) cells[20].textContent = '--'; // Inicio
        if (cells[21]) cells[21].textContent = '--'; // Fin
        if (cells[22]) cells[22].innerHTML = '<span class="status-cancelled">CANCELADO</span>'; // Turno

        // Resaltar fila como cancelada
        row.style.backgroundColor = '#6c6c6c';
        row.style.color = '#ccc';
        row.style.textDecoration = 'line-through';
      } else {
        // Plan activo - mostrar colculos normales
        if (cells[19]) cells[19].textContent = minutesToTime(calc.productionTime);
        if (cells[20]) cells[20].textContent = calc.startTime;
        if (cells[21]) cells[21].textContent = calc.endTime;

        // Actualizar indicador de tiempo extra en la columna Turno
        if (cells[22]) {
          cells[22].innerHTML = calc.isOvertime ?
            '<span class="status-extra">EXTRA</span>' :
            '<span class="status-normal">NORMAL</span>';
        }

        // Resaltar fila si esto en tiempo extra
        if (calc.isOvertime) {
          row.style.backgroundColor = '#8e2e2e';
          row.style.color = '#fff';
          row.style.textDecoration = '';
        } else {
          row.style.backgroundColor = '';
          row.style.color = '';
          row.style.textDecoration = '';
        }
      }

    // NO sobrescribir el status real de la base de datos (cells[18])
      // El status real (PLAN, EN PROGRESO, CANCELADO, etc.) debe mantenerse
    }
  });
}

// Renderizar grupos visuales actuales sin leer del DOM
function renderCurrentVisualGroups() {
  const table = document.getElementById('assy-table');
  const oldTbody = document.getElementById('assy-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'assy-tableBody';

  // Renderizar cada grupo usando los datos ya en memoria
  visualGroups.groups.forEach((group, groupIndex) => {
    // Fila de encabezado del grupo
    const groupHeaderRow = document.createElement('tr');
    groupHeaderRow.className = 'group-header-row';
    groupHeaderRow.innerHTML = `
      <td colspan="23" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>${group.name}</span>
          <div>
            <span id="group-${groupIndex}-total" style="margin-right: 10px;">Total: 0.0h</span>
            <span id="group-${groupIndex}-status" class="status-calc">CALCULANDO</span>
          </div>
        </div>
      </td>
    `;
    tbody.appendChild(groupHeaderRow);

    // Zona de drop para el grupo
    const dropZoneRow = document.createElement('tr');
    dropZoneRow.className = 'group-drop-zone';
    dropZoneRow.dataset.groupIndex = groupIndex;
    dropZoneRow.innerHTML = `
      <td colspan="23" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
        <div class="drop-zone-content">
          ${group.plans.length === 0 ? 'Arrastra planes aquo para asignarlos a este grupo' : ''}
        </div>
      </td>
    `;
    tbody.appendChild(dropZoneRow);

    // Renderizar planes del grupo en el orden actual
    group.plans.forEach((plan, planIndex) => {
      const tr = document.createElement('tr');
      tr.className = 'assy-row';
      tr.dataset.lot = plan.lot_no;
      tr.dataset.groupIndex = groupIndex;
      tr.draggable = true;

      // Calcular secuencia dentro del grupo
      const groupSequence = planIndex + 1;

      tr.innerHTML = `
        <td style="background-color: #e74c3c; color: white; font-weight: bold; text-align: center;">${groupSequence}</td>
        <td>${plan.lot_no}</td>
        <td>${plan.wo_code || ""}</td>
        <td>${plan.po_code || ""}</td>
        <td>${plan.working_date}</td>
        <td>${plan.line}</td>
        <td>${routingToTurno(plan.routing)}</td>
        <td>${plan.model_code}</td>
        <td>${partNoWithBomRevision(plan)}</td>
        <td>${plan.sub_assy || ''}</td>
        <td>${plan.project}</td>
        <td>${plan.process || ""}</td>
        <td>${plan.ct || "0"}</td>
        <td>${plan.uph || "0"}</td>
        <td>${plan.plan_count}</td>
        <td>${plan.produced ?? 0}</td>
        <td>${plan.output ?? 0}</td>
        <td>${plan.entregadas_main ?? 0}</td>
        <td>${plan.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell fecha-inicio-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold;">-</td>
      `;

      tbody.appendChild(tr);
    });

    // Espacio entre grupos
    if (groupIndex < visualGroups.groups.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'group-spacer';
      spacerRow.innerHTML = `<td colspan="23" style="height: 10px; background-color: #2c2c2c;"></td>`;
      tbody.appendChild(spacerRow);
    }
  });

  // Reemplazar tbody para limpiar listeners viejos y reconfigurar drag & drop
  if (oldTbody && oldTbody.parentNode) {
    oldTbody.parentNode.replaceChild(tbody, oldTbody);
  } else if (table) {
    table.appendChild(tbody);
  }
  setupGroupDragDrop();

  // Calcular tiempos para grupos
  calculateGroupTimes();
}

// Recargar tabla manteniendo datos actuales
function reloadTableWithCurrentData() {
  // Obtener datos actuales del DOM
  const tbody = document.getElementById("assy-tableBody");
  const planRows = tbody.querySelectorAll('.assy-row');
  const currentData = [];

  planRows.forEach(row => {
    const cells = row.querySelectorAll('td');
    const lotNo = row.dataset.lot;

    if (!lotNo) return; // Skip si no tiene lot_no

    // ? BUSCAR PRIMERO en originalPlansData para preservar todos los campos (especialmente status)
    let planData = originalPlansData.find(p => p.lot_no === lotNo);

    // Si no esto en originalPlansData, reconstruir desde HTML (con ondices corregidos)
    if (!planData) {
      planData = {
        lot_no: lotNo,
        wo_code: cells[2]?.textContent?.trim() || '',
        po_code: cells[3]?.textContent?.trim() || '',
        working_date: cells[4]?.textContent?.trim() || '',
        line: cells[5]?.textContent?.trim() || '',
        routing: turnoToRouting(cells[6]?.textContent?.trim()) || 1,
        model_code: cells[7]?.textContent?.trim() || '',
        part_no: cells[8]?.textContent?.trim() || '',
        project: cells[10]?.textContent?.trim() || '',
        process: cells[11]?.textContent?.trim() || 'MAIN',
        ct: cells[12]?.textContent?.trim() || '0',
        uph: parseInt(cells[13]?.textContent?.trim()) || 0,
        plan_count: parseInt(cells[14]?.textContent?.trim()) || 0,
        produced: parseInt(cells[15]?.textContent?.trim()) || 0,
        output: parseInt(cells[16]?.textContent?.trim()) || 0,
        entregadas_main: parseInt(cells[17]?.textContent?.trim()) || 0,
        status: cells[18]?.textContent?.trim() || 'PLAN' // ? CORREGIDO: cells[17] no cells[16]
      };
    }

    // Validar que los datos esenciales existan
    if (planData.lot_no && planData.part_no) {
      currentData.push(planData);
    }
  });



  // Re-renderizar con datos actuales
  renderTableWithVisualGroups(currentData);

  // Actualizar fechas de inicio despuos del renderizado
  setTimeout(() => {
    // Ya no necesitamos updateStartDates
  }, 100);
}

function autoArrangePlans() {
  const tbody = document.getElementById('assy-tableBody');
  const planRows = Array.from(tbody.querySelectorAll('.assy-row'));

  if (planRows.length === 0) {
    // Feedback visual en lugar de alert
    const autoBtn = document.getElementById('assy-auto-arrange-btn');
    const originalText = autoBtn.textContent;
    autoBtn.textContent = '?? Sin planes';
    autoBtn.style.backgroundColor = '#e67e22';

    setTimeout(() => {
      autoBtn.textContent = originalText;
      autoBtn.style.backgroundColor = '#27ae60';
    }, 2000);
    return;
  }

  // Obtener datos de los planes desde el DOM
  const plans = planRows.map(row => {
    const cells = row.querySelectorAll('td');
    const lotNo = row.dataset.lot;

    return {
      lot_no: lotNo,
      line: cells[5]?.textContent?.trim() || '',
      uph: parseInt(cells[13]?.textContent) || 0,
      plan_count: parseInt(cells[14]?.textContent) || 0,
      productionTime: calculateProductionTime(
        parseInt(cells[14]?.textContent) || 0,
        parseInt(cells[13]?.textContent) || 0
      ),
      // Datos completos del plan
      wo_code: cells[2]?.textContent?.trim() || '',
      po_code: cells[3]?.textContent?.trim() || '',
      working_date: cells[4]?.textContent?.trim() || '',
      routing: cells[6]?.textContent?.trim() === 'DIA' ? 1 :
        cells[6]?.textContent?.trim() === 'TIEMPO EXTRA' ? 2 :
          cells[6]?.textContent?.trim() === 'NOCHE' ? 3 : 1,
      model_code: cells[7]?.textContent?.trim() || '',
      part_no: cells[8]?.textContent?.trim() || '',
      project: cells[10]?.textContent?.trim() || '',
      process: cells[11]?.textContent?.trim() || 'MAIN',
      ct: cells[12]?.textContent?.trim() || '0',
      produced: parseInt(cells[15]?.textContent) || 0,
      output: parseInt(cells[16]?.textContent) || 0,
      entregadas_main: parseInt(cells[17]?.textContent) || 0,
      status: cells[18]?.textContent?.trim() || 'PLAN'
    };
  });

  // Agrupar planes por lonea primero
  const lineGroups = {};
  plans.forEach(plan => {
    if (!lineGroups[plan.line]) {
      lineGroups[plan.line] = [];
    }
    lineGroups[plan.line].push(plan);
  });

  // Ordenar planes dentro de cada lonea por tiempo de produccion (menor a mayor)
  Object.keys(lineGroups).forEach(line => {
    lineGroups[line].sort((a, b) => a.productionTime - b.productionTime);
  });

  // Distribuir manteniendo loneas juntas de forma secuencial
  const groupCount = parseInt(document.getElementById('assy-groups-count').value) || 6;
  visualGroups.planAssignments.clear();

  // Algoritmo mejorado: asignacion secuencial de loneas a grupos
  const productiveMinutes = (currentConfig.productiveHours || 9) * 60; // 9 horas productivas = 540 min
  const groupTimes = new Array(groupCount).fill(0);
  const groupLines = new Array(groupCount).fill().map(() => new Map()); // Loneas y sus tiempos por grupo

  // Auto-acomodo iniciado (modo secuencial)

  // Ordenar loneas con orden especofico: M1, M2, M3, M4, D1, D2, D3, H1, etc.
  const sortedLines = Object.keys(lineGroups).sort((a, b) => {
    // Extraer letra y nomero de cada lonea
    const matchA = a.match(/^([A-Z]+)(\d+)$/);
    const matchB = b.match(/^([A-Z]+)(\d+)$/);
    
    if (!matchA || !matchB) {
      return a.localeCompare(b); // Fallback para formatos no estondar
    }
    
    const [, letterA, numA] = matchA;
    const [, letterB, numB] = matchB;
    
    // Orden de prioridad de letras: M, D, H, luego alfabotico
    const letterOrder = { 'M': 1, 'D': 2, 'H': 3 };
    const orderA = letterOrder[letterA] || 99;
    const orderB = letterOrder[letterB] || 99;
    
    // Primero comparar por letra (M antes que D antes que H)
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    
    // Si la letra es igual, ordenar por nomero
    return parseInt(numA) - parseInt(numB);
  });
  
  // console.log('?? Orden de loneas para auto-acomodo:', sortedLines.join(', '));

  // Asignar cada lonea a un grupo de forma secuencial (round-robin)
  sortedLines.forEach((line, lineIndex) => {
    const linePlans = lineGroups[line];
    const totalLineTime = linePlans.reduce((sum, plan) => sum + plan.productionTime, 0);

    // Asignacion secuencial: M1 -> Grupo 0, M2 -> Grupo 1, M3 -> Grupo 2, etc.
    // Si hay mos loneas que grupos, se hace round-robin (M7 -> Grupo 0, M8 -> Grupo 1, etc.)
    const groupIndex = lineIndex % groupCount;

    // console.log(`?? Auto-acomodo: Lonea ${line} ? Grupo ${groupIndex + 1} (${totalLineTime.toFixed(1)} min)`);

    // Asignar todos los planes de la lonea al grupo correspondiente
    linePlans.forEach(plan => {
      visualGroups.planAssignments.set(plan.lot_no, groupIndex);
    });

    // Actualizar estadosticas del grupo
    groupTimes[groupIndex] += totalLineTime;
    if (!groupLines[groupIndex].has(line)) {
      groupLines[groupIndex].set(line, 0);
    }
    groupLines[groupIndex].set(line, groupLines[groupIndex].get(line) + totalLineTime);
  });

  // Mostrar reporte de distribucion
  const groupsWithOvertime = groupTimes.filter(time => time > productiveMinutes).length;
  const totalTime = groupTimes.reduce((sum, time) => sum + time, 0);
  const avgTimePerGroup = totalTime / groupCount;

  // Resultado del auto-acomodo

  // Re-renderizar tabla con nueva distribucion
  renderTableWithVisualGroups(plans);

  // Recalcular tiempos despuos de la redistribucion
  calculateGroupTimes();

  // Feedback visual mejorado
  const autoBtn = document.getElementById('assy-auto-arrange-btn');
  const originalText = autoBtn.textContent;

  if (groupsWithOvertime === 0) {
    autoBtn.textContent = '? Sin Tiempo Extra';
    autoBtn.style.backgroundColor = '#27ae60';
  } else {
    autoBtn.textContent = `?? ${groupsWithOvertime} con Extra`;
    autoBtn.style.backgroundColor = '#f39c12';
  }

  setTimeout(() => {
    autoBtn.textContent = originalText;
    autoBtn.style.backgroundColor = '#27ae60'; // Verde original
  }, 3000);
}

// Exponer funcion globalmente
window.autoArrangePlans = autoArrangePlans;

// ====== VISTA POR LINEAS ======
// Variable de estado para controlar la vista activa
let currentViewMode = 'groups'; // 'groups' | 'lines'

// Funcion para alternar entre vista de grupos y vista por lineas
function toggleViewMode() {
  const toggleBtn = document.getElementById('assy-toggle-view-btn');
  const groupsCountSelect = document.getElementById('assy-groups-count');
  const groupsLabel = groupsCountSelect?.previousElementSibling;
  const autoArrangeBtn = document.getElementById('assy-auto-arrange-btn');
  const saveSeqBtn = document.getElementById('assy-save-sequences-btn');
  const lineFilter = document.getElementById('assy-line-filter');

  if (currentViewMode === 'groups') {
    // Cambiar a vista por lineas
    currentViewMode = 'lines';
    if (toggleBtn) {
      toggleBtn.textContent = 'Vista por Grupos';
      toggleBtn.style.backgroundColor = '#2980b9';
    }
    // Ocultar controles de grupos
    if (groupsCountSelect) groupsCountSelect.style.display = 'none';
    if (groupsLabel) groupsLabel.style.display = 'none';
    if (autoArrangeBtn) autoArrangeBtn.style.display = 'none';
    if (saveSeqBtn) saveSeqBtn.style.display = 'none';
    // Mostrar filtro de linea
    if (lineFilter) lineFilter.style.display = 'inline-block';

    // Renderizar vista por lineas
    renderTableByLines();
  } else {
    // Cambiar a vista por grupos
    currentViewMode = 'groups';
    if (toggleBtn) {
      toggleBtn.textContent = 'Vista por Lineas';
      toggleBtn.style.backgroundColor = '#16a085';
    }
    // Mostrar controles de grupos
    if (groupsCountSelect) groupsCountSelect.style.display = 'inline-block';
    if (groupsLabel) groupsLabel.style.display = 'inline';
    if (autoArrangeBtn) autoArrangeBtn.style.display = 'inline-block';
    if (saveSeqBtn) saveSeqBtn.style.display = 'inline-block';
    // Ocultar filtro de linea
    if (lineFilter) lineFilter.style.display = 'none';

    // Re-renderizar con grupos
    reloadTableWithCurrentData();
  }
}

// Poblar filtro de lineas con las lineas disponibles
function populateLineFilter(plans) {
  const lineFilter = document.getElementById('assy-line-filter');
  if (!lineFilter) return;

  const lines = new Set();
  plans.forEach(p => {
    if (p.line) lines.add(p.line);
  });

  // Ordenar lineas: M1, M2, M3, M4, D1, D2, D3, H1, etc
  const sortedLines = Array.from(lines).sort((a, b) => {
    const matchA = a.match(/^([A-Z]+)(\d+)$/);
    const matchB = b.match(/^([A-Z]+)(\d+)$/);
    if (!matchA || !matchB) return a.localeCompare(b);
    const letterOrder = { 'M': 1, 'D': 2, 'H': 3 };
    const orderA = letterOrder[matchA[1]] || 99;
    const orderB = letterOrder[matchB[1]] || 99;
    if (orderA !== orderB) return orderA - orderB;
    return parseInt(matchA[2]) - parseInt(matchB[2]);
  });

  // Preservar seleccion actual
  const currentValue = lineFilter.value;
  lineFilter.innerHTML = '<option value="">Todas</option>';
  sortedLines.forEach(line => {
    const opt = document.createElement('option');
    opt.value = line;
    opt.textContent = line;
    lineFilter.appendChild(opt);
  });
  lineFilter.value = currentValue;
}

function renderTableByLines(filterLine) {
  const table = document.getElementById('assy-table');
  const oldTbody = document.getElementById('assy-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'assy-tableBody';

  // Obtener todos los planes disponibles
  let allPlans = [];
  if (originalPlansData && originalPlansData.length > 0) {
    allPlans = originalPlansData.map(p => ({ ...p }));
  } else if (visualGroups && visualGroups.groups) {
    visualGroups.groups.forEach(g => {
      if (g.plans) allPlans.push(...g.plans.map(p => ({ ...p })));
    });
  }

  // Poblar filtro de lineas
  populateLineFilter(allPlans);

  // Aplicar filtro de linea si existe
  if (filterLine) {
    allPlans = allPlans.filter(p => p.line === filterLine);
  }

  // Agrupar por linea
  const lineGroups = {};
  allPlans.forEach(plan => {
    const line = plan.line || 'SIN LINEA';
    if (!lineGroups[line]) lineGroups[line] = [];
    lineGroups[line].push(plan);
  });

  // Ordenar lineas
  const sortedLines = Object.keys(lineGroups).sort((a, b) => {
    const matchA = a.match(/^([A-Z]+)(\d+)$/);
    const matchB = b.match(/^([A-Z]+)(\d+)$/);
    if (!matchA || !matchB) return a.localeCompare(b);
    const letterOrder = { 'M': 1, 'D': 2, 'H': 3 };
    const orderA = letterOrder[matchA[1]] || 99;
    const orderB = letterOrder[matchB[1]] || 99;
    if (orderA !== orderB) return orderA - orderB;
    return parseInt(matchA[2]) - parseInt(matchB[2]);
  });

  // Limpiar calculos previos para recalcular por linea
  planningCalculations.clear();

  // Renderizar cada linea como un grupo visual
  sortedLines.forEach((line, lineIdx) => {
    const plans = lineGroups[line];

    // Ordenar planes dentro de la linea por sequence o por order guardado
    plans.sort((a, b) => {
      const aSeq = a.sequence || 999;
      const bSeq = b.sequence || 999;
      return aSeq - bSeq;
    });

    // Calcular tiempos para la linea
    let currentTime = timeToMinutes(currentConfig.shiftStart);
    let totalProductiveMinutes = 0;
    const productiveMinutes = (currentConfig.productiveHours || 9) * 60;

    const activePlans = plans.filter(p => p.status !== 'CANCELADO');

    activePlans.forEach(plan => {
      const productionTime = calculateProductionTime(plan.plan_count || 0, plan.uph || 0);
      const startTime = currentTime;
      const plannedEndTime = currentTime + productionTime;

      // Verificar breaks
      let breaksDuringPlan = 0;
      currentConfig.breaks.forEach(breakInfo => {
        const breakStart = timeToMinutes(breakInfo.start);
        const breakEnd = timeToMinutes(breakInfo.end);
        const breakDuration = breakEnd - breakStart;
        if (breakStart >= startTime && breakStart < plannedEndTime) {
          breaksDuringPlan += breakDuration;
        }
      });

      const actualEndTime = plannedEndTime + breaksDuringPlan;

      planningCalculations.set(plan.lot_no, {
        groupNumber: lineIdx + 1,
        productionTime: productionTime,
        startTime: minutesToTime(startTime),
        endTime: minutesToTime(actualEndTime),
        isOvertime: false,
        totalGroupTime: totalProductiveMinutes + productionTime
      });

      currentTime = actualEndTime;
      totalProductiveMinutes += productionTime;
    });

    // Planes cancelados
    plans.filter(p => p.status === 'CANCELADO').forEach(plan => {
      planningCalculations.set(plan.lot_no, {
        groupNumber: lineIdx + 1,
        productionTime: 0,
        startTime: '--',
        endTime: '--',
        isOvertime: false,
        totalGroupTime: 0,
        isCancelled: true
      });
    });

    // Marcar overtime
    const isLineOvertime = totalProductiveMinutes > productiveMinutes;
    let accumulatedTime = 0;
    activePlans.forEach(plan => {
      const calc = planningCalculations.get(plan.lot_no);
      if (calc) {
        accumulatedTime += calc.productionTime;
        calc.isOvertime = accumulatedTime > productiveMinutes;
      }
    });

    // Header de linea
    const totalHours = (totalProductiveMinutes / 60).toFixed(1);
    const statusClass = isLineOvertime ? 'status-extra' : 'status-normal';
    const statusText = isLineOvertime ? 'TIEMPO EXTRA' : 'NORMAL';

    const headerRow = document.createElement('tr');
    headerRow.className = 'group-header-row line-header-row';
    headerRow.innerHTML = `
      <td colspan="23" style="background-color: #1a3a4a; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #16a085;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 14px;">LINEA ${line}</span>
          <div>
            <span style="margin-right: 10px;">Total: ${totalHours}h</span>
            <span class="${statusClass}">${statusText}</span>
          </div>
        </div>
      </td>
    `;
    tbody.appendChild(headerRow);

    // Renderizar planes
    plans.forEach((plan, planIndex) => {
      const tr = document.createElement('tr');
      tr.dataset.lot = plan.lot_no;
      tr.dataset.line = line;
      tr.className = 'assy-row';

      const calc = planningCalculations.get(plan.lot_no);
      const isCancelled = plan.status === 'CANCELADO';

      let tiempoCell = '--:--';
      let inicioCell = '--:--';
      let finCell = '--:--';
      let turnoHTML = '-';

      if (calc && !isCancelled) {
        tiempoCell = minutesToTime(calc.productionTime);
        inicioCell = calc.startTime;
        finCell = calc.endTime;
        turnoHTML = calc.isOvertime
          ? '<span class="status-extra">EXTRA</span>'
          : '<span class="status-normal">NORMAL</span>';
      } else if (isCancelled) {
        turnoHTML = '<span class="status-cancelled">CANCELADO</span>';
      }

      tr.innerHTML = `
        <td style="background-color: #16a085; color: white; font-weight: bold; text-align: center;">${planIndex + 1}</td>
        <td>${plan.lot_no}</td>
        <td>${plan.wo_code || ''}</td>
        <td>${plan.po_code || ''}</td>
        <td>${plan.working_date || ''}</td>
        <td>${plan.line || ''}</td>
        <td>${routingToTurno(plan.routing)}</td>
        <td>${plan.model_code || ''}</td>
        <td>${partNoWithBomRevision(plan)}</td>
        <td>${plan.sub_assy || ''}</td>
        <td>${plan.project || ''}</td>
        <td>${plan.process || ''}</td>
        <td>${plan.ct || '0'}</td>
        <td>${plan.uph || '0'}</td>
        <td>${plan.plan_count || 0}</td>
        <td>${plan.produced ?? 0}</td>
        <td>${plan.output ?? 0}</td>
        <td>${plan.entregadas_main ?? 0}</td>
        <td>${plan.status || 'PLAN'}</td>
        <td class="tiempo-cell">${tiempoCell}</td>
        <td class="tiempo-cell fecha-inicio-cell">${inicioCell}</td>
        <td class="tiempo-cell">${finCell}</td>
        <td style="text-align:center; font-weight:bold;">${turnoHTML}</td>
      `;

      // Estilos para cancelado u overtime
      if (isCancelled) {
        tr.style.backgroundColor = '#6c6c6c';
        tr.style.color = '#ccc';
        tr.style.textDecoration = 'line-through';
      } else if (calc && calc.isOvertime) {
        tr.style.backgroundColor = '#8e2e2e';
        tr.style.color = '#fff';
      }

      tbody.appendChild(tr);
    });

    // Espacio entre lineas
    if (lineIdx < sortedLines.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'group-spacer';
      spacerRow.innerHTML = `<td colspan="23" style="height: 10px; background-color: #2c2c2c;"></td>`;
      tbody.appendChild(spacerRow);
    }
  });

  // Si no hay planes
  if (sortedLines.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = `<td colspan="23" style="text-align: center; padding: 20px; color: #888;">No hay planes para mostrar</td>`;
    tbody.appendChild(emptyRow);
  }

  // Reemplazar tbody
  if (oldTbody && oldTbody.parentNode) {
    oldTbody.parentNode.replaceChild(tbody, oldTbody);
  } else if (table) {
    table.appendChild(tbody);
  }
}

function calculateAndUpdateTimes() {
  const tbody = document.getElementById('assy-tableBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  // Obtener datos actuales
  const plans = rows.map(row => {
    const cells = row.querySelectorAll('td');
    return {
      lot_no: row.dataset.lot,
      line: cells[5]?.textContent || '',
      uph: parseInt(cells[13]?.textContent) || 0,
      plan_count: parseInt(cells[14]?.textContent) || 0
    };
  });

  // Calcular tiempos
  calculatePlanningTimes(plans);

  // Actualizar filas con nueva informacion
  rows.forEach((row, index) => {
    const lotNo = row.dataset.lot;
    const calc = planningCalculations.get(lotNo);

    if (calc) {
      // Agregar celdas de planeacion si no existen
      let cells = row.querySelectorAll('td');

      // Tiempo de produccion
      if (cells.length >= 19) {
        cells[19].textContent = minutesToTime(calc.productionTime);
        cells[19].className = 'tiempo-cell';
      } else {
        const timeCell = document.createElement('td');
        timeCell.textContent = minutesToTime(calc.productionTime);
        timeCell.className = 'tiempo-cell';
        row.appendChild(timeCell);
      }

      // Hora inicio
      if (cells.length >= 20) {
        cells[20].textContent = calc.startTime;
        cells[20].className = 'tiempo-cell fecha-inicio-cell';
      } else {
        const startCell = document.createElement('td');
        startCell.textContent = calc.startTime;
        startCell.className = 'tiempo-cell fecha-inicio-cell';
        row.appendChild(startCell);
      }

      // Hora fin
      if (cells.length >= 21) {
        cells[21].textContent = calc.endTime;
        cells[21].className = 'tiempo-cell';
      } else {
        const endCell = document.createElement('td');
        endCell.textContent = calc.endTime;
        endCell.className = 'tiempo-cell';
        row.appendChild(endCell);
      }

      // Indicador de tiempo extra en la oltima columna (Turno)
      if (cells.length >= 22) {
        cells[22].innerHTML = calc.isOvertime ?
          '<span style="background:#e74c3c; color:white; padding:2px 6px; border-radius:3px; font-size:9px;">EXTRA</span>' :
          '<span style="background:#27ae60; color:white; padding:2px 6px; border-radius:3px; font-size:9px;">NORMAL</span>';
      } else {
        const extraCell = document.createElement('td');
        extraCell.innerHTML = calc.isOvertime ?
          '<span style="background:#e74c3c; color:white; padding:2px 6px; border-radius:3px; font-size:9px;">EXTRA</span>' :
          '<span style="background:#27ae60; color:white; padding:2px 6px; border-radius:3px; font-size:9px;">NORMAL</span>';
        row.appendChild(extraCell);
      }

      // Resaltar fila si esto en tiempo extra
      if (calc.isOvertime) {
        row.style.backgroundColor = '#8e2e2e';
        row.style.color = '#fff';
      } else {
        row.style.backgroundColor = '';
        row.style.color = '';
      }
    }
  });
}

// ====== Función para llenar el selector de grupos dinámicamente ======
function populateGroupSelector() {
  const selectElement = document.getElementById('target-group-select');
  if (!selectElement) {
    console.warn('Selector de grupos no encontrado');
    return;
  }

  // Obtener número de grupos actual
  const groupCount = parseInt(document.getElementById('assy-groups-count')?.value) || 6;
  
  // Limpiar opciones existentes (excepto la primera opción "Automático")
  selectElement.innerHTML = '<option value="">Automático (al final)</option>';
  
  // Agregar una opción por cada grupo
  for (let i = 1; i <= groupCount; i++) {
    const option = document.createElement('option');
    option.value = i;
    option.textContent = `Grupo ${i}`;
    selectElement.appendChild(option);
  }
  
  // console.log(`Selector de grupos actualizado con ${groupCount} grupos`);
}

// ====== Función para asignar un plan a un grupo específico ======
function assignPlanToGroup(lotNo, targetGroupIndex) {
  // console.log(`Asignando plan ${lotNo} al grupo ${targetGroupIndex + 1}`);
  
  // Actualizar visualGroups.planAssignments
  visualGroups.planAssignments.set(lotNo, targetGroupIndex);
  
  // Buscar el plan en originalPlansData
  const planData = originalPlansData.find(p => p.lot_no === lotNo);
  
  if (!planData) {
    console.error(`Plan ${lotNo} no encontrado en originalPlansData`);
    return;
  }
  
  // Remover el plan de todos los grupos
  visualGroups.groups.forEach(group => {
    const index = group.plans.findIndex(p => p.lot_no === lotNo);
    if (index !== -1) {
      group.plans.splice(index, 1);
    }
  });
  
  // Asegurarse de que el grupo destino existe
  while (visualGroups.groups.length <= targetGroupIndex) {
    visualGroups.groups.push({ plans: [] });
  }
  
  // Agregar el plan al grupo destino
  visualGroups.groups[targetGroupIndex].plans.push(planData);
  
  // console.log(`Plan ${lotNo} asignado al grupo ${targetGroupIndex + 1}`);
  
  // Re-renderizar la tabla
  const allPlans = [];
  visualGroups.groups.forEach(group => {
    allPlans.push(...group.plans);
  });
  
  renderTableWithVisualGroups(allPlans);
}

async function saveGroupSequences(options = {}) {
  const silent = options === true || options.silent === true;
  const saveBtn = document.getElementById('assy-save-sequences-btn');
  if (!saveBtn && !silent) return;

  // Mostrar loading
  if (!silent && saveBtn) {
    saveBtn.textContent = 'Guardando...';
    saveBtn.disabled = true;
  }

  try {
    const sequenceData = [];

    // Verificar que visualGroups esto disponible
    if (!visualGroups || !visualGroups.groups) {
      throw new Error('No hay grupos de planeacion disponibles');
    }

    // Recopilar datos de secuencia para cada plan (solo planes activos)
    visualGroups.groups.forEach((group, groupIndex) => {
      if (group && group.plans && Array.isArray(group.plans)) {
        // Filtrar planes que NO eston cancelados
        const activePlans = group.plans.filter(plan => plan && plan.lot_no && plan.status !== 'CANCELADO');

        activePlans.forEach((plan, planIndex) => {
          const startTime = planningCalculations.get(plan.lot_no)?.startTime || '--';
          const endTime = planningCalculations.get(plan.lot_no)?.endTime || '--';
          const productionTime = planningCalculations.get(plan.lot_no)?.productionTime || 0;

          // Convertir startTime (HH:MM) a DATETIME para planned_start
          // IMPORTANTE: NO usar toISOString() porque convierte a UTC sumando horas
          // En su lugar, construir el string directamente en zona horaria local (Nuevo León)
          let plannedStart = null;
          if (startTime !== '--') {
            const planDateStr = plan.working_date || getTodayInNuevoLeon(); // Fecha del plan
            const [hours, minutes] = startTime.split(':');
            // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
            plannedStart = `${planDateStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
          }

          // Convertir endTime (HH:MM) a DATETIME para planned_end
          // IMPORTANTE: NO usar toISOString() porque convierte a UTC sumando horas
          let plannedEnd = null;
          if (endTime !== '--') {
            const planDateStr = plan.working_date || getTodayInNuevoLeon(); // Fecha del plan
            const [hours, minutes] = endTime.split(':');
            // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
            plannedEnd = `${planDateStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
          }

          // Tambion enviar solo la fecha para plan_start_date
          let planStartDate = null;
          if (startTime !== '--') {
            planStartDate = plan.working_date || getTodayInNuevoLeon(); // Formato: YYYY-MM-DD
          }

          // Calcular effective_minutes (tiempo productivo sin breaks)
          const effectiveMinutes = productionTime; // productionTime ya esto en minutos

          // Calcular breaks_minutes (estimar breaks que caen durante la produccion)
          let breaksMinutes = 0;
          if (startTime !== '--' && endTime !== '--') {
            const startMinutes = timeToMinutes(startTime);
            const endMinutes = timeToMinutes(endTime);

            // Verificar breaks que caen durante este plan
            currentConfig.breaks.forEach(breakInfo => {
              const breakStart = timeToMinutes(breakInfo.start);
              const breakEnd = timeToMinutes(breakInfo.end);
              const breakDuration = breakEnd - breakStart;

              // Si el break cae durante la produccion de este plan
              if (breakStart >= startMinutes && breakStart < endMinutes) {
                breaksMinutes += breakDuration;
              }
            });
          }

          sequenceData.push({
            lot_no: String(plan.lot_no), // Asegurar que sea string
            group_no: groupIndex + 1,
            sequence: planIndex + 1,
            plan_start_date: planStartDate,
            planned_start: plannedStart,
            planned_end: plannedEnd,
            effective_minutes: effectiveMinutes,
            breaks_minutes: breaksMinutes
          });
        });
      }
    });

    if (sequenceData.length === 0) {
      throw new Error('No hay planes para guardar');
    }





    const response = await fetch('/api/plan/save-sequences', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sequences: sequenceData
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (!silent && saveBtn) {
        saveBtn.textContent = '? Guardado';
        saveBtn.style.backgroundColor = '#27ae60';
      }

      // Mostrar mensaje de confirmacion
      const message = result.message || 'Secuencias guardadas correctamente';
      if (!silent) {
        showNotification(message, 'success');
      }

      // Actualizar localStorage para mantener consistencia
      const currentOrder = [];
      visualGroups.groups.forEach(group => {
        if (group && group.plans) {
          group.plans.forEach(plan => {
            if (plan && plan.lot_no) {
              currentOrder.push(plan.lot_no);
            }
          });
        }
      });

      // Guardar en localStorage usando las fechas actuales
      const fs = document.getElementById("assy-filter-start")?.value;
      const fe = document.getElementById("assy-filter-end")?.value;
      const key = orderStorageKey(fs, fe);
      localStorage.setItem(key, JSON.stringify(currentOrder));
      // LocalStorage actualizado con el orden guardado

      if (!silent && saveBtn) {
        setTimeout(() => {
          saveBtn.textContent = 'Guardar Orden';
          saveBtn.style.backgroundColor = '#3498db';
          saveBtn.disabled = false;
        }, 2000);
      }
      return true;
    } else {
      const errorData = await response.json();
      // Error response:
      throw new Error(errorData.error || 'Error al guardar');
    }
  } catch (error) {
    // Error completo al guardar secuencias
    // Stack trace:
    if (silent) {
      console.warn('Auto guardado de orden falló:', error);
      return false;
    }

    saveBtn.textContent = '? Error';
    saveBtn.style.backgroundColor = '#e74c3c';

    // Mostrar mensaje de error mos detallado
    const errorMessage = error.message || 'Error desconocido al guardar';
    showNotification('Error al guardar: ' + errorMessage, 'error');

    setTimeout(() => {
      saveBtn.textContent = '?? Guardar Orden';
      saveBtn.style.backgroundColor = '#3498db';
      saveBtn.disabled = false;
    }, 3000);
  }
}

// Exponer funcion globalmente
window.saveGroupSequences = saveGroupSequences;

// Funcion para actualizar las secuencias en tiempo real cuando se mueven planes
function updateSequenceNumbers() {
  const tbody = document.getElementById("assy-tableBody");
  const planRows = tbody.querySelectorAll('.assy-row');

  // Agrupar filas por grupo
  const rowsByGroup = {};
  planRows.forEach(row => {
    const groupIndex = parseInt(row.dataset.groupIndex);
    if (!rowsByGroup[groupIndex]) {
      rowsByGroup[groupIndex] = [];
    }
    rowsByGroup[groupIndex].push(row);
  });

  // Actualizar secuencias dentro de cada grupo
  Object.keys(rowsByGroup).forEach(groupIndex => {
    const groupRows = rowsByGroup[groupIndex];
    groupRows.forEach((row, index) => {
      // Actualizar la celda de secuencia (primera columna)
      const sequenceCell = row.querySelector('td:first-child');
      if (sequenceCell) {
        sequenceCell.textContent = index + 1;

        // Agregar animacion sutil para indicar cambio
        sequenceCell.style.transition = 'background-color 0.3s ease';
        sequenceCell.style.backgroundColor = '#27ae60';

        setTimeout(() => {
          sequenceCell.style.backgroundColor = '#e74c3c';
        }, 200);
      }
    });
  });
}

// Funcion para recalcular fechas de inicio despuos de mover planes
function updateStartDates() {
  visualGroups.groups.forEach((group, groupIndex) => {
    let currentTime = timeToMinutes(currentConfig.shiftStart);

    group.plans.forEach((plan, planIndex) => {
      const productionTime = calculateProductionTime(plan.plan_count || 0, plan.uph || 0);
      const startTime = currentTime;

      // Verificar breaks que caen durante este plan
      let breaksDuringPlan = 0;
      currentConfig.breaks.forEach(breakInfo => {
        const breakStart = timeToMinutes(breakInfo.start);
        const breakEnd = timeToMinutes(breakInfo.end);
        const breakDuration = breakEnd - breakStart;

        if (breakStart >= startTime && breakStart < (startTime + productionTime)) {
          breaksDuringPlan += breakDuration;
        }
      });

      // Actualizar fecha de inicio en los colculos
      planningCalculations.set(plan.lot_no, {
        ...planningCalculations.get(plan.lot_no),
        startTime: minutesToTime(startTime)
      });

      // Avanzar tiempo para el siguiente plan
      currentTime += productionTime + breaksDuringPlan;
    });
  });

  // Actualizar las celdas de fecha de inicio en la tabla
  const tbody = document.getElementById("assy-tableBody");
  const planRows = tbody.querySelectorAll('.assy-row');

  planRows.forEach(row => {
    const lotNo = row.dataset.lot;
    const calculation = planningCalculations.get(lotNo);
    if (calculation) {
      const fechaInicioCell = row.querySelector('.fecha-inicio-cell');
      if (fechaInicioCell) {
        fechaInicioCell.textContent = calculation.startTime || '--';
      }
    }
  });
}

