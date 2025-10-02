// ====== Variables Globales para Planeación ======

// Función helper para obtener fecha en zona horaria de Nuevo León, México (America/Monterrey)
function getTodayInNuevoLeon() {
  // Crear fecha en zona horaria de Monterrey
  const options = { timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit' };
  const formatter = new Intl.DateTimeFormat('en-CA', options); // en-CA da formato YYYY-MM-DD
  return formatter.format(new Date());
}

// Función helper para obtener Date object ajustado a Nuevo León
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

// Variables globales para planeación integrada
let planningData = [];
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

// Datos calculados de planeación por fila
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
  
  // Crear overlay
  const overlay = document.createElement('div');
  overlay.className = 'table-loading-overlay';
  overlay.id = `${containerId}-loading`;
  
  // Crear spinner
  const spinner = document.createElement('div');
  spinner.className = 'loading-spinner';
  
  // Crear texto
  const text = document.createElement('div');
  text.className = 'loading-text';
  text.textContent = message;
  
  // Agregar elementos al overlay
  overlay.appendChild(spinner);
  overlay.appendChild(text);
  
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

// Función para mostrar modal de éxito
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
        <div style="font-size: 48px; color: #28a745; margin-bottom: 15px;">✅</div>
        <h3 style="margin: 0 0 15px 0; color: #28a745;">¡Éxito!</h3>
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

// Función para ocultar modal de éxito
function hideSuccessModal() {
  const modal = document.getElementById('success-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// Agregar estado de carga a un botón
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
// para que funcionen con contenido cargado dinámicamente

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
  ...código movido a handleNewPlanSubmit()...
});
*/

// Prefijar filtros a hoy
function setDefaultDateFilters(){
  const iso = getTodayInNuevoLeon();
  const fs = document.getElementById("filter-start");
  const fe = document.getElementById("filter-end");
  if(fs && !fs.value) fs.value = iso;
  if(fe && !fe.value) fe.value = iso;
}

// Map routing value to turno label
function routingToTurno(v){
  if(v === 1 || v === "1") return "DIA";
  if(v === 2 || v === "2") return "TIEMPO EXTRA";
  if(v === 3 || v === "3") return "NOCHE";
  return "";
}

// Cargar planes
async function loadPlans(){
  try {
    // Mostrar loading en el tbody de la tabla
  showTableBodyLoading('plan-tableBody', 'Cargando planes...', 16);
    
    setDefaultDateFilters();
    const fs = document.getElementById("filter-start")?.value;
    const fe = document.getElementById("filter-end")?.value;
    let url = "/api/plan";
    const params = [];
    if(fs) params.push(`start=${encodeURIComponent(fs)}`);
    if(fe) params.push(`end=${encodeURIComponent(fe)}`);
    if(params.length) url += `?${params.join("&")}`;
    
    let res = await axios.get(url);
    let data = Array.isArray(res.data) ? res.data.slice() : [];
    // Aplicar orden guardado (si existe) antes de renderizar
    data = applySavedOrderToData(data, fs, fe);

    let tbody = document.getElementById("plan-tableBody");
    tbody.innerHTML = "";
    
    data.forEach((r, idx) => {
      let tr = document.createElement("tr");
      tr.dataset.lot = r.lot_no;
      tr.draggable = true;
      tr.innerHTML = `
        <td>${idx+1}</td>
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
        <td>${r.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold;">-</td>
      `;
      tbody.appendChild(tr);
    });

    enableRowDragDrop(tbody, fs, fe);
    // ensureOrderToolbar(fs, fe); // Ya no necesario - usamos save-sequences-btn
  } catch(error) {
    alert("Error al cargar planes: " + (error.response?.data?.error || error.message));
    // En caso de error, limpiar la tabla
    let tbody = document.getElementById("plan-tableBody");
  tbody.innerHTML = `<tr class="message-row"><td colspan="21" style="display: table-cell; text-align: center; padding: 20px; color: #888;">Error al cargar los datos</td></tr>`;
  }
}

// ====== Drag & Drop Reordenamiento ======
function enableRowDragDrop(tbody, fs, fe){
  let dragSrcEl = null;
  tbody.addEventListener('dragstart', (e) => {
    const row = e.target.closest('tr');
    if (!row) return;
    dragSrcEl = row;
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', row.dataset.lot || ''); } catch {}
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
      if (firstCell) firstCell.textContent = String(i+1);
    });
    // Recalcular tiempos automáticamente después del drag
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

function getDragAfterElement(container, y){
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

function orderStorageKey(fs, fe){
  return `plan-order:${fs||''}:${fe||''}`;
}

function saveCurrentOrder(tbody, fs, fe){
  const order = Array.from(tbody.querySelectorAll('tr')).map(tr => tr.dataset.lot).filter(Boolean);
  try {
    localStorage.setItem(orderStorageKey(fs, fe), JSON.stringify(order));
  } catch {}
}

function applySavedOrderToData(data, fs, fe){
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
    return data.slice().sort((a,b) => {
      const ia = indexMap.has(a.lot_no) ? indexMap.get(a.lot_no) : Infinity;
      const ib = indexMap.has(b.lot_no) ? indexMap.get(b.lot_no) : Infinity;
      if (ia === ib) return 0;
      return ia - ib;
    });
  } catch(error) { 

    return data; 
  }
}

function ensureOrderToolbar(fs, fe){
  // Esta función ya no es necesaria porque usamos el botón save-sequences-btn del toolbar principal
  // El botón "💾 Guardar Orden" maneja tanto grupos como secuencias correctamente
}

// Estilos mínimos para drag
(function injectDragStyles(){
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
// Ver initializePlanEventListeners() más abajo
// ============================================================
/*
// CÓDIGO ANTIGUO - Reemplazado por event delegation
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

async function openEditModal(lotNo){
  try {
    // Mostrar modal inmediatamente con loading
    const modal = document.getElementById("plan-editModal");
    const form = document.getElementById("plan-editForm");
    
    modal.style.display = "flex";
    
    // Ocultar el formulario mientras carga
    form.style.display = "none";
    
    showTableLoading('plan-modal-content', 'Cargando datos del plan...');
    
    // Hacer la consulta a la API
    let res = await axios.get("/api/plan");
    let plan = res.data.find(p => p.lot_no === lotNo);
    
    if(!plan) {
      hideTableLoading('plan-modal-content');
      modal.style.display = "none";
      return alert("Plan no encontrado");
    }

    // Llenar el formulario con los datos
    form.lot_no.value = plan.lot_no;
    
    // Set turno based on routing
    const turnoSel = form.elements["turno"];
    if(turnoSel){
      turnoSel.value = routingToTurno(plan.routing) || "DIA";
    }
    
    form.plan_count.value = plan.plan_count;
    form.wo_code.value = plan.wo_code || "";
    form.po_code.value = plan.po_code || "";
    form.line.value = plan.line;

    // Pequeña pausa para mejor UX (mínimo 500ms para que se vea el loading)
    await new Promise(resolve => setTimeout(resolve, 300));

    // Ocultar loading y mostrar formulario con animación suave
    hideTableLoading('plan-modal-content');
    form.style.display = "block";
    form.style.opacity = "0";
    form.style.transform = "translateY(10px)";
    
    // Animación de entrada
    setTimeout(() => {
      form.style.transition = "all 0.3s ease";
      form.style.opacity = "1";
      form.style.transform = "translateY(0)";
    }, 50);
    
  } catch(error) {
    hideTableLoading('plan-modal-content');
    document.getElementById("plan-editModal").style.display = "none";
    alert("Error al cargar datos del plan: " + (error.response?.data?.error || error.message));
  }
}

// Guardar edición
// ========= PLAN EDIT FORM HANDLERS (Ahora manejados por Event Delegation) =========

/**
 * Manejar submit del formulario de edición de plan
 */
async function handleEditPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn?.textContent || 'Guardar';
  
  try {
    // Cambiar el botón a estado de carga
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Actualizando...';
      submitBtn.style.backgroundColor = '#6c757d';
      submitBtn.style.cursor = 'not-allowed';
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
                  setTimeout(() => reject(new Error('Timeout: La petición tardó más de 5 segundos')), 5000);
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
                // Actualizar al menos el part_no aunque falle la búsqueda en RAW
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
    
    // Mostrar modal de éxito
    showSuccessModal(`Plan ${data.lot_no} actualizado exitosamente`);
    
    document.getElementById("plan-editModal").style.display = "none";
    loadPlans();
  } catch(error) {
    console.error('Error en handleEditPlanSubmit:', error);
    alert("Error actualizando plan: " + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar botón
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
 * Manejar cancelación de plan
 */
async function handleCancelPlan() {
  const form = document.getElementById("plan-editForm");
  if (!form) return;
  
  const lot = form.lot_no.value;
  if(!lot) return;
  if(!confirm(`¿Cancelar plan ${lot}?`)) return;
  
  const cancelBtn = document.getElementById("plan-cancelBtn");
  const originalText = cancelBtn?.textContent || 'Cancelar plan';
  
  try {
    // Cambiar el botón a estado de carga
    if (cancelBtn) {
      cancelBtn.disabled = true;
      cancelBtn.innerHTML = 'Cancelando...';
      cancelBtn.style.backgroundColor = '#6c757d';
      cancelBtn.style.cursor = 'not-allowed';
    }
    
    showTableLoading('plan-editModal-content', 'Cancelando plan...');
    
    await axios.post("/api/plan/update", { lot_no: lot, status: "CANCELADO" });
    
    // Mostrar modal de éxito
    showSuccessModal(`Plan ${lot} cancelado exitosamente`);
    
    document.getElementById("plan-editModal").style.display = "none";
    loadPlans();
  } catch(error) {
    alert("Error cancelando plan: " + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar botón
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
 * Manejar submit del formulario de nuevo plan
 */
async function handleNewPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn?.textContent || 'Registrar';
  
  try {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Guardando...';
      submitBtn.style.cursor = 'not-allowed';
    }
    
    await axios.post("/api/plan", data);
    
    // Mostrar modal de éxito
    showSuccessModal('Plan registrado exitosamente');
    
    document.getElementById("plan-modal").style.display = "none";
    form.reset();
    loadPlans();
  } catch(error) {
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

/* REMOVIDO - Ahora manejado por event delegation y handleEditPlanSubmit()
[Código del event listener de plan-editForm submit movido a handleEditPlanSubmit()]
*/

/* REMOVIDO - Ahora manejado por event delegation y handleCancelPlan()
[Código del event listener de plan-cancelBtn movido a handleCancelPlan()]
*/


// ========= WORK ORDERS FUNCTIONALITY =========

// Crear modal de Work Orders dinámicamente
function createWorkOrdersModal() {
  // Verificar si ya existe
  if (document.getElementById('wo-modal')) {
    return;
  }

  const modalHTML = `
    <div id="wo-modal" class="modal-overlay">
      <div class="modal-content" id="wo-modal-content">
        <div class="modal-header">
          <h3>Work Orders - Importar como Planes</h3>
          <button id="wo-closeModalBtn" class="plan-btn modal-close-btn">×</button>
        </div>
        
        <div class="modal-filters">
          <label>Buscar WO/PO:</label>
          <input type="text" id="wo-search-input" class="plan-input" placeholder="Buscar por código WO o PO...">
          
          <label>Fecha Op. Desde:</label>
          <input type="date" id="wo-filter-desde" class="plan-input" title="Filtrar WOs desde esta fecha">
          
          <label>Fecha Op. Hasta:</label>
          <input type="date" id="wo-filter-hasta" class="plan-input" title="Filtrar WOs hasta esta fecha">
          
          <label>Estado:</label>
          <select id="wo-filter-estado" class="plan-input">
            <option value="">Todos</option>
            <option value="CREADA">CREADA</option>
            <option value="PLANIFICADA">PLANIFICADA</option>
            <option value="EN PROGRESO">EN PROGRESO</option>
            <option value="CERRADA">CERRADA</option>
          </select>
          
          <button id="wo-reload-btn" class="plan-btn">Recargar</button>
          <button id="wo-import-selected-btn" class="plan-btn plan-btn-add">Importar Seleccionados</button>
          
          <label>Fecha de Importación:</label>
          <input type="date" id="wo-filter-date" class="plan-input" title="Fecha a la que se importarán los planes seleccionados">
        </div>

        <div class="modal-table-container">
          <table class="modal-table">
            <thead>
              <tr>
                <th>
                  <input type="checkbox" id="wo-select-all">
                </th>
                <th>WO Code</th>
                <th>PO Code</th>
                <th>Modelo</th>
                <th>Cantidad</th>
                <th>Fecha Op.</th>
                <th>Estado</th>
                <th>Modificador</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody id="wo-tableBody"></tbody>
          </table>
        </div>

        <div class="modal-status">
          <span id="wo-status">Seleccione los WOs que desea importar como planes</span>
        </div>
      </div>
    </div>
  `;

  // Insertar el modal en el body
  document.body.insertAdjacentHTML('beforeend', modalHTML);

  // Configurar event listeners después de crear el modal
  setupWorkOrdersModalEvents();
}

// Exponer función globalmente
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

  // Botón de recarga
  const reloadBtn = document.getElementById('wo-reload-btn');
  if (reloadBtn) {
    reloadBtn.addEventListener('click', loadWorkOrders);
  }

  // Input de búsqueda - filtrar en tiempo real
  const searchInput = document.getElementById('wo-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', filterWorkOrdersTable);
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        filterWorkOrdersTable();
      }
    });
  }

  // Checkbox "Seleccionar todos"
  const selectAll = document.getElementById('wo-select-all');
  if (selectAll) {
    selectAll.addEventListener('change', function() {
      toggleAllWOs(this);
    });
  }

  // Botón "Importar Seleccionados"
  const importBtn = document.getElementById('wo-import-selected-btn');
  if (importBtn) {
    importBtn.addEventListener('click', importAllSelectedWOs);
  }

  // Delegación de eventos para botones de importación individual
  const tbody = document.getElementById('wo-tableBody');
  if (tbody) {
    tbody.addEventListener('click', function(e) {
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
    filterDate.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        loadWorkOrders();
      }
    });
  }
  
  if (filterDesde) {
    filterDesde.addEventListener('change', function() {
      loadWorkOrders(); // Recargar automáticamente al cambiar fecha desde
    });
  }
  
  if (filterHasta) {
    filterHasta.addEventListener('change', function() {
      loadWorkOrders(); // Recargar automáticamente al cambiar fecha hasta
    });
  }
  
  if (filterEstado) {
    filterEstado.addEventListener('change', function() {
      loadWorkOrders(); // Recargar automáticamente al cambiar estado
    });
  }

  // Establecer fecha de importación por defecto (hoy en Nuevo León)
  if (filterDate && !filterDate.value) {
    filterDate.value = getTodayInNuevoLeon();
  }
  
  // Establecer rango de fechas por defecto (día actual en Nuevo León)
  if (filterDesde && !filterDesde.value) {
    filterDesde.value = getTodayInNuevoLeon(); // Día actual
  }
  
  if (filterHasta && !filterHasta.value) {
    filterHasta.value = getTodayInNuevoLeon(); // Día actual
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
    
    // Construir URL con parámetros
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
    
    // Limpiar el campo de búsqueda al recargar
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

// Exponer función globalmente
window.loadWorkOrders = loadWorkOrders;

// Variable global para almacenar todos los WOs cargados (para filtrado)
let allWorkOrders = [];

// Función para filtrar WOs en el frontend
function filterWorkOrdersTable() {
  const searchInput = document.getElementById('wo-search-input');
  if (!searchInput) return;
  
  const searchTerm = searchInput.value.toLowerCase().trim();
  
  if (!searchTerm) {
    // Si no hay búsqueda, mostrar todos
    renderWorkOrdersTable(allWorkOrders);
    return;
  }
  
  // Filtrar WOs por código WO, código PO, o modelo
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

// Exponer función globalmente
window.filterWorkOrdersTable = filterWorkOrdersTable;

// Renderizar tabla de Work Orders
function renderWorkOrdersTable(workOrders) {
  // NO sobrescribir allWorkOrders aquí, se maneja en loadWorkOrders
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
    switch(wo.estado) {
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
      row.title = `⚠️ WO ya importada como LOT NO: ${wo.lot_no_existente || 'N/A'}`;
    }
    
    row.innerHTML = `
      <td style="padding:6px; text-align:center;">
        <input type="checkbox" class="wo-checkbox" value="${wo.id}" 
               ${wo.estado === 'CERRADA' || yaImportado ? 'disabled' : ''}>
        ${yaImportado ? '<div style="color:#e74c3c; font-size:9px; font-weight:bold; margin-top:2px;">✓ IMPORTADO</div>' : ''}
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
          `<span style="padding:2px 6px; font-size:9px; background:#555; color:#999; border-radius:3px;">🔒 Bloqueado</span>` :
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
    
    updateWOStatus("Importando Work Order...");
    
    const response = await axios.post("/api/work-orders/import", {
      wo_ids: [woId],
      import_date: importDate
    });
    
    if (response.data.success) {
      const plan = response.data.plans[0];
      alert(`✅ WO importado exitosamente como Plan: ${plan.lot_no}`);
      loadPlans(); // Recargar tabla principal
      loadWorkOrders(); // Recargar WOs
    } else {
      alert("❌ Error en importación: " + (response.data.errors || []).join(", "));
    }
  } catch (error) {
    alert("❌ Error importando WO: " + (error.response?.data?.error || error.message));
  } finally {
    // Restaurar botón
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
  
  const woIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
  
  if (!confirm(`¿Importar ${woIds.length} Work Order(s) como planes para el ${importDate}?`)) {
    return;
  }
  
  try {
    // Mostrar loading en el modal
    showTableLoading('wo-modal-content', `Importando ${woIds.length} Work Orders...`);
    updateWOStatus("Importando work orders...");
    
    // Deshabilitar botón de importar
    setButtonLoading('wo-import-selected-btn', true, 'Importando...');
    
    const response = await axios.post("/api/work-orders/import", {
      wo_ids: woIds,
      import_date: importDate
    });
    
    if (response.data.success) {
      const { imported, errors } = response.data;
      let message = `✅ ${imported} Work Orders importados exitosamente`;
      
      if (errors && errors.length > 0) {
        message += `\n\n⚠️ WOs no importados:\n`;
        errors.forEach((error, index) => {
          message += `${index + 1}. ${error}\n`;
        });
      }
      
      alert(message);
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
    setButtonLoading('wo-import-selected-btn', false, 'Importar Seleccionados');
    updateWOStatus("Listo para importar");
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
    dateFrom.value = getDateInNuevoLeon(-7); // Una semana atrás en Nuevo León
  }
  if (dateTo && !dateTo.value) {
    dateTo.value = getTodayInNuevoLeon(); // Hoy en Nuevo León
  }
  if (newDate && !newDate.value) {
    newDate.value = getTodayInNuevoLeon(); // Hoy en Nuevo León
  }
}

// Exponer función globalmente
window.setDefaultRescheduleDates = setDefaultRescheduleDates;

// Cargar planes pendientes
async function loadPendingPlans() {
  const dateFromInput = document.getElementById("reschedule-date-from");
  const dateToInput = document.getElementById("reschedule-date-to");
  
  if (!dateFromInput || !dateToInput) {
    console.error('❌ Elementos de fecha no encontrados');
    alert("Error: Elementos de fecha no disponibles");
    return;
  }
  
  const dateFrom = dateFromInput.value;
  const dateTo = dateToInput.value;
  
  if (!dateFrom || !dateTo) {
    alert("⚠️ Seleccione el rango de fechas para buscar");
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
    console.error('❌ Error al cargar planes pendientes:', error);
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

// Toggle selección de todos los planes pendientes
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
  
  if (!confirm(`¿Reprogramar ${lotNos.length} plan(es) para la fecha ${newDate}?`)) {
    return;
  }
  
  try {
    updateRescheduleStatus("Reprogramando planes...");
    
    // Enviar solicitud de reprogramación
    const response = await axios.post('/api/plan/reschedule', {
      lot_nos: lotNos,
      new_working_date: newDate
    });
    
    // Mostrar modal de éxito
    showSuccessModal(`${lotNos.length} plan(es) reprogramado(s) exitosamente para ${newDate}`);
    
    // Recargar la lista de pendientes
    loadPendingPlans();
    
    // Recargar planes principales si está en la misma fecha
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
    console.error('❌ Error al reprogramar planes:', error);
    alert("Error al reprogramar planes: " + (error.response?.data?.error || error.message));
    updateRescheduleStatus("Error en reprogramación");
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

// ====== FUNCIONALIDAD DE PLANEACIÓN INTEGRADA ======

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
  
  // Verificar si los datos tienen información de grupos guardada
  const hasGroupData = data.some(plan => plan.group_no != null && plan.sequence != null);
  
  if (hasGroupData) {

    
    // Asignar planes basándose en group_no y sequence de la base de datos
    data.forEach((plan) => {
      if (plan.group_no != null && plan.sequence != null) {
        const groupIndex = plan.group_no - 1; // Convertir de 1-indexed a 0-indexed
        if (groupIndex >= 0 && groupIndex < groupCount) {
          visualGroups.groups[groupIndex].plans.push(plan);
          visualGroups.planAssignments.set(plan.lot_no, groupIndex);
        } else {
          // Si el group_no está fuera del rango actual, asignar al último grupo
          const fallbackGroup = groupCount - 1;
          visualGroups.groups[fallbackGroup].plans.push(plan);
          visualGroups.planAssignments.set(plan.lot_no, fallbackGroup);
        }
      } else {
        // Para planes sin grupo asignado, usar distribución automática
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
        // Asignar automáticamente si no tiene asignación previa
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
      <td colspan="21" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
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
      <td colspan="21" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
        <div class="drop-zone-content">
          ${group.plans.length === 0 ? 'Arrastra planes aquí para asignarlos a este grupo' : ''}
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
        <td>${plan.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold; background-color: #3498db; color: white;">${groupIndex + 1}</td>
        <td class="fecha-inicio-cell">--</td>
      `;
      
      tbody.appendChild(tr);
    });
    
    // Espacio entre grupos
    if (groupIndex < visualGroups.groups.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'group-spacer';
      spacerRow.innerHTML = `<td colspan="21" style="height: 10px; background-color: #2c2c2c;"></td>`;
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
}

// Configurar drag & drop entre grupos y dentro de grupos
function setupGroupDragDrop() {
  const tbody = document.getElementById("plan-tableBody");
  let draggedElement = null;
  let draggedFromGroup = null;
  let dropIndicator = null;
  let isDraggingOverDropZone = false;
  
  // Crear indicador visual de inserción
  function createDropIndicator() {
    const indicator = document.createElement('tr');
    indicator.className = 'drop-indicator';
    indicator.innerHTML = `<td colspan="21" style="height: 3px; background: #3498db; border: none; padding: 0;"></td>`;
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
    
    // Lógica para reordenamiento dentro del grupo
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
      
      // Determinar dónde insertar el indicador
      const rect = targetRow.getBoundingClientRect();
      const midpoint = rect.top + rect.height / 2;
      
      if (e.clientY < midpoint) {
        // Insertar antes de la fila target
        targetRow.parentNode.insertBefore(dropIndicator, targetRow);
      } else {
        // Insertar después de la fila target
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
      
      // Actualizar asignación
      visualGroups.planAssignments.set(lotNo, targetGroupIndex);
      
      // Recargar tabla con nueva asignación
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
      
      dropZoneContent.innerHTML = `✅ Plan ${lotNo.split('-')[2]} movido aquí`;
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

// Función para reordenar planes dentro del mismo grupo
function reorderWithinGroup(draggedRow, targetRow, groupIndex, clientY) {
  const lotNo = draggedRow.dataset.lot;
  const targetLotNo = targetRow.dataset.lot;
  

  
  // Obtener el grupo actual
  const currentGroup = visualGroups.groups[groupIndex];
  if (!currentGroup) {

    return;
  }
  
  // Encontrar índices de los planes
  const draggedIndex = currentGroup.plans.findIndex(plan => plan.lot_no === lotNo);
  const targetIndex = currentGroup.plans.findIndex(plan => plan.lot_no === targetLotNo);
  
  if (draggedIndex === -1 || targetIndex === -1) {

    return;
  }
  

  
  // Determinar la nueva posición basada en la posición del mouse
  const rect = targetRow.getBoundingClientRect();
  const midpoint = rect.top + rect.height / 2;
  let newIndex;
  
  if (clientY < midpoint) {
    // Insertar antes del target
    newIndex = targetIndex;
  } else {
    // Insertar después del target
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
    
    // Filtrar planes que NO están cancelados
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
        
        // Si el break cae durante la producción de este plan
        if (breakStart >= startTime && breakStart < plannedEndTime) {
          breaksDuringPlan += breakDuration;
        }
      });
      
      // Tiempo real de fin (incluyendo breaks)
      const actualEndTime = plannedEndTime + breaksDuringPlan;
      
      // Actualizar cálculos individuales
      planningCalculations.set(plan.lot_no, {
        groupNumber: groupIndex + 1,
        productionTime: productionTime,
        startTime: minutesToTime(startTime),
        endTime: minutesToTime(actualEndTime), // Incluye breaks
        isOvertime: false, // Se calculará después
        totalGroupTime: totalProductiveMinutes + productionTime
      });
      
      currentTime = actualEndTime; // Avanzar al tiempo real (con breaks)
      totalProductiveMinutes += productionTime; // Solo sumar tiempo productivo
    });
    
    // Para planes cancelados, no calcular tiempos pero mantener el registro
    group.plans.filter(plan => plan.status === 'CANCELADO').forEach(plan => {
      planningCalculations.set(plan.lot_no, {
        groupNumber: groupIndex + 1,
        productionTime: 0, // Sin tiempo de producción
        startTime: '--',
        endTime: '--',
        isOvertime: false,
        totalGroupTime: 0,
        isCancelled: true // Marca especial para planes cancelados
      });
    });
    
    // Determinar si el grupo está en overtime (más de 9 horas productivas)
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
  
  // Actualizar filas de planes con cálculos
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

// Actualizar filas de planes con cálculos
function updatePlanRows() {
  const tbody = document.getElementById("plan-tableBody");
  const planRows = tbody.querySelectorAll('.plan-row');
  
  planRows.forEach(row => {
    const lotNo = row.dataset.lot;
    const calc = planningCalculations.get(lotNo);
    
    if (calc) {
      const cells = row.querySelectorAll('td');
      
      // Si el plan está cancelado, mostrar tiempos como -- y marcar como cancelado
      if (calc.isCancelled) {
        if (cells[17]) cells[17].textContent = '--'; // Tiempo Productivo
        if (cells[18]) cells[18].textContent = '--'; // Inicio
        if (cells[19]) cells[19].textContent = '--'; // Fin
        if (cells[20]) cells[20].textContent = calc.groupNumber; // Grupo
        if (cells[21]) cells[21].innerHTML = '<span class="status-cancelled">CANCELADO</span>'; // Turno
        
        // Resaltar fila como cancelada
        row.style.backgroundColor = '#6c6c6c';
        row.style.color = '#ccc';
        row.style.textDecoration = 'line-through';
      } else {
        // Plan activo - mostrar cálculos normales
        if (cells[17]) cells[17].textContent = minutesToTime(calc.productionTime);
        if (cells[18]) cells[18].textContent = calc.startTime;
        if (cells[19]) cells[19].textContent = calc.endTime;
        if (cells[20]) cells[20].textContent = calc.groupNumber;
        
        // Actualizar indicador de tiempo extra en la columna Turno
        if (cells[21]) {
          cells[21].innerHTML = calc.isOvertime ? 
            '<span class="status-extra">EXTRA</span>' : 
            '<span class="status-normal">NORMAL</span>';
        }
        
        // Resaltar fila si está en tiempo extra
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
      
      // NO sobrescribir el status real de la base de datos (cells[16])
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
      <td colspan="21" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
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
      <td colspan="21" style="background-color: #34495e; border: 2px dashed #20688C; text-align: center; padding: 10px; color: #bdc3c7;">
        <div class="drop-zone-content">
          ${group.plans.length === 0 ? 'Arrastra planes aquí para asignarlos a este grupo' : ''}
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
        <td>${plan.status}</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td class="tiempo-cell">--:--</td>
        <td style="text-align:center; font-weight:bold; background-color: #3498db; color: white;">${groupIndex + 1}</td>
        <td class="fecha-inicio-cell">--</td>
      `;
      
      tbody.appendChild(tr);
    });
    
    // Espacio entre grupos
    if (groupIndex < visualGroups.groups.length - 1) {
      const spacerRow = document.createElement('tr');
      spacerRow.className = 'group-spacer';
      spacerRow.innerHTML = `<td colspan="21" style="height: 10px; background-color: #2c2c2c;"></td>`;
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
    
    const planData = {
      lot_no: lotNo,
      wo_code: cells[2]?.textContent?.trim() || '',
      po_code: cells[3]?.textContent?.trim() || '',
      working_date: cells[4]?.textContent?.trim() || '',
      line: cells[5]?.textContent?.trim() || '',
      routing: cells[6]?.textContent?.trim() === 'DIA' ? 1 : 
               cells[6]?.textContent?.trim() === 'TIEMPO EXTRA' ? 2 : 
               cells[6]?.textContent?.trim() === 'NOCHE' ? 3 : 1,
      model_code: cells[7]?.textContent?.trim() || '',
      part_no: cells[8]?.textContent?.trim() || '',
      project: cells[9]?.textContent?.trim() || '',
      process: cells[10]?.textContent?.trim() || 'MAIN',
      ct: cells[11]?.textContent?.trim() || '0',
      uph: parseInt(cells[12]?.textContent?.trim()) || 0,
      plan_count: parseInt(cells[13]?.textContent?.trim()) || 0,
      produced: parseInt(cells[14]?.textContent?.trim()) || 0,
      status: cells[15]?.textContent?.trim() || 'PLAN'
    };
    
    // Validar que los datos esenciales existan
    if (planData.lot_no && planData.part_no) {
      currentData.push(planData);
    }
  });
  

  
  // Re-renderizar con datos actuales
  renderTableWithVisualGroups(currentData);
  
  // Actualizar fechas de inicio después del renderizado
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

// Agrupar planes en N grupos según la selección
function groupPlansIntoNGroups(plans, groupCount) {
  const groups = [];
  for (let i = 0; i < groupCount; i++) {
    groups.push([]);
  }
  
  // Distribuir planes por líneas en grupos
  const lineGroups = {};
  plans.forEach(plan => {
    const line = plan.line;
    if (!lineGroups[line]) lineGroups[line] = [];
    lineGroups[line].push(plan);
  });
  
  // Asignar líneas a grupos de manera balanceada
  const lines = Object.keys(lineGroups);
  lines.forEach((line, index) => {
    const groupIndex = index % groupCount;
    groups[groupIndex] = groups[groupIndex].concat(lineGroups[line]);
  });
  
  return groups;
}

// Calcular tiempos de planeación para cada fila
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
      
      // Calcular si está en tiempo extra (termina después de 17:30)
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

// Auto acomodo de planes por optimización distribuida
function autoArrangePlans() {
  console.log('🚀 Función autoArrangePlans ejecutándose...');
  const tbody = document.getElementById('plan-tableBody');
  const planRows = Array.from(tbody.querySelectorAll('.plan-row'));
  
  if (planRows.length === 0) {
    // Feedback visual en lugar de alert
    const autoBtn = document.getElementById('auto-arrange-btn');
    const originalText = autoBtn.textContent;
    autoBtn.textContent = '⚠️ Sin planes';
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
      status: cells[15]?.textContent?.trim() || 'PLAN'
    };
  });
  
  // Agrupar planes por línea primero
  const lineGroups = {};
  plans.forEach(plan => {
    if (!lineGroups[plan.line]) {
      lineGroups[plan.line] = [];
    }
    lineGroups[plan.line].push(plan);
  });
  
  // Ordenar planes dentro de cada línea por tiempo de producción (menor a mayor)
  Object.keys(lineGroups).forEach(line => {
    lineGroups[line].sort((a, b) => a.productionTime - b.productionTime);
  });
  
  // Distribuir manteniendo líneas juntas y evitando tiempo extra
  const groupCount = parseInt(document.getElementById('groups-count').value) || 6;
  visualGroups.planAssignments.clear();
  
  // Algoritmo mejorado que prioriza mantener líneas juntas y evitar tiempo extra
  const productiveMinutes = (currentConfig.productiveHours || 9) * 60; // 9 horas productivas = 540 min
  const groupTimes = new Array(groupCount).fill(0);
  const groupLines = new Array(groupCount).fill().map(() => new Map()); // Líneas y sus tiempos por grupo
  
  // Auto-acomodo iniciado
  
  // Ordenar líneas por tiempo total (líneas más pesadas primero para mejor distribución)
  const sortedLines = Object.keys(lineGroups).sort((a, b) => {
    const timeA = lineGroups[a].reduce((sum, plan) => sum + plan.productionTime, 0);
    const timeB = lineGroups[b].reduce((sum, plan) => sum + plan.productionTime, 0);
    return timeB - timeA; // Mayor a menor
  });
  
  // Procesar línea por línea manteniendo planes juntos
  sortedLines.forEach(line => {
    const linePlans = lineGroups[line];
    const totalLineTime = linePlans.reduce((sum, plan) => sum + plan.productionTime, 0);
    

    
    // Buscar el mejor grupo para toda la línea
    let bestGroupIndex = 0;
    let bestScore = Infinity;
    
    for (let i = 0; i < groupCount; i++) {
      const currentGroupTime = groupTimes[i];
      const newTime = currentGroupTime + totalLineTime;
      
      // Bonus si ya hay planes de la misma línea (mantener líneas juntas)
      const lineBonus = groupLines[i].has(line) ? -100 : 0;
      
      // Penalty severo por tiempo extra
      let overtimePenalty = 0;
      if (newTime > productiveMinutes) {
        overtimePenalty = (newTime - productiveMinutes) * 3; // 3x penalty por overtime
      }
      
      // Bonus por balance (preferir grupos con menos tiempo)
      const balanceBonus = -currentGroupTime * 0.1;
      
      // Calcular puntuación final (menor es mejor)
      const score = newTime + overtimePenalty + lineBonus + balanceBonus;
      

      
      if (score < bestScore) {
        bestScore = score;
        bestGroupIndex = i;
      }
    }
    
    // Asignar todos los planes de la línea al mejor grupo
    linePlans.forEach(plan => {
      visualGroups.planAssignments.set(plan.lot_no, bestGroupIndex);
    });
    
    // Actualizar estadísticas del grupo
    groupTimes[bestGroupIndex] += totalLineTime;
    if (!groupLines[bestGroupIndex].has(line)) {
      groupLines[bestGroupIndex].set(line, 0);
    }
    groupLines[bestGroupIndex].set(line, groupLines[bestGroupIndex].get(line) + totalLineTime);
    

  });
  
  // Mostrar reporte de distribución
  const groupsWithOvertime = groupTimes.filter(time => time > productiveMinutes).length;
  const totalTime = groupTimes.reduce((sum, time) => sum + time, 0);
  const avgTimePerGroup = totalTime / groupCount;
  
  // Resultado del auto-acomodo
  
  // Re-renderizar tabla con nueva distribución
  renderTableWithVisualGroups(plans);
  
  // Recalcular tiempos después de la redistribución
  calculateGroupTimes();
  
  // Feedback visual mejorado
  const autoBtn = document.getElementById('auto-arrange-btn');
  const originalText = autoBtn.textContent;
  
  if (groupsWithOvertime === 0) {
    autoBtn.textContent = '✅ Sin Tiempo Extra';
    autoBtn.style.backgroundColor = '#27ae60';
  } else {
    autoBtn.textContent = `⚠️ ${groupsWithOvertime} con Extra`;
    autoBtn.style.backgroundColor = '#f39c12';
  }
  
  setTimeout(() => {
    autoBtn.textContent = originalText;
    autoBtn.style.backgroundColor = '#27ae60'; // Verde original
  }, 3000);
}

// Exponer función globalmente
window.autoArrangePlans = autoArrangePlans;

// Exponer funciones de reprogramación globalmente
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
  
  // Actualizar filas con nueva información
  rows.forEach((row, index) => {
    const lotNo = row.dataset.lot;
    const calc = planningCalculations.get(lotNo);
    
    if (calc) {
      // Agregar celdas de planeación si no existen
      let cells = row.querySelectorAll('td');
      
      // Tiempo de producción
      if (cells.length >= 17) {
        cells[16].textContent = minutesToTime(calc.productionTime);
        cells[16].className = 'tiempo-cell';
      } else {
        const timeCell = document.createElement('td');
        timeCell.textContent = minutesToTime(calc.productionTime);
        timeCell.className = 'tiempo-cell';
        row.appendChild(timeCell);
      }
      
      // Hora inicio
      if (cells.length >= 18) {
        cells[17].textContent = calc.startTime;
        cells[17].className = 'tiempo-cell';
      } else {
        const startCell = document.createElement('td');
        startCell.textContent = calc.startTime;
        startCell.className = 'tiempo-cell';
        row.appendChild(startCell);
      }
      
      // Hora fin
      if (cells.length >= 19) {
        cells[18].textContent = calc.endTime;
        cells[18].className = 'tiempo-cell';
      } else {
        const endCell = document.createElement('td');
        endCell.textContent = calc.endTime;
        endCell.className = 'tiempo-cell';
        row.appendChild(endCell);
      }
      
      // Número de grupo
      if (cells.length >= 20) {
        cells[19].textContent = calc.groupNumber;
        cells[19].style.textAlign = 'center';
        cells[19].style.fontWeight = 'bold';
      } else {
        const groupCell = document.createElement('td');
        groupCell.textContent = calc.groupNumber;
        groupCell.style.textAlign = 'center';
        groupCell.style.fontWeight = 'bold';
        row.appendChild(groupCell);
      }
      
      // Indicador de tiempo extra en la última columna (Turno)
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
      
      // Resaltar fila si está en tiempo extra
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

// Función de inicialización de event listeners usando event delegation
function initializePlanEventListeners() {
  console.log('🔧 Inicializando event listeners de plan con event delegation...');
  
  // Usar event delegation en document.body para capturar clicks incluso en contenido dinámico
  if (!document.body.dataset.planListenersAttached) {
    document.body.addEventListener('click', function(e) {
      const target = e.target;
      
      // ========== BOTONES DE MODALES ==========
      
      // Abrir modal Nuevo Plan
      if (target.id === 'plan-openModalBtn' || target.closest('#plan-openModalBtn')) {
        e.preventDefault();
        console.log('🎯 Click en plan-openModalBtn detectado');
        const modal = document.getElementById('plan-modal');
        if (modal) modal.style.display = 'flex';
        return;
      }
      
      // Cerrar modal Nuevo Plan
      if (target.id === 'plan-closeModalBtn' || target.closest('#plan-closeModalBtn')) {
        e.preventDefault();
        console.log('🎯 Click en plan-closeModalBtn detectado');
        const modal = document.getElementById('plan-modal');
        if (modal) modal.style.display = 'none';
        return;
      }
      
      // Abrir modal Work Orders
      if (target.id === 'wo-openModalBtn' || target.closest('#wo-openModalBtn')) {
        e.preventDefault();
        console.log('🎯 Click en wo-openModalBtn detectado');
        if (typeof createWorkOrdersModal === 'function') createWorkOrdersModal();
        const modal = document.getElementById('wo-modal');
        if (modal) {
          modal.style.display = 'flex';
          if (typeof loadWorkOrders === 'function') loadWorkOrders();
        }
        return;
      }
      
      // Abrir modal Reprogramar
      if (target.id === 'reschedule-openModalBtn' || target.closest('#reschedule-openModalBtn')) {
        e.preventDefault();
        console.log('🎯 Click en reschedule-openModalBtn detectado');
        const modal = document.getElementById('reschedule-modal');
        if (modal) {
          modal.style.display = 'flex';
          if (typeof setDefaultRescheduleDates === 'function') setDefaultRescheduleDates();
        }
        return;
      }
      
      // Cerrar modal Reprogramar
      if (target.id === 'reschedule-closeModalBtn' || target.closest('#reschedule-closeModalBtn')) {
        e.preventDefault();
        console.log('🎯 Click en reschedule-closeModalBtn detectado');
        const modal = document.getElementById('reschedule-modal');
        if (modal) modal.style.display = 'none';
        return;
      }
      
      // Botón Buscar Pendientes del modal Reprogramar
      if (target.id === 'reschedule-search-btn' || target.closest('#reschedule-search-btn')) {
        e.preventDefault();
        console.log('🎯 Click en reschedule-search-btn detectado');
        if (typeof loadPendingPlans === 'function') loadPendingPlans();
        return;
      }
      
      // Botón Reprogramar Seleccionados
      if (target.id === 'reschedule-submit-btn' || target.closest('#reschedule-submit-btn')) {
        e.preventDefault();
        console.log('🎯 Click en reschedule-submit-btn detectado');
        if (typeof reschedulePendingPlans === 'function') reschedulePendingPlans();
        return;
      }
      
      // ========== MODAL DE EDICIÓN ==========
      
      // Botón Cerrar modal Editar (el botón "Cerrar" dentro del form)
      if (target.closest('#plan-editForm button[type="button"]') && 
          target.textContent.includes('Cerrar')) {
        e.preventDefault();
        console.log('🎯 Click en cerrar modal de edición detectado');
        const modal = document.getElementById('plan-editModal');
        if (modal) modal.style.display = 'none';
        return;
      }
      
      // Botón Cancelar Plan (botón rojo)
      if (target.id === 'plan-cancelBtn' || target.closest('#plan-cancelBtn')) {
        e.preventDefault();
        console.log('🎯 Click en plan-cancelBtn detectado');
        if (typeof handleCancelPlan === 'function') handleCancelPlan();
        return;
      }
      
      // ========== BOTONES DE ACCIONES ==========
      
      // Auto acomodo
      if (target.id === 'auto-arrange-btn' || target.closest('#auto-arrange-btn')) {
        e.preventDefault();
        console.log('🎯 Click en auto-arrange-btn detectado');
        autoArrangePlans();
        return;
      }
      
      // Exportar a Excel
      if (target.id === 'export-excel-btn' || target.closest('#export-excel-btn')) {
        e.preventDefault();
        console.log('🎯 Click en export-excel-btn detectado');
        exportarExcel();
        return;
      }
      
      // Guardar secuencias
      if (target.id === 'save-sequences-btn' || target.closest('#save-sequences-btn')) {
        e.preventDefault();
        console.log('🎯 Click en save-sequences-btn detectado');
        saveGroupSequences();
        return;
      }
      
      // Calcular tiempos
      if (target.id === 'calc-times-btn' || target.closest('#calc-times-btn')) {
        e.preventDefault();
        console.log('🎯 Click en calc-times-btn detectado');
        reloadTableWithCurrentData();
        return;
      }
    });
    
    // ========== EVENT LISTENERS DE SUBMIT ==========
    
    // Listener para submit del formulario de edición
    document.body.addEventListener('submit', function(e) {
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
        console.log('🎯 Submit de plan-form detectado');
        if (typeof window.handleNewPlanSubmit === 'function') {
          window.handleNewPlanSubmit(e.target);
        }
        return;
      }
    });
    
    // Listener para cambio en número de grupos
    document.body.addEventListener('change', function(e) {
      const target = e.target;
      
      // Selector de número de grupos
      if (target.id === 'groups-count') {
        console.log('🎯 Cambio en groups-count detectado');
        reloadTableWithCurrentData();
        return;
      }
      
      // Checkbox "Seleccionar todos" del modal Reprogramar
      if (target.id === 'reschedule-select-all') {
        console.log('🎯 Change en reschedule-select-all detectado');
        if (typeof toggleAllReschedule === 'function') toggleAllReschedule(target);
        return;
      }
    });
    
    // ========== EVENT LISTENER DE DOBLE CLICK ==========
    // Doble click en filas de la tabla para editar
    document.body.addEventListener('dblclick', function(e) {
      console.log('🎯 Doble click detectado en:', e.target);
      
      // Verificar si el doble click fue en una fila de la tabla de planes
      const row = e.target.closest('tr.plan-row');
      if (!row) {
        console.log('❌ No es una fila de plan');
        return;
      }
      
      const lotNo = row.dataset.lot;
      console.log('✅ Fila de plan detectada, lot_no:', lotNo);
      
      if (lotNo && typeof openEditModal === 'function') {
        console.log('🔧 Abriendo modal de edición para lot_no:', lotNo);
        openEditModal(lotNo);
      } else {
        console.error('⚠️ No se pudo abrir modal:', { lotNo, openEditModal: typeof openEditModal });
      }
    });
    
    document.body.dataset.planListenersAttached = 'true';
    console.log('✅ Event delegation configurado en document.body');
  }
  
  console.log('✅ Inicialización de event listeners completada');
}

// Event listeners para nuevos controles
document.addEventListener('DOMContentLoaded', initializePlanEventListeners);

// Exponer la función globalmente para que pueda ser llamada después de cargar contenido dinámico
window.initializePlanEventListeners = initializePlanEventListeners;

// También ejecutar inmediatamente si el DOM ya está listo (para scripts defer)
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  initializePlanEventListeners();
}

// Modificar loadPlans para usar grupos visuales
const originalLoadPlans = loadPlans;
loadPlans = async function() {
  try {
    // Mostrar loading en el tbody de la tabla
    showTableBodyLoading('plan-tableBody', 'Cargando planes...', 21);
    
    setDefaultDateFilters();
    const fs = document.getElementById("filter-start")?.value;
    const fe = document.getElementById("filter-end")?.value;
    let url = "/api/plan";
    const params = [];
    if(fs) params.push(`start=${encodeURIComponent(fs)}`);
    if(fe) params.push(`end=${encodeURIComponent(fe)}`);
    if(params.length) url += `?${params.join("&")}`;
    
    let res = await axios.get(url);
    let data = Array.isArray(res.data) ? res.data.slice() : [];
    
    // Aplicar orden guardado (si existe) antes de renderizar
    data = applySavedOrderToData(data, fs, fe);

    // Usar nueva función de renderizado con grupos visuales
    renderTableWithVisualGroups(data);
    
    // ensureOrderToolbar(fs, fe); // Ya no necesario - usamos save-sequences-btn
  } catch(error) {
    alert("Error al cargar planes: " + (error.response?.data?.error || error.message));
    // En caso de error, limpiar la tabla
    let tbody = document.getElementById("plan-tableBody");
    tbody.innerHTML = `<tr class="message-row"><td colspan="21" style="display: table-cell; text-align: center; padding: 20px; color: #888;">Error al cargar los datos</td></tr>`;
  }
};

// Función para exportar a Excel
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
        // Añadir marcador de grupo
        groupedPlansData.push({
          isGroupHeader: true,
          groupTitle: group.title || `GRUPO ${groupIndex + 1}`,
          groupIndex: groupIndex
        });
        
        // Añadir todos los planes del grupo en orden de secuencia
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
    
    // Si no hay grupos visuales definidos, usar el método anterior como fallback
    if (groupedPlansData.length === 0) {
      const tbody = document.getElementById('plan-tableBody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      
      rows.forEach((row, index) => {
        // Saltar filas de separadores de grupos
        if (row.classList.contains('group-spacer')) {
          // Agregar marcador de grupo
          const groupTitle = row.textContent?.trim() || `GRUPO ${Math.floor(index/5) + 1}`;
          groupedPlansData.push({
            isGroupHeader: true,
            groupTitle: groupTitle,
            groupIndex: Math.floor(index/5)
          });
          return;
        }
        
        const cells = row.querySelectorAll('td');
        if (cells.length === 0) return;
        
        // Obtener lot_no para determinar el grupo visual
        const lot_no = cells[1]?.textContent?.trim() || '';
        
        // Determinar el grupo visual basado en la posición en visualGroups
        let grupoVisual = `GRUPO ${Math.floor(index/5) + 1}`;
        if (lot_no && visualGroups.planAssignments.has(lot_no)) {
          const groupIndex = visualGroups.planAssignments.get(lot_no);
          if (visualGroups.groups[groupIndex]) {
            grupoVisual = visualGroups.groups[groupIndex].title || `GRUPO ${groupIndex + 1}`;
          }
        }
        
        // Si no se encuentra en visualGroups, buscar por la sección del DOM
        if (!grupoVisual || grupoVisual.includes('undefined')) {
          // Buscar hacia atrás para encontrar el separador de grupo más cercano
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
          status: cells[15]?.textContent?.trim() || 'PLAN',
          tiempo_produccion: cells[16]?.textContent?.trim() || '',
          inicio: cells[17]?.textContent?.trim() || '',
          fin: cells[18]?.textContent?.trim() || '',
          grupo: grupoVisual, // Usar el grupo visual real en lugar del campo de celda
          extra: cells[20]?.textContent?.trim() || '',
          groupIndex: Math.floor(index/5)
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
    
    // Feedback de éxito
    exportBtn.textContent = '✅ Excel Descargado';
    exportBtn.style.backgroundColor = '#27ae60';
    
    setTimeout(() => {
      exportBtn.textContent = originalText;
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 2000);
    
  } catch (error) {
    // Error al exportar a Excel
    
    const exportBtn = document.getElementById('export-excel-btn');
    exportBtn.textContent = '❌ Error al exportar';
    exportBtn.style.backgroundColor = '#e74c3c';
    
    setTimeout(() => {
      exportBtn.textContent = '📊 Exportar Excel';
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 3000);
  }
}

// Inicial
setDefaultDateFilters();
loadPlans();

// Utilidad de depuración: ver grupos y secuencias actuales
window.debugGroups = function(){
  try {
    console.log('visualGroups:', visualGroups.groups.map((g,i)=>({g:i+1, lots:g.plans.map(p=>p.lot_no)})));
    const rows = [...document.querySelectorAll('#plan-tableBody tr.plan-row')];
    const perGroup = {};
    rows.forEach(r=>{ const gi=parseInt(r.dataset.groupIndex)||0; const lot=r.dataset.lot; (perGroup[gi]=perGroup[gi]||[]).push(lot); });
    console.log('DOM rows by group:', perGroup);
  } catch (e) { console.warn(e); }
}

// Función para guardar el orden actual de los grupos
async function saveGroupSequences() {
  const saveBtn = document.getElementById('save-sequences-btn');
  if (!saveBtn) return;
  
  // Mostrar loading
  saveBtn.textContent = 'Guardando...';
  saveBtn.disabled = true;
  
  try {
    const sequenceData = [];
    
    // Verificar que visualGroups esté disponible
    if (!visualGroups || !visualGroups.groups) {
      throw new Error('No hay grupos de planeación disponibles');
    }
    
    // Recopilar datos de secuencia para cada plan (solo planes activos)
    visualGroups.groups.forEach((group, groupIndex) => {
      if (group && group.plans && Array.isArray(group.plans)) {
        // Filtrar planes que NO están cancelados
        const activePlans = group.plans.filter(plan => plan && plan.lot_no && plan.status !== 'CANCELADO');
        
        activePlans.forEach((plan, planIndex) => {
          const startTime = planningCalculations.get(plan.lot_no)?.startTime || '--';
          const endTime = planningCalculations.get(plan.lot_no)?.endTime || '--';
          const productionTime = planningCalculations.get(plan.lot_no)?.productionTime || 0;
          
          // Convertir startTime (HH:MM) a DATETIME para planned_start
          let plannedStart = null;
          if (startTime !== '--') {
            const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo León
            const [year, month, day] = todayStr.split('-').map(Number);
            const [hours, minutes] = startTime.split(':').map(Number);
            const dateTime = new Date(year, month - 1, day, hours, minutes, 0);
            plannedStart = dateTime.toISOString().slice(0, 19).replace('T', ' '); // Formato: YYYY-MM-DD HH:MM:SS
          }
          
          // Convertir endTime (HH:MM) a DATETIME para planned_end
          let plannedEnd = null;
          if (endTime !== '--') {
            const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo León
            const [year, month, day] = todayStr.split('-').map(Number);
            const [hours, minutes] = endTime.split(':').map(Number);
            const dateTime = new Date(year, month - 1, day, hours, minutes, 0);
            plannedEnd = dateTime.toISOString().slice(0, 19).replace('T', ' '); // Formato: YYYY-MM-DD HH:MM:SS
          }
          
          // También enviar solo la fecha para plan_start_date
          let planStartDate = null;
          if (startTime !== '--') {
            planStartDate = getTodayInNuevoLeon(); // Formato: YYYY-MM-DD en Nuevo León
          }
          
          // Calcular effective_minutes (tiempo productivo sin breaks)
          const effectiveMinutes = productionTime; // productionTime ya está en minutos
          
          // Calcular breaks_minutes (estimar breaks que caen durante la producción)
          let breaksMinutes = 0;
          if (startTime !== '--' && endTime !== '--') {
            const startMinutes = timeToMinutes(startTime);
            const endMinutes = timeToMinutes(endTime);
            
            // Verificar breaks que caen durante este plan
            currentConfig.breaks.forEach(breakInfo => {
              const breakStart = timeToMinutes(breakInfo.start);
              const breakEnd = timeToMinutes(breakInfo.end);
              const breakDuration = breakEnd - breakStart;
              
              // Si el break cae durante la producción de este plan
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
      saveBtn.textContent = '✅ Guardado';
      saveBtn.style.backgroundColor = '#27ae60';
      
      // Mostrar mensaje de confirmación
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
    saveBtn.textContent = '❌ Error';
    saveBtn.style.backgroundColor = '#e74c3c';
    
    // Mostrar mensaje de error más detallado
    const errorMessage = error.message || 'Error desconocido al guardar';
    showNotification('Error al guardar: ' + errorMessage, 'error');
    
    setTimeout(() => {
      saveBtn.textContent = '💾 Guardar Orden';
      saveBtn.style.backgroundColor = '#3498db';
      saveBtn.disabled = false;
    }, 3000);
  }
}

// Exponer función globalmente
window.saveGroupSequences = saveGroupSequences;

// Función para actualizar las secuencias en tiempo real cuando se mueven planes
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
        
        // Agregar animación sutil para indicar cambio
        sequenceCell.style.transition = 'background-color 0.3s ease';
        sequenceCell.style.backgroundColor = '#27ae60';
        
        setTimeout(() => {
          sequenceCell.style.backgroundColor = '#e74c3c';
        }, 200);
      }
    });
  });
}

// Función para recalcular fechas de inicio después de mover planes
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
      
      // Actualizar fecha de inicio en los cálculos
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

// Configurar event listeners de modales (estos siempre están en el HTML)
// ========= EVENT LISTENERS DINÁMICOS PARA MODALES =========
// NOTA: Los event listeners del modal de Reprogramar ahora están en event delegation
// Ver sección "EVENT DELEGATION: CLICK" para los botones reschedule-search-btn y reschedule-submit-btn
// Ver sección "EVENT DELEGATION: CHANGE" para el checkbox reschedule-select-all

// Los event listeners del modal WO se configuran en setupWorkOrdersModalEvents()
// cuando se crea el modal dinámicamente

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

// Función para mostrar notificaciones
function showNotification(message, type = 'info') {
  // Remover notificación existente si la hay
  const existingNotification = document.querySelector('.notification');
  if (existingNotification) {
    existingNotification.remove();
  }
  
  // Crear nueva notificación
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
  
  // Establecer color según el tipo
  if (type === 'success') {
    notification.style.backgroundColor = '#27ae60';
  } else if (type === 'error') {
    notification.style.backgroundColor = '#e74c3c';
  } else {
    notification.style.backgroundColor = '#3498db';
  }
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  // Remover después de 4 segundos
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 4000);
}