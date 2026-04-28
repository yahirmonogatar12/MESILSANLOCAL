// ====== Variables Globales del Módulo ICT ======
let ictModuleData = [];
let allDefects = [];
let currentBarcode = "";
let currentTimestamp = "";

// Registros marcados para comparacion. Clave = `${barcode}|${ts}`.
const selectedCompareRecords = new Map();
let compareRunsData = [];

// Campos a comparar y resaltar diferencias (auditoria)
const COMPARE_FIELDS = [
  { key: "act_value", label: "ACT" },
  { key: "act_unit", label: "UNIT" },
  { key: "std_value", label: "STD" },
  { key: "std_unit", label: "UNIT" },
  { key: "m_value", label: "M" },
  { key: "r_value", label: "R" },
  { key: "hlim_pct", label: "HLIM %", suffix: "%" },
  { key: "llim_pct", label: "LLIM %", suffix: "%" },
  { key: "hp_value", label: "HP" },
  { key: "lp_value", label: "LP" },
  { key: "ws_value", label: "WS" },
  { key: "ds_value", label: "DS" },
  { key: "rc_value", label: "RC" },
  { key: "p_flag", label: "P" },
  { key: "j_flag", label: "J" },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function cleanupIctModule() {
  ["ict-table-loading", "ict-defects-loading", "ict-compare-loading"].forEach(id => {
    const loader = document.getElementById(id);
    if (loader) {
      loader.classList.remove("active");
    }
  });

  const container = document.getElementById("historial-ict-unique-container");
  ["defects-modal", "compare-modal"].forEach(id => {
    const modal = document.getElementById(id);
    if (modal) {
      modal.classList.remove("active");
      if (container && modal.parentNode === document.body) {
        container.appendChild(modal);
      }
    }
  });

  selectedCompareRecords.clear();
  compareRunsData = [];
}

window.limpiarHistorialICT = cleanupIctModule;

async function downloadFile(url, fallbackName, successMessage) {
  try {
    const response = await fetch(url, { method: "GET", credentials: "same-origin" });
    if (!response.ok) {
      let errorMessage = `Error al descargar archivo (status ${response.status})`;
      try {
        const errorBody = await response.json();
        errorMessage = errorBody?.error || errorMessage;
      } catch (_) {
        // Mantener el error HTTP si el backend no envio JSON.
      }
      throw new Error(errorMessage);
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
    showNotification(error.message || "Error al descargar el archivo", "error");
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
    tr.classList.add("ict-row-openable");
    const barcode = row.barcode ?? "";
    const ts = row.ts ?? "";
    tr.dataset.barcode = barcode;
    tr.dataset.ts = ts;
    if (row.resultado === "NG") {
      tr.classList.add("ict-row-ng");
    }
    const compareKey = `${barcode}|${ts}`;
    const isChecked = selectedCompareRecords.has(compareKey);
    if (isChecked) tr.classList.add("ict-row-selected");
    tr.innerHTML = `
      <td class="ict-col-check"><input type="checkbox" class="ict-compare-check" data-barcode="${escapeHtml(barcode)}" data-ts="${escapeHtml(ts)}" data-fecha="${escapeHtml(row.fecha)}" data-hora="${escapeHtml(row.hora)}" data-linea="${escapeHtml(row.linea)}" data-resultado="${escapeHtml(row.resultado)}"${isChecked ? " checked" : ""}></td>
      <td>${escapeHtml(row.fecha)}</td>
      <td>${escapeHtml(row.hora)}</td>
      <td>${escapeHtml(row.linea)}</td>
      <td>${escapeHtml(row.ict)}</td>
      <td>${escapeHtml(row.resultado)}</td>
      <td>${escapeHtml(row.no_parte)}</td>
      <td>${escapeHtml(row.barcode)}</td>
      <td>${escapeHtml(row.fuente_archivo)}</td>
      <td title="${escapeHtml(row.defect_code)}">${escapeHtml(row.defect_code)}</td>
      <td title="${escapeHtml(row.defect_valor)}">${escapeHtml(row.defect_valor)}</td>
    `;
    tbody.appendChild(tr);
  });

  syncSelectAllCheckbox();
  updateCompareButton();
}

/**
 * Marcar/desmarcar un registro para comparacion
 */
function toggleCompareSelection(checkbox) {
  const barcode = checkbox.dataset.barcode || "";
  const ts = checkbox.dataset.ts || "";
  const key = `${barcode}|${ts}`;
  const row = checkbox.closest("tr");

  if (checkbox.checked) {
    selectedCompareRecords.set(key, {
      barcode,
      ts,
      fecha: checkbox.dataset.fecha || "",
      hora: checkbox.dataset.hora || "",
      linea: checkbox.dataset.linea || "",
      resultado: checkbox.dataset.resultado || "",
    });
    row?.classList.add("ict-row-selected");
  } else {
    selectedCompareRecords.delete(key);
    row?.classList.remove("ict-row-selected");
  }

  syncSelectAllCheckbox();
  updateCompareButton();
}

/**
 * Marcar/desmarcar todos los registros visibles
 */
function toggleSelectAllCompare(checkAll) {
  const checks = document.querySelectorAll(".ict-compare-check");
  checks.forEach(cb => {
    if (cb.checked !== checkAll) {
      cb.checked = checkAll;
      toggleCompareSelection(cb);
    }
  });
}

function syncSelectAllCheckbox() {
  const selectAll = document.getElementById("select-all-ict");
  if (!selectAll) return;
  const checks = Array.from(document.querySelectorAll(".ict-compare-check"));
  if (checks.length === 0) {
    selectAll.checked = false;
    selectAll.indeterminate = false;
    return;
  }
  const checkedCount = checks.filter(c => c.checked).length;
  selectAll.checked = checkedCount === checks.length;
  selectAll.indeterminate = checkedCount > 0 && checkedCount < checks.length;
}

function updateCompareButton() {
  const btn = document.getElementById("btn-compare");
  const counter = document.getElementById("compare-count");
  const count = selectedCompareRecords.size;

  if (btn) {
    btn.disabled = count < 2;
    btn.classList.toggle("active", count >= 2);
    btn.title = count < 2
      ? "Selecciona 2 o mas registros para comparar parametros"
      : `Comparar ${count} registros`;
  }

  if (counter) {
    if (count > 0) {
      counter.style.display = "";
      counter.textContent = `${count} seleccionado${count !== 1 ? "s" : ""}`;
    } else {
      counter.style.display = "none";
    }
  }
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

  const filterSelect = document.getElementById("modal-filter-resultado");
  if (filterSelect) {
    filterSelect.value = "";
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
    if (!r.ok) {
      throw new Error(data?.error || `Error al cargar parametros (status ${r.status})`);
    }
    
    // Guardar todos los defectos
    allDefects = Array.isArray(data) ? data : [];
    
    // Aplicar el filtro actual
    filterDefects();
  } catch (error) {
    console.error(error);
    allDefects = [];
    renderDefectsTable([]);
    showNotification(error.message || "Error al cargar parametros", "error");
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

  if (!defects.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="25" style="text-align:center;color:#95a5a6;padding:18px;">Sin parametros para mostrar</td>';
    tbody.appendChild(tr);
    return;
  }
  
  defects.forEach(d => {
    const tr = document.createElement("tr");
    tr.dataset.resultado = d.resultado_local ?? "";
    
    const fecha = d.ts ? d.ts.split(" ")[0] : "";
    const hora = d.ts ? d.ts.split(" ")[1] : "";
    
    const hlim = d.hlim_pct ? `${d.hlim_pct}%` : "";
    const llim = d.llim_pct ? `${d.llim_pct}%` : "";
    
    tr.innerHTML = `
      <td>${escapeHtml(fecha)}</td>
      <td>${escapeHtml(hora)}</td>
      <td>${escapeHtml(d.linea)}</td>
      <td>${escapeHtml(d.ict)}</td>
      <td>${escapeHtml(d.barcode)}</td>
      <td>${escapeHtml(d.componente)}</td>
      <td>${escapeHtml(d.pinref)}</td>
      <td>${escapeHtml(d.act_value)}</td>
      <td>${escapeHtml(d.act_unit)}</td>
      <td>${escapeHtml(d.std_value)}</td>
      <td>${escapeHtml(d.std_unit)}</td>
      <td>${escapeHtml(d.meas_value)}</td>
      <td>${escapeHtml(d.m_value)}</td>
      <td>${escapeHtml(d.r_value)}</td>
      <td>${escapeHtml(hlim)}</td>
      <td>${escapeHtml(llim)}</td>
      <td>${escapeHtml(d.hp_value)}</td>
      <td>${escapeHtml(d.lp_value)}</td>
      <td>${escapeHtml(d.ws_value)}</td>
      <td>${escapeHtml(d.ds_value)}</td>
      <td>${escapeHtml(d.rc_value)}</td>
      <td>${escapeHtml(d.p_flag)}</td>
      <td>${escapeHtml(d.j_flag)}</td>
      <td>${escapeHtml(d.resultado_local)}</td>
      <td>${escapeHtml(d.defecto_tipo)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Abrir modal de comparacion de parametros
 */
async function openCompareModal() {
  if (selectedCompareRecords.size < 2) {
    showNotification("Selecciona al menos 2 registros para comparar", "error");
    return;
  }

  const modal = document.getElementById("compare-modal");
  if (modal) {
    if (modal.parentNode !== document.body) {
      document.body.appendChild(modal);
    }
    modal.classList.add("active");
  }

  const loader = document.getElementById("ict-compare-loading");
  if (loader) loader.classList.add("active");

  const tbody = document.getElementById("compare-body");
  if (tbody) tbody.innerHTML = "";

  const runs = Array.from(selectedCompareRecords.values());
  try {
    const fetched = await Promise.all(runs.map(async (rec, idx) => {
      const url = `/api/ict/defects?barcode=${encodeURIComponent(rec.barcode)}&ts=${encodeURIComponent(rec.ts ?? "")}`;
      const r = await fetch(url);
      const data = await r.json();
      if (!r.ok) {
        throw new Error(data?.error || `Error cargando ${rec.barcode}`);
      }
      return {
        runIndex: idx + 1,
        ...rec,
        defects: Array.isArray(data) ? data : [],
      };
    }));
    compareRunsData = fetched;
    renderCompareTable();
  } catch (error) {
    console.error(error);
    compareRunsData = [];
    showNotification(error.message || "Error al cargar parametros", "error");
  } finally {
    if (loader) loader.classList.remove("active");
  }
}

function closeCompareModal() {
  const modal = document.getElementById("compare-modal");
  if (modal) modal.classList.remove("active");
}

/**
 * Comparar valores normalizando vacios y casing
 */
function normalizeCompareValue(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

/**
 * Construir tabla de comparacion con resaltado de diferencias
 */
function renderCompareTable() {
  const tbody = document.getElementById("compare-body");
  const summaryRuns = document.getElementById("compare-runs-summary");
  const summaryDiff = document.getElementById("compare-diff-summary");
  if (!tbody) return;
  tbody.innerHTML = "";

  const onlyDiffs = document.getElementById("compare-only-diffs")?.checked ?? true;

  // Agrupar por (componente, pinref)
  const groups = new Map();
  compareRunsData.forEach(run => {
    run.defects.forEach(d => {
      const componente = d.componente ?? "";
      const pinref = d.pinref ?? "";
      const key = `${componente}||${pinref}`;
      if (!groups.has(key)) {
        groups.set(key, { componente, pinref, runs: new Map() });
      }
      groups.get(key).runs.set(run.runIndex, d);
    });
  });

  let totalDiffGroups = 0;
  const sortedGroups = Array.from(groups.values()).sort((a, b) => {
    const ca = (a.componente || "").localeCompare(b.componente || "");
    if (ca !== 0) return ca;
    return (a.pinref || "").localeCompare(b.pinref || "");
  });

  sortedGroups.forEach(group => {
    // Determinar campos con diferencia y filas faltantes
    const diffFields = new Set();
    COMPARE_FIELDS.forEach(f => {
      const values = new Set();
      compareRunsData.forEach(run => {
        const d = group.runs.get(run.runIndex);
        if (d) values.add(normalizeCompareValue(d[f.key]));
      });
      if (values.size > 1) diffFields.add(f.key);
    });

    const missingInSomeRun = compareRunsData.some(run => !group.runs.has(run.runIndex));
    const hasAnyDiff = diffFields.size > 0 || missingInSomeRun;
    if (hasAnyDiff) totalDiffGroups++;

    if (onlyDiffs && !hasAnyDiff) return;

    compareRunsData.forEach((run, idx) => {
      const d = group.runs.get(run.runIndex);
      const tr = document.createElement("tr");
      tr.classList.add("compare-row");
      if (idx === 0) tr.classList.add("compare-group-start");
      if (hasAnyDiff) tr.classList.add("compare-group-diff");
      if (!d) tr.classList.add("compare-row-missing");

      const runLabel = `#${run.runIndex} - ${escapeHtml(run.barcode)} <span class="compare-run-meta">${escapeHtml(run.fecha)} ${escapeHtml(run.hora)}</span>`;

      let html = `
        <td class="compare-cell-key">${escapeHtml(group.componente)}</td>
        <td class="compare-cell-key">${escapeHtml(group.pinref)}</td>
        <td class="compare-cell-run">${runLabel}</td>
      `;

      COMPARE_FIELDS.forEach(f => {
        if (!d) {
          html += `<td class="compare-missing">&mdash;</td>`;
          return;
        }
        const raw = d[f.key];
        const value = (raw === null || raw === undefined || raw === "") ? "" : raw;
        const display = (value !== "" && f.suffix) ? `${value}${f.suffix}` : value;
        const isDiff = diffFields.has(f.key);
        html += `<td class="${isDiff ? "compare-diff" : ""}">${escapeHtml(display)}</td>`;
      });

      tr.innerHTML = html;
      tbody.appendChild(tr);
    });
  });

  if (summaryRuns) {
    summaryRuns.textContent = `${compareRunsData.length} registro${compareRunsData.length !== 1 ? "s" : ""}`;
  }
  if (summaryDiff) {
    summaryDiff.textContent = `${totalDiffGroups} pin${totalDiffGroups !== 1 ? "es" : ""} con diferencias`;
  }

  if (!tbody.children.length) {
    const tr = document.createElement("tr");
    const colspan = 3 + COMPARE_FIELDS.length;
    const msg = onlyDiffs && groups.size > 0
      ? "Sin diferencias entre los registros seleccionados"
      : "Sin parametros para comparar";
    tr.innerHTML = `<td colspan="${colspan}" style="text-align:center;color:#95a5a6;padding:18px;">${msg}</td>`;
    tbody.appendChild(tr);
  }
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

    // Boton comparar parametros
    if (target.id === "btn-compare" || target.closest("#btn-compare")) {
      e.preventDefault();
      const btn = document.getElementById("btn-compare");
      if (btn && !btn.disabled) openCompareModal();
      return;
    }

    // Cerrar modal (delegado por data-close para distinguir cual cerrar)
    const closeBtn = target.closest(".close-modal");
    if (closeBtn) {
      e.preventDefault();
      const which = closeBtn.dataset.close;
      if (which === "compare-modal") {
        closeCompareModal();
      } else {
        closeDefectsModal();
      }
      return;
    }

    // Click fuera del modal para cerrar
    if (target.id === "defects-modal") {
      e.preventDefault();
      closeDefectsModal();
      return;
    }
    if (target.id === "compare-modal") {
      e.preventDefault();
      closeCompareModal();
      return;
    }

    // Click en checkbox o celda de checkbox: detener propagacion para evitar abrir defects
    if (target.classList.contains("ict-compare-check") || target.id === "select-all-ict") {
      e.stopPropagation();
      return;
    }
    if (target.classList.contains("ict-col-check") || target.closest(".ict-col-check")) {
      return;
    }

    // Doble click en cualquier fila para abrir parametros locales
    const openableRow = target.closest(".ict-row-openable");
    if (openableRow && e.detail === 2) {
      e.preventDefault();
      const barcode = openableRow.dataset.barcode;
      const ts = openableRow.dataset.ts;
      openDefectsModal(barcode, ts);
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

    // Toggle "solo mostrar diferencias" en modal de comparacion
    if (e.target.id === "compare-only-diffs") {
      renderCompareTable();
      return;
    }

    // Cambios en checkbox individual (cuando se cambia con teclado)
    if (e.target.classList && e.target.classList.contains("ict-compare-check")) {
      toggleCompareSelection(e.target);
      return;
    }

    // Cambio en select-all
    if (e.target.id === "select-all-ict") {
      toggleSelectAllCompare(e.target.checked);
      return;
    }
  });

  // Event delegation para input (búsqueda con debounce)
  let barcodeTimer;
  document.body.addEventListener("input", function (e) {
    if (e.target.id === "filter-barcode") {
      clearTimeout(barcodeTimer);
      const barcodeValue = e.target.value.trim();
      
      // Buscar automaticamente solo con prefijos suficientemente especificos.
      if (barcodeValue.length >= 6 || barcodeValue.length === 0) {
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
window.openCompareModal = openCompareModal;
window.closeCompareModal = closeCompareModal;

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
