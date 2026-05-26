// ====== plan-assy-workorders.js (importar Work Orders) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

function createWorkOrdersModal() {
  // Verificar si ya existe
  if (document.getElementById('wo-modal')) {
    return;
  }

  // console.log('?? Creando modal wo-modal con estilos');

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
        <input type="text" id="wo-search-input" class="assy-input" placeholder="Buscar por codigo WO o PO..." style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 180px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha Op. Desde:</label>
        <input type="date" id="wo-filter-desde" class="assy-input" title="Filtrar WOs desde esta fecha" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha Op. Hasta:</label>
        <input type="date" id="wo-filter-hasta" class="assy-input" title="Filtrar WOs hasta esta fecha" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
        
        <label style="font-size: 11px; color: #ecf0f1;">Estado:</label>
        <select id="wo-filter-estado" class="assy-input" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 120px;">
          <option value="">Todos</option>
          <option value="CREADA">CREADA</option>
          <option value="PLANIFICADA">PLANIFICADA</option>
          <option value="EN PROGRESO">EN PROGRESO</option>
          <option value="CERRADA">CERRADA</option>
        </select>
        
        <button id="wo-reload-btn" class="assy-btn" style="background-color: #2980b9; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Recargar</button>
        <button id="wo-import-selected-btn" class="plan-btn plan-btn-add" style="background-color: #27ae60; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Importar Seleccionados</button>
        
        <label style="font-size: 11px; color: #ecf0f1;">Fecha de Importacion:</label>
        <input type="date" id="wo-filter-date" class="assy-input" title="Fecha a la que se importaron los planes seleccionados" style="background: #2B2D3E; color: lightgray; border: 1px solid #20688C; padding: 6px 8px; border-radius: 4px; font-size: 12px; width: 140px;">
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
document.getElementById("assy-wo-openModalBtn").addEventListener("click", () => {
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
        alert(` WO importado exitosamente como Plan: ${plan.lot_no}`);
        await loadPlans(); // Recargar tabla principal
        await saveGroupSequences({ silent: true });
        loadWorkOrders(); // Recargar WOs
      } else if (errors.length > 0) {
        hideTableLoading('plan-main-table');
        alert(` No se pudo importar:\n\n${errors.join('\n')}`);
      }
    } else {
      hideTableLoading('plan-main-table');
      alert(" Error en importación: " + (response.data.errors || []).join(", "));
    }
  } catch (error) {
    hideTableLoading('plan-main-table');
    alert(" Error importando WO: " + (error.response?.data?.error || error.message));
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
      alert(" Todas las WOs seleccionadas ya fueron importadas.");
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
    showTableLoading('wo-modal-content', `Importando ${woIds.length} Work Order${woIds.length > 1 ? 's' : ''}...`);
    showTableLoading('plan-main-table', `Procesando ${woIds.length} Work Order${woIds.length > 1 ? 's' : ''}...`);
    updateWOStatus(`Importando ${woIds.length} work orders...`);

    // Deshabilitar boton de importar
    setButtonLoading('wo-import-selected-btn', true, 'Importando...');

    const response = await axios.post("/api/work-orders/import", {
      wo_ids: woIds,
      import_date: importDate
    });

    if (response.data.success) {
      const { imported, errors } = response.data;
      
      if (imported > 0) {
        let message = ` ${imported} Work Order(s) importado(s) exitosamente`;

        if (errors && errors.length > 0) {
          message += `\n\n⚠️ WOs ya importadas (${errors.length}):\n`;
          errors.forEach((error, index) => {
            message += `${index + 1}. ${error}\n`;
          });
        }

        alert(message);
      } else if (errors && errors.length > 0) {
        let message = ` Ninguna WO pudo ser importada:\n\n`;
        errors.forEach((error, index) => {
          message += `${index + 1}. ${error}\n`;
        });
        alert(message);
      }
      
      await loadPlans(); // Recargar tabla principal
      await saveGroupSequences({ silent: true });
      loadWorkOrders(); // Recargar WOs

      // Desmarcar "Seleccionar todos"
      document.getElementById("wo-select-all").checked = false;

    } else {
      alert(" Error en importación: " + (response.data.errors || []).join(", "));
    }
  } catch (error) {
    alert(" Error importando WOs: " + (error.response?.data?.error || error.message));
  } finally {
    // Ocultar loading y restaurar botones
    hideTableLoading('wo-modal-content');
    hideTableLoading('plan-main-table');
    setButtonLoading('wo-import-selected-btn', false, 'Importar Seleccionados');
    updateWOStatus(" Listo para importar");
  }
}

// Actualizar estado del modal WO
function updateWOStatus(message) {
  const statusElement = document.getElementById("wo-status");
  if (statusElement) {
    statusElement.textContent = message;
  }
}

