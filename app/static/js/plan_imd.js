// ====== Plan IMD - Vista Simple por Filas ======

// Mapeo de líneas: Frontend <-> MySQL
const LINE_MAP_IMD = {
  'P1': 'PANA A',
  'P2': 'PANA B',
  'P3': 'PANA C',
  'P4': 'PANA D'
};

const LINE_MAP_REVERSE_IMD = {
  'PANA A': 'P1',
  'PANA B': 'P2',
  'PANA C': 'P3',
  'PANA D': 'P4'
};

// Convertir código DB a nombre visible
function lineToDisplay(dbCode) {
  return LINE_MAP_IMD[dbCode] || dbCode;
}

// Convertir nombre visible a código DB
function lineToDb(displayName) {
  return LINE_MAP_REVERSE_IMD[displayName] || displayName;
}

// Variables globales
let planningDataIMD = [];
let currentConfigIMD = {
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
function getTodayIMD() {
  const options = { timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit' };
  const formatter = new Intl.DateTimeFormat('en-CA', options);
  return formatter.format(new Date());
}

// ====== Cargar Planes IMD ======
async function loadPlansIMD() {
  try {
    showLoadingIMD();
    
    setDefaultDateFilterIMD();
    const filterStart = document.getElementById('imd-filter-start')?.value;
    
    let url = '/api/plan-imd';
    if (filterStart) {
      url += `?start=${encodeURIComponent(filterStart)}`;
    }
    
    const response = await axios.get(url);
    planningDataIMD = Array.isArray(response.data) ? response.data : [];
    
    renderTableIMD(planningDataIMD);
  } catch (error) {
    console.error('Error cargando planes IMD:', error);
    showErrorIMD('Error al cargar los datos');
  }
}

function setDefaultDateFilterIMD() {
  const filterStart = document.getElementById('imd-filter-start');
  if (filterStart && !filterStart.value) {
    filterStart.value = getTodayIMD();
  }
}

// ====== Renderizar Tabla Simple ======
function renderTableIMD(plans) {
  const tbody = document.getElementById('imd-plan-tableBody');
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
  
  // Agrupar por línea
  const lineOrder = ['P1', 'P2', 'P3', 'P4'];
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
  
  // Ordenar líneas: primero las conocidas, luego las demás
  const sortedLines = Object.keys(grouped).sort((a, b) => {
    const ia = lineOrder.indexOf(a);
    const ib = lineOrder.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });
  
  // Color uniforme para todas las líneas
  const lineColor = '#16a085';
  
  let html = '';
  let globalSeq = 0;
  
  sortedLines.forEach(lineCode => {
    const linePlans = grouped[lineCode];
    const displayName = lineToDisplay(lineCode);
    const color = lineColor;
    const totalPlan = linePlans.reduce((s, p) => s + (parseInt(p.plan_count) || 0), 0);
    const totalOutput = linePlans.reduce((s, p) => s + (parseInt(p.output) || 0), 0);
    
    // Header de grupo - estilo ASSY
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
    let currentTime = parseTimeIMD(currentConfigIMD.shiftStart);
    let lineSeq = 0;
    
    linePlans.forEach(plan => {
      globalSeq++;
      lineSeq++;
      const uph = parseInt(plan.uph) || 100;
      const planCount = parseInt(plan.plan_count) || 0;
      const effectiveMinutes = Math.ceil((planCount / uph) * 60);
      
      const startTime = formatTimeIMD(currentTime);
      let endMinutes = currentTime + effectiveMinutes;
      
      // Ajustar por breaks
      currentConfigIMD.breaks.forEach(brk => {
        const breakStart = parseTimeIMD(brk.start);
        const breakEnd = parseTimeIMD(brk.end);
        if (currentTime < breakEnd && endMinutes > breakStart) {
          endMinutes += (breakEnd - breakStart);
        }
      });
      
      const endTime = formatTimeIMD(endMinutes);
      const timeFormatted = formatDurationIMD(effectiveMinutes);
      currentTime = endMinutes;
      
      const statusClass = getStatusClassIMD(plan.status);
      const isOvertime = endMinutes > parseTimeIMD(currentConfigIMD.shiftEnd);
      
      html += `
        <tr class="plan-row ${statusClass}" draggable="true" data-id="${plan.id}" data-lot="${plan.lot_no}" data-line="${lineCode}" data-seq="${lineSeq}" style="border-left: 4px solid ${color}; cursor: grab; ${isOvertime ? 'background-color: rgba(231, 76, 60, 0.2);' : ''}">
          <td style="display: none;" class="reschedule-col"><input type="checkbox" class="plan-checkbox-imd" data-plan-id="${plan.id}" style="cursor:pointer;"></td>
          <td>${lineSeq}</td>
          <td>${plan.lot_no || ''}</td>
          <td>${plan.wo_code || ''}</td>
          <td>${plan.po_code || ''}</td>
          <td>${formatDateIMD(plan.working_date)}</td>
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
  initDragDropIMD();
}

// ====== Drag & Drop ======
let draggedRowIMD = null;

function initDragDropIMD() {
  const tbody = document.getElementById('imd-plan-tableBody');
  if (!tbody) return;
  
  tbody.querySelectorAll('tr.plan-row[draggable]').forEach(row => {
    row.addEventListener('dragstart', handleDragStartIMD);
    row.addEventListener('dragend', handleDragEndIMD);
    row.addEventListener('dragover', handleDragOverIMD);
    row.addEventListener('drop', handleDropIMD);
  });
}

function handleDragStartIMD(e) {
  draggedRowIMD = this;
  this.style.opacity = '0.4';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', this.dataset.lot);
}

function handleDragEndIMD() {
  this.style.opacity = '1';
  document.querySelectorAll('.plan-row.drag-over').forEach(r => r.classList.remove('drag-over'));
  draggedRowIMD = null;
}

function handleDragOverIMD(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  // Solo permitir drop en misma línea
  if (draggedRowIMD && this.dataset.line === draggedRowIMD.dataset.line && this !== draggedRowIMD) {
    document.querySelectorAll('.plan-row.drag-over').forEach(r => r.classList.remove('drag-over'));
    this.classList.add('drag-over');
  }
}

function handleDropIMD(e) {
  e.preventDefault();
  e.stopPropagation();
  this.classList.remove('drag-over');
  
  if (!draggedRowIMD || this === draggedRowIMD) return;
  if (this.dataset.line !== draggedRowIMD.dataset.line) return;
  
  const lineCode = this.dataset.line;
  const draggedLot = draggedRowIMD.dataset.lot;
  const targetLot = this.dataset.lot;
  
  // Reordenar en planningDataIMD
  const linePlans = planningDataIMD.filter(p => p.line === lineCode);
  linePlans.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  
  const dragIdx = linePlans.findIndex(p => p.lot_no === draggedLot);
  const targetIdx = linePlans.findIndex(p => p.lot_no === targetLot);
  
  if (dragIdx === -1 || targetIdx === -1) return;
  
  const [moved] = linePlans.splice(dragIdx, 1);
  linePlans.splice(targetIdx, 0, moved);
  
  // Actualizar sequences
  linePlans.forEach((p, i) => {
    p.sequence = i + 1;
    const orig = planningDataIMD.find(o => o.lot_no === p.lot_no);
    if (orig) orig.sequence = i + 1;
  });
  
  renderTableIMD(planningDataIMD);
  showSaveIndicatorIMD();
}

function showSaveIndicatorIMD() {
  const btn = document.getElementById('imd-save-sequences-btn');
  if (btn) {
    btn.style.background = '#e74c3c';
    btn.textContent = 'Guardar Orden *';
  }
}

async function saveSequencesIMD() {
  try {
    const sequences = planningDataIMD.map(p => ({
      lot_no: p.lot_no,
      group_no: 1,
      sequence: p.sequence || 1
    }));
    
    const response = await axios.post('/api/plan-imd/save-sequences', { sequences });
    
    if (response.data.success) {
      alert('Orden guardado correctamente');
      const btn = document.getElementById('imd-save-sequences-btn');
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
function openEditModalIMD(planId) {
  const plan = planningDataIMD.find(p => String(p.id) === String(planId));
  if (!plan) return;

  let modal = document.getElementById('imd-edit-modal');
  if (!modal) {
    const editHTML = `
    <div id="imd-edit-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10001; align-items: center; justify-content: center;">
      <div style="background: #32323E; border-radius: 8px; padding: 20px; max-width: 520px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px;">
          <h3 style="color: #ecf0f1; margin: 0; font-weight: 600;">Editar Plan</h3>
          <button id="imd-edit-closeBtn" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">&times;</button>
        </div>
        <form id="imd-edit-form">
          <input type="hidden" name="lot_no" id="imd-edit-lot_no">
          <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px;">
            <div><label style="color: #888; font-size: 12px;">Lot No</label><input type="text" id="imd-edit-lot_display" disabled style="width: 100%; background: #1a1b26; border: 1px solid #333; color: #888; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Linea</label>
              <select name="line" id="imd-edit-line" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="P1">PANA A</option><option value="P2">PANA B</option><option value="P3">PANA C</option><option value="P4">PANA D</option>
              </select>
            </div>
            <div><label style="color: #888; font-size: 12px;">Turno</label>
              <select name="shift" id="imd-edit-shift" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="DIA">DIA</option><option value="TARDE">TARDE</option><option value="NOCHE">NOCHE</option>
              </select>
            </div>
            <div><label style="color: #888; font-size: 12px;">Part No</label><input type="text" name="part_no" id="imd-edit-part_no" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
            <div><label style="color: #888; font-size: 12px;">Cantidad</label><input type="number" name="plan_count" id="imd-edit-plan_count" min="0" style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;"></div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 20px;">
            <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;">
              <button type="submit" style="width: 100%; background: #e67e22; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Guardar Cambios</button>
              <button type="button" id="imd-edit-cancelBtn" style="width: 100%; background: #7f8c8d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Cerrar</button>
            </div>
            <button type="button" id="imd-edit-cancel-plan-btn" style="width: 100%; background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Cancelar plan</button>
          </div>
        </form>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', editHTML);
    modal = document.getElementById('imd-edit-modal');
  }

  document.getElementById('imd-edit-lot_no').value = plan.lot_no;
  document.getElementById('imd-edit-lot_display').value = plan.lot_no;
  document.getElementById('imd-edit-line').value = plan.line || 'P1';
  document.getElementById('imd-edit-shift').value = plan.shift || 'DIA';
  document.getElementById('imd-edit-part_no').value = plan.part_no || '';
  document.getElementById('imd-edit-plan_count').value = plan.plan_count || 0;

  const cancelBtn = document.getElementById('imd-edit-cancel-plan-btn');
  if (cancelBtn) {
    if (String(plan.status || '').toUpperCase() === 'CANCELADO') {
      cancelBtn.textContent = 'Planear';
      cancelBtn.style.background = '#27ae60';
      cancelBtn.dataset.action = 'reactivar';
    } else {
      cancelBtn.textContent = 'Cancelar plan';
      cancelBtn.style.background = '#e74c3c';
      cancelBtn.dataset.action = 'cancelar';
    }
  }

  modal.style.display = 'flex';
}

async function updatePlanIMD(formData) {
  try {
    const partNo = (formData.get('part_no') || '').trim();
    if (!partNo) {
      alert('Part No es requerido');
      return;
    }

    const data = {
      lot_no: formData.get('lot_no'),
      line: formData.get('line'),
      shift: formData.get('shift'),
      part_no: partNo,
      plan_count: parseInt(formData.get('plan_count'), 10) || 0
    };

    const response = await axios.post('/api/plan-imd/update', data);

    if (response.data.success) {
      document.getElementById('imd-edit-modal').style.display = 'none';
      loadPlansIMD();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error actualizando plan:', error);
    alert('Error: ' + (error.response?.data?.error || error.message));
  }
}

async function handleCancelPlanIMD() {
  const lotNo = document.getElementById('imd-edit-lot_no')?.value;
  const cancelBtn = document.getElementById('imd-edit-cancel-plan-btn');
  if (!lotNo || !cancelBtn) return;

  const action = cancelBtn.dataset.action || 'cancelar';
  const isCancelAction = action === 'cancelar';
  const nextStatus = isCancelAction ? 'CANCELADO' : 'PLAN';
  const confirmMsg = isCancelAction ? `Cancelar plan ${lotNo}?` : `Reactivar plan ${lotNo}?`;

  if (!confirm(confirmMsg)) return;

  const originalText = cancelBtn.textContent;

  try {
    cancelBtn.disabled = true;
    cancelBtn.textContent = isCancelAction ? 'Cancelando...' : 'Reactivando...';
    cancelBtn.style.background = '#6c757d';
    cancelBtn.style.cursor = 'not-allowed';

    const response = await axios.post('/api/plan-imd/update', {
      lot_no: lotNo,
      status: nextStatus
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || 'No fue posible actualizar el estado');
    }

    document.getElementById('imd-edit-modal').style.display = 'none';
    loadPlansIMD();
  } catch (error) {
    alert('Error actualizando estado del plan: ' + (error.response?.data?.error || error.message));
  } finally {
    cancelBtn.disabled = false;
    cancelBtn.textContent = originalText;
    cancelBtn.style.background = '';
    cancelBtn.style.cursor = '';
  }
}
// ====== Funciones Auxiliares ======
function parseTimeIMD(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + m;
}

function formatTimeIMD(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function formatDurationIMD(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function formatDateIMD(dateStr) {
  if (!dateStr) return '';
  return String(dateStr).substring(0, 10);
}

function getStatusClassIMD(status) {
  const s = (status || '').toUpperCase();
  if (s === 'TERMINADO') return 'status-terminado';
  if (s === 'EN PROGRESO' || s === 'EN_PROGRESO') return 'status-progreso';
  if (s === 'PAUSADO') return 'status-pausado';
  if (s === 'CANCELADO') return 'status-cancelado';
  return 'status-plan';
}

function showLoadingIMD() {
  const tbody = document.getElementById('imd-plan-tableBody');
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

function showErrorIMD(message) {
  const tbody = document.getElementById('imd-plan-tableBody');
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
function createModalsInBodyIMD() {
  // Limpiar modales anteriores para evitar conflictos
  ['imd-plan-modal', 'imd-edit-modal', 'imd-reschedule-modal'].forEach(id => {
    const old = document.getElementById(id);
    if (old) old.remove();
  });
  
  const modalHTML = `
    <div id="imd-plan-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; align-items: center; justify-content: center;">
      <div class="plan-modal-content" style="background: #32323E; border-radius: 8px; padding: 20px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto;">
        <div class="plan-modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 10px;">
          <h3 style="color: #2c3e50; margin: 0;">Nuevo Plan IMD</h3>
          <button id="imd-closeModalBtn" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">&times;</button>
        </div>
        <form id="imd-plan-form">
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
            <div class="form-group">
              <label style="color: #888; font-size: 12px;">Linea *</label>
              <select name="line" required style="width: 100%; background: #1a1b26; border: 1px solid #444; color: lightgray; padding: 8px; border-radius: 4px;">
                <option value="">Seleccionar...</option>
                <option value="PANA A">PANA A</option>
                <option value="PANA B">PANA B</option>
                <option value="PANA C">PANA C</option>
                <option value="PANA D">PANA D</option>
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
            <button type="button" id="imd-cancelBtn" style="background: #7f8c8d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// ====== Crear Nuevo Plan ======
let isCreatingPlanIMD = false;

async function createPlanIMD(formData) {
  if (isCreatingPlanIMD) {
    console.log('⚠️ Ya se está creando un plan, ignorando...');
    return;
  }
  isCreatingPlanIMD = true;
  
  try {
    const data = {
      line: lineToDb(formData.get('line')),
      shift: formData.get('shift'),
      working_date: formData.get('working_date'),
      part_no: formData.get('part_no'),
      model_code: formData.get('model_code') || formData.get('part_no'),
      project: formData.get('project') || '',
      process: formData.get('process') || 'Main',
      plan_count: parseInt(formData.get('plan_count')) || 0,
      uph: parseInt(formData.get('uph')) || 100,
      status: 'PLAN'
    };
    
    const response = await axios.post('/api/plan-imd', data);
    
    if (response.data.success || response.data.lot_no) {
      alert('Plan creado exitosamente');
      document.getElementById('imd-plan-modal').style.display = 'none';
      document.getElementById('imd-plan-form').reset();
      loadPlansIMD();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error creando plan:', error);
    alert('Error: ' + (error.response?.data?.error || error.message));
  } finally {
    isCreatingPlanIMD = false;
  }
}

// ====== Exportar Excel ======
async function exportarExcelIMD() {
  try {
    const plans = planningDataIMD.map((p, i) => ({
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
    
    const response = await fetch('/api/plan-imd/export-excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plans })
    });
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Plan_IMD_${new Date().toISOString().split('T')[0]}.xlsx`;
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
function triggerImportExcelIMD() {
  let fileInput = document.getElementById('imd-import-excel-input');
  if (!fileInput) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'imd-import-excel-input';
    fileInput.accept = '.xlsx,.xls,.csv';
    fileInput.style.display = 'none';
    fileInput.addEventListener('change', handleImportFileIMD);
    document.body.appendChild(fileInput);
  }
  fileInput.value = '';
  fileInput.click();
}

async function handleImportFileIMD(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append('file', file);
  
  const filterDate = document.getElementById('imd-filter-start')?.value || getTodayIMD();
  formData.append('working_date', filterDate);
  
  try {
    const response = await axios.post('/api/plan-imd/import-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    if (response.data.success) {
      alert(`Importados ${response.data.imported || 0} planes correctamente`);
      loadPlansIMD();
    } else {
      alert('Error: ' + (response.data.error || 'Error desconocido'));
    }
  } catch (error) {
    console.error('Error importando:', error);
    alert('Error al importar: ' + (error.response?.data?.error || error.message));
  }
}

// ====== Event Listeners ======
let imdListenersInitialized = false;

function initializePlanIMDEventListeners() {
  if (imdListenersInitialized) {
    console.log('⚠️ Event listeners IMD ya inicializados, saltando...');
    return;
  }
  imdListenersInitialized = true;
  console.log('🔧 Inicializando event listeners de Plan IMD...');
  
  // Agregar estilos
  if (!document.getElementById('plan-imd-styles')) {
    const style = document.createElement('style');
    style.id = 'plan-imd-styles';
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
    if (target.id === 'imd-openModalBtn' || target.closest('#imd-openModalBtn')) {
      e.preventDefault();
      const modal = document.getElementById('imd-plan-modal');
      if (modal) {
        modal.style.display = 'flex';
        const dateInput = modal.querySelector('input[name="working_date"]');
        if (dateInput && !dateInput.value) {
          dateInput.value = getTodayIMD();
        }
      }
      return;
    }
    
    // Cerrar modal
    if (target.id === 'imd-closeModalBtn' || target.id === 'imd-cancelBtn') {
      const modal = document.getElementById('imd-plan-modal');
      if (modal) modal.style.display = 'none';
      return;
    }
    
    // Cerrar modal edición
    if (target.id === 'imd-edit-closeBtn' || target.id === 'imd-edit-cancelBtn') {
      const modal = document.getElementById('imd-edit-modal');
      if (modal) modal.style.display = 'none';
      return;
    }

    // Cancelar / reactivar plan
    if (target.id === 'imd-edit-cancel-plan-btn' || target.closest('#imd-edit-cancel-plan-btn')) {
      e.preventDefault();
      handleCancelPlanIMD();
      return;
    }
    
    // Guardar orden
    if (target.id === 'imd-save-sequences-btn' || target.closest('#imd-save-sequences-btn')) {
      e.preventDefault();
      saveSequencesIMD();
      return;
    }
    
    // Exportar Excel
    if (target.id === 'imd-export-excel-btn' || target.closest('#imd-export-excel-btn')) {
      e.preventDefault();
      exportarExcelIMD();
      return;
    }
    
    // Importar Excel
    if (target.id === 'imd-import-excel-btn' || target.closest('#imd-import-excel-btn')) {
      e.preventDefault();
      triggerImportExcelIMD();
      return;
    }
    
    // Reprogramar - abrir modal
    if (target.id === 'imd-reschedule-btn' || target.closest('#imd-reschedule-btn')) {
      e.preventDefault();
      openRescheduleModalIMD();
      return;
    }

    // Buscar pendientes
    if (target.id === 'imd-reschedule-search-btn') {
      e.preventDefault();
      loadPendingPlansIMD();
      return;
    }

    // Cerrar modal reprogramar
    if (target.id === 'imd-reschedule-closeBtn' || target.id === 'imd-reschedule-cancelBtn') {
      const modal = document.getElementById('imd-reschedule-modal');
      if (modal) modal.style.display = 'none';
      return;
    }

    // Confirmar reprogramar
    if (target.id === 'imd-reschedule-confirmBtn') {
      e.preventDefault();
      confirmRescheduleIMD();
      return;
    }
  });
  
  // Select all checkbox (reschedule pending table)
  document.body.addEventListener('change', function(e) {
    if (e.target.id === 'imd-reschedule-select-all') {
      const checked = e.target.checked;
      document.querySelectorAll('.imd-pending-cb').forEach(cb => cb.checked = checked);
    }
  });
  
  // Doble click para editar (solo si el row está dentro del contenedor IMD)
  document.body.addEventListener('dblclick', function(e) {
    const row = e.target.closest('tr.plan-row');
    if (!row || !row.dataset.id) return;
    // Verificar que la fila pertenece al contenedor IMD, no al de ASSY
    const imdContainer = row.closest('#plan-main-imd-unique-container');
    if (!imdContainer) return;
    openEditModalIMD(row.dataset.id);
  });
  
  // Submit forms
  document.body.addEventListener('submit', function(e) {
    if (e.target.id === 'imd-plan-form') {
      e.preventDefault();
      createPlanIMD(new FormData(e.target));
      return;
    }
    if (e.target.id === 'imd-edit-form') {
      e.preventDefault();
      updatePlanIMD(new FormData(e.target));
      return;
    }
  });
  
  console.log(' Event listeners de Plan IMD inicializados');
}

// ====== Reprogramar planes ======
function openRescheduleModalIMD() {
  let modal = document.getElementById('imd-reschedule-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'imd-reschedule-modal';
    modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:10000; justify-content:center; align-items:center;';
    modal.innerHTML = `
      <div style="background:#2a2a3a; border-radius:12px; padding:24px; width:750px; max-width:95%; max-height:85vh; overflow-y:auto; color:#ddd;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <h3 style="margin:0; color:#e67e22;">Reprogramar Planes IMD</h3>
          <button id="imd-reschedule-closeBtn" style="background:none; border:none; color:#888; font-size:20px; cursor:pointer;">&times;</button>
        </div>
        <div style="display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap; margin-bottom:16px;">
          <div>
            <label style="color:#888; font-size:12px;">Fecha Desde</label>
            <input type="date" id="imd-reschedule-from" style="display:block; padding:6px; background:#1e1e2e; border:1px solid #444; border-radius:6px; color:#ddd;">
          </div>
          <div>
            <label style="color:#888; font-size:12px;">Fecha Hasta</label>
            <input type="date" id="imd-reschedule-to" style="display:block; padding:6px; background:#1e1e2e; border:1px solid #444; border-radius:6px; color:#ddd;">
          </div>
          <button id="imd-reschedule-search-btn" style="padding:6px 14px; background:#3498db; border:none; border-radius:6px; color:white; cursor:pointer;">Buscar Pendientes</button>
          <div style="margin-left:auto;">
            <label style="color:#888; font-size:12px;">Nueva Fecha</label>
            <input type="date" id="imd-reschedule-new-date" style="display:block; padding:6px; background:#1e1e2e; border:1px solid #444; border-radius:6px; color:#ddd;">
          </div>
        </div>
        <div id="imd-reschedule-table-container" style="max-height:400px; overflow-y:auto; margin-bottom:16px;">
          <p style="color:#666; text-align:center; padding:20px;">Selecciona rango de fechas y busca pendientes</p>
        </div>
        <div style="display:flex; gap:10px; justify-content:flex-end;">
          <button id="imd-reschedule-cancelBtn" style="padding:8px 16px; background:#555; border:none; border-radius:6px; color:#ddd; cursor:pointer;">Cerrar</button>
          <button id="imd-reschedule-confirmBtn" style="padding:8px 16px; background:#e67e22; border:none; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">Reprogramar Seleccionados</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  const today = getTodayIMD();
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000);
  const fromDefault = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit' }).format(sevenDaysAgo);
  document.getElementById('imd-reschedule-from').value = fromDefault;
  document.getElementById('imd-reschedule-to').value = today;
  document.getElementById('imd-reschedule-new-date').value = today;
  document.getElementById('imd-reschedule-table-container').innerHTML = '<p style="color:#666; text-align:center; padding:20px;">Selecciona rango de fechas y busca pendientes</p>';
  modal.style.display = 'flex';
}

async function loadPendingPlansIMD() {
  const from = document.getElementById('imd-reschedule-from').value;
  const to = document.getElementById('imd-reschedule-to').value;
  const container = document.getElementById('imd-reschedule-table-container');
  if (!from || !to) {
    alert('Selecciona fecha desde y hasta');
    return;
  }
  container.innerHTML = '<p style="color:#3498db; text-align:center; padding:20px;">Buscando planes pendientes...</p>';
  try {
    const resp = await axios.get(`/api/plan-imd/pending-reschedule?start=${from}&end=${to}`);
    const plans = resp.data || [];
    if (plans.length === 0) {
      container.innerHTML = '<p style="color:#888; text-align:center; padding:20px;">No hay planes pendientes en este rango</p>';
      return;
    }
    let html = `<table style="width:100%; border-collapse:collapse; font-size:11px;">
      <thead><tr style="background:#172A46; color:#ecf0f1;">
        <th style="padding:6px; border:1px solid #444;"><input type="checkbox" id="imd-reschedule-select-all"></th>
        <th style="padding:6px; border:1px solid #444;">Lot No</th>
        <th style="padding:6px; border:1px solid #444;">Fecha</th>
        <th style="padding:6px; border:1px solid #444;">Part No</th>
        <th style="padding:6px; border:1px solid #444;">Linea</th>
        <th style="padding:6px; border:1px solid #444;">Plan</th>
        <th style="padding:6px; border:1px solid #444;">Produced</th>
        <th style="padding:6px; border:1px solid #444;">Pendiente</th>
        <th style="padding:6px; border:1px solid #444;">Status</th>
      </tr></thead><tbody>`;
    plans.forEach(p => {
      const pending = (p.plan_count || 0) - (p.produced_count || 0);
      html += `<tr style="border-bottom:1px solid #444;">
        <td style="padding:5px; text-align:center; border:1px solid #444;"><input type="checkbox" class="imd-pending-cb" data-lot="${p.lot_no}"></td>
        <td style="padding:5px; border:1px solid #444;">${p.lot_no}</td>
        <td style="padding:5px; border:1px solid #444;">${p.working_date}</td>
        <td style="padding:5px; border:1px solid #444;">${p.part_no || ''}</td>
        <td style="padding:5px; border:1px solid #444;">${lineToDisplay(p.line) || p.line}</td>
        <td style="padding:5px; text-align:right; border:1px solid #444;">${p.plan_count || 0}</td>
        <td style="padding:5px; text-align:right; border:1px solid #444;">${p.produced_count || 0}</td>
        <td style="padding:5px; text-align:right; border:1px solid #444; color:#e67e22; font-weight:bold;">${pending}</td>
        <td style="padding:5px; border:1px solid #444;">${p.status || ''}</td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color:#e74c3c; text-align:center; padding:20px;">Error: ${err.message}</p>`;
  }
}

async function confirmRescheduleIMD() {
  const newDate = document.getElementById('imd-reschedule-new-date').value;
  if (!newDate) {
    alert('Selecciona la nueva fecha');
    return;
  }
  const checked = document.querySelectorAll('.imd-pending-cb:checked');
  const lotNos = Array.from(checked).map(cb => cb.dataset.lot);
  if (lotNos.length === 0) {
    alert('Selecciona al menos un plan');
    return;
  }
  if (!confirm(`Reprogramar ${lotNos.length} plan(es) a ${newDate}?\nSe crearan sublotes con la cantidad pendiente y los originales quedaran como TERMINADO.`)) return;
  try {
    const resp = await axios.post('/api/plan-imd/reschedule', { lot_nos: lotNos, new_working_date: newDate });
    if (resp.data.success) {
      alert(resp.data.message || 'Planes reprogramados');
      const modal = document.getElementById('imd-reschedule-modal');
      if (modal) modal.style.display = 'none';
      loadPlansIMD();
    } else {
      alert(resp.data.error || 'Error al reprogramar');
    }
  } catch (err) {
    alert('Error: ' + (err.response?.data?.error || err.message));
  }
}

// ====== Limpieza al navegar fuera del módulo ======
function cleanupPlanIMD() {
  // Remover modales del body para no interferir con otros módulos
  ['imd-plan-modal', 'imd-edit-modal', 'imd-reschedule-modal'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.remove();
  });
  console.log('🧹 Modales IMD limpiados');
}

// ====== Exportar funciones globalmente ======
window.loadPlansIMD = loadPlansIMD;
window.initializePlanIMDEventListeners = initializePlanIMDEventListeners;
window.createModalsInBodyIMD = createModalsInBodyIMD;
window.saveSequencesIMD = saveSequencesIMD;
window.cleanupPlanIMD = cleanupPlanIMD;

console.log('📝 plan_imd.js cargado correctamente');
