// ====== plan-assy-reschedule.js (reprogramar planes pendientes) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

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
    console.error(' Elemento reschedule-new-date no encontrado');
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
    showSuccessModal(` ${created} nuevo(s) plan(es) creado(s) exitosamente para ${newDate}\n\nCada plan tiene la cantidad pendiente calculada automáticamente.`);

    // Recargar la lista de pendientes
    loadPendingPlans();

    // Recargar planes principales si están en la misma fecha
    const currentStartInput = document.getElementById("assy-filter-start");
    const currentEndInput = document.getElementById("assy-filter-end");

    if (currentStartInput && currentEndInput) {
      const currentStart = currentStartInput.value;
      const currentEnd = currentEndInput.value;
      if (newDate >= currentStart && newDate <= currentEnd) {
        loadPlans();
      }
    }

  } catch (error) {
    console.error(' Error al crear nuevos planes:', error);
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

