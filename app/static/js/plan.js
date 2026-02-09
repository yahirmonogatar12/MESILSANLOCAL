// ====== Variables Globales para Planeacion ======

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

  // Crear icono central
  const icon = document.createElement('div');
  icon.innerHTML = '📦';
  icon.style.cssText = `
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 24px;
    animation: pulse 1.5s ease-in-out infinite;
  `;

  spinnerContainer.appendChild(spinnerOuter);
  spinnerContainer.appendChild(spinner);
  spinnerContainer.appendChild(icon);

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

  // Crear subtexto
  const subtext = document.createElement('div');
  subtext.style.cssText = `
    color: #95a5a6;
    font-size: 12px;
    margin-top: 15px;
    animation: fadeInUp 0.7s ease;
  `;
  subtext.textContent = 'Por favor espere...';

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
  overlay.appendChild(subtext);

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

// Abrir modal
// ========= LISTENERS DE MODALES (Ahora manejados por Event Delegation) =========
// NOTA: Estos listeners fueron movidos a initializePlanEventListeners() usando event delegation
// para que funcionen con contenido cargado dinomicamente

/* REMOVIDO - Ahora manejado por event delegation
document.getElementById("plan-openModalBtn").addEventListener("click", () => {
  document.getElementById("plan-modal").style.display = "flex";
});
*/

/* REMOVIDO - Ahora manejado por event delegation
// Cerrar modal
document.getElementById("plan-closeModalBtn").addEventListener("click", () => {
  document.getElementById("plan-modal").style.display = "none";
});
*/

/* REMOVIDO - Ahora manejado por event delegation y handleNewPlanSubmit()
// Registrar plan
document.getElementById("plan-form").addEventListener("submit", async function(e){
  ...codigo movido a handleNewPlanSubmit()...
});
*/

// Prefijar filtros a hoy
function setDefaultDateFilters() {
  const iso = getTodayInNuevoLeon();
  const fs = document.getElementById("filter-start");
  const fe = document.getElementById("filter-end");
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

// Cargar planes
async function loadPlans() {
  try {
    // Mostrar loading en el tbody de la tabla
    showTableBodyLoading('plan-tableBody', 'Cargando planes...', 22);

    setDefaultDateFilters();
    const fs = document.getElementById("filter-start")?.value;
    const fe = document.getElementById("filter-end")?.value;
    let url = "/api/plan";
    const params = [];
    if (fs) params.push(`start=${encodeURIComponent(fs)}`);
    if (fe) params.push(`end=${encodeURIComponent(fe)}`);
    if (params.length) url += `?${params.join("&")}`;

    let res = await axios.get(url);
    let data = Array.isArray(res.data) ? res.data.slice() : [];

    // ? IMPORTANTE: Guardar copia profunda de los datos originales
    // Esta copia se usa para recuperar datos completos cuando se reorganizan planes
    originalPlansData = data.map(plan => ({ ...plan }));

    // Aplicar orden guardado (si existe) antes de renderizar
    data = applySavedOrderToData(data, fs, fe);

    let tbody = document.getElementById("plan-tableBody");
    tbody.innerHTML = "";

    data.forEach((r, idx) => {
      let tr = document.createElement("tr");
      tr.dataset.lot = r.lot_no;
      tr.draggable = true;
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td>${r.lot_no}</td>
        <td>${r.wo_code || ""}</td>
        <td>${r.po_code || ""}</td>
        <td>${r.working_date}</td>
        <td>${r.line}</td>
        <td>${routingToTurno(r.routing)}</td>
        <td>${r.model_code}</td>
        <td>${r.part_no}</td>
        <td>${r.project}</td>
        <td>${r.process || ""}</td>
        <td>${r.ct || "0"}</td>
        <td>${r.uph || "0"}</td>
        <td>${r.plan_count}</td>
        <td>${r.produced ?? 0}</td>
        <td>${r.output ?? 0}</td>
        <td>${r.entregadas_main ?? 0}</td>
        <td>${r.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell fecha-inicio-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold;">-</td>
      `;
      tbody.appendChild(tr);
    });

    enableRowDragDrop(tbody, fs, fe);
    // ensureOrderToolbar(fs, fe); // Ya no necesario - usamos save-sequences-btn
  } catch (error) {
    alert("Error al cargar planes: " + (error.response?.data?.error || error.message));
    // En caso de error, limpiar la tabla
    let tbody = document.getElementById("plan-tableBody");
    tbody.innerHTML = `<tr class="message-row"><td colspan="22" style="display: table-cell; text-align: center; padding: 20px; color: #888;">Error al cargar los datos</td></tr>`;
  }
}

// ====== Drag & Drop Reordenamiento ======
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
  const tbody = document.getElementById('plan-tableBody');
  if (!tbody) {
    return;
  }

  const rows = Array.from(tbody.querySelectorAll('tr'));
  if (rows.length === 0) {
    return;
  }

  // Obtener nomero de grupos actual
  const groupCount = parseInt(document.getElementById('groups-count')?.value) || 6;

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
    #plan-tableBody tr.dragging { opacity: .6; outline: 2px dashed #3498db; }
    #plan-tableBody tr { cursor: grab; }
    #plan-tableBody tr:active { cursor: grabbing; }
  `;
  document.head.appendChild(style);
})();

// ============================================================
// NOTA: El evento de doble click ahora usa event delegation
// Ver initializePlanEventListeners() mos abajo
// ============================================================
/*
// CoDIGO ANTIGUO - Reemplazado por event delegation
const planTableEl = document.getElementById('plan-table');
if (planTableEl) {
  planTableEl.addEventListener('dblclick', (e) => {
    const row = e.target.closest('tr.plan-row');
    if (!row) return;
    const lotNo = row.dataset.lot;
    if (lotNo) openEditModal(lotNo);
  });
}
*/

async function openEditModal(lotNo) {
  try {
    // Mostrar modal inmediatamente con loading
    const modal = document.getElementById("plan-editModal");
    const form = document.getElementById("plan-editForm");

    // CRÍTICO: Limpiar tanto display como visibility
    modal.style.display = "flex";
    modal.style.visibility = "visible";

    // Ocultar el formulario mientras carga
    form.style.display = "none";

    showTableLoading('plan-modal-content', 'Cargando datos del plan...');

    // Hacer la consulta a la API
    let res = await axios.get("/api/plan");
    let plan = res.data.find(p => p.lot_no === lotNo);

    if (!plan) {
      hideTableLoading('plan-modal-content');
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

    // *** NUEVO: Cambiar botón según estado del plan ***
    const cancelBtn = document.getElementById('plan-cancelBtn');
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
    hideTableLoading('plan-modal-content');
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
    hideTableLoading('plan-modal-content');
    document.getElementById("plan-editModal").style.display = "none";
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

    showTableLoading('plan-modal-content', 'Buscando Work Order y datos actualizados en RAW...');

    // Buscar datos actualizados en la tabla RAW antes de guardar
    try {
      // El formulario no tiene part_no, pero tiene wo_code
      // Primero buscar el WO para obtener el part_no (modelo)
      const woCode = data.wo_code;

      if (woCode && woCode !== 'SIN-WO') {
        // Buscar el WO en la tabla work_orders
        const woResponse = await axios.get(`/api/work-orders?q=${encodeURIComponent(woCode)}`);

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

    showTableLoading('plan-modal-content', 'Actualizando plan...');

    const updateResponse = await axios.post("/api/plan/update", data);

    // Mostrar modal de oxito
    showSuccessModal(`Plan ${data.lot_no} actualizado exitosamente`);

    document.getElementById("plan-editModal").style.display = "none";
    loadPlans();
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
    hideTableLoading('plan-modal-content');
  }
}

/**
 * Manejar cancelacion de plan
 */
async function handleCancelPlan() {
  const form = document.getElementById("plan-editForm");
  if (!form) return;

  const lot = form.lot_no.value;
  if (!lot) return;
  
  const cancelBtn = document.getElementById("plan-cancelBtn");
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

    document.getElementById("plan-editModal").style.display = "none";
    loadPlans();
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

/**
 * Validar que no haya conflictos de horario en la misma línea
 * Retorna null si no hay conflicto, o un objeto con información del conflicto
 */
function validarConflictoLineaHorario(nuevoPlan) {
  console.log('🔍 Validando conflictos de línea/horario para:', nuevoPlan);
  
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
  
  console.log(`📊 Comparando contra ${planesConHorario.length} planes activos`);
  
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
  
  console.log(`🕐 Hora de inicio del nuevo plan: ${horaInicioNuevoPlan}`);
  
  // Buscar conflictos: misma línea Y misma hora de inicio
  for (const planExistente of planesConHorario) {
    // Comparar línea
    const mismaLinea = planExistente.line === nuevoPlan.line;
    
    // Comparar fecha
    const mismaFecha = planExistente.fecha === (nuevoPlan.fecha || nuevoPlan.working_date);
    
    // Comparar hora de inicio (solo si el plan existente tiene hora calculada)
    const mismoInicio = planExistente.inicio && planExistente.inicio === horaInicioNuevoPlan;
    
    if (mismaLinea && mismaFecha && mismoInicio) {
      console.log('❌ Conflicto detectado:', {
        planExistente: {
          lot_no: planExistente.lot_no,
          line: planExistente.line,
          fecha: planExistente.fecha,
          inicio: planExistente.inicio,
          model_code: planExistente.model_code,
          group_no: planExistente.group_no
        },
        nuevoPlan: {
          lot_no: nuevoPlan.lot_no || 'NUEVO',
          line: nuevoPlan.line,
          fecha: nuevoPlan.fecha || nuevoPlan.working_date,
          inicio: horaInicioNuevoPlan,
          model_code: nuevoPlan.model_code,
          group_no: grupoDestino
        }
      });
      
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
  
  console.log('✅ No se detectaron conflictos');
  return null;
}

/**
 * Manejar submit del formulario de nuevo plan
 */
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
      console.log('⚠️ Conflicto detectado, buscando grupo del plan conflictivo...');
      
      // Buscar en qué grupo está el plan con conflicto
      const planConflictivo = conflicto.planConflicto;
      let grupoDestino = null;
      
      // Buscar el grupo del plan conflictivo en visualGroups
      for (let i = 0; i < visualGroups.groups.length; i++) {
        const group = visualGroups.groups[i];
        const planEnGrupo = group.plans.find(p => p.lot_no === planConflictivo.lot_no);
        if (planEnGrupo) {
          grupoDestino = i + 1; // Los grupos son 1-indexed
          console.log(`✅ Plan conflictivo ${planConflictivo.lot_no} encontrado en GRUPO ${grupoDestino}`);
          break;
        }
      }
      
      if (grupoDestino) {
        // Asignar el nuevo plan al final de ese grupo
        data.group_no = grupoDestino;
        console.log(`📍 Asignando nuevo plan al GRUPO ${grupoDestino} (al final del grupo con conflicto)`);
        
        // Mostrar notificación informativa (no bloqueante)
        console.log(`ℹ️ Plan agregado al final del GRUPO ${grupoDestino} debido a conflicto de horario en línea ${data.line}`);
      } else {
        console.warn('⚠️ No se encontró el grupo del plan conflictivo, continuando sin asignación automática');
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

    document.getElementById("plan-modal").style.display = "none";
    form.reset();
    
    // Recargar planes - ahora el plan ya viene con su grupo asignado desde la BD
    await loadPlans();
    
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

// Exponer funciones globalmente
window.openEditModal = openEditModal;
window.handleEditPlanSubmit = handleEditPlanSubmit;
window.handleCancelPlan = handleCancelPlan;
window.handleNewPlanSubmit = handleNewPlanSubmit;
window.populateGroupSelector = populateGroupSelector;
window.assignPlanToGroup = assignPlanToGroup;

/* REMOVIDO - Ahora manejado por event delegation y handleEditPlanSubmit()
[Codigo del event listener de plan-editForm submit movido a handleEditPlanSubmit()]
*/

/* REMOVIDO - Ahora manejado por event delegation y handleCancelPlan()
[Codigo del event listener de plan-cancelBtn movido a handleCancelPlan()]
*/


// ========= WORK ORDERS FUNCTIONALITY =========

// Crear modal de Work Orders dinomicamente
function createWorkOrdersModal() {
  // Verificar si ya existe
  if (document.getElementById('wo-modal')) {
    return;
  }

  console.log('?? Creando modal wo-modal con estilos');

  const woModal = document.createElement('div');
  woModal.id = 'wo-modal';
  woModal.className = 'modal-overlay';
  
  // IMPORTANTE: Agregar estilos inline como fallback
  woModal.style.cssText = `
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
  
  woModal.innerHTML = `
    <div class="modal-content" id="wo-modal-content" style="background: #34334E; border-radius: 8px; width: 90%; max-width: 1200px; max-height: 90%; padding: 20px; color: lightgray; overflow: auto;">
      <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #ecf0f1;">Work Orders - Importar como Planes</h3>
        <button id="wo-closeModalBtn" class="plan-btn modal-close-btn" style="background: #666; border: none; color: white; font-size: 24px; cursor: pointer; width: 30px; height: 30px; border-radius: 4px; display: flex; align-items: center; justify-content: center; padding: 0; line-height: 1;">×</button>
      </div>

      <div class="modal-filters" style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
        <label style="font-size: 11px; color: #ecf0f1;">Buscar WO/PO:</label>
        <input type="text" id="wo-search-input" class="plan-input" placeholder="Buscar por codigo WO o PO..." style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 180px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha Op. Desde:</label>
        <input type="date" id="wo-filter-desde" class="plan-input" title="Filtrar WOs desde esta fecha" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha Op. Hasta:</label>
        <input type="date" id="wo-filter-hasta" class="plan-input" title="Filtrar WOs hasta esta fecha" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Estado:</label>
        <select id="wo-filter-estado" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 120px;">
          <option value="">Todos</option>
          <option value="CREADA">CREADA</option>
          <option value="PLANIFICADA">PLANIFICADA</option>
          <option value="EN PROGRESO">EN PROGRESO</option>
          <option value="CERRADA">CERRADA</option>
        </select>
        
        <button id="wo-reload-btn" class="plan-btn" style="background-color: #2980b9; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Recargar</button>
        <button id="wo-import-selected-btn" class="plan-btn plan-btn-add" style="background-color: #27ae60; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Importar Seleccionados</button>
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha de Importacion:</label>
        <input type="date" id="wo-filter-date" class="plan-input" title="Fecha a la que se importaron los planes seleccionados" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
      </div>

      <div class="modal-table-container" style="overflow-x: auto; margin-bottom: 20px;">
        <table class="modal-table" style="width: 100%; border-collapse: collapse; background: #2B2D3E;">
          <thead>
            <tr style="background: #1e1e2e;">
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">
                <input type="checkbox" id="wo-select-all">
              </th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">WO Code</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">PO Code</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Modelo</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Cantidad</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Fecha Op.</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Estado</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Modificador</th>
              <th style="padding: 10px; text-align: left; border-bottom: 2px solid #20688C; color: #ecf0f1;">Accion</th>
            </tr>
          </thead>
          <tbody id="wo-tableBody" style="color: lightgray;"></tbody>
        </table>
      </div>

      <div class="modal-status" style="padding: 10px; text-align: center; color: #95a5a6; font-size: 12px;">
        <span id="wo-status">Seleccione los WOs que desea importar como planes</span>
      </div>
    </div>
  `;

  // Insertar el modal en el body
  document.body.appendChild(woModal);

  // Configurar event listeners despuos de crear el modal
  setupWorkOrdersModalEvents();
}
// Exponer funcion globalmente
window.createWorkOrdersModal = createWorkOrdersModal;

// Configurar event listeners del modal WO
function setupWorkOrdersModalEvents() {
  // Cerrar modal
  const closeBtn = document.getElementById("wo-closeModalBtn");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      document.getElementById("wo-modal").style.display = "none";
    });
  }

  // Boton de recarga
  const reloadBtn = document.getElementById('wo-reload-btn');
  if (reloadBtn) {
    reloadBtn.addEventListener('click', loadWorkOrders);
  }

  // Input de bosqueda - filtrar en tiempo real
  const searchInput = document.getElementById('wo-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', filterWorkOrdersTable);
    searchInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        filterWorkOrdersTable();
      }
    });
  }

  // Checkbox "Seleccionar todos"
  const selectAll = document.getElementById('wo-select-all');
  if (selectAll) {
    selectAll.addEventListener('change', function () {
      toggleAllWOs(this);
    });
  }

  // Boton "Importar Seleccionados"
  const importBtn = document.getElementById('wo-import-selected-btn');
  if (importBtn) {
    importBtn.addEventListener('click', importAllSelectedWOs);
  }

  // Delegacion de eventos para botones de importacion individual
  const tbody = document.getElementById('wo-tableBody');
  if (tbody) {
    tbody.addEventListener('click', function (e) {
      if (e.target.classList.contains('wo-import-single-btn')) {
        const woId = parseInt(e.target.dataset.woId);
        if (woId && !e.target.disabled) {
          importSingleWO(woId, e.target);
        }
      }
    });
  }

  // Permitir recarga con Enter en filtros de fecha
  const filterDate = document.getElementById('wo-filter-date');
  const filterDesde = document.getElementById('wo-filter-desde');
  const filterHasta = document.getElementById('wo-filter-hasta');
  const filterEstado = document.getElementById('wo-filter-estado');

  if (filterDate) {
    filterDate.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        loadWorkOrders();
      }
    });
  }

  if (filterDesde) {
    filterDesde.addEventListener('change', function () {
      loadWorkOrders(); // Recargar automoticamente al cambiar fecha desde
    });
  }

  if (filterHasta) {
    filterHasta.addEventListener('change', function () {
      loadWorkOrders(); // Recargar automoticamente al cambiar fecha hasta
    });
  }

  if (filterEstado) {
    filterEstado.addEventListener('change', function () {
      loadWorkOrders(); // Recargar automoticamente al cambiar estado
    });
  }

  // Establecer fecha de importacion por defecto (hoy en Nuevo Leon)
  if (filterDate && !filterDate.value) {
    filterDate.value = getTodayInNuevoLeon();
  }

  // Establecer rango de fechas por defecto (doa actual en Nuevo Leon)
  if (filterDesde && !filterDesde.value) {
    filterDesde.value = getTodayInNuevoLeon(); // Doa actual
  }

  if (filterHasta && !filterHasta.value) {
    filterHasta.value = getTodayInNuevoLeon(); // Doa actual
  }
}

// Abrir modal WO (Ahora manejado por event delegation)
/* REMOVIDO - Ahora manejado por event delegation
document.getElementById("wo-openModalBtn").addEventListener("click", () => {
  createWorkOrdersModal(); // Crear el modal si no existe
  document.getElementById("wo-modal").style.display = "flex";
  loadWorkOrders();
});
*/

// Cargar Work Orders
async function loadWorkOrders() {
  try {
    // Mostrar loading en el tbody de work orders
    showTableBodyLoading('wo-tableBody', 'Cargando Work Orders...', 9);
    updateWOStatus("Cargando...");

    // Obtener valores de los filtros
    const desde = document.getElementById("wo-filter-desde")?.value || "";
    const hasta = document.getElementById("wo-filter-hasta")?.value || "";
    const estado = document.getElementById("wo-filter-estado")?.value || "";

    // Construir URL con parometros
    let url = "/api/work-orders";
    const params = [];
    if (desde) params.push(`desde=${desde}`);
    if (hasta) params.push(`hasta=${hasta}`);
    if (estado) params.push(`estado=${estado}`);
    if (params.length) url += "?" + params.join("&");

    const response = await axios.get(url);
    const workOrders = response.data;

    // Guardar todos los WOs para filtrado
    allWorkOrders = workOrders;

    renderWorkOrdersTable(workOrders);
    updateWOStatus(`${workOrders.length} work orders encontrados`);

    // Limpiar el campo de bosqueda al recargar
    const searchInput = document.getElementById('wo-search-input');
    if (searchInput) searchInput.value = '';

  } catch (error) {
    updateWOStatus("Error al cargar work orders");
    // En caso de error, mostrar mensaje en la tabla
    const tbody = document.getElementById('wo-tableBody');
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 20px; color: #888;">Error al cargar los work orders</td></tr>';
    }
  }
}

// Exponer funcion globalmente
window.loadWorkOrders = loadWorkOrders;

// Variable global para almacenar todos los WOs cargados (para filtrado)
let allWorkOrders = [];

// Funcion para filtrar WOs en el frontend
function filterWorkOrdersTable() {
  const searchInput = document.getElementById('wo-search-input');
  if (!searchInput) return;

  const searchTerm = searchInput.value.toLowerCase().trim();

  if (!searchTerm) {
    // Si no hay bosqueda, mostrar todos
    renderWorkOrdersTable(allWorkOrders);
    return;
  }

  // Filtrar WOs por codigo WO, codigo PO, o modelo
  const filtered = allWorkOrders.filter(wo => {
    const woCode = (wo.codigo_wo || '').toLowerCase();
    const poCode = (wo.codigo_po || '').toLowerCase();
    const modelo = (wo.modelo || '').toLowerCase();
    const nombreModelo = (wo.nombre_modelo || '').toLowerCase();

    return woCode.includes(searchTerm) ||
      poCode.includes(searchTerm) ||
      modelo.includes(searchTerm) ||
      nombreModelo.includes(searchTerm);
  });

  renderWorkOrdersTable(filtered);
  updateWOStatus(`${filtered.length} de ${allWorkOrders.length} work orders`);
}

// Exponer funcion globalmente
window.filterWorkOrdersTable = filterWorkOrdersTable;

// Renderizar tabla de Work Orders
function renderWorkOrdersTable(workOrders) {
  // NO sobrescribir allWorkOrders aquo, se maneja en loadWorkOrders
  const tbody = document.getElementById("wo-tableBody");
  tbody.innerHTML = "";

  if (workOrders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:20px;">No hay work orders disponibles</td></tr>';
    return;
  }

  workOrders.forEach(wo => {
    const row = document.createElement("tr");
    row.style.borderBottom = "1px solid #555";

    // Verificar si ya fue importado (agregar atributo para identificarlo)
    const yaImportado = wo.ya_importado || false;

    // Estado visual
    let estadoClass = "";
    switch (wo.estado) {
      case "CREADA": estadoClass = "background: #3498db; color: white;"; break;
      case "PLANIFICADA": estadoClass = "background: #f39c12; color: white;"; break;
      case "EN_PRODUCCION": estadoClass = "background: #27ae60; color: white;"; break;
      case "CERRADA": estadoClass = "background: #95a5a6; color: white;"; break;
    }

    // Si ya fue importado, aplicar estilo diferente
    if (yaImportado) {
      row.style.backgroundColor = "#3a3a3a";
      row.style.opacity = "0.6";
      row.style.cursor = "not-allowed";
      row.title = `?? WO ya importada como LOT NO: ${wo.lot_no_existente || 'N/A'}`;
    }

    row.innerHTML = `
      <td style="padding:6px; text-align:center;">
        <input type="checkbox" class="wo-checkbox" value="${wo.id}" 
               ${wo.estado === 'CERRADA' || yaImportado ? 'disabled' : ''}>
        ${yaImportado ? '<div style="color:#e74c3c; font-size:9px; font-weight:bold; margin-top:2px;">? IMPORTADO</div>' : ''}
      </td>
      <td style="padding:6px; font-size:10px;">${wo.codigo_wo || ''}</td>
      <td style="padding:6px; font-size:10px;">${wo.codigo_po || ''}</td>
      <td style="padding:6px; font-size:10px;">${wo.nombre_modelo || wo.modelo || ''}</td>
      <td style="padding:6px; font-size:10px; text-align:center;">${wo.cantidad_planeada || 0}</td>
      <td style="padding:6px; font-size:10px;">${wo.fecha_operacion || ''}</td>
      <td style="padding:6px; font-size:10px; text-align:center;">
        <span style="padding:2px 6px; border-radius:3px; font-size:9px; ${estadoClass}">
          ${wo.estado}
        </span>
      </td>
      <td style="padding:6px; font-size:10px;">${wo.modificador || ''}</td>
      <td style="padding:6px; text-align:center;">
        ${yaImportado ?
        `<span style="padding:2px 6px; font-size:9px; background:#555; color:#999; border-radius:3px;">?? Bloqueado</span>` :
        `<button class="plan-btn wo-import-single-btn" data-wo-id="${wo.id}"
                  style="padding:2px 6px; font-size:9px; background:#27ae60;"
                  ${wo.estado === 'CERRADA' ? 'disabled' : ''}>
            Importar
          </button>`
      }
      </td>
    `;

    tbody.appendChild(row);
  });
}

// Toggle all WOs
function toggleAllWOs(selectAllCheckbox) {
  const checkboxes = document.querySelectorAll(".wo-checkbox:not([disabled])");
  checkboxes.forEach(cb => {
    cb.checked = selectAllCheckbox.checked;
  });
}

// Importar WO individual
async function importSingleWO(woId, button) {
  const originalText = button.textContent;

  try {
    // Verificar si la fila está marcada como ya importada
    const row = button.closest('tr');
    if (row && row.style.opacity === '0.6') {
      alert('⚠️ Esta Work Order ya fue importada anteriormente.');
      return;
    }

    // Obtener fecha de importación
    const importDateInput = document.getElementById('wo-filter-date');
    const importDate = importDateInput ? importDateInput.value : getTodayInNuevoLeon();

    if (!importDate) {
      alert('⚠️ Por favor seleccione una fecha de importación');
      return;
    }

    // Mostrar estado de carga en el botón
    button.textContent = 'Importando...';
    button.disabled = true;
    button.classList.add('loading');

    // Mostrar loading mejorado en la tabla de planes
    showTableLoading('plan-main-table', 'Importando Work Order...');
    updateWOStatus("Importando Work Order...");

    const response = await axios.post("/api/work-orders/import", {
      wo_ids: [woId],
      import_date: importDate
    });

    if (response.data.success) {
      const imported = response.data.imported || 0;
      const errors = response.data.errors || [];
      
      if (imported > 0) {
        const plan = response.data.plans[0];
        // Ocultar loading con transición suave
        hideTableLoading('plan-main-table');
        alert(`✅ WO importado exitosamente como Plan: ${plan.lot_no}`);
        loadPlans(); // Recargar tabla principal
        loadWorkOrders(); // Recargar WOs
      } else if (errors.length > 0) {
        hideTableLoading('plan-main-table');
        alert(`❌ No se pudo importar:\n\n${errors.join('\n')}`);
      }
    } else {
      hideTableLoading('plan-main-table');
      alert("❌ Error en importación: " + (response.data.errors || []).join(", "));
    }
  } catch (error) {
    hideTableLoading('plan-main-table');
    alert("❌ Error importando WO: " + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar boton
    button.textContent = originalText;
    button.disabled = false;
    button.classList.remove('loading');
    updateWOStatus("Listo para importar");
  }
}

// Importar WOs seleccionados
async function importAllSelectedWOs() {
  const selectedCheckboxes = document.querySelectorAll(".wo-checkbox:checked");

  if (selectedCheckboxes.length === 0) {
    alert("⚠️ Seleccione al menos un Work Order para importar");
    return;
  }

  // Obtener fecha de importación
  const importDateInput = document.getElementById('wo-filter-date');
  const importDate = importDateInput ? importDateInput.value : getTodayInNuevoLeon();

  if (!importDate) {
    alert('⚠️ Por favor seleccione una fecha de importación');
    return;
  }

  // Filtrar WOs que NO están ya importadas
  const woIdsToImport = [];
  const alreadyImported = [];
  
  selectedCheckboxes.forEach(cb => {
    const woId = parseInt(cb.value);
    const woRow = cb.closest('tr');
    const isImported = woRow && woRow.style.opacity === '0.6'; // WO ya importada
    
    if (isImported) {
      // Buscar el código WO para el mensaje
      const woCode = woRow.cells[1]?.textContent || `ID ${woId}`;
      alreadyImported.push(woCode);
    } else {
      woIdsToImport.push(woId);
    }
  });

  // Mostrar advertencia si hay WOs ya importadas seleccionadas
  if (alreadyImported.length > 0) {
    const message = `⚠️ ${alreadyImported.length} WO(s) ya importada(s) serán omitida(s):\n${alreadyImported.join(', ')}\n\n¿Continuar con las ${woIdsToImport.length} WO(s) restantes?`;
    if (woIdsToImport.length === 0) {
      alert("❌ Todas las WOs seleccionadas ya fueron importadas.");
      return;
    }
    if (!confirm(message)) {
      return;
    }
  } else {
    if (!confirm(`¿Importar ${woIdsToImport.length} Work Order(s) como planes para el ${importDate}?`)) {
      return;
    }
  }

  const woIds = woIdsToImport;

  try {
    // Mostrar loading mejorado en múltiples lugares
    showTableLoading('wo-modal-content', `📦 Importando ${woIds.length} Work Order${woIds.length > 1 ? 's' : ''}...`);
    showTableLoading('plan-main-table', `📦 Procesando ${woIds.length} Work Order${woIds.length > 1 ? 's' : ''}...`);
    updateWOStatus(`⏳ Importando ${woIds.length} work orders...`);

    // Deshabilitar boton de importar
    setButtonLoading('wo-import-selected-btn', true, '📦 Importando...');

    const response = await axios.post("/api/work-orders/import", {
      wo_ids: woIds,
      import_date: importDate
    });

    if (response.data.success) {
      const { imported, errors } = response.data;
      
      if (imported > 0) {
        let message = `✅ ${imported} Work Order(s) importado(s) exitosamente`;

        if (errors && errors.length > 0) {
          message += `\n\n⚠️ WOs ya importadas (${errors.length}):\n`;
          errors.forEach((error, index) => {
            message += `${index + 1}. ${error}\n`;
          });
        }

        alert(message);
      } else if (errors && errors.length > 0) {
        let message = `❌ Ninguna WO pudo ser importada:\n\n`;
        errors.forEach((error, index) => {
          message += `${index + 1}. ${error}\n`;
        });
        alert(message);
      }
      
      loadPlans(); // Recargar tabla principal
      loadWorkOrders(); // Recargar WOs

      // Desmarcar "Seleccionar todos"
      document.getElementById("wo-select-all").checked = false;

    } else {
      alert("❌ Error en importación: " + (response.data.errors || []).join(", "));
    }
  } catch (error) {
    alert("❌ Error importando WOs: " + (error.response?.data?.error || error.message));
  } finally {
    // Ocultar loading y restaurar botones
    hideTableLoading('wo-modal-content');
    hideTableLoading('plan-main-table');
    setButtonLoading('wo-import-selected-btn', false, 'Importar Seleccionados');
    updateWOStatus("✅ Listo para importar");
  }
}

// Actualizar estado del modal WO
function updateWOStatus(message) {
  const statusElement = document.getElementById("wo-status");
  if (statusElement) {
    statusElement.textContent = message;
  }
}


// ========= RESCHEDULE FUNCTIONALITY =========

// Abrir modal Reprogramar (Ahora manejado por event delegation)
/* REMOVIDO - Ahora manejado por event delegation
document.getElementById("reschedule-openModalBtn").addEventListener("click", () => {
  document.getElementById("reschedule-modal").style.display = "flex";
  setDefaultRescheduleDates();
});
*/

// Cerrar modal Reprogramar (Ahora manejado por event delegation)
/* REMOVIDO - Ahora manejado por event delegation
document.getElementById("reschedule-closeModalBtn").addEventListener("click", () => {
  document.getElementById("reschedule-modal").style.display = "none";
});
*/

// Establecer fechas por defecto
function setDefaultRescheduleDates() {
  const dateFrom = document.getElementById("reschedule-date-from");
  const dateTo = document.getElementById("reschedule-date-to");
  const newDate = document.getElementById("reschedule-new-date");

  if (dateFrom && !dateFrom.value) {
    dateFrom.value = getDateInNuevoLeon(-7); // Una semana atros en Nuevo Leon
  }
  if (dateTo && !dateTo.value) {
    dateTo.value = getTodayInNuevoLeon(); // Hoy en Nuevo Leon
  }
  if (newDate && !newDate.value) {
    newDate.value = getTodayInNuevoLeon(); // Hoy en Nuevo Leon
  }
}

// Exponer funcion globalmente
window.setDefaultRescheduleDates = setDefaultRescheduleDates;

// Cargar planes pendientes
async function loadPendingPlans() {
  const dateFromInput = document.getElementById("reschedule-date-from");
  const dateToInput = document.getElementById("reschedule-date-to");

  if (!dateFromInput || !dateToInput) {
    console.error('? Elementos de fecha no encontrados');
    alert("Error: Elementos de fecha no disponibles");
    return;
  }

  const dateFrom = dateFromInput.value;
  const dateTo = dateToInput.value;

  if (!dateFrom || !dateTo) {
    alert("?? Seleccione el rango de fechas para buscar");
    return;
  }

  try {
    showTableBodyLoading('reschedule-tableBody', 'Buscando planes pendientes...', 9);
    updateRescheduleStatus("Buscando planes pendientes...");

    // Consultar planes con input pendiente
    const response = await axios.get(`/api/plan/pending?start=${dateFrom}&end=${dateTo}`);
    const pendingPlans = response.data;

    renderPendingPlans(pendingPlans);
    updateRescheduleStatus(`${pendingPlans.length} planes con input pendiente encontrados`);

  } catch (error) {
    console.error('? Error al cargar planes pendientes:', error);
    alert("Error al cargar planes pendientes: " + (error.response?.data?.error || error.message));
    updateRescheduleStatus("Error al cargar planes");
  }
}

// Renderizar planes pendientes en la tabla
function renderPendingPlans(plans) {
  const tbody = document.getElementById("reschedule-tableBody");
  tbody.innerHTML = "";

  if (plans.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align:center; padding:20px; color:#888;">
          No hay planes con input pendiente en el rango seleccionado
        </td>
      </tr>
    `;
    return;
  }

  plans.forEach(plan => {
    const pendingQty = (plan.plan_count || 0) - (plan.input || 0);

    const row = document.createElement("tr");
    row.style.cursor = "pointer";
    row.innerHTML = `
      <td style="padding:6px; border:1px solid #555; text-align:center;">
        <input type="checkbox" class="reschedule-checkbox" value="${plan.lot_no}">
      </td>
      <td style="padding:6px; border:1px solid #555;">${plan.lot_no}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.working_date || '--'}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.part_no || '--'}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.line || '--'}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.plan_count || 0}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.input || 0}</td>
      <td style="padding:6px; border:1px solid #555; color:#e74c3c; font-weight:bold;">${pendingQty}</td>
      <td style="padding:6px; border:1px solid #555;">${plan.status || '--'}</td>
    `;

    tbody.appendChild(row);
  });
}

// Toggle seleccion de todos los planes pendientes
function toggleAllReschedule(masterCheckbox) {
  const checkboxes = document.querySelectorAll(".reschedule-checkbox");
  checkboxes.forEach(cb => {
    cb.checked = masterCheckbox.checked;
  });
}

// Reprogramar planes seleccionados
async function reschedulePendingPlans() {
  const selectedCheckboxes = document.querySelectorAll(".reschedule-checkbox:checked");
  const newDateInput = document.getElementById("reschedule-new-date");

  if (!newDateInput) {
    console.error('❌ Elemento reschedule-new-date no encontrado');
    alert("Error: Elemento de fecha no disponible");
    return;
  }

  const newDate = newDateInput.value;

  if (selectedCheckboxes.length === 0) {
    alert("⚠️ Seleccione al menos un plan para reprogramar");
    return;
  }

  if (!newDate) {
    alert("⚠️ Seleccione la nueva fecha de trabajo");
    return;
  }

  const lotNos = Array.from(selectedCheckboxes).map(cb => cb.value);

  if (!confirm(`¿Crear ${lotNos.length} nuevo(s) plan(es) con la cantidad pendiente para la fecha ${newDate}?\n\nSe creará un nuevo registro con:\n- Mismo número de lote y parte\n- Cantidad pendiente (plan - producido)\n- Nueva fecha de trabajo`)) {
    return;
  }

  try {
    updateRescheduleStatus("Creando nuevos planes...");

    // Enviar solicitud de reprogramacion
    const response = await axios.post('/api/plan/reschedule', {
      lot_nos: lotNos,
      new_working_date: newDate
    });

    // Mostrar modal de éxito con información detallada
    const created = response.data.created || 0;
    showSuccessModal(`✅ ${created} nuevo(s) plan(es) creado(s) exitosamente para ${newDate}\n\nCada plan tiene la cantidad pendiente calculada automáticamente.`);

    // Recargar la lista de pendientes
    loadPendingPlans();

    // Recargar planes principales si están en la misma fecha
    const currentStartInput = document.getElementById("filter-start");
    const currentEndInput = document.getElementById("filter-end");

    if (currentStartInput && currentEndInput) {
      const currentStart = currentStartInput.value;
      const currentEnd = currentEndInput.value;
      if (newDate >= currentStart && newDate <= currentEnd) {
        loadPlans();
      }
    }

  } catch (error) {
    console.error('❌ Error al crear nuevos planes:', error);
    alert("Error al crear nuevos planes: " + (error.response?.data?.error || error.message));
    updateRescheduleStatus("Error al crear planes");
  }
}

// Actualizar estado del modal Reprogramar
function updateRescheduleStatus(message) {
  const statusElement = document.getElementById("reschedule-status");
  if (statusElement) {
    statusElement.textContent = message;
  }
}

// ========= INITIALIZATION =========

// ====== FUNCIONALIDAD DE PLANEACIoN INTEGRADA ======

// Inicializar grupos visuales
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
  const table = document.getElementById('plan-table');
  const oldTbody = document.getElementById('plan-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'plan-tableBody';

  const groupCount = parseInt(document.getElementById('groups-count').value) || 6;
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
      <td colspan="22" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
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
      <td colspan="22" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
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
      tr.className = 'plan-row';

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
        <td>${plan.part_no}</td>
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
      spacerRow.innerHTML = `<td colspan="22" style="height: 10px; background-color: #2c2c2c;"></td>`;
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
  console.log('🔍 Buscando conflictos de línea/horario para resaltar...');
  
  // *** CORRECCIÓN: Obtener planes desde visualGroups en lugar de planningData ***
  const todosLosPlanes = [];
  visualGroups.groups.forEach(group => {
    todosLosPlanes.push(...group.plans);
  });
  
  console.log('📊 Total de planes en grupos:', todosLosPlanes.length);
  console.log('📊 planningCalculations size:', planningCalculations.size);
  
  // Crear mapa de planes con su hora de inicio calculada
  const planesConHorario = [];
  
  todosLosPlanes.forEach(plan => {
    // Obtener cálculos del plan
    const calc = planningCalculations.get(plan.lot_no);
    
    console.log(`Plan ${plan.lot_no}: line=${plan.line}, status=${plan.status}, calc=`, calc);
    
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
      console.log(`  ✅ Agregado: ${plan.lot_no} - ${plan.line} - ${calc.startTime}`);
    }
  });
  
  console.log(`📊 Analizando ${planesConHorario.length} planes activos con horario calculado`);
  
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
  
  console.log('🗺️ Mapa de conflictos:', Array.from(conflictosMap.entries()));
  
  // Identificar claves con conflictos (más de un plan)
  const clavesConConflicto = Array.from(conflictosMap.entries())
    .filter(([clave, planes]) => planes.length > 1);
  
  if (clavesConConflicto.length === 0) {
    console.log('✅ No se encontraron conflictos de línea/horario');
    return;
  }
  
  console.log(`⚠️ Se encontraron ${clavesConConflicto.length} conflictos`);
  
  // Obtener todos los lot_no que tienen conflicto
  const lotNosConConflicto = new Set();
  clavesConConflicto.forEach(([clave, planes]) => {
    const lotNos = planes.map(p => p.lot_no);
    lotNos.forEach(lotNo => lotNosConConflicto.add(lotNo));
    
    // Log detallado del conflicto
    const [linea, fecha, hora] = clave.split('-');
    console.log(`⚠️ Conflicto en Línea: ${linea}, Fecha: ${fecha}, Hora: ${hora}`);
    planes.forEach(p => {
      console.log(`   - Lot: ${p.lot_no}, Modelo: ${p.model_code}, Grupo: ${p.group_no}`);
    });
  });
  
  console.log('🎯 Lot numbers con conflicto:', Array.from(lotNosConConflicto));
  
  // Resaltar filas con conflicto
  const tbody = document.getElementById('plan-tableBody');
  if (!tbody) {
    console.error('❌ No se encontró plan-tableBody');
    return;
  }
  
  const rows = tbody.querySelectorAll('tr.plan-row');
  console.log(`📋 Filas encontradas en tabla: ${rows.length}`);
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
        if (cells[19]) {
          cells[19].style.backgroundColor = '#e74c3c';
          cells[19].style.fontWeight = 'bold';
          cells[19].style.color = '#ffffff';
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
  
  console.log(`✅ ${conflictosResaltados} filas resaltadas con conflicto`);
  
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
  const tbody = document.getElementById("plan-tableBody");
  let draggedElement = null;
  let draggedFromGroup = null;
  let dropIndicator = null;
  let isDraggingOverDropZone = false;

  // Crear indicador visual de insercion
  function createDropIndicator() {
    const indicator = document.createElement('tr');
    indicator.className = 'drop-indicator';
    indicator.innerHTML = `<td colspan="22" style="height: 3px; background: #3498db; border: none; padding: 0;"></td>`;
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
    const row = e.target.closest('.plan-row');
    if (!row) return;

    draggedElement = row;
    draggedFromGroup = parseInt(row.dataset.groupIndex);
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  tbody.addEventListener('dragend', (e) => {
    const row = e.target.closest('.plan-row');
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
    const targetRow = e.target.closest('.plan-row');
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
      const targetRow = e.target.closest('.plan-row');
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
  const tbody = document.getElementById("plan-tableBody");
  const planRows = tbody.querySelectorAll('.plan-row');

  planRows.forEach(row => {
    const lotNo = row.dataset.lot;
    const calc = planningCalculations.get(lotNo);

    if (calc) {
      const cells = row.querySelectorAll('td');

      // Si el plan esto cancelado, mostrar tiempos como -- y marcar como cancelado
      if (calc.isCancelled) {
        if (cells[18]) cells[18].textContent = '--'; // Tiempo Productivo
        if (cells[19]) cells[19].textContent = '--'; // Inicio
        if (cells[20]) cells[20].textContent = '--'; // Fin
        if (cells[21]) cells[21].innerHTML = '<span class="status-cancelled">CANCELADO</span>'; // Turno

        // Resaltar fila como cancelada
        row.style.backgroundColor = '#6c6c6c';
        row.style.color = '#ccc';
        row.style.textDecoration = 'line-through';
      } else {
        // Plan activo - mostrar colculos normales
        if (cells[18]) cells[18].textContent = minutesToTime(calc.productionTime);
        if (cells[19]) cells[19].textContent = calc.startTime;
        if (cells[20]) cells[20].textContent = calc.endTime;

        // Actualizar indicador de tiempo extra en la columna Turno
        if (cells[21]) {
          cells[21].innerHTML = calc.isOvertime ?
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

    // NO sobrescribir el status real de la base de datos (cells[17])
      // El status real (PLAN, EN PROGRESO, CANCELADO, etc.) debe mantenerse
    }
  });
}

// Renderizar grupos visuales actuales sin leer del DOM
function renderCurrentVisualGroups() {
  const table = document.getElementById('plan-table');
  const oldTbody = document.getElementById('plan-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'plan-tableBody';

  // Renderizar cada grupo usando los datos ya en memoria
  visualGroups.groups.forEach((group, groupIndex) => {
    // Fila de encabezado del grupo
    const groupHeaderRow = document.createElement('tr');
    groupHeaderRow.className = 'group-header-row';
    groupHeaderRow.innerHTML = `
      <td colspan="22" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
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
      <td colspan="22" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
        <div class="drop-zone-content">
          ${group.plans.length === 0 ? 'Arrastra planes aquo para asignarlos a este grupo' : ''}
        </div>
      </td>
    `;
    tbody.appendChild(dropZoneRow);

    // Renderizar planes del grupo en el orden actual
    group.plans.forEach((plan, planIndex) => {
      const tr = document.createElement('tr');
      tr.className = 'plan-row';
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
        <td>${plan.part_no}</td>
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
      spacerRow.innerHTML = `<td colspan="22" style="height: 10px; background-color: #2c2c2c;"></td>`;
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
  const tbody = document.getElementById("plan-tableBody");
  const planRows = tbody.querySelectorAll('.plan-row');
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
        project: cells[9]?.textContent?.trim() || '',
        process: cells[10]?.textContent?.trim() || 'MAIN',
        ct: cells[11]?.textContent?.trim() || '0',
        uph: parseInt(cells[12]?.textContent?.trim()) || 0,
        plan_count: parseInt(cells[13]?.textContent?.trim()) || 0,
        produced: parseInt(cells[14]?.textContent?.trim()) || 0,
        output: parseInt(cells[15]?.textContent?.trim()) || 0,
        entregadas_main: parseInt(cells[16]?.textContent?.trim()) || 0,
        status: cells[17]?.textContent?.trim() || 'PLAN' // ? CORREGIDO: cells[16] no cells[15]
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

// Utilidades de tiempo
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
  const groupCount = parseInt(document.getElementById('groups-count').value) || 6;
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

// Auto acomodo de planes por optimizacion distribuida
function autoArrangePlans() {
  const tbody = document.getElementById('plan-tableBody');
  const planRows = Array.from(tbody.querySelectorAll('.plan-row'));

  if (planRows.length === 0) {
    // Feedback visual en lugar de alert
    const autoBtn = document.getElementById('auto-arrange-btn');
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
      uph: parseInt(cells[12]?.textContent) || 0,
      plan_count: parseInt(cells[13]?.textContent) || 0,
      productionTime: calculateProductionTime(
        parseInt(cells[13]?.textContent) || 0,
        parseInt(cells[12]?.textContent) || 0
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
      project: cells[9]?.textContent?.trim() || '',
      process: cells[10]?.textContent?.trim() || 'MAIN',
      ct: cells[11]?.textContent?.trim() || '0',
      produced: parseInt(cells[14]?.textContent) || 0,
      output: parseInt(cells[15]?.textContent) || 0,
      entregadas_main: parseInt(cells[16]?.textContent) || 0,
      status: cells[17]?.textContent?.trim() || 'PLAN'
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
  const groupCount = parseInt(document.getElementById('groups-count').value) || 6;
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
  
  console.log('?? Orden de loneas para auto-acomodo:', sortedLines.join(', '));

  // Asignar cada lonea a un grupo de forma secuencial (round-robin)
  sortedLines.forEach((line, lineIndex) => {
    const linePlans = lineGroups[line];
    const totalLineTime = linePlans.reduce((sum, plan) => sum + plan.productionTime, 0);

    // Asignacion secuencial: M1 -> Grupo 0, M2 -> Grupo 1, M3 -> Grupo 2, etc.
    // Si hay mos loneas que grupos, se hace round-robin (M7 -> Grupo 0, M8 -> Grupo 1, etc.)
    const groupIndex = lineIndex % groupCount;

    console.log(`?? Auto-acomodo: Lonea ${line} ? Grupo ${groupIndex + 1} (${totalLineTime.toFixed(1)} min)`);

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
  const autoBtn = document.getElementById('auto-arrange-btn');
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
  const toggleBtn = document.getElementById('toggle-view-btn');
  const groupsCountSelect = document.getElementById('groups-count');
  const groupsLabel = groupsCountSelect?.previousElementSibling;
  const autoArrangeBtn = document.getElementById('auto-arrange-btn');
  const saveSeqBtn = document.getElementById('save-sequences-btn');
  const lineFilter = document.getElementById('line-filter');

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
  const lineFilter = document.getElementById('line-filter');
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

// Renderizar tabla agrupada por lineas de produccion
function renderTableByLines(filterLine) {
  const table = document.getElementById('plan-table');
  const oldTbody = document.getElementById('plan-tableBody');
  const tbody = document.createElement('tbody');
  tbody.id = 'plan-tableBody';

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
      <td colspan="22" style="background-color: #1a3a4a; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #16a085;">
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
      tr.className = 'plan-row';

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
        <td>${plan.part_no || ''}</td>
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
      spacerRow.innerHTML = `<td colspan="22" style="height: 10px; background-color: #2c2c2c;"></td>`;
      tbody.appendChild(spacerRow);
    }
  });

  // Si no hay planes
  if (sortedLines.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = `<td colspan="22" style="text-align: center; padding: 20px; color: #888;">No hay planes para mostrar</td>`;
    tbody.appendChild(emptyRow);
  }

  // Reemplazar tbody
  if (oldTbody && oldTbody.parentNode) {
    oldTbody.parentNode.replaceChild(tbody, oldTbody);
  } else if (table) {
    table.appendChild(tbody);
  }
}

// Exponer funciones globalmente
window.toggleViewMode = toggleViewMode;
window.renderTableByLines = renderTableByLines;

// Exponer funciones de reprogramacion globalmente
window.loadPendingPlans = loadPendingPlans;
window.reschedulePendingPlans = reschedulePendingPlans;
window.toggleAllReschedule = toggleAllReschedule;

// Calcular y actualizar tiempos en la tabla
function calculateAndUpdateTimes() {
  const tbody = document.getElementById('plan-tableBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  // Obtener datos actuales
  const plans = rows.map(row => {
    const cells = row.querySelectorAll('td');
    return {
      lot_no: row.dataset.lot,
      line: cells[5]?.textContent || '',
      uph: parseInt(cells[12]?.textContent) || 0,
      plan_count: parseInt(cells[13]?.textContent) || 0
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
        cells[18].textContent = minutesToTime(calc.productionTime);
        cells[18].className = 'tiempo-cell';
      } else {
        const timeCell = document.createElement('td');
        timeCell.textContent = minutesToTime(calc.productionTime);
        timeCell.className = 'tiempo-cell';
        row.appendChild(timeCell);
      }

      // Hora inicio
      if (cells.length >= 20) {
        cells[19].textContent = calc.startTime;
        cells[19].className = 'tiempo-cell fecha-inicio-cell';
      } else {
        const startCell = document.createElement('td');
        startCell.textContent = calc.startTime;
        startCell.className = 'tiempo-cell fecha-inicio-cell';
        row.appendChild(startCell);
      }

      // Hora fin
      if (cells.length >= 21) {
        cells[20].textContent = calc.endTime;
        cells[20].className = 'tiempo-cell';
      } else {
        const endCell = document.createElement('td');
        endCell.textContent = calc.endTime;
        endCell.className = 'tiempo-cell';
        row.appendChild(endCell);
      }

      // Indicador de tiempo extra en la oltima columna (Turno)
      if (cells.length >= 22) {
        cells[21].innerHTML = calc.isOvertime ?
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
  const groupCount = parseInt(document.getElementById('groups-count')?.value) || 6;
  
  // Limpiar opciones existentes (excepto la primera opción "Automático")
  selectElement.innerHTML = '<option value="">Automático (al final)</option>';
  
  // Agregar una opción por cada grupo
  for (let i = 1; i <= groupCount; i++) {
    const option = document.createElement('option');
    option.value = i;
    option.textContent = `Grupo ${i}`;
    selectElement.appendChild(option);
  }
  
  console.log(`Selector de grupos actualizado con ${groupCount} grupos`);
}

// ====== Función para asignar un plan a un grupo específico ======
function assignPlanToGroup(lotNo, targetGroupIndex) {
  console.log(`Asignando plan ${lotNo} al grupo ${targetGroupIndex + 1}`);
  
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
  
  console.log(`Plan ${lotNo} asignado al grupo ${targetGroupIndex + 1}`);
  
  // Re-renderizar la tabla
  const allPlans = [];
  visualGroups.groups.forEach(group => {
    allPlans.push(...group.plans);
  });
  
  renderTableWithVisualGroups(allPlans);
}

// Funcion para crear modales dinomicamente en el body
function createModalsInBody() {
  console.log('??? Creando modales dinomicamente en el body...');

  // Verificar que los estilos CSS eston cargados
  const testDiv = document.createElement('div');
  testDiv.className = 'modal-overlay';
  testDiv.style.display = 'none';
  document.body.appendChild(testDiv);
  const computedStyle = window.getComputedStyle(testDiv);
  console.log('?? Estilos CSS de modal-overlay:', {
    position: computedStyle.position,
    zIndex: computedStyle.zIndex,
    display: computedStyle.display
  });
  document.body.removeChild(testDiv);

  // Modal de Nuevo Plan
  if (!document.getElementById('plan-modal')) {
    console.log('?? Creando modal plan-modal');
    const planModal = document.createElement('div');
    planModal.id = 'plan-modal';
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
      <div id="plan-modal-content" style="
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
        <form id="plan-form" style="display: flex; flex-direction: column; gap: 12px;">
          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Fecha:</label>
          <input type="date" name="working_date" required class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Part No:</label>
          <input type="text" name="part_no" required class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Line:</label>
          <input type="text" name="line" required class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Turno:</label>
          <select name="turno" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="DIA" selected>DIA</option>
            <option value="TIEMPO EXTRA">TIEMPO EXTRA</option>
            <option value="NOCHE">NOCHE</option>
          </select>

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Plan Count:</label>
          <input type="number" name="plan_count" value="0" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">WO Code:</label>
          <input type="text" name="wo_code" value="SIN-WO" placeholder="SIN-WO" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">PO Code:</label>
          <input type="text" name="po_code" value="SIN-PO" placeholder="SIN-PO" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Asignar a Grupo:</label>
          <select name="target_group" id="target-group-select" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="">📋 Automático (al final)</option>
          </select>

          <div class="form-actions" style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
            <button type="submit" class="plan-btn plan-btn-add" style="flex: 1; min-width: 120px; background: #27ae60; color: white; border: none; padding: 12px 10px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Registrar</button>
            <button type="button" id="plan-closeModalBtn" class="plan-btn" style="flex: 1; min-width: 120px; background: #666; color: white; border: none; padding: 12px 10px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); touch-action: manipulation;">Cancelar</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(planModal);
  }

  // Modal de Editar Plan
  if (!document.getElementById('plan-editModal')) {
    console.log('?? Creando modal plan-editModal');
    const editModal = document.createElement('div');
    editModal.id = 'plan-editModal';
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
      <div id="plan-modal-content" style="
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
        <form id="plan-editForm" style="display: flex; flex-direction: column; gap: 12px;">
          <input type="hidden" name="lot_no">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Turno:</label>
          <select name="turno" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">
            <option value="DIA">DIA</option>
            <option value="TIEMPO EXTRA">TIEMPO EXTRA</option>
            <option value="NOCHE">NOCHE</option>
          </select>

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Plan Count:</label>
          <input type="number" name="plan_count" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">WO Code:</label>
          <input type="text" name="wo_code" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">PO Code:</label>
          <input type="text" name="po_code" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <label style="color: #ecf0f1; font-size: clamp(11px, 2.5vw, 13px); margin-bottom: -8px;">Line:</label>
          <input type="text" name="line" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 10px 8px; border-radius: 4px; font-size: clamp(12px, 3vw, 14px); width: 100%; box-sizing: border-box;">

          <div class="form-actions-with-gap" style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button type="submit" class="plan-btn plan-btn-add" style="flex: 1; min-width: 100px; background: #27ae60; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Guardar</button>
              <button type="button" class="plan-btn" style="flex: 1; min-width: 100px; background: #666; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); touch-action: manipulation;">Cerrar</button>
            </div>
            <button type="button" id="plan-cancelBtn" class="plan-btn plan-btn-danger" style="width: 100%; background: #e74c3c; color: white; border: none; padding: 12px 15px; border-radius: 4px; cursor: pointer; font-size: clamp(12px, 3vw, 14px); font-weight: 500; touch-action: manipulation;">Cancelar plan</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(editModal);
  }

  // Modal de Reprogramar
  if (!document.getElementById('reschedule-modal')) {
    console.log('?? Creando modal reschedule-modal');
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
          <input type="date" id="reschedule-date-from" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
          <label style="font-size: 11px; color: #ecf0f1;">Fecha Hasta:</label>
          <input type="date" id="reschedule-date-to" class="plan-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
          <label style="font-size: 11px; color: #ecf0f1;">Nueva Fecha:</label>
          <input type="date" id="reschedule-new-date" class="plan-input" required style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px; border-radius: 4px;">
          
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

  console.log('? Modales creados dinomicamente en el body');
}

// Funcion de inicializacion de event listeners usando event delegation
function initializePlanEventListeners() {
  console.log('?? initializePlanEventListeners llamada');

  // IMPORTANTE: Siempre crear modales dinomicamente en el body
  // Esto asegura que los modales siempre eston al nivel correcto del DOM
  createModalsInBody();

  // IMPORTANTE: Usar proteccion para evitar agregar listeners duplicados
  // Solo agregar listeners una vez, ya que eston en document.body
  if (document.body.dataset.planListenersAttached === 'true') {
    console.log('? Listeners ya eston configurados, saltando re-inicializacion de listeners');
    console.log('?? Los modales fueron creados/verificados en el body');
    return;
  }

  console.log('?? Configurando event listeners con event delegation...');

  // ========== EVENT LISTENER DE CLICKS (Event Delegation) ==========
  document.body.addEventListener('click', function (e) {
    const target = e.target;

    // ========== BOTONES DE MODALES ==========

    // Abrir modal Nuevo Plan
    if (target.id === 'plan-openModalBtn' || target.closest('#plan-openModalBtn')) {
      e.preventDefault();
      console.log('🔵 Click en plan-openModalBtn detectado');

      // Asegurar que el modal existe antes de abrirlo
      if (!document.getElementById('plan-modal')) {
        console.log('🏗️ Modal no existe, creándolo...');
        createModalsInBody();
      }

      // Llenar el selector de grupos antes de abrir el modal
      populateGroupSelector();

      // Llenar el campo de fecha con la fecha de hoy
      const dateInput = document.querySelector('#plan-form input[name="working_date"]');
      if (dateInput) {
        const today = getTodayInNuevoLeon(); // Formato YYYY-MM-DD
        dateInput.value = today;
        console.log('📅 Fecha del día establecida:', today);
      }

      const modal = document.getElementById('plan-modal');
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
        console.log('✅ Modal plan-modal abierto con estilos forzados');
      } else {
        console.error('❌ Modal plan-modal no encontrado después de crearlo');
      }
      return;
    }

    // Cerrar modal Nuevo Plan
    if (target.id === 'plan-closeModalBtn' || target.closest('#plan-closeModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('plan-modal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    // Abrir modal Work Orders
    if (target.id === 'wo-openModalBtn' || target.closest('#wo-openModalBtn')) {
      e.preventDefault();
      console.log('?? Click en wo-openModalBtn detectado');

      // Crear modal WO si no existe
      if (typeof createWorkOrdersModal === 'function') {
        createWorkOrdersModal();
        console.log('? Modal WO creado/verificado');
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
        console.log('? Modal wo-modal abierto con estilos forzados');
        if (typeof loadWorkOrders === 'function') loadWorkOrders();
      } else {
        console.error('? Modal wo-modal no encontrado despuos de crearlo');
      }
      return;
    }

    // Abrir modal Reprogramar
    if (target.id === 'reschedule-openModalBtn' || target.closest('#reschedule-openModalBtn')) {
      e.preventDefault();
      console.log('?? Click en reschedule-openModalBtn detectado');

      // Asegurar que el modal existe antes de abrirlo
      if (!document.getElementById('reschedule-modal')) {
        console.log('?? Modal no existe, creondolo...');
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

        console.log('? Modal reschedule-modal abierto con estilos forzados');
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
    if (target.closest('#plan-editForm button[type="button"]') &&
      target.textContent.includes('Cerrar')) {
      e.preventDefault();
      const modal = document.getElementById('plan-editModal');
      if (modal) {
        modal.style.display = 'none';
        modal.style.visibility = 'hidden';
      }
      return;
    }

    // Boton Cancelar Plan (boton rojo)
    if (target.id === 'plan-cancelBtn' || target.closest('#plan-cancelBtn')) {
      e.preventDefault();
      if (typeof handleCancelPlan === 'function') handleCancelPlan();
      return;
    }

    // ========== BOTONES DE ACCIONES ==========

    // Auto acomodo
    if (target.id === 'auto-arrange-btn' || target.closest('#auto-arrange-btn')) {
      e.preventDefault();
      autoArrangePlans();
      return;
    }

    // Exportar a Excel
    if (target.id === 'export-excel-btn' || target.closest('#export-excel-btn')) {
      e.preventDefault();
      exportarExcel();
      return;
    }

    // Guardar secuencias
    if (target.id === 'save-sequences-btn' || target.closest('#save-sequences-btn')) {
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
    if (target.id === 'toggle-view-btn' || target.closest('#toggle-view-btn')) {
      e.preventDefault();
      toggleViewMode();
      return;
    }
  });

  // ========== EVENT LISTENER DE CHANGE PARA LINE-FILTER ==========
  document.body.addEventListener('change', function (e) {
    const target = e.target;
    
    // Filtro de lineas
    if (target.id === 'line-filter') {
      renderTableByLines(target.value);
      return;
    }
  });

  // ========== EVENT LISTENERS DE SUBMIT ==========
  document.body.addEventListener('submit', function (e) {
    // Submit del form de editar plan
    if (e.target.id === 'plan-editForm') {
      e.preventDefault();
      if (typeof window.handleEditPlanSubmit === 'function') {
        window.handleEditPlanSubmit(e.target);
      }
      return;
    }

    // Submit del form de nuevo plan
    if (e.target.id === 'plan-form') {
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
    if (target.id === 'groups-count') {
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
    console.log('🖱️ Doble click detectado en:', e.target);
    
    // Verificar si el doble click fue en una fila de la tabla de planes
    const row = e.target.closest('tr.plan-row');
    
    if (!row) {
      console.log('❌ No se encontró tr.plan-row');
      return;
    }
    
    // Verificar que la fila pertenece al contenedor ASSY, no al de IMD
    const assyContainer = row.closest('#plan-main-assy-unique-container');
    if (!assyContainer) {
      console.log('⚠️ Fila no pertenece a ASSY, ignorando...');
      return;
    }
    
    console.log('✅ Fila encontrada:', row);

    const lotNo = row.dataset.lot;
    console.log('📋 Lot No:', lotNo);
    
    if (lotNo && typeof openEditModal === 'function') {
      console.log('✅ Abriendo modal de edición para:', lotNo);
      openEditModal(lotNo);
    } else {
      console.log('❌ No se puede abrir modal. lotNo:', lotNo, 'openEditModal existe:', typeof openEditModal === 'function');
    }
  };
  
  // Agregar el listener
  document.body.addEventListener('dblclick', document.body.dblclickHandler);

  // Marcar como inicializado
  document.body.dataset.planListenersAttached = 'true';
  console.log('✅ Event listeners configurados correctamente');
}

// Event listeners para nuevos controles
document.addEventListener('DOMContentLoaded', initializePlanEventListeners);

// Exponer funciones globalmente para que puedan ser llamadas despuos de cargar contenido dinomico
window.initializePlanEventListeners = initializePlanEventListeners;
window.createModalsInBody = createModalsInBody;

// Tambion ejecutar inmediatamente si el DOM ya esto listo (para scripts defer)
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  initializePlanEventListeners();
}

// Modificar loadPlans para usar grupos visuales
const originalLoadPlans = loadPlans;
loadPlans = async function () {
  try {
    // Mostrar loading en el tbody de la tabla
    showTableBodyLoading('plan-tableBody', 'Cargando planes...', 22);

    setDefaultDateFilters();
    const fs = document.getElementById("filter-start")?.value;
    const fe = document.getElementById("filter-end")?.value;
    let url = "/api/plan";
    const params = [];
    if (fs) params.push(`start=${encodeURIComponent(fs)}`);
    if (fe) params.push(`end=${encodeURIComponent(fe)}`);
    if (params.length) url += `?${params.join("&")}`;

    let res = await axios.get(url);
    let data = Array.isArray(res.data) ? res.data.slice() : [];

    // Aplicar orden guardado (si existe) antes de renderizar
    data = applySavedOrderToData(data, fs, fe);

    // Renderizar segun el modo de vista actual
    if (currentViewMode === 'lines') {
      // En modo lineas, poblar el filtro y renderizar por lineas
      populateLineFilter(data);
      const lineFilter = document.getElementById('line-filter');
      const selectedLine = lineFilter ? lineFilter.value : '';
      renderTableByLines(selectedLine);
    } else {
      // Usar nueva funcion de renderizado con grupos visuales
      renderTableWithVisualGroups(data);
    };

    // ensureOrderToolbar(fs, fe); // Ya no necesario - usamos save-sequences-btn
  } catch (error) {
    alert("Error al cargar planes: " + (error.response?.data?.error || error.message));
    // En caso de error, limpiar la tabla
    let tbody = document.getElementById("plan-tableBody");
    tbody.innerHTML = `<tr class="message-row"><td colspan="22" style="display: table-cell; text-align: center; padding: 20px; color: #888;">Error al cargar los datos</td></tr>`;
  }
};

// Funcion para exportar a Excel
async function exportarExcel() {
  try {
    const exportBtn = document.getElementById('export-excel-btn');
    const originalText = exportBtn.textContent;

    // Mostrar estado de carga
    exportBtn.textContent = 'Generando Excel...';
    exportBtn.disabled = true;
    exportBtn.style.backgroundColor = '#f39c12';

    // Recopilar todos los datos organizados por grupos visuales
    const groupedPlansData = [];

    // Iterar sobre los grupos visuales en orden
    visualGroups.groups.forEach((group, groupIndex) => {
      if (group.plans && group.plans.length > 0) {
        // Aoadir marcador de grupo
        groupedPlansData.push({
          isGroupHeader: true,
          groupTitle: group.title || `GRUPO ${groupIndex + 1}`,
          groupIndex: groupIndex
        });

        // Aoadir todos los planes del grupo en orden de secuencia
        const sortedPlans = [...group.plans].sort((a, b) => (a.sequence || 0) - (b.sequence || 0));

        sortedPlans.forEach(plan => {
          const planData = {
            secuencia: plan.sequence || '',
            lot_no: plan.lot_no || '',
            wo_code: plan.wo_code || '',
            po_code: plan.po_code || '',
            working_date: plan.working_date || '',
            line: plan.line || '',
            turno: plan.turno || '',
            model_code: plan.model_code || '',
            part_no: plan.part_no || '',
            project: plan.project || '',
            process: plan.process || '',
            ct: plan.ct || '',
            uph: plan.uph || '',
            plan_count: parseInt(plan.plan_count) || 0,
            produced: parseInt(plan.produced) || 0,
            output: parseInt(plan.output) || 0,
            entregadas_main: parseInt(plan.entregadas_main) || 0,
            status: plan.status || 'PLAN',
            tiempo_produccion: plan.tiempo_produccion || '',
            inicio: plan.inicio || '',
            fin: plan.fin || '',
            grupo: group.title || `GRUPO ${groupIndex + 1}`,
            extra: plan.extra || '',
            groupIndex: groupIndex
          };

          groupedPlansData.push(planData);
        });
      }
    });

    // Si no hay grupos visuales definidos, usar el motodo anterior como fallback
    if (groupedPlansData.length === 0) {
      const tbody = document.getElementById('plan-tableBody');
      const rows = Array.from(tbody.querySelectorAll('tr'));

      rows.forEach((row, index) => {
        // Saltar filas de separadores de grupos
        if (row.classList.contains('group-spacer')) {
          // Agregar marcador de grupo
          const groupTitle = row.textContent?.trim() || `GRUPO ${Math.floor(index / 5) + 1}`;
          groupedPlansData.push({
            isGroupHeader: true,
            groupTitle: groupTitle,
            groupIndex: Math.floor(index / 5)
          });
          return;
        }

        const cells = row.querySelectorAll('td');
        if (cells.length === 0) return;

        // Obtener lot_no para determinar el grupo visual
        const lot_no = cells[1]?.textContent?.trim() || '';

        // Determinar el grupo visual basado en la posicion en visualGroups
        let grupoVisual = `GRUPO ${Math.floor(index / 5) + 1}`;
        if (lot_no && visualGroups.planAssignments.has(lot_no)) {
          const groupIndex = visualGroups.planAssignments.get(lot_no);
          if (visualGroups.groups[groupIndex]) {
            grupoVisual = visualGroups.groups[groupIndex].title || `GRUPO ${groupIndex + 1}`;
          }
        }

        // Si no se encuentra en visualGroups, buscar por la seccion del DOM
        if (!grupoVisual || grupoVisual.includes('undefined')) {
          // Buscar hacia atros para encontrar el separador de grupo mos cercano
          let currentRow = row.previousElementSibling;
          while (currentRow) {
            if (currentRow.classList.contains('group-spacer')) {
              const spacerText = currentRow.textContent?.trim();
              if (spacerText && spacerText.includes('GRUPO')) {
                grupoVisual = spacerText;
                break;
              }
            }
            currentRow = currentRow.previousElementSibling;
          }
        }

        // Extraer datos de cada celda
        const planData = {
          secuencia: cells[0]?.textContent?.trim() || '',
          lot_no: lot_no,
          wo_code: cells[2]?.textContent?.trim() || '',
          po_code: cells[3]?.textContent?.trim() || '',
          working_date: cells[4]?.textContent?.trim() || '',
          line: cells[5]?.textContent?.trim() || '',
          turno: cells[6]?.textContent?.trim() || '',
          model_code: cells[7]?.textContent?.trim() || '',
          part_no: cells[8]?.textContent?.trim() || '',
          project: cells[9]?.textContent?.trim() || '',
          process: cells[10]?.textContent?.trim() || '',
          ct: cells[11]?.textContent?.trim() || '',
          uph: cells[12]?.textContent?.trim() || '',
          plan_count: parseInt(cells[13]?.textContent) || 0,
          produced: parseInt(cells[14]?.textContent) || 0,
          output: parseInt(cells[15]?.textContent) || 0,
          entregadas_main: parseInt(cells[16]?.textContent) || 0,
          status: cells[17]?.textContent?.trim() || 'PLAN',
          tiempo_produccion: cells[18]?.textContent?.trim() || '',
          inicio: cells[19]?.textContent?.trim() || '',
          fin: cells[20]?.textContent?.trim() || '',
          grupo: grupoVisual, // Usar el grupo visual real en lugar del campo de celda
          extra: cells[21]?.textContent?.trim() || '',
          groupIndex: Math.floor(index / 5)
        };

        groupedPlansData.push(planData);
      });
    }

    if (groupedPlansData.length === 0) {
      throw new Error('No hay datos para exportar');
    }

    // Enviar datos al backend
    const response = await fetch('/api/plan/export-excel', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        plans: groupedPlansData
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Error al generar el archivo Excel');
    }

    // Obtener el archivo como blob
    const blob = await response.blob();

    // Crear enlace de descarga
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;

    // Generar nombre del archivo con fecha
    const now = new Date();
    const dateStr = now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') + '_' +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0');
    const filename = `Plan_Produccion_${dateStr}.xlsx`;

    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    // Feedback de oxito
    exportBtn.textContent = '? Excel Descargado';
    exportBtn.style.backgroundColor = '#27ae60';

    setTimeout(() => {
      exportBtn.textContent = originalText;
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 2000);

  } catch (error) {
    // Error al exportar a Excel

    const exportBtn = document.getElementById('export-excel-btn');
    exportBtn.textContent = '? Error al exportar';
    exportBtn.style.backgroundColor = '#e74c3c';

    setTimeout(() => {
      exportBtn.textContent = '?? Exportar Excel';
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 3000);
  }
}

// Inicial
setDefaultDateFilters();
loadPlans();

// Utilidad de depuracion: ver grupos y secuencias actuales
window.debugGroups = function () {
  try {
    const rows = [...document.querySelectorAll('#plan-tableBody tr.plan-row')];
    const perGroup = {};
    rows.forEach(r => { const gi = parseInt(r.dataset.groupIndex) || 0; const lot = r.dataset.lot; (perGroup[gi] = perGroup[gi] || []).push(lot); });
    return { visualGroups: visualGroups.groups.map((g, i) => ({ g: i + 1, lots: g.plans.map(p => p.lot_no) })), domRows: perGroup };
  } catch (e) { console.warn(e); }
}

// Funcion para guardar el orden actual de los grupos
async function saveGroupSequences() {
  const saveBtn = document.getElementById('save-sequences-btn');
  if (!saveBtn) return;

  // Mostrar loading
  saveBtn.textContent = 'Guardando...';
  saveBtn.disabled = true;

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
            const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo Leon (YYYY-MM-DD)
            const [hours, minutes] = startTime.split(':');
            // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
            plannedStart = `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
          }

          // Convertir endTime (HH:MM) a DATETIME para planned_end
          // IMPORTANTE: NO usar toISOString() porque convierte a UTC sumando horas
          let plannedEnd = null;
          if (endTime !== '--') {
            const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo Leon (YYYY-MM-DD)
            const [hours, minutes] = endTime.split(':');
            // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
            plannedEnd = `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
          }

          // Tambion enviar solo la fecha para plan_start_date
          let planStartDate = null;
          if (startTime !== '--') {
            planStartDate = getTodayInNuevoLeon(); // Formato: YYYY-MM-DD en Nuevo Leon
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
      saveBtn.textContent = '? Guardado';
      saveBtn.style.backgroundColor = '#27ae60';

      // Mostrar mensaje de confirmacion
      const message = result.message || 'Secuencias guardadas correctamente';
      showNotification(message, 'success');

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
      const fs = document.getElementById("filter-start")?.value;
      const fe = document.getElementById("filter-end")?.value;
      const key = orderStorageKey(fs, fe);
      localStorage.setItem(key, JSON.stringify(currentOrder));
      // LocalStorage actualizado con el orden guardado

      setTimeout(() => {
        saveBtn.textContent = 'Guardar Orden';
        saveBtn.style.backgroundColor = '#3498db';
        saveBtn.disabled = false;
      }, 2000);
    } else {
      const errorData = await response.json();
      // Error response:
      throw new Error(errorData.error || 'Error al guardar');
    }
  } catch (error) {
    // Error completo al guardar secuencias
    // Stack trace:
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
  const tbody = document.getElementById("plan-tableBody");
  const planRows = tbody.querySelectorAll('.plan-row');

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
  const tbody = document.getElementById("plan-tableBody");
  const planRows = tbody.querySelectorAll('.plan-row');

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

// Configurar event listeners de modales (estos siempre eston en el HTML)
// ========= EVENT LISTENERS DINoMICOS PARA MODALES =========
// NOTA: Los event listeners del modal de Reprogramar ahora eston en event delegation
// Ver seccion "EVENT DELEGATION: CLICK" para los botones reschedule-search-btn y reschedule-submit-btn
// Ver seccion "EVENT DELEGATION: CHANGE" para el checkbox reschedule-select-all

// Los event listeners del modal WO se configuran en setupWorkOrdersModalEvents()
// cuando se crea el modal dinomicamente

/* REMOVIDO - Ahora manejado por event delegation
document.addEventListener('DOMContentLoaded', function() {
  const rescheduleSearchBtn = document.getElementById('reschedule-search-btn');
  if (rescheduleSearchBtn) {
    rescheduleSearchBtn.addEventListener('click', loadPendingPlans);
  }
  
  const rescheduleSelectAll = document.getElementById('reschedule-select-all');
  if (rescheduleSelectAll) {
    rescheduleSelectAll.addEventListener('change', function() {
      toggleAllReschedule(this);
    });
  }
  
  const rescheduleSubmitBtn = document.getElementById('reschedule-submit-btn');
  if (rescheduleSubmitBtn) {
    rescheduleSubmitBtn.addEventListener('click', reschedulePendingPlans);
  }
});
*/

// Funcion para mostrar notificaciones
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
