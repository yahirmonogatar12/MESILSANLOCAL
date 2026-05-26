// ====== plan-assy-helpers.js (loading, modals, drag-drop, date/time/planning helpers) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

﻿// ====== Variables Globales para Planeacion ======

// Funcion helper para obtener fecha en zona horaria de Nuevo Leon, Moxico (America/Monterrey)
function getTodayInNuevoLeon() {
  // Crear fecha en zona horaria de Monterrey
  const options = { timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit' };
  const formatter = new Intl.DateTimeFormat('en-CA', options); // en-CA da formato YYYY-MM-DD
  return formatter.format(new Date());
}

// Funcion helper para obtener Date object ajustado a Nuevo Leon
function getDateInNuevoLeon(daysOffset = 0) {
  const dateStr = getTodayInNuevoLeon();
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  if (daysOffset !== 0) {
    date.setDate(date.getDate() + daysOffset);
  }
  // Formatear a YYYY-MM-DD
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// Variables globales para planeacion integrada
let planningData = [];

// ? NUEVO: Almacenar copia original de los planes cargados desde la BD
// Esta copia NUNCA se modifica y se usa para recuperar datos completos (incluyendo status)
let originalPlansData = [];

let currentConfig = {
  breaks: [
    { start: '09:30', end: '09:45', name: 'Break 1' },
    { start: '12:00', end: '12:30', name: 'Almuerzo' },
    { start: '15:00', end: '15:15', name: 'Break 2' }
  ],
  shiftStart: '07:30',
  shiftEnd: '17:30',
  productiveHours: 9,  // 9 horas reales de trabajo (10 - 1 hora de breaks)
  lineFlows: {
    'M1': 'D1',
    'M2': 'D2',
    'M3': 'D3'
  }
};

// Datos calculados de planeacion por fila
let planningCalculations = new Map();

// Estructura de grupos visibles
let visualGroups = {
  groups: [],
  planAssignments: new Map() // lot_no -> groupIndex
};

let scanLotsData = [];
let scanLotPlanOptions = [];

// ====== Funciones de Carga y Loading ======

// Crear spinner de carga
function createLoadingSpinner(size = 'normal') {
  const spinner = document.createElement('div');
  spinner.className = `loading-spinner ${size === 'large' ? 'large' : ''}`;
  return spinner;
}

// Mostrar overlay de carga en tabla
function showTableLoading(containerId, message = 'Cargando...') {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Remover cualquier loading previo
  hideTableLoading(containerId);

  // Asegurar que el container tenga position relative
  const computedStyle = window.getComputedStyle(container);
  if (computedStyle.position === 'static') {
    container.style.position = 'relative';
  }

  // Crear overlay mejorado
  const overlay = document.createElement('div');
  overlay.className = 'table-loading-overlay';
  overlay.id = `${containerId}-loading`;
  overlay.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(26, 27, 38, 0.95);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    backdrop-filter: blur(5px);
    animation: fadeIn 0.3s ease;
  `;

  // Crear contenedor del spinner con efecto de pulsación
  const spinnerContainer = document.createElement('div');
  spinnerContainer.style.cssText = `
    position: relative;
    width: 80px;
    height: 80px;
    margin-bottom: 20px;
  `;

  // Crear spinner principal (círculo giratorio)
  const spinner = document.createElement('div');
  spinner.className = 'loading-spinner-enhanced';
  spinner.style.cssText = `
    width: 60px;
    height: 60px;
    border: 4px solid rgba(74, 144, 226, 0.2);
    border-top-color: #4A90E2;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    position: absolute;
    top: 10px;
    left: 10px;
  `;

  // Crear segundo spinner (efecto de onda)
  const spinnerOuter = document.createElement('div');
  spinnerOuter.style.cssText = `
    width: 80px;
    height: 80px;
    border: 3px solid transparent;
    border-top-color: rgba(74, 144, 226, 0.4);
    border-radius: 50%;
    animation: spin 1.5s linear infinite reverse;
    position: absolute;
    top: 0;
    left: 0;
  `;

  spinnerContainer.appendChild(spinnerOuter);
  spinnerContainer.appendChild(spinner);

  // Crear texto con estilo mejorado
  const text = document.createElement('div');
  text.className = 'loading-text-enhanced';
  text.style.cssText = `
    color: #4A90E2;
    font-size: 16px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 10px;
    animation: fadeInUp 0.5s ease;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  `;
  text.textContent = message;

  // Crear barra de progreso animada
  const progressBar = document.createElement('div');
  progressBar.style.cssText = `
    width: 200px;
    height: 4px;
    background: rgba(74, 144, 226, 0.2);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 15px;
  `;

  const progressFill = document.createElement('div');
  progressFill.style.cssText = `
    height: 100%;
    background: linear-gradient(90deg, #4A90E2, #5cb3ff);
    border-radius: 2px;
    animation: progressIndeterminate 1.5s ease-in-out infinite;
  `;
  progressBar.appendChild(progressFill);

  // Agregar animaciones CSS si no existen
  if (!document.getElementById('loading-animations-style')) {
    const style = document.createElement('style');
    style.id = 'loading-animations-style';
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes fadeInUp {
        from { 
          opacity: 0; 
          transform: translateY(10px); 
        }
        to { 
          opacity: 1; 
          transform: translateY(0); 
        }
      }
      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      @keyframes pulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.8; }
      }
      @keyframes progressIndeterminate {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(300%); }
      }
    `;
    document.head.appendChild(style);
  }

  // Agregar elementos al overlay
  overlay.appendChild(spinnerContainer);
  overlay.appendChild(text);
  overlay.appendChild(progressBar);

  // Agregar overlay al container
  container.appendChild(overlay);
}

// Mostrar loading dentro del tbody de una tabla
function showTableBodyLoading(tbodyId, message = 'Cargando...', colSpan = 15) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  tbody.innerHTML = `
    <tr class="loading-row">
      <td colspan="${colSpan}" style="display: table-cell; text-align: center; padding: 40px; background: #2A2D3E;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; color: #E0E0E0;">
          <div class="loading-spinner"></div>
          <span style="font-size: 14px;">${message}</span>
        </div>
      </td>
    </tr>
  `;
}

// Ocultar overlay de carga
function hideTableLoading(containerId) {
  const overlay = document.getElementById(`${containerId}-loading`);
  if (overlay) {
    overlay.remove();
  }
}

// Funcion para mostrar modal de oxito
function showSuccessModal(message) {
  // Crear modal si no existe
  let modal = document.getElementById('success-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'success-modal';
    modal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.6);
      z-index: 10001;
      justify-content: center;
      align-items: center;
    `;

    modal.innerHTML = `
      <div style="background: #2A2D3E; border-radius: 12px; padding: 30px; color: #E0E0E0; text-align: center; max-width: 400px; margin: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <div style="margin-bottom: 15px;">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#28a745"/>
            <path d="M8 12.5L10.5 15L16 9.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h3 style="margin: 0 0 15px 0; color: #28a745;">Éxito!</h3>
        <p id="success-message" style="margin: 0 0 25px 0; line-height: 1.4;"></p>
        <button onclick="hideSuccessModal()" style="background: #28a745; color: white; border: none; padding: 10px 25px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500;">
          OK
        </button>
      </div>
    `;

    document.body.appendChild(modal);
  }

  // Actualizar mensaje y mostrar
  document.getElementById('success-message').textContent = message;
  modal.style.display = 'flex';
}

// Funcion para ocultar modal de oxito
function hideSuccessModal() {
  const modal = document.getElementById('success-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// Función para mostrar modal de advertencia
function showWarningModal(message) {
  // Crear modal si no existe
  let modal = document.getElementById('warning-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'warning-modal';
    modal.style.cssText = `
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.7);
      z-index: 16000;
      justify-content: center;
      align-items: center;
    `;

    modal.innerHTML = `
      <div style="background: #2D363D; border: 2px solid #e74c3c; border-radius: 12px; padding: 30px; color: #E0E0E0; text-align: center; max-width: 500px; margin: 20px; box-shadow: 0 10px 30px rgba(231, 76, 60, 0.3);">
        <div style="margin-bottom: 15px;">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#e74c3c"/>
            <path d="M12 8v4M12 16h.01" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h3 style="margin: 0 0 15px 0; color: #e74c3c; font-family: 'LG regular', sans-serif; font-weight: bold;">ADVERTENCIA</h3>
        <p id="warning-message" style="margin: 0 0 25px 0; line-height: 1.6; white-space: pre-line; font-family: 'LG regular', sans-serif;"></p>
        <button id="btn-close-warning" style="background: #e74c3c; color: white; border: none; padding: 10px 25px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; font-family: 'LG regular', sans-serif;">
          Entendido
        </button>
      </div>
    `;

    document.body.appendChild(modal);
  }

  // Vincular evento del botón
  const btnClose = document.getElementById('btn-close-warning');
  if (btnClose) {
    btnClose.onclick = function() {
      hideWarningModal();
    };
  }

  // Actualizar mensaje y mostrar
  document.getElementById('warning-message').textContent = message;
  modal.style.cssText = `
    display: flex !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    background: rgba(0,0,0,0.7) !important;
    z-index: 16000 !important;
    justify-content: center !important;
    align-items: center !important;
  `;
}

// Función para ocultar modal de advertencia
function hideWarningModal() {
  const modal = document.getElementById('warning-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// Agregar estado de carga a un boton
function setButtonLoading(buttonId, loading = true, originalText = '') {
  const button = document.getElementById(buttonId);
  if (!button) return;

  if (loading) {
    button.dataset.originalText = button.textContent;
    button.classList.add('loading');
    button.disabled = true;
    button.textContent = originalText || 'Cargando...';
  } else {
    button.classList.remove('loading');
    button.disabled = false;
    button.textContent = button.dataset.originalText || originalText;
  }
}

function setDefaultDateFilters() {
  const iso = getTodayInNuevoLeon();
  const fs = document.getElementById("assy-filter-start");
  const fe = document.getElementById("assy-filter-end");
  if (fs && !fs.value) fs.value = iso;
  if (fe && !fe.value) fe.value = iso;
}

// Map routing value to turno label
function routingToTurno(v) {
  if (v === 1 || v === "1") return "DIA";
  if (v === 2 || v === "2") return "TIEMPO EXTRA";
  if (v === 3 || v === "3") return "NOCHE";
  return "";
}

// Map turno label to routing value
function turnoToRouting(turno) {
  if (turno === "DIA") return 1;
  if (turno === "TIEMPO EXTRA") return 2;
  if (turno === "NOCHE") return 3;
  return 1; // Default DIA
}

function escapePlanHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function partNoWithBomRevision(plan) {
  const partNo = escapePlanHtml(plan?.part_no || '');
  const bomRev = String(plan?.assigned_bom_rev || '').trim();
  if (!bomRev) return partNo;
  return `${partNo}<div style="font-size:10px; color:#7fb3d5; opacity:.9;">BOM rev ${escapePlanHtml(bomRev)}</div>`;
}

async function loadPlanBomRevisionOptions(partNo, selectedRev, selectEl) {
  if (!selectEl) return;
  selectEl.disabled = true;
  selectEl.innerHTML = '<option value="">Automatico - revision vigente</option>';
  if (!partNo) {
    selectEl.disabled = false;
    return;
  }
  try {
    const response = await axios.get(`/api/plan/bom-revisions?part_no=${encodeURIComponent(partNo)}`);
    const revisions = Array.isArray(response.data?.data) ? response.data.data : [];
    revisions.forEach((row) => {
      const option = document.createElement('option');
      option.value = row.bom_rev || '';
      const labels = [`BOM rev ${row.bom_rev}`];
      if (row.is_current) labels.push('vigente');
      if (row.eco_no) labels.push(`ECO ${row.eco_no}${row.eco_effective_at ? ` ${String(row.eco_effective_at).slice(0, 10)}` : ''}`);
      option.textContent = labels.join(' - ');
      selectEl.appendChild(option);
    });
    selectEl.value = selectedRev || '';
  } catch (error) {
    const option = document.createElement('option');
    option.value = selectedRev || '';
    option.textContent = selectedRev
      ? `BOM rev ${selectedRev} - catalogo no disponible`
      : 'No se pudieron cargar revisiones KS';
    selectEl.appendChild(option);
    selectEl.value = selectedRev || '';
  } finally {
    selectEl.disabled = false;
  }
}

function enableRowDragDrop(tbody, fs, fe) {
  let dragSrcEl = null;
  tbody.addEventListener('dragstart', (e) => {
    const row = e.target.closest('tr');
    if (!row) return;
    dragSrcEl = row;
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', row.dataset.lot || ''); } catch { }
  });
  tbody.addEventListener('dragend', (e) => {
    const row = e.target.closest('tr');
    if (row) row.classList.remove('dragging');
    dragSrcEl = null;
    // Guardar orden al terminar un drag
    saveCurrentOrder(tbody, fs, fe);
    // Renumerar secuencia visual inmediatamente
    Array.from(tbody.querySelectorAll('tr')).forEach((tr, i) => {
      const firstCell = tr.querySelector('td');
      if (firstCell) firstCell.textContent = String(i + 1);
    });

    // IMPORTANTE: Sincronizar visualGroups con el orden actual de la tabla
    syncVisualGroupsWithTableOrder();

    // Recalcular tiempos automoticamente despuos del drag
    setTimeout(calculateAndUpdateTimes, 100);
  });
  tbody.addEventListener('dragover', (e) => {
    e.preventDefault();
    const afterElement = getDragAfterElement(tbody, e.clientY);
    const dragging = tbody.querySelector('.dragging');
    if (!dragging) return;
    if (afterElement == null) {
      tbody.appendChild(dragging);
    } else {
      tbody.insertBefore(dragging, afterElement);
    }
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll('tr:not(.dragging)')];
  return draggableElements.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset: offset, element: child };
    } else {
      return closest;
    }
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Funcion para sincronizar visualGroups con el orden actual de la tabla HTML
function syncVisualGroupsWithTableOrder() {
  const tbody = document.getElementById('assy-tableBody');
  if (!tbody) {
    return;
  }

  const rows = Array.from(tbody.querySelectorAll('tr'));
  if (rows.length === 0) {
    return;
  }

  // Obtener nomero de grupos actual
  const groupCount = parseInt(document.getElementById('assy-groups-count')?.value) || 6;

  // ? IMPORTANTE: Usar originalPlansData (copia inmutable de BD) como fuente de verdad
  // Esta copia siempre tiene los datos completos incluyendo status

  // Guardar tambion el estado actual de visualGroups por si originalPlansData esto vacoo
  const visualGroupsBackup = [];
  if (visualGroups && visualGroups.groups) {
    visualGroups.groups.forEach(group => {
      if (group && group.plans) {
        group.plans.forEach(plan => {
          if (plan && plan.lot_no) {
            visualGroupsBackup.push({ ...plan });
          }
        });
      }
    });
  }

  // Reinicializar grupos
  initializeVisualGroups(groupCount);

  // Reconstruir los grupos basondose en el orden visual actual
  rows.forEach((row, rowIndex) => {
    const lotNo = row.dataset.lot;
    if (!lotNo) return;

    // Buscar el plan en originalPlansData PRIMERO (fuente de verdad)
    let planData = originalPlansData.find(p => p.lot_no === lotNo);

    // Si no esto en originalPlansData, buscar en el backup de visualGroups
    if (!planData) {
      planData = visualGroupsBackup.find(p => p.lot_no === lotNo);
    }

    // Si aon no encontramos el plan, crear un objeto desde la tabla HTML
    if (!planData) {
      const cells = row.querySelectorAll('td');
      planData = {
        lot_no: lotNo,
        wo_code: cells[2]?.textContent || '',
        po_code: cells[3]?.textContent || '',
        working_date: cells[4]?.textContent || '',
        line: cells[5]?.textContent || '',
        routing: turnoToRouting(cells[6]?.textContent) || 1,
        model_code: cells[7]?.textContent || '',
        part_no: cells[8]?.textContent || '',
        project: cells[9]?.textContent || '',
        process: cells[10]?.textContent || 'MAIN',
        ct: parseFloat(cells[11]?.textContent) || 0,
        uph: parseInt(cells[12]?.textContent) || 0,
        plan_count: parseInt(cells[13]?.textContent) || 0,
        produced: parseInt(cells[14]?.textContent) || 0,
        output: parseInt(cells[15]?.textContent) || 0,
        entregadas_main: parseInt(cells[16]?.textContent) || 0,
        status: cells[17]?.textContent?.trim() || 'PLAN' // Preservar status desde la celda
      };
    }

    // Determinar a quo grupo pertenece (distribucion por filas)
    const groupIndex = rowIndex % groupCount;

    // Agregar plan al grupo correspondiente (preservando todos los campos)
    visualGroups.groups[groupIndex].plans.push(planData);
    visualGroups.planAssignments.set(lotNo, groupIndex);
  });
}

function orderStorageKey(fs, fe) {
  return `plan-order:${fs || ''}:${fe || ''}`;
}

function saveCurrentOrder(tbody, fs, fe) {
  const order = Array.from(tbody.querySelectorAll('tr')).map(tr => tr.dataset.lot).filter(Boolean);
  try {
    localStorage.setItem(orderStorageKey(fs, fe), JSON.stringify(order));
  } catch { }
}

function applySavedOrderToData(data, fs, fe) {
  try {
    // Primero intentar usar el orden guardado en MySQL (group_no y sequence)
    const plansWithOrder = data.filter(plan => plan.group_no != null && plan.sequence != null);

    if (plansWithOrder.length > 0) {


      // Los datos ya vienen ordenados desde el backend por group_no y sequence
      // Solo necesitamos verificar que el orden sea correcto
      const orderedData = data.slice().sort((a, b) => {
        const aGroup = a.group_no || 999;
        const bGroup = b.group_no || 999;
        const aSeq = a.sequence || 999;
        const bSeq = b.sequence || 999;

        if (aGroup !== bGroup) {
          return aGroup - bGroup;
        }
        return aSeq - bSeq;
      });


      return orderedData;
    }

    // Si no hay orden en MySQL, usar localStorage como respaldo
    const key = orderStorageKey(fs, fe);
    const raw = localStorage.getItem(key);
    if (!raw) {

      return data;
    }


    const order = JSON.parse(raw);
    if (!Array.isArray(order) || !order.length) return data;

    const indexMap = new Map();
    order.forEach((lot, i) => indexMap.set(lot, i));
    return data.slice().sort((a, b) => {
      const ia = indexMap.has(a.lot_no) ? indexMap.get(a.lot_no) : Infinity;
      const ib = indexMap.has(b.lot_no) ? indexMap.get(b.lot_no) : Infinity;
      if (ia === ib) return 0;
      return ia - ib;
    });
  } catch (error) {

    return data;
  }
}

function ensureOrderToolbar(fs, fe) {
  // Esta funcion ya no es necesaria porque usamos el boton save-sequences-btn del toolbar principal
  // El boton "?? Guardar Orden" maneja tanto grupos como secuencias correctamente
}

// Estilos monimos para drag
(function injectDragStyles() {
  const style = document.createElement('style');
  style.textContent = `
    #assy-tableBody tr.dragging { opacity: .6; outline: 2px dashed #3498db; }
    #assy-tableBody tr { cursor: grab; }
    #assy-tableBody tr:active { cursor: grabbing; }
  `;
  document.head.appendChild(style);
})();

// ============================================================
// NOTA: El evento de doble click ahora usa event delegation
// Ver initializePlanEventListeners() mos abajo
// ============================================================
/*
// CoDIGO ANTIGUO - Reemplazado por event delegation
const planTableEl = document.getElementById('assy-table');
if (planTableEl) {
  planTableEl.addEventListener('dblclick', (e) => {
    const row = e.target.closest('tr.assy-row');
    if (!row) return;
    const lotNo = row.dataset.lot;
    if (lotNo) openEditModal(lotNo);
  });
}
*/

function timeToMinutes(timeStr) {
  if (!timeStr) return 0;
  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours * 60 + minutes;
}

function minutesToTime(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

function calculateProductionTime(planCount, uph) {
  if (!uph || uph === 0) return 0;
  return Math.round((planCount / uph) * 60); // minutos
}

// Agrupar planes en N grupos segon la seleccion
function groupPlansIntoNGroups(plans, groupCount) {
  const groups = [];
  for (let i = 0; i < groupCount; i++) {
    groups.push([]);
  }

  // Distribuir planes por loneas en grupos
  const lineGroups = {};
  plans.forEach(plan => {
    const line = plan.line;
    if (!lineGroups[line]) lineGroups[line] = [];
    lineGroups[line].push(plan);
  });

  // Asignar loneas a grupos de manera balanceada
  const lines = Object.keys(lineGroups);
  lines.forEach((line, index) => {
    const groupIndex = index % groupCount;
    groups[groupIndex] = groups[groupIndex].concat(lineGroups[line]);
  });

  return groups;
}

// Calcular tiempos de planeacion para cada fila
function calculatePlanningTimes(plans) {
  planningCalculations.clear();
  const groupCount = parseInt(document.getElementById('assy-groups-count').value) || 6;
  const groups = groupPlansIntoNGroups(plans, groupCount);

  groups.forEach((groupPlans, groupIndex) => {
    let currentTime = timeToMinutes(currentConfig.shiftStart);
    let totalGroupTime = 0;

    groupPlans.forEach(plan => {
      const productionTime = calculateProductionTime(plan.plan_count || 0, plan.uph || 0);
      const startTime = currentTime;
      const endTime = currentTime + productionTime;

      // Calcular si esto en tiempo extra (termina despuos de 17:30)
      const shiftEndMinutes = timeToMinutes(currentConfig.shiftEnd || '17:30');
      const isOvertime = endTime > shiftEndMinutes;

      planningCalculations.set(plan.lot_no, {
        groupNumber: groupIndex + 1,
        productionTime: productionTime,
        startTime: minutesToTime(startTime),
        endTime: minutesToTime(endTime),
        isOvertime: isOvertime,
        totalGroupTime: totalGroupTime + productionTime
      });

      currentTime = endTime;
      totalGroupTime += productionTime;
    });
  });
}

function showNotification(message, type = 'info') {
  // Remover notificacion existente si la hay
  const existingNotification = document.querySelector('.notification');
  if (existingNotification) {
    existingNotification.remove();
  }

  // Crear nueva notificacion
  const notification = document.createElement('div');
  notification.className = 'notification';
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 5px;
    color: white;
    font-weight: bold;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    animation: slideIn 0.3s ease;
  `;

  // Establecer color segon el tipo
  if (type === 'success') {
    notification.style.backgroundColor = '#27ae60';
  } else if (type === 'error') {
    notification.style.backgroundColor = '#e74c3c';
  } else {
    notification.style.backgroundColor = '#3498db';
  }

  notification.textContent = message;
  document.body.appendChild(notification);

  // Remover despuos de 4 segundos
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 4000);
}



// ====== Export al window.AssyState para acceso desde otros plan-assy-*.js ======
window.AssyState = {
  get planningData() { return planningData; },
  set planningData(v) { planningData = v; },
  get originalPlansData() { return originalPlansData; },
  set originalPlansData(v) { originalPlansData = v; },
  get currentConfig() { return currentConfig; },
  set currentConfig(v) { currentConfig = v; },
  get planningCalculations() { return planningCalculations; },
  set planningCalculations(v) { planningCalculations = v; },
  get visualGroups() { return visualGroups; },
  set visualGroups(v) { visualGroups = v; },
  get scanLotsData() { return scanLotsData; },
  set scanLotsData(v) { scanLotsData = v; },
  get scanLotPlanOptions() { return scanLotPlanOptions; },
  set scanLotPlanOptions(v) { scanLotPlanOptions = v; },
};
