// ====== WF_004: Garantizar CSS del modulo en <head> ======
(function ensureModuleStyles() {
  const sheets = [
    { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
    { id: "ict-css", href: "/static/css/ict.css?v=20260630a" },
    { id: "history-vision-css", href: "/static/css/history_vision.css?v=20260629f" },
  ];
  sheets.forEach(({ id, href }) => {
    let link = document.getElementById(id);
    if (link) {
      const version = href.split("v=")[1];
      if (version && !link.getAttribute("href")?.includes(version)) {
        link.setAttribute("href", href);
      }
      return;
    }
    link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  });
})();

let visionModuleData = [];
let visionStopsData = [];
let visionRecordsCurrentPage = 1;
let visionRecordsPerPage = 1000;
let visionRecordsTotalRows = 0;
let visionRecordsTotalPages = 1;
let visionRecordsRequestToken = 0;
let visionRecordsFilterTimer = null;
let visionStopsCurrentPage = 1;
let visionStopsPerPage = 1000;
let visionStopsTotalRows = 0;
let visionStopsTotalPages = 1;
let visionStopsTotalSeconds = 0;
let visionStopsRequestToken = 0;
let visionStopsFilterTimer = null;
let currentVisionPreviewToken = 0;
const visionPreviewState = {
  scale: 1,
  minScale: 1,
  maxScale: 6,
  translateX: 0,
  translateY: 0,
  isDragging: false,
  pointerId: null,
  dragStartX: 0,
  dragStartY: 0,
};
const VISION_FILTERS_STORAGE_KEY = "historialVisionFilters";
const VISION_COLUMN_FILTERS_STORAGE_KEY = "historialVisionColumnFilters";
let visionColumnFilters = null;

function getVisionColumnFilterState() {
  if (visionColumnFilters) {
    return visionColumnFilters;
  }

  visionColumnFilters = { records: {}, stops: {} };
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(VISION_COLUMN_FILTERS_STORAGE_KEY) || "{}",
    );
    ["records", "stops"].forEach((tableKey) => {
      if (stored?.[tableKey] && typeof stored[tableKey] === "object") {
        visionColumnFilters[tableKey] = stored[tableKey];
      }
    });
  } catch (error) {
    console.warn("No se pudieron leer los filtros por columna de Vision", error);
  }
  return visionColumnFilters;
}

function saveVisionColumnFilters() {
  try {
    window.localStorage.setItem(
      VISION_COLUMN_FILTERS_STORAGE_KEY,
      JSON.stringify(getVisionColumnFilterState()),
    );
  } catch (error) {
    console.warn("No se pudieron guardar los filtros por columna de Vision", error);
  }
}

function getVisionColumnFilters(tableKey) {
  return getVisionColumnFilterState()[tableKey] || {};
}

function setVisionColumnFilter(tableKey, field, value) {
  const state = getVisionColumnFilterState();
  state[tableKey] ||= {};
  const normalizedValue = String(value || "").trim();

  if (normalizedValue) {
    state[tableKey][field] = normalizedValue;
  } else {
    delete state[tableKey][field];
  }
  saveVisionColumnFilters();
}

function clearAllVisionColumnFilters(tableKey) {
  getVisionColumnFilterState()[tableKey] = {};
  saveVisionColumnFilters();
}

function renderVisionColumnFilterHeaders() {
  const root = document.getElementById("historial-vision-root");
  if (!root) {
    return;
  }

  root
    .querySelectorAll("th[data-vision-filter-table][data-vision-filter-field]")
    .forEach((header) => {
      if (header.dataset.visionFilterReady === "true") {
        return;
      }

      const tableKey = header.dataset.visionFilterTable;
      const field = header.dataset.visionFilterField;
      const label = header.textContent.trim();
      const value = getVisionColumnFilters(tableKey)[field] || "";
      header.classList.add("vision-column-filterable");
      header.dataset.visionFilterReady = "true";
      header.innerHTML = `
        <div class="vision-column-header">
          <span>${escapeVisionHtml(label)}</span>
          <button class="vision-column-filter-btn${value ? " active" : ""}"
                  type="button"
                  data-vision-table-key="${escapeVisionHtml(tableKey)}"
                  data-vision-field="${escapeVisionHtml(field)}"
                  aria-label="Filtrar ${escapeVisionHtml(label)}"
                  aria-expanded="false"
                  title="Filtrar ${escapeVisionHtml(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path>
            </svg>
          </button>
        </div>
        <div class="vision-column-filter-popover"
             data-vision-table-key="${escapeVisionHtml(tableKey)}"
             data-vision-field="${escapeVisionHtml(field)}">
          <input class="vision-column-filter-input"
                 data-vision-table-key="${escapeVisionHtml(tableKey)}"
                 data-vision-field="${escapeVisionHtml(field)}"
                 value="${escapeVisionHtml(value)}"
                 placeholder="Buscar..."
                 aria-label="Buscar en ${escapeVisionHtml(label)}"
                 autocomplete="off">
          <div class="vision-column-filter-actions">
            <button class="vision-column-filter-clear" type="button">Limpiar</button>
            <button class="vision-column-filter-clear-all" type="button">Todos</button>
          </div>
        </div>`;
    });
}

function closeVisionColumnFilterPopovers(exceptPopover = null) {
  document
    .querySelectorAll(".vision-column-filter-popover.open")
    .forEach((popover) => {
      if (popover === exceptPopover) {
        return;
      }
      popover.classList.remove("open");
      popover.closest("th")?.classList.remove("filter-open");
      const button = popover
        .closest("th")
        ?.querySelector(".vision-column-filter-btn");
      button?.classList.remove("open");
      button?.setAttribute("aria-expanded", "false");
    });
}

function syncVisionColumnFilterControls(tableKey) {
  const filters = getVisionColumnFilters(tableKey);
  document
    .querySelectorAll(
      `.vision-column-filter-input[data-vision-table-key="${tableKey}"]`,
    )
    .forEach((input) => {
      const value = filters[input.dataset.visionField] || "";
      input.value = value;
      input
        .closest("th")
        ?.querySelector(".vision-column-filter-btn")
        ?.classList.toggle("active", Boolean(value));
    });
}

function renderFilteredVisionTable(tableKey) {
  if (tableKey === "stops") {
    window.clearTimeout(visionStopsFilterTimer);
    visionStopsCurrentPage = 1;
    visionStopsFilterTimer = window.setTimeout(
      () => loadVisionStopsData({ resetPage: false }),
      250,
    );
    return;
  }
  window.clearTimeout(visionRecordsFilterTimer);
  visionRecordsCurrentPage = 1;
  visionRecordsFilterTimer = window.setTimeout(
    () => loadHistorialVisionData({ resetPage: false }),
    250,
  );
}

function getVisionToday() {
  return new Date().toISOString().split("T")[0];
}

function getVisionFilterElements() {
  return {
    fechaDesde: document.getElementById("vision-filter-fecha-desde"),
    fechaHasta: document.getElementById("vision-filter-fecha-hasta"),
    linea: document.getElementById("vision-filter-linea"),
    resultado: document.getElementById("vision-filter-resultado"),
    numeroParte: document.getElementById("vision-filter-numero-parte"),
    qr: document.getElementById("vision-filter-qr"),
    barcode: document.getElementById("vision-filter-barcode"),
  };
}

function getStoredVisionFilters() {
  try {
    const rawValue = window.sessionStorage.getItem(VISION_FILTERS_STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    const parsedValue = JSON.parse(rawValue);
    return parsedValue && typeof parsedValue === "object" ? parsedValue : null;
  } catch (error) {
    console.warn("No se pudo leer el estado de filtros de Vision", error);
    return null;
  }
}

function saveVisionFilters(filters = null) {
  const elements = getVisionFilterElements();
  const nextFilters = filters || {
    fechaDesde: elements.fechaDesde?.value || "",
    fechaHasta: elements.fechaHasta?.value || "",
    linea: elements.linea?.value || "",
    resultado: elements.resultado?.value || "",
    numeroParte: elements.numeroParte?.value || "",
    qr: elements.qr?.value || "",
    barcode: elements.barcode?.value || "",
  };

  try {
    window.sessionStorage.setItem(
      VISION_FILTERS_STORAGE_KEY,
      JSON.stringify(nextFilters),
    );
  } catch (error) {
    console.warn("No se pudo guardar el estado de filtros de Vision", error);
  }

  return nextFilters;
}

function resolveVisionFilters() {
  const elements = getVisionFilterElements();
  const storedFilters = getStoredVisionFilters() || {};
  const today = getVisionToday();

  const resolvedFilters = {
    fechaDesde: elements.fechaDesde?.value || storedFilters.fechaDesde || today,
    fechaHasta: elements.fechaHasta?.value || storedFilters.fechaHasta || today,
    linea: elements.linea?.value || storedFilters.linea || "",
    resultado: elements.resultado?.value || storedFilters.resultado || "",
    numeroParte: elements.numeroParte?.value || storedFilters.numeroParte || "",
    qr: elements.qr?.value || storedFilters.qr || "",
    barcode: elements.barcode?.value || storedFilters.barcode || "",
  };

  if (elements.fechaDesde) {
    elements.fechaDesde.value = resolvedFilters.fechaDesde;
  }

  if (elements.fechaHasta) {
    elements.fechaHasta.value = resolvedFilters.fechaHasta;
  }

  if (elements.linea) {
    elements.linea.value = resolvedFilters.linea;
  }

  if (elements.resultado) {
    elements.resultado.value = resolvedFilters.resultado;
  }

  if (elements.numeroParte) {
    elements.numeroParte.value = resolvedFilters.numeroParte;
  }

  if (elements.qr) {
    elements.qr.value = resolvedFilters.qr;
  }

  if (elements.barcode) {
    elements.barcode.value = resolvedFilters.barcode;
  }

  saveVisionFilters(resolvedFilters);
  return resolvedFilters;
}

function getVisionPreviewImage() {
  return document.getElementById("vision-preview-image");
}

function getVisionPreviewStage() {
  return document.getElementById("vision-preview-stage");
}

function updateVisionPreviewZoomLabel() {
  const zoomLabel = document.getElementById("vision-preview-zoom-level");
  if (!zoomLabel) {
    return;
  }

  zoomLabel.textContent = `${Math.round(visionPreviewState.scale * 100)}%`;
}

function applyVisionPreviewTransform() {
  const image = getVisionPreviewImage();
  const stage = getVisionPreviewStage();
  if (!image || !stage) {
    return;
  }

  image.style.transform = `translate(${visionPreviewState.translateX}px, ${visionPreviewState.translateY}px) scale(${visionPreviewState.scale})`;
  stage.classList.toggle("is-zoomed", visionPreviewState.scale > 1);
  stage.classList.toggle("is-dragging", visionPreviewState.isDragging);
  updateVisionPreviewZoomLabel();
}

function stopVisionPreviewDrag() {
  visionPreviewState.isDragging = false;
  visionPreviewState.pointerId = null;
  applyVisionPreviewTransform();
}

function resetVisionPreviewZoom() {
  visionPreviewState.scale = 1;
  visionPreviewState.translateX = 0;
  visionPreviewState.translateY = 0;
  stopVisionPreviewDrag();
  applyVisionPreviewTransform();
}

function setVisionPreviewScale(nextScale) {
  const normalizedScale = Math.min(
    visionPreviewState.maxScale,
    Math.max(visionPreviewState.minScale, Number(nextScale) || 1),
  );

  visionPreviewState.scale = normalizedScale;
  if (normalizedScale <= 1) {
    visionPreviewState.translateX = 0;
    visionPreviewState.translateY = 0;
    stopVisionPreviewDrag();
    return;
  }

  applyVisionPreviewTransform();
}

function adjustVisionPreviewZoom(delta) {
  setVisionPreviewScale(visionPreviewState.scale + delta);
}

function cleanupVisionModule() {
  saveVisionFilters();
  currentVisionPreviewToken += 1;
  hideVisionLoading();
  hideVisionImageLoading();
  clearVisionPreviewImage();
  closeVisionPreviewModal({ restoreToContainer: true });
}

window.limpiarHistorialVision = cleanupVisionModule;

async function downloadVisionFile(url, fallbackName, successMessage) {
  try {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw new Error(`Error al descargar archivo (status ${response.status})`);
    }

    const blob = await response.blob();
    let filename = fallbackName;
    const disposition = response.headers.get("content-disposition");

    if (disposition) {
      const match =
        /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
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

    showVisionNotification(successMessage, "success");
  } catch (error) {
    console.error(error);
    showVisionNotification("Error al descargar el archivo", "error");
  }
}

function showVisionLoading() {
  const loader = document.getElementById("vision-table-loading");
  if (loader) {
    loader.classList.add("active");
  }
}

function hideVisionLoading() {
  const loader = document.getElementById("vision-table-loading");
  if (loader) {
    loader.classList.remove("active");
  }
}

function showVisionImageLoading() {
  const loader = document.getElementById("vision-image-loading");
  if (loader) {
    loader.classList.add("active");
  }
}

function hideVisionImageLoading() {
  const loader = document.getElementById("vision-image-loading");
  if (loader) {
    loader.classList.remove("active");
  }
}

async function loadHistorialVisionData(options = {}) {
  if (options.resetPage !== false) {
    visionRecordsCurrentPage = 1;
  }
  const requestToken = ++visionRecordsRequestToken;
  showVisionLoading();

  try {
    const {
      fechaDesde,
      fechaHasta,
      linea,
      resultado,
      numeroParte,
      qr,
      barcode,
    } = resolveVisionFilters();

    const perPageSelect = document.getElementById("vision-records-per-page");
    const selectedPerPage = Number.parseInt(perPageSelect?.value || "", 10);
    if (selectedPerPage > 0) {
      visionRecordsPerPage = selectedPerPage;
    }

    const query = new URLSearchParams({
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      linea,
      resultado,
      numero_parte: numeroParte,
      qr,
      barcode,
      page: String(visionRecordsCurrentPage),
      per_page: String(visionRecordsPerPage),
    });
    Object.entries(getVisionColumnFilters("records")).forEach(([field, value]) => {
      if (String(value || "").trim()) {
        query.set(`cf_${field}`, String(value).trim());
      }
    });

    const url = `/api/vision/data?${query.toString()}`;

    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();
    if (requestToken !== visionRecordsRequestToken) {
      return;
    }

    if (!response.ok) {
      throw new Error(data?.error || "Error al consultar historial vision");
    }

    visionModuleData = Array.isArray(data) ? data : data.rows || [];
    visionRecordsTotalRows = Array.isArray(data)
      ? visionModuleData.length
      : Number(data.total || 0);
    visionRecordsTotalPages = Array.isArray(data)
      ? 1
      : Math.max(1, Number(data.total_pages || 1));
    if (!Array.isArray(data)) {
      visionRecordsCurrentPage = Math.max(1, Number(data.page || 1));
      visionRecordsPerPage = Math.max(
        1,
        Number(data.per_page || visionRecordsPerPage),
      );
    }

    renderHistorialVisionTable(visionModuleData);
    renderVisionRecordsPagination();
  } catch (error) {
    if (requestToken !== visionRecordsRequestToken) {
      return;
    }
    console.error(error);
    visionModuleData = [];
    visionRecordsTotalRows = 0;
    visionRecordsTotalPages = 1;
    renderHistorialVisionTable([]);
    renderVisionRecordsPagination();
    showVisionNotification("Error al cargar datos", "error");
  } finally {
    if (requestToken === visionRecordsRequestToken) {
      hideVisionLoading();
    }
  }
}

function renderHistorialVisionTable(data) {
  const tbody = document.getElementById("vision-body");
  if (!tbody) {
    return;
  }
  const sourceRows = Array.isArray(data) ? data : [];
  const recordCount = document.getElementById("vision-record-count");
  if (recordCount) {
    recordCount.textContent = `${visionRecordsTotalRows} registro${visionRecordsTotalRows !== 1 ? "s" : ""}`;
  }

  if (sourceRows.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="vision-table-empty">No se encontraron registros.</td></tr>';
    return;
  }

  tbody.innerHTML = sourceRows
    .map((row) => {
      const resultado = row.resultado ?? "";
      const resultClass =
        resultado === "OK"
          ? "vision-result-ok"
          : resultado === "NG"
            ? "vision-result-ng"
            : "";
      const recordId = row.id ?? "";

      return `
        <tr class="vision-row-interactive" data-record-id="${escapeVisionHtml(recordId)}" title="Doble click para ver imagen">
          <td>${escapeVisionHtml(row.linea ?? "")}</td>
          <td>${escapeVisionHtml(row.fecha ?? "")}</td>
          <td>${escapeVisionHtml(row.hora ?? "")}</td>
          <td>${escapeVisionHtml(row.numero_parte ?? "")}</td>
          <td title="${escapeVisionHtml(row.qr ?? "")}">${escapeVisionHtml(row.qr ?? "")}</td>
          <td title="${escapeVisionHtml(row.barcode ?? "")}">${escapeVisionHtml(row.barcode ?? "")}</td>
          <td class="${resultClass}">${escapeVisionHtml(resultado)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderVisionRecordsPagination() {
  const pagination = document.getElementById("vision-records-pagination");
  if (!pagination) {
    return;
  }
  pagination.hidden = visionRecordsTotalRows <= 0;
  if (pagination.hidden) {
    return;
  }

  const start = (visionRecordsCurrentPage - 1) * visionRecordsPerPage + 1;
  const end = Math.min(
    visionRecordsCurrentPage * visionRecordsPerPage,
    visionRecordsTotalRows,
  );
  const summary = document.getElementById("vision-records-pagination-summary");
  const pageInput = document.getElementById("vision-records-page-input");
  const pageTotal = document.getElementById("vision-records-page-total");
  if (summary) {
    summary.textContent = `${start} - ${end} de ${visionRecordsTotalRows}`;
  }
  if (pageInput) {
    pageInput.value = String(visionRecordsCurrentPage);
    pageInput.max = String(visionRecordsTotalPages);
  }
  if (pageTotal) {
    pageTotal.textContent = String(visionRecordsTotalPages);
  }

  const atFirst = visionRecordsCurrentPage <= 1;
  const atLast = visionRecordsCurrentPage >= visionRecordsTotalPages;
  document.getElementById("vision-records-page-first")?.toggleAttribute("disabled", atFirst);
  document.getElementById("vision-records-page-prev")?.toggleAttribute("disabled", atFirst);
  document.getElementById("vision-records-page-next")?.toggleAttribute("disabled", atLast);
  document.getElementById("vision-records-page-last")?.toggleAttribute("disabled", atLast);
}

function gotoVisionRecordsPage(page) {
  const nextPage = Math.max(
    1,
    Math.min(visionRecordsTotalPages, Number.parseInt(page, 10) || 1),
  );
  if (nextPage === visionRecordsCurrentPage) {
    renderVisionRecordsPagination();
    return;
  }
  visionRecordsCurrentPage = nextPage;
  loadHistorialVisionData({ resetPage: false });
}

function formatVisionStopSeconds(seconds) {
  if (seconds === null || seconds === undefined || isNaN(seconds)) {
    return "-";
  }
  const ms = Math.round(Number(seconds) * 1000);
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const millis = ms % 1000;
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}.${pad(millis, 3)}`;
}

async function loadVisionStopsData(options = {}) {
  if (options.resetPage !== false) {
    visionStopsCurrentPage = 1;
  }
  const requestToken = ++visionStopsRequestToken;
  const loader = document.getElementById("vision-stops-loading");
  loader?.classList.add("active");
  try {
    const { fechaDesde, fechaHasta, linea } = resolveVisionFilters();
    const perPageSelect = document.getElementById("vision-stops-per-page");
    const selectedPerPage = Number.parseInt(perPageSelect?.value || "", 10);
    if (selectedPerPage > 0) {
      visionStopsPerPage = selectedPerPage;
    }

    const query = new URLSearchParams({
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      linea,
      page: String(visionStopsCurrentPage),
      per_page: String(visionStopsPerPage),
    });
    Object.entries(getVisionColumnFilters("stops")).forEach(([field, value]) => {
      if (String(value || "").trim()) {
        query.set(`cf_${field}`, String(value).trim());
      }
    });

    const url = `/api/vision/stops?${query.toString()}`;
    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();
    if (requestToken !== visionStopsRequestToken) {
      return;
    }
    if (!response.ok) {
      throw new Error(data?.error || "Error al consultar paros de vision");
    }

    visionStopsData = Array.isArray(data) ? data : data.rows || [];
    visionStopsTotalRows = Array.isArray(data)
      ? visionStopsData.length
      : Number(data.total || 0);
    visionStopsTotalSeconds = Array.isArray(data)
      ? visionStopsData.reduce((total, row) => {
          const stopSeconds =
            row.recovery_status === "confirmed"
              ? row.real_stop_seconds
              : row.real_stop_prov;
          return total + (Number(stopSeconds) || 0);
        }, 0)
      : Number(data.total_stop_seconds || 0);
    visionStopsTotalPages = Array.isArray(data)
      ? 1
      : Math.max(1, Number(data.total_pages || 1));
    if (!Array.isArray(data)) {
      visionStopsCurrentPage = Math.max(1, Number(data.page || 1));
      visionStopsPerPage = Math.max(1, Number(data.per_page || visionStopsPerPage));
    }
    renderVisionStopsTable(visionStopsData);
    renderVisionStopsPagination();
  } catch (error) {
    if (requestToken !== visionStopsRequestToken) {
      return;
    }
    console.error(error);
    visionStopsData = [];
    visionStopsTotalRows = 0;
    visionStopsTotalPages = 1;
    visionStopsTotalSeconds = 0;
    renderVisionStopsTable([]);
    renderVisionStopsPagination();
    showVisionNotification("Error al cargar paros de vision", "error");
  } finally {
    if (requestToken === visionStopsRequestToken) {
      loader?.classList.remove("active");
    }
  }
}

function renderVisionStopsTable(data) {
  const tbody = document.getElementById("vision-stops-body");
  if (!tbody) {
    return;
  }
  const sourceRows = Array.isArray(data) ? data : [];
  const count = document.getElementById("vision-stops-count");
  if (count) {
    count.textContent = `${visionStopsTotalRows} paro${visionStopsTotalRows !== 1 ? "s" : ""}`;
  }
  const totalTime = document.getElementById("vision-stops-total-time");
  if (totalTime) {
    totalTime.textContent = formatVisionStopSeconds(visionStopsTotalSeconds);
  }
  if (sourceRows.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="vision-table-empty">No se encontraron paros.</td></tr>';
    return;
  }
  tbody.innerHTML = sourceRows
    .map((row) => {
      const confirmed = row.recovery_status === "confirmed";
      const paro = confirmed ? row.real_stop_seconds : row.real_stop_prov;
      const ajustes = Array.isArray(row.ajustes) ? row.ajustes : [];
      const ajusteTxt = ajustes.length
        ? ajustes
            .map((a) => {
              const tec = a.tecnico
                ? `${escapeVisionHtml(a.tecnico)}: `
                : "";
              return `${tec}${escapeVisionHtml(a.inicio_local ?? "")} - ${escapeVisionHtml(a.fin_local ?? "")}`;
            })
            .join("<br>")
        : "-";
      return `
        <tr class="${confirmed ? "" : "vision-stop-open"}">
          <td>${escapeVisionHtml(row.linea ?? "")}</td>
          <td>${escapeVisionHtml(row.numero_parte ?? "")}</td>
          <td>${escapeVisionHtml(row.sequence_error_datetime ?? "")}</td>
          <td>${escapeVisionHtml(row.stable_run_datetime ?? "-")}</td>
          <td><strong>${formatVisionStopSeconds(paro)}</strong></td>
          <td>${escapeVisionHtml(String(row.run_attempt_count ?? 0))}</td>
          <td>${ajusteTxt}</td>
        </tr>
      `;
    })
    .join("");
}

function renderVisionStopsPagination() {
  const pagination = document.getElementById("vision-stops-pagination");
  if (!pagination) {
    return;
  }
  pagination.hidden = visionStopsTotalRows <= 0;
  if (pagination.hidden) {
    return;
  }

  const start = (visionStopsCurrentPage - 1) * visionStopsPerPage + 1;
  const end = Math.min(
    visionStopsCurrentPage * visionStopsPerPage,
    visionStopsTotalRows,
  );
  const summary = document.getElementById("vision-stops-pagination-summary");
  const pageInput = document.getElementById("vision-stops-page-input");
  const pageTotal = document.getElementById("vision-stops-page-total");
  if (summary) {
    summary.textContent = `${start} - ${end} de ${visionStopsTotalRows}`;
  }
  if (pageInput) {
    pageInput.value = String(visionStopsCurrentPage);
    pageInput.max = String(visionStopsTotalPages);
  }
  if (pageTotal) {
    pageTotal.textContent = String(visionStopsTotalPages);
  }

  const atFirst = visionStopsCurrentPage <= 1;
  const atLast = visionStopsCurrentPage >= visionStopsTotalPages;
  document.getElementById("vision-stops-page-first")?.toggleAttribute("disabled", atFirst);
  document.getElementById("vision-stops-page-prev")?.toggleAttribute("disabled", atFirst);
  document.getElementById("vision-stops-page-next")?.toggleAttribute("disabled", atLast);
  document.getElementById("vision-stops-page-last")?.toggleAttribute("disabled", atLast);
}

function gotoVisionStopsPage(page) {
  const nextPage = Math.max(
    1,
    Math.min(visionStopsTotalPages, Number.parseInt(page, 10) || 1),
  );
  if (nextPage === visionStopsCurrentPage) {
    renderVisionStopsPagination();
    return;
  }
  visionStopsCurrentPage = nextPage;
  loadVisionStopsData({ resetPage: false });
}

function switchVisionTab(tab) {
  const root = document.getElementById("historial-vision-root");
  if (!root) {
    return;
  }
  root.querySelectorAll(".vision-tab").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex = active ? 0 : -1;
  });
  root.querySelectorAll("[data-tab-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.tabPanel !== tab;
  });
}

function getActiveVisionTab() {
  return (
    document.querySelector("#historial-vision-root .vision-tab.is-active")
      ?.dataset.tab || "registros"
  );
}

function loadActiveVisionTab() {
  if (getActiveVisionTab() === "paros") {
    return loadVisionStopsData();
  }
  return loadHistorialVisionData();
}

async function exportHistorialVisionToExcel() {
  const {
    fechaDesde,
    fechaHasta,
    linea,
    resultado,
    numeroParte,
    qr,
    barcode,
  } = resolveVisionFilters();

  const query = new URLSearchParams({
    fecha_desde: fechaDesde,
    fecha_hasta: fechaHasta,
    linea,
    resultado,
    numero_parte: numeroParte,
    qr,
    barcode,
  });
  Object.entries(getVisionColumnFilters("records")).forEach(([field, value]) => {
    if (String(value || "").trim()) {
      query.set(`cf_${field}`, String(value).trim());
    }
  });
  const url = `/api/vision/export?${query.toString()}`;

  await downloadVisionFile(
    url,
    `historial_vision_${Date.now()}.xlsx`,
    "Exportacion completada",
  );
}

async function exportVisionStopsToExcel() {
  const { fechaDesde, fechaHasta, linea } = resolveVisionFilters();
  const query = new URLSearchParams({
    fecha_desde: fechaDesde,
    fecha_hasta: fechaHasta,
    linea,
  });
  Object.entries(getVisionColumnFilters("stops")).forEach(([field, value]) => {
    if (String(value || "").trim()) {
      query.set(`cf_${field}`, String(value).trim());
    }
  });
  const url = `/api/vision/stops/export?${query.toString()}`;

  await downloadVisionFile(
    url,
    `paros_vision_${Date.now()}.xlsx`,
    "Exportacion de paros completada",
  );
}

function openVisionPreviewModalContainer() {
  const modal = document.getElementById("vision-preview-modal");
  if (!modal) {
    return null;
  }

  if (modal.parentNode !== document.body) {
    document.body.appendChild(modal);
  }

  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
  return modal;
}

function closeVisionPreviewModal(options = {}) {
  const modal = document.getElementById("vision-preview-modal");
  if (!modal) {
    return;
  }

  currentVisionPreviewToken += 1;
  hideVisionImageLoading();
  resetVisionPreviewZoom();

  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");

  if (options.restoreToContainer) {
    const visionRoot = document.getElementById("historial-vision-root");
    if (visionRoot && modal.parentNode === document.body) {
      visionRoot.appendChild(modal);
    }
  }
}

function clearVisionPreviewImage() {
  const image = document.getElementById("vision-preview-image");
  if (!image) {
    return;
  }

  resetVisionPreviewZoom();
  image.onload = null;
  image.onerror = null;
  image.classList.remove("is-visible");
  image.removeAttribute("src");
}

function showVisionPreviewPlaceholder(message) {
  const emptyState = document.getElementById("vision-preview-empty");
  if (!emptyState) {
    return;
  }

  emptyState.textContent = message;
  emptyState.classList.add("is-visible");
}

function hideVisionPreviewPlaceholder() {
  const emptyState = document.getElementById("vision-preview-empty");
  if (!emptyState) {
    return;
  }

  emptyState.classList.remove("is-visible");
}

function setVisionPreviewStatus(message, type = "info") {
  const status = document.getElementById("vision-preview-status");
  if (!status) {
    return;
  }

  status.textContent = message || "-";
  status.classList.remove("is-info", "is-success", "is-error");
  status.classList.add(
    type === "success" ? "is-success" : type === "error" ? "is-error" : "is-info",
  );
}

function setVisionPreviewField(id, value, fallback = "-") {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }

  const normalized = value ?? "";
  element.textContent =
    String(normalized).trim().length > 0 ? String(normalized) : fallback;
}

function setVisionPreviewCode(id, value, fallback = "-") {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }

  const normalized = value ?? "";
  element.textContent =
    String(normalized).trim().length > 0 ? String(normalized) : fallback;
}

function buildVisionRowFallback(recordId) {
  const row = visionModuleData.find(
    (item) => String(item.id ?? "") === String(recordId ?? ""),
  );
  if (!row) {
    return {};
  }

  return {
    record_id: row.id ?? "",
    linea: row.linea ?? "",
    resultado: row.resultado ?? "",
    numero_parte: row.numero_parte ?? "",
    qr: row.qr ?? "",
    barcode: row.barcode ?? "",
    fecha_hora:
      row.fecha && row.hora ? `${row.fecha} ${row.hora}` : row.fecha ?? row.hora ?? "",
  };
}

function populateVisionPreviewInfo(data = {}, fallback = {}) {
  setVisionPreviewField("vision-preview-linea", data.linea ?? fallback.linea);
  setVisionPreviewField(
    "vision-preview-resultado",
    data.resultado ?? fallback.resultado,
  );
  setVisionPreviewField(
    "vision-preview-numero-parte",
    data.numero_parte ?? fallback.numero_parte,
  );
  setVisionPreviewField(
    "vision-preview-fecha-hora",
    data.fecha_hora ?? fallback.fecha_hora,
  );
  setVisionPreviewField("vision-preview-qr", data.qr ?? fallback.qr);
  setVisionPreviewField(
    "vision-preview-barcode",
    data.barcode ?? fallback.barcode,
  );
  setVisionPreviewCode("vision-preview-path", data.resolved_path);

  const subtitle = document.getElementById("vision-preview-subtitle");
  if (subtitle) {
    const subtitleParts = [
      data.linea ?? fallback.linea ?? "",
      data.numero_parte ?? fallback.numero_parte ?? "",
      data.resultado ?? fallback.resultado ?? "",
    ].filter((part) => String(part || "").trim().length > 0);
    subtitle.textContent =
      subtitleParts.length > 0
        ? subtitleParts.join(" | ")
        : "Doble click en un registro para cargar la imagen.";
  }
}

function prepareVisionPreview(recordId) {
  clearVisionPreviewImage();
  showVisionImageLoading();
  showVisionPreviewPlaceholder("Resolviendo imagen...");
  setVisionPreviewStatus("Buscando imagen en carpetas compartidas...", "info");
  populateVisionPreviewInfo({}, buildVisionRowFallback(recordId));
  updateVisionPreviewZoomLabel();
}

function buildVisionPreviewError(message, payload = {}) {
  const error = new Error(message);
  error.payload = payload;
  return error;
}

function loadVisionPreviewImage(imageUrl, requestToken) {
  const image = document.getElementById("vision-preview-image");
  if (!image) {
    return Promise.reject(
      buildVisionPreviewError("No se encontro el contenedor de imagen."),
    );
  }

  clearVisionPreviewImage();

  return new Promise((resolve, reject) => {
    image.onload = function () {
      if (requestToken !== currentVisionPreviewToken) {
        resolve();
        return;
      }

      resetVisionPreviewZoom();
      image.classList.add("is-visible");
      hideVisionPreviewPlaceholder();
      hideVisionImageLoading();
      resolve();
    };

    image.onerror = function () {
      if (requestToken !== currentVisionPreviewToken) {
        reject(
          buildVisionPreviewError(
            "La carga de imagen fue invalidada por una nueva solicitud.",
          ),
        );
        return;
      }

      hideVisionImageLoading();
      reject(
        buildVisionPreviewError("No se pudo cargar la imagen resuelta.", {
          image_url: imageUrl,
        }),
      );
    };

    image.src = imageUrl;
  });
}

function handleVisionPreviewError(error, recordId) {
  const payload = error?.payload || {};
  populateVisionPreviewInfo(payload, buildVisionRowFallback(recordId));
  clearVisionPreviewImage();
  hideVisionImageLoading();
  showVisionPreviewPlaceholder(
    payload.error || error?.message || "No se pudo mostrar la imagen.",
  );
  setVisionPreviewStatus(
    payload.error || error?.message || "No se pudo mostrar la imagen.",
    "error",
  );
}

async function openVisionPreviewModal(recordId) {
  const modal = openVisionPreviewModalContainer();
  if (!modal || !recordId) {
    return;
  }

  currentVisionPreviewToken += 1;
  const requestToken = currentVisionPreviewToken;
  prepareVisionPreview(recordId);

  try {
    const response = await fetch(
      `/api/vision/image-info?id=${encodeURIComponent(recordId)}&_=${Date.now()}`,
      {
        credentials: "same-origin",
      },
    );
    const data = await response.json();

    if (requestToken !== currentVisionPreviewToken) {
      return;
    }

    populateVisionPreviewInfo(data, buildVisionRowFallback(recordId));

    if (!response.ok) {
      throw buildVisionPreviewError(
        data?.error || "No se encontro imagen para el registro.",
        data,
      );
    }

    const imageUrl = `${data.image_url}${data.image_url.includes("?") ? "&" : "?"}_=${Date.now()}`;
    await loadVisionPreviewImage(imageUrl, requestToken);

    if (requestToken !== currentVisionPreviewToken) {
      return;
    }

    setVisionPreviewStatus("Imagen cargada correctamente.", "success");
  } catch (error) {
    if (requestToken !== currentVisionPreviewToken) {
      return;
    }
    console.error(error);
    handleVisionPreviewError(error, recordId);
  }
}

function initializeHistorialVisionEventListeners() {
  renderVisionColumnFilterHeaders();

  if (document.body.dataset.visionListenersAttached) {
    return;
  }

  document.body.addEventListener("click", function (e) {
    const target = e.target;
    const visionRoot = document.getElementById("historial-vision-root");

    if (!target.closest(".vision-column-filterable")) {
      closeVisionColumnFilterPopovers();
    }

    const clearColumnButton = target.closest(".vision-column-filter-clear");
    if (clearColumnButton && visionRoot?.contains(clearColumnButton)) {
      e.preventDefault();
      e.stopPropagation();
      const popover = clearColumnButton.closest(
        ".vision-column-filter-popover",
      );
      const tableKey = popover?.dataset.visionTableKey;
      const field = popover?.dataset.visionField;
      if (tableKey && field) {
        setVisionColumnFilter(tableKey, field, "");
        syncVisionColumnFilterControls(tableKey);
        renderFilteredVisionTable(tableKey);
        popover.querySelector(".vision-column-filter-input")?.focus();
      }
      return;
    }

    const clearAllButton = target.closest(".vision-column-filter-clear-all");
    if (clearAllButton && visionRoot?.contains(clearAllButton)) {
      e.preventDefault();
      e.stopPropagation();
      const popover = clearAllButton.closest(".vision-column-filter-popover");
      const tableKey = popover?.dataset.visionTableKey;
      if (tableKey) {
        clearAllVisionColumnFilters(tableKey);
        syncVisionColumnFilterControls(tableKey);
        renderFilteredVisionTable(tableKey);
        popover.querySelector(".vision-column-filter-input")?.focus();
      }
      return;
    }

    const columnFilterButton = target.closest(".vision-column-filter-btn");
    if (columnFilterButton && visionRoot?.contains(columnFilterButton)) {
      e.preventDefault();
      e.stopPropagation();
      const header = columnFilterButton.closest("th");
      const popover = header?.querySelector(".vision-column-filter-popover");
      if (!popover) {
        return;
      }
      const shouldOpen = !popover.classList.contains("open");
      closeVisionColumnFilterPopovers();
      if (shouldOpen) {
        popover.classList.add("open");
        header.classList.add("filter-open");
        columnFilterButton.classList.add("open");
        columnFilterButton.setAttribute("aria-expanded", "true");
        popover.querySelector(".vision-column-filter-input")?.focus();
      }
      return;
    }

    if (
      target.id === "vision-btn-consultar" ||
      target.closest("#vision-btn-consultar")
    ) {
      e.preventDefault();
      loadActiveVisionTab();
      return;
    }

    if (
      target.id === "vision-records-page-first" ||
      target.closest("#vision-records-page-first")
    ) {
      e.preventDefault();
      gotoVisionRecordsPage(1);
      return;
    }
    if (
      target.id === "vision-records-page-prev" ||
      target.closest("#vision-records-page-prev")
    ) {
      e.preventDefault();
      gotoVisionRecordsPage(visionRecordsCurrentPage - 1);
      return;
    }
    if (
      target.id === "vision-records-page-next" ||
      target.closest("#vision-records-page-next")
    ) {
      e.preventDefault();
      gotoVisionRecordsPage(visionRecordsCurrentPage + 1);
      return;
    }
    if (
      target.id === "vision-records-page-last" ||
      target.closest("#vision-records-page-last")
    ) {
      e.preventDefault();
      gotoVisionRecordsPage(visionRecordsTotalPages);
      return;
    }

    if (
      target.id === "vision-stops-page-first" ||
      target.closest("#vision-stops-page-first")
    ) {
      e.preventDefault();
      gotoVisionStopsPage(1);
      return;
    }
    if (
      target.id === "vision-stops-page-prev" ||
      target.closest("#vision-stops-page-prev")
    ) {
      e.preventDefault();
      gotoVisionStopsPage(visionStopsCurrentPage - 1);
      return;
    }
    if (
      target.id === "vision-stops-page-next" ||
      target.closest("#vision-stops-page-next")
    ) {
      e.preventDefault();
      gotoVisionStopsPage(visionStopsCurrentPage + 1);
      return;
    }
    if (
      target.id === "vision-stops-page-last" ||
      target.closest("#vision-stops-page-last")
    ) {
      e.preventDefault();
      gotoVisionStopsPage(visionStopsTotalPages);
      return;
    }

    const tabBtn = target.closest(".vision-tab");
    if (tabBtn && visionRoot?.contains(tabBtn)) {
      e.preventDefault();
      switchVisionTab(tabBtn.dataset.tab);
      if (tabBtn.dataset.tab === "paros") {
        loadVisionStopsData();
      }
      return;
    }

    if (
      target.id === "vision-btn-export-excel" ||
      target.closest("#vision-btn-export-excel")
    ) {
      e.preventDefault();
      exportHistorialVisionToExcel();
      return;
    }

    if (
      target.id === "vision-btn-export-stops" ||
      target.closest("#vision-btn-export-stops")
    ) {
      e.preventDefault();
      exportVisionStopsToExcel();
      return;
    }

    if (
      target.id === "vision-preview-close" ||
      target.closest("#vision-preview-close")
    ) {
      e.preventDefault();
      closeVisionPreviewModal();
      return;
    }

    if (target.id === "vision-zoom-in" || target.closest("#vision-zoom-in")) {
      e.preventDefault();
      adjustVisionPreviewZoom(0.25);
      return;
    }

    if (target.id === "vision-zoom-out" || target.closest("#vision-zoom-out")) {
      e.preventDefault();
      adjustVisionPreviewZoom(-0.25);
      return;
    }

    if (
      target.id === "vision-zoom-reset" ||
      target.closest("#vision-zoom-reset")
    ) {
      e.preventDefault();
      resetVisionPreviewZoom();
      return;
    }

    if (target.id === "vision-preview-modal") {
      e.preventDefault();
      closeVisionPreviewModal();
    }
  });

  document.body.addEventListener("dblclick", function (e) {
    const row = e.target.closest("#vision-body tr[data-record-id]");
    const visionRoot = document.getElementById("historial-vision-root");

    if (!row || !visionRoot || !visionRoot.contains(row)) {
      return;
    }

    const recordId = row.dataset.recordId;
    if (!recordId) {
      return;
    }

    e.preventDefault();
    openVisionPreviewModal(recordId);
  });

  document.body.addEventListener("keydown", function (e) {
    const modal = document.getElementById("vision-preview-modal");
    if (e.key === "Escape" && modal?.classList.contains("active")) {
      e.preventDefault();
      closeVisionPreviewModal();
      return;
    }

    const visionRoot = document.getElementById("historial-vision-root");
    if (!visionRoot || !e.target || !visionRoot.contains(e.target)) {
      return;
    }

    if (e.target.id === "vision-records-page-input") {
      if (e.key === "Enter") {
        e.preventDefault();
        gotoVisionRecordsPage(e.target.value);
      }
      return;
    }

    if (e.target.id === "vision-stops-page-input") {
      if (e.key === "Enter") {
        e.preventDefault();
        gotoVisionStopsPage(e.target.value);
      }
      return;
    }

    if (e.target.matches(".vision-column-filter-input")) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeVisionColumnFilterPopovers();
      }
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      loadActiveVisionTab();
    }
  });

  document.body.addEventListener("input", function (e) {
    const visionRoot = document.getElementById("historial-vision-root");
    if (!visionRoot || !e.target || !visionRoot.contains(e.target)) {
      return;
    }

    if (e.target.matches(".vision-column-filter-input")) {
      const tableKey = e.target.dataset.visionTableKey;
      const field = e.target.dataset.visionField;
      if (tableKey && field) {
        setVisionColumnFilter(tableKey, field, e.target.value);
        e.target
          .closest("th")
          ?.querySelector(".vision-column-filter-btn")
          ?.classList.toggle("active", Boolean(e.target.value.trim()));
        renderFilteredVisionTable(tableKey);
      }
      return;
    }

    if (
      e.target.id === "vision-filter-fecha-desde" ||
      e.target.id === "vision-filter-fecha-hasta" ||
      e.target.id === "vision-filter-linea" ||
      e.target.id === "vision-filter-numero-parte" ||
      e.target.id === "vision-filter-qr" ||
      e.target.id === "vision-filter-barcode"
    ) {
      saveVisionFilters();
    }
  });

  document.body.addEventListener("change", function (e) {
    const visionRoot = document.getElementById("historial-vision-root");
    if (!visionRoot || !e.target || !visionRoot.contains(e.target)) {
      return;
    }

    if (e.target.id === "vision-filter-resultado") {
      saveVisionFilters();
      return;
    }

    if (e.target.id === "vision-stops-per-page") {
      const perPage = Number.parseInt(e.target.value, 10);
      if (perPage > 0) {
        visionStopsPerPage = perPage;
        visionStopsCurrentPage = 1;
        loadVisionStopsData({ resetPage: false });
      }
      return;
    }

    if (e.target.id === "vision-records-per-page") {
      const perPage = Number.parseInt(e.target.value, 10);
      if (perPage > 0) {
        visionRecordsPerPage = perPage;
        visionRecordsCurrentPage = 1;
        loadHistorialVisionData({ resetPage: false });
      }
    }
  });

  document.body.addEventListener(
    "wheel",
    function (e) {
      const stage = e.target.closest("#vision-preview-stage");
      const image = getVisionPreviewImage();
      if (!stage || !image || !image.classList.contains("is-visible")) {
        return;
      }

      e.preventDefault();
      adjustVisionPreviewZoom(e.deltaY < 0 ? 0.2 : -0.2);
    },
    { passive: false },
  );

  document.body.addEventListener("pointerdown", function (e) {
    const stage = e.target.closest("#vision-preview-stage");
    const image = getVisionPreviewImage();
    if (!stage || !image || !image.classList.contains("is-visible")) {
      return;
    }

    if (visionPreviewState.scale <= 1) {
      return;
    }

    e.preventDefault();
    visionPreviewState.isDragging = true;
    visionPreviewState.pointerId = e.pointerId;
    visionPreviewState.dragStartX = e.clientX - visionPreviewState.translateX;
    visionPreviewState.dragStartY = e.clientY - visionPreviewState.translateY;
    applyVisionPreviewTransform();
  });

  document.body.addEventListener("pointermove", function (e) {
    if (
      !visionPreviewState.isDragging ||
      visionPreviewState.pointerId !== e.pointerId
    ) {
      return;
    }

    e.preventDefault();
    visionPreviewState.translateX = e.clientX - visionPreviewState.dragStartX;
    visionPreviewState.translateY = e.clientY - visionPreviewState.dragStartY;
    applyVisionPreviewTransform();
  });

  document.body.addEventListener("pointerup", function (e) {
    if (visionPreviewState.pointerId !== e.pointerId) {
      return;
    }
    stopVisionPreviewDrag();
  });

  document.body.addEventListener("pointercancel", function (e) {
    if (visionPreviewState.pointerId !== e.pointerId) {
      return;
    }
    stopVisionPreviewDrag();
  });

  document.body.dataset.visionListenersAttached = "true";
}

function showVisionNotification(message, type = "info") {
  const existingNotification = document.querySelector(".vision-notification");
  if (existingNotification) {
    existingNotification.remove();
  }

  const notification = document.createElement("div");
  notification.className = "vision-notification";
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 10px;
    color: white;
    font-weight: 700;
    font-size: 0.9rem;
    z-index: 10000;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28);
  `;

  if (type === "success") {
    notification.style.backgroundColor = "#1f8f55";
  } else if (type === "error") {
    notification.style.backgroundColor = "#c0392b";
  } else {
    notification.style.backgroundColor = "#20688c";
  }

  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 3500);
}

function setVisionDefaultDate() {
  resolveVisionFilters();
}

function escapeVisionHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

window.initializeHistorialVisionEventListeners =
  initializeHistorialVisionEventListeners;
window.loadHistorialVisionData = loadHistorialVisionData;
window.exportHistorialVisionToExcel = exportHistorialVisionToExcel;
window.exportVisionStopsToExcel = exportVisionStopsToExcel;
window.openVisionPreviewModal = openVisionPreviewModal;
window.closeVisionPreviewModal = closeVisionPreviewModal;

document.addEventListener("DOMContentLoaded", function () {
  setVisionDefaultDate();
  initializeHistorialVisionEventListeners();
  loadHistorialVisionData();
});

if (
  document.readyState === "interactive" ||
  document.readyState === "complete"
) {
  setVisionDefaultDate();
  initializeHistorialVisionEventListeners();
  setTimeout(() => loadHistorialVisionData(), 100);
}
