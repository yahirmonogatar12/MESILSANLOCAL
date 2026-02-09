// ====== Plan SMT - Vista Simple por Filas ======

// Mapeo de lineas: Frontend <-> MySQL
const LINE_MAP_SMT = {
  'SA': 'SMT A',
  'SB': 'SMT B',
  'SC': 'SMT C',
  'SD': 'SMT D',
  'SE': 'SMT E'
};

const LINE_MAP_REVERSE_SMT = {
  'SMT A': 'SA',
  'SMT B': 'SB',
  'SMT C': 'SC',
  'SMT D': 'SD',
  'SMT E': 'SE'
};

// Convertir codigo DB a nombre visible
function lineToDisplaySMT(dbCode) {
  return LINE_MAP_SMT[dbCode] || dbCode;
}

// Convertir nombre visible a codigo DB
function lineToDbSMT(displayName) {
  return LINE_MAP_REVERSE_SMT[displayName] || displayName;
}

// Variables globales
let planningDataSMT = [];
let currentConfigSMT = {
  breaks: [
    { start: '09:30', end: '09:45', name: 'Break 1' },
    { start: '12:00', end: '12:30', name: 'Almuerzo' },
    { start: '15:00', end: '15:15', name: 'Break 2' }
  ],
  shiftStart: '07:30',
  shiftEnd: '17:30',
  productiveHours: 9
};

// Helper para fecha en zona horaria Monterrey
function getTodaySMT() {
  const options = { timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit' };
  const formatter = new Intl.DateTimeFormat('en-CA', options);
  return formatter.format(new Date());
}

// ====== Cargar Planes SMT ======
async function loadPlansSMT() {
  try {
    showLoadingSMT();
    
    setDefaultDateFilterSMT();
    const filterStart = document.getElementById('smt-filter-start')?.value;
    
    let url = '/api/plan-smt';
    if (filterStart) {
      url += `?start=${encodeURIComponent(filterStart)}`;
    }
    
    const response = await axios.get(url);
    planningDataSMT = Array.isArray(response.data) ? response.data : [];
    
    renderTableSMT(planningDataSMT);
  } catch (error) {
    console.error('Error cargando planes SMT:', error);
    showErrorSMT('Error al cargar los datos');
  }
}

function setDefaultDateFilterSMT() {
  const filterStart = document.getElementById('smt-filter-start');
  if (filterStart && !filterStart.value) {
    filterStart.value = getTodaySMT();
  }
}

// ====== Renderizar Tabla Simple ======
function renderTableSMT(plans) {
  const tbody = document.getElementById('smt-plan-tableBody');
  if (!tbody) return;
  
  if (!plans || plans.length === 0) {
    tbody.innerHTML = `
      <tr class="message-row">
        <td colspan="20" style="display: table-cell; text-align: center; padding: 40px; color: #888;">
          No hay planes para mostrar
        </td>
      </tr>`;
    return;
  }
  
  // Agrupar por linea
  const lineOrder = ['SA', 'SB', 'SC', 'SD', 'SE'];
  const grouped = {};
  
  plans.forEach(plan => {
    const line = plan.line || 'SIN LINEA';
    if (!grouped[line]) grouped[line] = [];
    grouped[line].push(plan);
  });
  
  // Ordenar cada grupo por sequence
  Object.values(grouped).forEach(group => {
    group.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  });
  
  // Ordenar lineas: primero las conocidas, luego las demas
  const sortedLines = Object.keys(grouped).sort((a, b) => {
    const ia = lineOrder.indexOf(a);
    const ib = lineOrder.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });
  
  // Color uniforme para todas las lineas
  const lineColor = '#16a085';
  
  let html = '';
  let globalSeq = 0;
  
  sortedLines.forEach(lineCode => {
    const linePlans = grouped[lineCode];
    const displayName = lineToDisplaySMT(lineCode);
    const color = lineColor;
    const totalPlan = linePlans.reduce((s, p) => s + (parseInt(p.plan_count) || 0), 0);
    const totalOutput = linePlans.reduce((s, p) => s + (parseInt(p.output) || 0), 0);
    
    // Header de grupo
    html += `
      <tr class="line-group-header">
        <td colspan="99" style="background-color: #2c3e50; color: #ecf0f1; font-weight: bold; text-align: center; padding: 8px; border: 2px solid #20688C;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: white;">${displayName}</span>
            <div>
              <span style="margin-right: 10px; color: #ccc; font-size: 12px;">${linePlans.length} plan${linePlans.length !== 1 ? 'es' : ''} &nbsp;|&nbsp; Plan: ${totalPlan.toLocaleString()} &nbsp;|&nbsp; Output: ${totalOutput.toLocaleString()}</span>
            </div>
          </div>
        </td>
      </tr>
    `;
    
    // Calcular tiempos por grupo
    let currentTime = parseTimeSMT(currentConfigSMT.shiftStart);
    let lineSeq = 0;
    
    linePlans.forEach(plan => {
      globalSeq++;
      lineSeq++;
      const uph = parseInt(plan.uph) || 100;
      const planCount = parseInt(plan.plan_count) || 0;
      const effectiveMinutes = Math.ceil((planCount / uph) * 60);
      
      const startTime = formatTimeSMT(currentTime);
      let endMinutes = currentTime + effectiveMinutes;
      
      // Ajustar por breaks
      currentConfigSMT.breaks.forEach(brk => {
        const breakStart = parseTimeSMT(brk.start);
        const breakEnd = parseTimeSMT(brk.end);
        if (currentTime < breakEnd && endMinutes > breakStart) {
          endMinutes += (breakEnd - breakStart);
        }
      });
      
      const endTime = formatTimeSMT(endMinutes);
      const timeFormatted = formatDurationSMT(effectiveMinutes);
      currentTime = endMinutes;
      
      const statusClass = getStatusClassSMT(plan.status);
      const isOvertime = endMinutes > parseTimeSMT(currentConfigSMT.shiftEnd);
      
      html += `
        <tr class="plan-row ${statusClass}" draggable="true" data-id="${plan.id}" data-lot="${plan.lot_no}" data-line="${lineCode}" data-seq="${lineSeq}" style="border-left: 4px solid ${color}; cursor: grab; ${isOvertime ? 'background-color: rgba(231, 76, 60, 0.2);' : ''}">
          <td style="display: none;" class="reschedule-col"><input type="checkbox" class="plan-checkbox-smt" data-plan-id="${plan.id}" style="cursor:pointer;"></td>
          <td>${lineSeq}</td>
          <td>${plan.lot_no || ''}</td>
          <td>${plan.wo_code || ''}</td>
          <td>${plan.po_code || ''}</td>
          <td>${formatDateSMT(plan.working_date)}</td>
          <td style="color: ${color}; font-weight: bold;">${displayName}</td>
          <td>${plan.shift || 'DIA'}</td>
          <td>${plan.model_code || ''}</td>
          <td>${plan.part_no || ''}</td>
          <td>${plan.process || ''}</td>
          <td>${plan.ct || 0}</td>
          <td>${plan.uph || 0}</td>
          <td>${plan.plan_count || 0}</td>
          <td>${plan.produced_count || 0}</td>
          <td><span class="status-badge ${statusClass}">${plan.status || 'PLAN'}</span></td>
          <td>${plan.shift || 'DIA'}</td>
        </tr>
      `;
    });
  });
  
  tbody.innerHTML = html;
  initDragDropSMT();
}

// ====== Drag & Drop ======
let draggedRowSMT = null;

function initDragDropSMT() {
  const tbody = document.getElementById('smt-plan-tableBody');
  if (!tbody) return;
  
  tbody.querySelectorAll('tr.plan-row[draggable]').forEach(row => {
    row.addEventListener('dragstart', handleDragStartSMT);
    row.addEventListener('dragend', handleDragEndSMT);
    row.addEventListener('dragover', handleDragOverSMT);
    row.addEventListener('drop', handleDropSMT);
  });
}

function handleDragStartSMT(e) {
  draggedRowSMT = this;
  this.style.opacity = '0.4';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', this.dataset.lot);
}

function handleDragEndSMT() {
  this.style.opacity = '1';
  document.querySelectorAll('.plan-row.drag-over').forEach(r => r.classList.remove('drag-over'));
  draggedRowSMT = null;
}

function handleDragOverSMT(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  if (draggedRowSMT && this.dataset.line === draggedRowSMT.dataset.line && this !== draggedRowSMT) {
    document.querySelectorAll('.plan-row.drag-over').forEach(r => r.classList.remove('drag-over'));
    this.classList.add('drag-over');
  }
}

function handleDropSMT(e) {
  e.preventDefault();
  e.stopPropagation();
  this.classList.remove('drag-over');
  
  if (!draggedRowSMT || this === draggedRowSMT) return;
  if (this.dataset.line !== draggedRowSMT.dataset.line) return;
  
  const lineCode = this.dataset.line;
  const draggedLot = draggedRowSMT.dataset.lot;
  const targetLot = this.dataset.lot;
  
  // Reordenar en planningDataSMT
  const linePlans = planningDataSMT.filter(p => p.line === lineCode);
  linePlans.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  
  const dragIdx = linePlans.findIndex(p => p.lot_no === draggedLot);
  const targetIdx = linePlans.findIndex(p => p.lot_no === targetLot);
  
  if (dragIdx === -1 || targetIdx === -1) return;
  
  const [moved] = linePlans.splice(dragIdx, 1);
  linePlans.splice(targetIdx, 0, moved);
  
  // Actualizar sequences
  linePlans.forEach((p, i) => {
    p.sequence = i + 1;
    const orig = planningDataSMT.find(o => o.lot_no === p.lot_no);
    if (orig) orig.sequence = i + 1;
  });
  
  renderTableSMT(planningDataSMT);
  showSaveIndicatorSMT();
}

function showSaveIndicatorSMT() {
  const btn = document.getElementById('smt-save-sequences-btn');
  if (btn) {
    btn.style.background = '#e74c3c';
    btn.textContent = 'Guardar Orden *';
  }
}

async function saveSequencesSMT() {
  try {
    const sequences = planningDataSMT.map(p => ({
      lot_no: p.lot_no,
      group_no: 1,
      sequence: p.sequence || 1
    }));
    
    const response = await axios.post('/api/plan-smt/save-sequences', { sequences });
    
    if (response.data.success) {
      alert('Orden guardado correctamente');
      const btn = document.getElementById('smt-save-sequences-btn');
      if (btn) {
        btn.style.background = '';
        btn.textContent = 'Guardar Orden';
      }
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error guardando secuencias:', error);
    alert('Error al guardar: ' + error.message);
  }
}

// ====== Doble Click para Editar ======
function openEditModalSMT(planId) {
  const plan = planningDataSMT.find(p => String(p.id) === String(planId));
  if (!plan) return;
  
  let modal = document.getElementById('smt-edit-modal');
  if (!modal) {
    const editHTML = `
    <div id="smt-edit-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10001; align-items: center; justify-content: center;">
      <div style="background: #32323E; border-radius: 8px; padding: 20px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px;">
          <h3 style="color: #2c3e50; margin: 0;">Editar Plan</h3>
          <button id="smt-edit-closeBtn" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">&times;</button>
        </div>
        <form id="smt-edit-form">
          <input type="hidden" name="lot_no" id="smt-edit-lot_no">
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
            <div><label style="color: #888; font-size: 12px;">Lot No</label><input type="text" id="smt-edit-lot_display" disabled style="width: 100%; background: #1a1b26; border: 1px solid #333; color: #888; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Linea</label>
              <select name="line" id="smt-edit-line" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="SA">SMT A</option><option value="SB">SMT B</option><option value="SC">SMT C</option><option value="SD">SMT D</option><option value="SE">SMT E</option>
              </select>
            </div>
            <div><label style="color: #888; font-size: 12px;">Turno</label>
              <select name="shift" id="smt-edit-shift" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="DIA">DIA</option><option value="TARDE">TARDE</option><option value="NOCHE">NOCHE</option>
              </select>
            </div>
            <div><label style="color: #888; font-size: 12px;">Fecha</label><input type="date" name="working_date" id="smt-edit-working_date" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Part No</label><input type="text" name="part_no" id="smt-edit-part_no" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Model Code</label><input type="text" name="model_code" id="smt-edit-model_code" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Project</label><input type="text" name="project" id="smt-edit-project" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Process</label><input type="text" name="process" id="smt-edit-process" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Plan Count</label><input type="number" name="plan_count" id="smt-edit-plan_count" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">CT</label><input type="number" name="ct" id="smt-edit-ct" step="0.01" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">UPH</label><input type="number" name="uph" id="smt-edit-uph" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Status</label>
              <select name="status" id="smt-edit-status" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="PLAN">PLAN</option><option value="EN PROGRESO">EN PROGRESO</option><option value="PAUSADO">PAUSADO</option><option value="TERMINADO">TERMINADO</option><option value="CANCELADO">CANCELADO</option>
              </select>
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
            <button type="submit" style="background: #e67e22; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Guardar Cambios</button>
            <button type="button" id="smt-edit-cancelBtn" style="background: #7f8c8d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Cancelar</button>
          </div>
        </form>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', editHTML);
    modal = document.getElementById('smt-edit-modal');
  }
  
  // Llenar datos
  document.getElementById('smt-edit-lot_no').value = plan.lot_no;
  document.getElementById('smt-edit-lot_display').value = plan.lot_no;
  document.getElementById('smt-edit-line').value = plan.line || 'SA';
  document.getElementById('smt-edit-shift').value = plan.shift || 'DIA';
  document.getElementById('smt-edit-working_date').value = formatDateSMT(plan.working_date);
  document.getElementById('smt-edit-part_no').value = plan.part_no || '';
  document.getElementById('smt-edit-model_code').value = plan.model_code || '';
  document.getElementById('smt-edit-project').value = plan.project || '';
  document.getElementById('smt-edit-process').value = plan.process || '';
  document.getElementById('smt-edit-plan_count').value = plan.plan_count || 0;
  document.getElementById('smt-edit-ct').value = plan.ct || 0;
  document.getElementById('smt-edit-uph').value = plan.uph || 0;
  document.getElementById('smt-edit-status').value = plan.status || 'PLAN';
  
  modal.style.display = 'flex';
}

async function updatePlanSMT(formData) {
  try {
    const data = {
      lot_no: formData.get('lot_no'),
      line: formData.get('line'),
      shift: formData.get('shift'),
      working_date: formData.get('working_date'),
      part_no: formData.get('part_no'),
      model_code: formData.get('model_code'),
      project: formData.get('project'),
      process: formData.get('process'),
      plan_count: parseInt(formData.get('plan_count')) || 0,
      ct: parseFloat(formData.get('ct')) || 0,
      uph: parseInt(formData.get('uph')) || 0,
      status: formData.get('status')
    };
    
    const response = await axios.post('/api/plan-smt/update', data);
    
    if (response.data.success) {
      document.getElementById('smt-edit-modal').style.display = 'none';
      loadPlansSMT();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error actualizando plan:', error);
    alert('Error: ' + (error.response?.data?.error || error.message));
  }
}

// ====== Funciones Auxiliares ======
function parseTimeSMT(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + m;
}

function formatTimeSMT(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function formatDurationSMT(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function formatDateSMT(dateStr) {
  if (!dateStr) return '';
  return String(dateStr).substring(0, 10);
}

function getStatusClassSMT(status) {
  const s = (status || '').toUpperCase();
  if (s === 'TERMINADO') return 'status-terminado';
  if (s === 'EN PROGRESO' || s === 'EN_PROGRESO') return 'status-progreso';
  if (s === 'PAUSADO') return 'status-pausado';
  if (s === 'CANCELADO') return 'status-cancelado';
  return 'status-plan';
}

function showLoadingSMT() {
  const tbody = document.getElementById('smt-plan-tableBody');
  if (tbody) {
    tbody.innerHTML = `
      <tr class="message-row">
        <td colspan="20" style="display: table-cell; text-align: center; padding: 40px;">
          <div style="display: flex; flex-direction: column; align-items: center; gap: 15px;">
            <div style="width: 40px; height: 40px; border: 3px solid rgba(74,144,226,0.2); border-top-color: #4A90E2; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <span style="color: #4A90E2;">Cargando planes...</span>
          </div>
        </td>
      </tr>`;
  }
}

function showErrorSMT(message) {
  const tbody = document.getElementById('smt-plan-tableBody');
  if (tbody) {
    tbody.innerHTML = `
      <tr class="message-row">
        <td colspan="20" style="display: table-cell; text-align: center; padding: 40px; color: #e74c3c;">
          ${message}
        </td>
      </tr>`;
  }
}

// ====== Crear Modal Nuevo Plan ======
function createModalsInBodySMT() {
  // Limpiar modales anteriores para evitar conflictos
  ['smt-plan-modal', 'smt-edit-modal', 'smt-reschedule-modal'].forEach(id => {
    const old = document.getElementById(id);
    if (old) old.remove();
  });
  
  const modalHTML = `
    <div id="smt-plan-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; align-items: center; justify-content: center;">
      <div class="plan-modal-content" style="background: #32323E; border-radius: 8px; padding: 20px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <div class="plan-modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px;">
          <h3 style="color: #2c3e50; margin: 0;">Nuevo Plan SMT</h3>
          <button id="smt-closeModalBtn" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">&times;</button>
        </div>
        <form id="smt-plan-form">
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Linea *</label>
              <select name="line" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="">Seleccionar...</option>
                <option value="SMT A">SMT A</option>
                <option value="SMT B">SMT B</option>
                <option value="SMT C">SMT C</option>
                <option value="SMT D">SMT D</option>
                <option value="SMT E">SMT E</option>
              </select>
            </div>
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Turno *</label>
              <select name="shift" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="DIA">DIA</option>
                <option value="TARDE">TARDE</option>
                <option value="NOCHE">NOCHE</option>
              </select>
            </div>
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Fecha *</label>
              <input type="date" name="working_date" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
            </div>
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Part No *</label>
              <input type="text" name="part_no" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
            </div>
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Plan Count *</label>
              <input type="number" name="plan_count" value="0" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
            <button type="submit" style="background: #27ae60; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Crear Plan</button>
            <button type="button" id="smt-cancelBtn" style="background: #7f8c8d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// ====== Crear Nuevo Plan ======
let isCreatingPlanSMT = false;

async function createPlanSMT(formData) {
  if (isCreatingPlanSMT) {
    return;
  }
  isCreatingPlanSMT = true;
  
  try {
    const data = {
      line: lineToDbSMT(formData.get('line')),
      shift: formData.get('shift'),
      working_date: formData.get('working_date'),
      part_no: formData.get('part_no'),
      model_code: formData.get('model_code') || formData.get('part_no'),
      project: formData.get('project') || '',
      process: formData.get('process') || 'SMT',
      plan_count: parseInt(formData.get('plan_count')) || 0,
      uph: parseInt(formData.get('uph')) || 100,
      status: 'PLAN'
    };
    
    const response = await axios.post('/api/plan-smt', data);
    
    if (response.data.success || response.data.lot_no) {
      alert('Plan creado exitosamente');
      document.getElementById('smt-plan-modal').style.display = 'none';
      document.getElementById('smt-plan-form').reset();
      loadPlansSMT();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error creando plan:', error);
    alert('Error: ' + (error.response?.data?.error || error.message));
  } finally {
    isCreatingPlanSMT = false;
  }
}

// ====== Exportar Excel ======
async function exportarExcelSMT() {
  try {
    const plans = planningDataSMT.map((p, i) => ({
      secuencia: i + 1,
      lot_no: p.lot_no,
      wo_code: p.wo_code,
      po_code: p.po_code,
      working_date: p.working_date,
      line: p.line,
      shift: p.shift,
      model_code: p.model_code,
      part_no: p.part_no,
      project: p.project,
      process: p.process,
      ct: p.ct,
      uph: p.uph,
      plan_count: p.plan_count,
      output: p.output,
      status: p.status
    }));
    
    const response = await fetch('/api/plan-smt/export-excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plans })
    });
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Plan_SMT_${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
    } else {
      alert('Error al exportar');
    }
  } catch (error) {
    console.error('Error exportando:', error);
    alert('Error al exportar: ' + error.message);
  }
}

// ====== Importar Excel ======
function triggerImportExcelSMT() {
  let fileInput = document.getElementById('smt-import-excel-input');
  if (!fileInput) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'smt-import-excel-input';
    fileInput.accept = '.xlsx,.xls,.csv';
    fileInput.style.display = 'none';
    fileInput.addEventListener('change', handleImportFileSMT);
    document.body.appendChild(fileInput);
  }
  fileInput.value = '';
  fileInput.click();
}

async function handleImportFileSMT(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  const filterDate = document.getElementById('smt-filter-start')?.value || getTodaySMT();
  formData.append('working_date', filterDate);
  
  try {
    const response = await axios.post('/api/plan-smt/import-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    if (response.data.success) {
      alert(`Importados ${response.data.imported || 0} planes correctamente`);
      loadPlansSMT();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error importando:', error);
    alert('Error al importar: ' + (error.response?.data?.error || error.message));
  }
}

// ====== Event Listeners ======
let smtListenersInitialized = false;

function initializePlanSMTEventListeners() {
  if (smtListenersInitialized) {
    return;
  }
  smtListenersInitialized = true;
  
  // Agregar estilos
  if (!document.getElementById('plan-smt-styles')) {
    const style = document.createElement('style');
    style.id = 'plan-smt-styles';
    style.textContent = `
      @keyframes spin { to { transform: rotate(360deg); } }
      .status-terminado { background: #27ae60; color: white; padding: 2px 8px; border-radius: 3px; }
      .status-progreso { background: #f39c12; color: white; padding: 2px 8px; border-radius: 3px; }
      .status-pausado { background: #e67e22; color: white; padding: 2px 8px; border-radius: 3px; }
      .status-cancelado { background: #95a5a6; color: white; padding: 2px 8px; border-radius: 3px; text-decoration: line-through; }
      .status-plan { background: #3498db; color: white; padding: 2px 8px; border-radius: 3px; }
      .plan-row:hover { background-color: rgba(74, 144, 226, 0.1) !important; cursor: grab; }
      .plan-row.drag-over { border-top: 3px solid #4A90E2 !important; }
      .plan-row:active { cursor: grabbing; }
    `;
    document.head.appendChild(style);
  }
  
  // Event delegation
  document.body.addEventListener('click', function(e) {
    const target = e.target;
    
    // Abrir modal nuevo plan
    if (target.id === 'smt-openModalBtn' || target.closest('#smt-openModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('smt-plan-modal');
      if (modal) {
        modal.style.display = 'flex';
        const dateInput = modal.querySelector('input[name="working_date"]');
        if (dateInput && !dateInput.value) {
          dateInput.value = getTodaySMT();
        }
      }
      return;
    }
    
    // Cerrar modal
    if (target.id === 'smt-closeModalBtn' || target.id === 'smt-cancelBtn') {
      const modal = document.getElementById('smt-plan-modal');
      if (modal) modal.style.display = 'none';
      return;
    }
    
    // Cerrar modal edicion
    if (target.id === 'smt-edit-closeBtn' || target.id === 'smt-edit-cancelBtn') {
      const modal = document.getElementById('smt-edit-modal');
      if (modal) modal.style.display = 'none';
      return;
    }
    
    // Guardar orden
    if (target.id === 'smt-save-sequences-btn' || target.closest('#smt-save-sequences-btn')) {
      e.preventDefault();
      saveSequencesSMT();
      return;
    }
    
    // Exportar Excel
    if (target.id === 'smt-export-excel-btn' || target.closest('#smt-export-excel-btn')) {
      e.preventDefault();
      exportarExcelSMT();
      return;
    }
    
    // Importar Excel
    if (target.id === 'smt-import-excel-btn' || target.closest('#smt-import-excel-btn')) {
      e.preventDefault();
      triggerImportExcelSMT();
      return;
    }
    
    // Reprogramar
    if (target.id === 'smt-reschedule-btn' || target.closest('#smt-reschedule-btn')) {
      e.preventDefault();
      toggleRescheduleModeSMT();
      return;
    }
    
    // Cancelar seleccion reprogramar
    if (target.id === 'smt-reschedule-cancel-btn' || target.closest('#smt-reschedule-cancel-btn')) {
      e.preventDefault();
      exitRescheduleModeSMT();
      return;
    }
    
    // Cerrar modal reprogramar
    if (target.id === 'smt-reschedule-closeBtn' || target.id === 'smt-reschedule-cancelBtn') {
      const modal = document.getElementById('smt-reschedule-modal');
      if (modal) modal.style.display = 'none';
      return;
    }
    
    // Confirmar reprogramar
    if (target.id === 'smt-reschedule-confirmBtn') {
      e.preventDefault();
      confirmRescheduleSMT();
      return;
    }
  });
  
  // Select all checkbox
  document.body.addEventListener('change', function(e) {
    if (e.target.id === 'select-all-smt') {
      const checked = e.target.checked;
      document.querySelectorAll('.plan-checkbox-smt').forEach(cb => cb.checked = checked);
    }
  });
  
  // Doble click para editar (solo si el row esta dentro del contenedor SMT)
  document.body.addEventListener('dblclick', function(e) {
    const row = e.target.closest('tr.plan-row');
    if (!row || !row.dataset.id) return;
    const smtContainer = row.closest('#plan-main-smt-unique-container');
    if (!smtContainer) return;
    openEditModalSMT(row.dataset.id);
  });
  
  // Submit forms
  document.body.addEventListener('submit', function(e) {
    if (e.target.id === 'smt-plan-form') {
      e.preventDefault();
      createPlanSMT(new FormData(e.target));
      return;
    }
    if (e.target.id === 'smt-edit-form') {
      e.preventDefault();
      updatePlanSMT(new FormData(e.target));
      return;
    }
  });
}

// ====== Reprogramar planes ======
let smtRescheduleMode = false;

function toggleRescheduleModeSMT() {
  if (!smtRescheduleMode) {
    smtRescheduleMode = true;
    document.querySelectorAll('.reschedule-col').forEach(el => el.style.display = 'table-cell');
    document.getElementById('smt-reschedule-btn').textContent = 'Confirmar Reprogramar';
    document.getElementById('smt-reschedule-btn').style.background = '#d35400';
    document.getElementById('smt-reschedule-cancel-btn').style.display = '';
  } else {
    openRescheduleModalSMT();
  }
}

function exitRescheduleModeSMT() {
  smtRescheduleMode = false;
  document.querySelectorAll('.reschedule-col').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.plan-checkbox-smt').forEach(cb => cb.checked = false);
  const selectAll = document.getElementById('select-all-smt');
  if (selectAll) selectAll.checked = false;
  document.getElementById('smt-reschedule-btn').textContent = 'Reprogramar';
  document.getElementById('smt-reschedule-btn').style.background = '#e67e22';
  document.getElementById('smt-reschedule-cancel-btn').style.display = 'none';
}

function openRescheduleModalSMT() {
  const selected = document.querySelectorAll('.plan-checkbox-smt:checked');
  if (selected.length === 0) {
    alert('Selecciona al menos un plan para reprogramar');
    return;
  }
  
  let modal = document.getElementById('smt-reschedule-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'smt-reschedule-modal';
    modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:10000; justify-content:center; align-items:center;';
    modal.innerHTML = `
      <div style="background:#2a2a3a; border-radius:12px; padding:24px; width:380px; color:#ddd;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <h3 style="margin:0; color:#e67e22;">Reprogramar Planes</h3>
          <button id="smt-reschedule-closeBtn" style="background:none; border:none; color:#888; font-size:20px; cursor:pointer;">&times;</button>
        </div>
        <p id="smt-reschedule-count" style="color:#aaa; margin-bottom:16px;"></p>
        <label style="color:#888; font-size:13px;">Nueva fecha:</label>
        <input type="date" id="smt-reschedule-date" style="width:100%; padding:8px; background:#1e1e2e; border:1px solid #444; border-radius:6px; color:#ddd; margin-top:4px; margin-bottom:20px;">
        <div style="display:flex; gap:10px; justify-content:flex-end;">
          <button id="smt-reschedule-cancelBtn" style="padding:8px 16px; background:#555; border:none; border-radius:6px; color:#ddd; cursor:pointer;">Cancelar</button>
          <button id="smt-reschedule-confirmBtn" style="padding:8px 16px; background:#e67e22; border:none; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">Reprogramar</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  
  document.getElementById('smt-reschedule-count').textContent = `${selected.length} plan(es) seleccionado(s)`;
  document.getElementById('smt-reschedule-date').value = getTodaySMT();
  modal.style.display = 'flex';
}

async function confirmRescheduleSMT() {
  const newDate = document.getElementById('smt-reschedule-date').value;
  if (!newDate) {
    alert('Selecciona una fecha');
    return;
  }
  
  const selected = document.querySelectorAll('.plan-checkbox-smt:checked');
  const planIds = Array.from(selected).map(cb => parseInt(cb.dataset.planId));
  
  if (planIds.length === 0) {
    alert('No hay planes seleccionados');
    return;
  }
  
  try {
    const resp = await axios.post('/api/plan-smt/reschedule', {
      plan_ids: planIds,
      new_date: newDate
    });
    
    if (resp.data.success) {
      alert(resp.data.message || `${planIds.length} plan(es) reprogramado(s)`);
      const modal = document.getElementById('smt-reschedule-modal');
      if (modal) modal.style.display = 'none';
      const selectAll = document.getElementById('select-all-smt');
      if (selectAll) selectAll.checked = false;
      exitRescheduleModeSMT();
      loadPlansSMT();
    } else {
      alert(resp.data.error || 'Error al reprogramar');
    }
  } catch (err) {
    console.error('Error reprogramando:', err);
    alert('Error al reprogramar planes');
  }
}

// ====== Limpieza al navegar fuera del modulo ======
function cleanupPlanSMT() {
  ['smt-plan-modal', 'smt-edit-modal', 'smt-reschedule-modal'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.remove();
  });
}

// ====== Exportar funciones globalmente ======
window.loadPlansSMT = loadPlansSMT;
window.initializePlanSMTEventListeners = initializePlanSMTEventListeners;
window.createModalsInBodySMT = createModalsInBodySMT;
window.saveSequencesSMT = saveSequencesSMT;
window.cleanupPlanSMT = cleanupPlanSMT;
