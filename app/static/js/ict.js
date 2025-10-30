// ====== Variables Globales del Módulo ICT ======
let ictModuleData = [];
let allDefects = [];
let currentBarcode = "";
let currentTimestamp = "";

function cleanupIctModule() {
  ["ict-table-loading", "ict-defects-loading"].forEach(id => {
    const loader = document.getElementById(id);
    if (loader) {
      loader.classList.remove("active");
    }
  });

  const modal = document.getElementById("defects-modal");
  if (modal) {
    modal.classList.remove("active");
    const container = document.getElementById("historial-ict-unique-container");
    if (container && modal.parentNode === document.body) {
      container.appendChild(modal);
    }
  }
}

window.limpiarHistorialICT = cleanupIctModule;

async function downloadFile(url, fallbackName, successMessage) {
  try {
    const response = await fetch(url, { method: "GET", credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Error al descargar archivo (status ${response.status})`);
    }

    const blob = await response.blob();
    let filename = fallbackName;

    const disposition = response.headers.get("content-disposition");
    if (disposition) {
      const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, "");
      }
    }

    const downloadUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(downloadUrl);

    if (successMessage) {
      showNotification(successMessage, "success");
    }
  } catch (error) {
    console.error(error);
    showNotification("Error al descargar el archivo", "error");
  }
}

// ====== Funciones Principales ======

/**
 * Mostrar overlay de carga
 */
function showLoading(context = "main") {
  const targetId = context === "modal" ? "ict-defects-loading" : "ict-table-loading";
  const loader = document.getElementById(targetId);
  const table = document.getElementById(context === "modal" ? "ict-defects-table" : "ict-table");

  if (loader && table) {
    const wrap = table.closest(".table-wrap");
    const thead = table.querySelector("thead");
    if (wrap && thead) {
      wrap.style.setProperty("--thead-height", `${thead.offsetHeight}px`);
    }
  }

  if (loader) {
    loader.classList.add("active");
  }
}

/**
 * Ocultar overlay de carga
 */
function hideLoading(context = "main") {
  const targetId = context === "modal" ? "ict-defects-loading" : "ict-table-loading";
  const loader = document.getElementById(targetId);
  if (loader) {
    loader.classList.remove("active");
  }
}

/**
 * Cargar datos del historial ICT
 */
async function loadIctData() {
  showLoading("main");
  
  try {
    let fecha = document.getElementById("filter-fecha")?.value || "";
    const linea = document.getElementById("filter-linea")?.value || "";
    const resultado = document.getElementById("filter-resultado")?.value || "";
    const barcode_like = document.getElementById("filter-barcode")?.value || "";
    
    // Si hay barcode, no filtrar por fecha (buscar en toda la DB)
    if (barcode_like.trim().length > 0) {
      fecha = "";
    }

    const url = `/api/ict/data?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&resultado=${encodeURIComponent(resultado)}&barcode_like=${encodeURIComponent(barcode_like)}`;
    const r = await fetch(url);
    const data = await r.json();
    
    ictModuleData = data;

    // Actualizar contador de registros
    const recordCount = document.getElementById("record-count");
    if (recordCount) {
      recordCount.textContent = `${data.length} registro${data.length !== 1 ? 's' : ''}`;
    }

    renderIctTable(data);
  } catch (error) {
    showNotification("Error al cargar datos", "error");
  } finally {
    hideLoading("main");
  }
}

/**
 * Renderizar tabla de historial ICT
 */
function renderIctTable(data) {
  const tbody = document.getElementById("ict-body");
  if (!tbody) return;
  
  tbody.innerHTML = "";
  
  data.forEach(row => {
    const tr = document.createElement("tr");
    if (row.resultado === "NG") {
      tr.classList.add("ict-row-ng");
      tr.dataset.barcode = row.barcode;
      tr.dataset.ts = row.ts;
    }
    tr.innerHTML = `
      <td>${row.fecha ?? ""}</td>
      <td>${row.hora ?? ""}</td>
      <td>${row.linea ?? ""}</td>
      <td>${row.ict ?? ""}</td>
      <td>${row.resultado ?? ""}</td>
      <td>${row.no_parte ?? ""}</td>
      <td>${row.barcode ?? ""}</td>
      <td>${row.fuente_archivo ?? ""}</td>
      <td title="${row.defect_code ?? ""}">${row.defect_code ?? ""}</td>
      <td title="${row.defect_valor ?? ""}">${row.defect_valor ?? ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Abrir modal de parámetros detallados
 */
async function openDefectsModal(barcode, ts) {
  // Guardar barcode y timestamp para exportar
  currentBarcode = barcode;
  currentTimestamp = ts;
  
  // Mostrar el modal
  const modal = document.getElementById("defects-modal");
  if (modal) {
    if (modal.parentNode !== document.body) {
      document.body.appendChild(modal);
    }
    modal.classList.add("active");
  }
  
  // Actualizar el título con el barcode
  const modalBarcode = document.getElementById("modal-barcode");
  if (modalBarcode) {
    modalBarcode.textContent = barcode;
  }
  
  // Cargar los defectos
  await loadDefects(barcode, ts);
}

/**
 * Cerrar modal de parámetros
 */
function closeDefectsModal() {
  const modal = document.getElementById("defects-modal");
  if (modal) {
    modal.classList.remove("active");
  }
}

/**
 * Cargar defectos/parámetros de un barcode
 */
async function loadDefects(barcode, ts) {
  showLoading("modal");
  
  try {
    const url = `/api/ict/defects?barcode=${encodeURIComponent(barcode)}&ts=${encodeURIComponent(ts ?? "")}`;
    const r = await fetch(url);
    const data = await r.json();
    
    // Guardar todos los defectos
    allDefects = data;
    
    // Aplicar el filtro actual
    filterDefects();
  } catch (error) {
    showNotification("Error al cargar parámetros", "error");
  } finally {
    hideLoading("modal");
  }
}

/**
 * Filtrar defectos por resultado
 */
function filterDefects() {
  const filterSelect = document.getElementById("modal-filter-resultado");
  const filterValue = filterSelect?.value || "";
  
  let filtered = allDefects;
  if (filterValue) {
    filtered = allDefects.filter(d => d.resultado_local === filterValue);
  }
  
  renderDefectsTable(filtered);
}

/**
 * Renderizar tabla de parámetros detallados
 */
function renderDefectsTable(defects) {
  const tbody = document.getElementById("defects-body");
  if (!tbody) return;
  
  tbody.innerHTML = "";
  
  defects.forEach(d => {
    const tr = document.createElement("tr");
    tr.dataset.resultado = d.resultado_local ?? "";
    
    const fecha = d.ts ? d.ts.split(" ")[0] : "";
    const hora = d.ts ? d.ts.split(" ")[1] : "";
    
    const hlim = d.hlim_pct ? `${d.hlim_pct}%` : "";
    const llim = d.llim_pct ? `${d.llim_pct}%` : "";
    
    tr.innerHTML = `
      <td>${fecha}</td>
      <td>${hora}</td>
      <td>${d.linea ?? ""}</td>
      <td>${d.ict ?? ""}</td>
      <td>${d.barcode ?? ""}</td>
      <td>${d.componente ?? ""}</td>
      <td>${d.pinref ?? ""}</td>
      <td>${d.act_value ?? ""}</td>
      <td>${d.act_unit ?? ""}</td>
      <td>${d.std_value ?? ""}</td>
      <td>${d.std_unit ?? ""}</td>
      <td>${d.meas_value ?? ""}</td>
      <td>${d.m_value ?? ""}</td>
      <td>${d.r_value ?? ""}</td>
      <td>${hlim}</td>
      <td>${llim}</td>
      <td>${d.hp_value ?? ""}</td>
      <td>${d.lp_value ?? ""}</td>
      <td>${d.ws_value ?? ""}</td>
      <td>${d.ds_value ?? ""}</td>
      <td>${d.rc_value ?? ""}</td>
      <td>${d.p_flag ?? ""}</td>
      <td>${d.j_flag ?? ""}</td>
      <td>${d.resultado_local ?? ""}</td>
      <td>${d.defecto_tipo ?? ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Exportar historial ICT a Excel
 */
async function exportIctToExcel() {
  const fecha = document.getElementById("filter-fecha")?.value || "";
  const linea = document.getElementById("filter-linea")?.value || "";
  const resultado = document.getElementById("filter-resultado")?.value || "";
  const barcode_like = document.getElementById("filter-barcode")?.value || "";

  const url = `/api/ict/export?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&resultado=${encodeURIComponent(resultado)}&barcode_like=${encodeURIComponent(barcode_like)}`;
  await downloadFile(url, `historial_ict_${Date.now()}.xlsx`, "Exportación completada");
}

/**
 * Exportar parámetros detallados a Excel
 */
async function exportDefectsToExcel() {
  const filtroResultado = document.getElementById("modal-filter-resultado")?.value || "";
  const url = `/api/ict/export-defects?barcode=${encodeURIComponent(currentBarcode)}&ts=${encodeURIComponent(currentTimestamp)}&resultado=${encodeURIComponent(filtroResultado)}`;
  await downloadFile(url, `parametros_ict_${Date.now()}.xlsx`, "Parámetros exportados");
}

// ====== Event Delegation (CRÍTICO PARA CARGA DINÁMICA) ======

/**
 * Función de inicialización usando Event Delegation
 * IMPORTANTE: Esta función debe poder llamarse múltiples veces sin causar problemas
 */
function initializeIctEventListeners() {
  // Protección contra inicialización múltiple
  if (document.body.dataset.ictListenersAttached) {
    return;
  }

  // Event delegation para clicks
  document.body.addEventListener("click", function (e) {
    const target = e.target;

    // Botón consultar
    if (target.id === "btn-consultar" || target.closest("#btn-consultar")) {
      e.preventDefault();
      loadIctData();
      return;
    }

    // Botón exportar historial
    if (target.id === "btn-export-excel" || target.closest("#btn-export-excel")) {
      e.preventDefault();
      exportIctToExcel();
      return;
    }

    // Botón exportar parámetros
    if (target.id === "btn-export-defects-excel" || target.closest("#btn-export-defects-excel")) {
      e.preventDefault();
      exportDefectsToExcel();
      return;
    }

    // Cerrar modal
    if (target.classList.contains("close-modal") || target.closest(".close-modal")) {
      e.preventDefault();
      closeDefectsModal();
      return;
    }

    // Click en fila NG (doble click)
    const ngRow = target.closest(".ict-row-ng");
    if (ngRow && e.detail === 2) {
      e.preventDefault();
      const barcode = ngRow.dataset.barcode;
      const ts = ngRow.dataset.ts;
      openDefectsModal(barcode, ts);
      return;
    }

    // Click fuera del modal para cerrar
    if (target.id === "defects-modal") {
      e.preventDefault();
      closeDefectsModal();
      return;
    }
  });

  // Event delegation para cambios (selects, inputs)
  document.body.addEventListener("change", function (e) {
    // Filtro de resultado en modal
    if (e.target.id === "modal-filter-resultado") {
      filterDefects();
      return;
    }
  });

  // Event delegation para input (búsqueda con debounce)
  let barcodeTimer;
  document.body.addEventListener("input", function (e) {
    if (e.target.id === "filter-barcode") {
      clearTimeout(barcodeTimer);
      const barcodeValue = e.target.value.trim();
      
      // Si hay barcode, buscar en toda la DB (sin fecha)
      if (barcodeValue.length > 0) {
        barcodeTimer = setTimeout(() => {
          loadIctData();
        }, 500);
      }
    }
  });

  document.body.dataset.ictListenersAttached = "true";
}

// ====== Funciones Auxiliares ======

/**
 * Mostrar notificaciones al usuario
 */
function showNotification(message, type = "info") {
  const existingNotification = document.querySelector(".notification");
  if (existingNotification) existingNotification.remove();

  const notification = document.createElement("div");
  notification.className = "notification";
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 6px;
    color: white;
    font-weight: 600;
    font-size: 0.9rem;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    animation: slideIn 0.3s ease;
  `;

  if (type === "success") notification.style.backgroundColor = "#27ae60";
  else if (type === "error") notification.style.backgroundColor = "#e74c3c";
  else notification.style.backgroundColor = "#3498db";

  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    if (notification.parentNode) notification.remove();
  }, 4000);
}

/**
 * Establecer fecha del día por defecto
 */
function setDefaultDate() {
  const fechaInput = document.getElementById("filter-fecha");
  if (fechaInput && !fechaInput.value) {
    const today = new Date().toISOString().split('T')[0];
    fechaInput.value = today;
  }
}

// ====== Exponer Funciones Globalmente (CRÍTICO) ======

// Exponer función de inicialización
window.initializeIctEventListeners = initializeIctEventListeners;

// Exponer funciones principales
window.loadIctData = loadIctData;
window.openDefectsModal = openDefectsModal;
window.closeDefectsModal = closeDefectsModal;
window.exportIctToExcel = exportIctToExcel;
window.exportDefectsToExcel = exportDefectsToExcel;
window.filterDefects = filterDefects;

// ====== Auto-inicialización ======

// Ejecutar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", function() {
  setDefaultDate();
  initializeIctEventListeners();
  loadIctData();
});

// También ejecutar inmediatamente si el DOM ya está listo (para scripts defer)
if (document.readyState === "interactive" || document.readyState === "complete") {
  setDefaultDate();
  initializeIctEventListeners();
  setTimeout(() => loadIctData(), 100);
}
