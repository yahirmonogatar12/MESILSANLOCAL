let ictPassFailModuleData = [];
let ictPassFailDetailContext = null;
let ictPassFailDetailSearchTimer = null;
const ICT_PASS_FAIL_FILTERS_STORAGE_KEY = "historialIctPassFailFilters";
const ICT_PASS_FAIL_LISTENER_VERSION = "20260429e";

function getIctPassFailToday() {
  return new Date().toISOString().split("T")[0];
}

function getIctPassFailFilterElements() {
  return {
    fechaDesde: document.getElementById("ict-pass-fail-filter-fecha-desde"),
    fechaHasta: document.getElementById("ict-pass-fail-filter-fecha-hasta"),
    numeroParte: document.getElementById("ict-pass-fail-filter-numero-parte"),
    turno: document.getElementById("ict-pass-fail-filter-turno"),
    barcode: document.getElementById("ict-pass-fail-filter-barcode"),
  };
}

function getStoredIctPassFailFilters() {
  try {
    const rawValue = window.sessionStorage.getItem(ICT_PASS_FAIL_FILTERS_STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    const parsedValue = JSON.parse(rawValue);
    return parsedValue && typeof parsedValue === "object" ? parsedValue : null;
  } catch (error) {
    console.warn("No se pudo leer el estado de filtros de ICT Pass/Fail", error);
    return null;
  }
}

function saveIctPassFailFilters(filters = null) {
  const elements = getIctPassFailFilterElements();
  const nextFilters = filters || {
    fechaDesde: elements.fechaDesde?.value || "",
    fechaHasta: elements.fechaHasta?.value || "",
    numeroParte: elements.numeroParte?.value || "",
    turno: elements.turno?.value || "",
    barcode: elements.barcode?.value || "",
  };

  try {
    window.sessionStorage.setItem(
      ICT_PASS_FAIL_FILTERS_STORAGE_KEY,
      JSON.stringify(nextFilters),
    );
  } catch (error) {
    console.warn("No se pudo guardar el estado de filtros de ICT Pass/Fail", error);
  }

  return nextFilters;
}

function resolveIctPassFailFilters() {
  const elements = getIctPassFailFilterElements();
  const storedFilters = getStoredIctPassFailFilters() || {};
  const today = getIctPassFailToday();

  const resolvedFilters = {
    fechaDesde: elements.fechaDesde?.value || storedFilters.fechaDesde || today,
    fechaHasta: elements.fechaHasta?.value || storedFilters.fechaHasta || today,
    numeroParte: elements.numeroParte?.value || storedFilters.numeroParte || "",
    turno: elements.turno?.value || storedFilters.turno || "",
    barcode: elements.barcode?.value || storedFilters.barcode || "",
  };

  if (elements.fechaDesde) {
    elements.fechaDesde.value = resolvedFilters.fechaDesde;
  }

  if (elements.fechaHasta) {
    elements.fechaHasta.value = resolvedFilters.fechaHasta;
  }

  if (elements.numeroParte) {
    elements.numeroParte.value = resolvedFilters.numeroParte;
  }

  if (elements.turno) {
    elements.turno.value = resolvedFilters.turno;
  }

  if (elements.barcode) {
    elements.barcode.value = resolvedFilters.barcode;
  }

  saveIctPassFailFilters(resolvedFilters);
  return resolvedFilters;
}

function showIctPassFailLoading() {
  const loader = document.getElementById("ict-pass-fail-table-loading");
  if (loader) {
    loader.classList.add("active");
  }
}

function hideIctPassFailLoading() {
  const loader = document.getElementById("ict-pass-fail-table-loading");
  if (loader) {
    loader.classList.remove("active");
  }
}

function cleanupIctPassFailModule() {
  hideIctPassFailLoading();
  closeIctPassFailDetailModal({ restoreToContainer: true });
}

window.limpiarHistorialICTPassFail = cleanupIctPassFailModule;

async function downloadIctPassFailFile(url, fallbackName, successMessage) {
  try {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
    });

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      let errorMessage = `Error al descargar archivo (status ${response.status})`;

      if (contentType.includes("application/json")) {
        const errorData = await response.json().catch(() => null);
        if (errorData?.error) {
          errorMessage = `${errorMessage}: ${errorData.error}`;
        }
      } else {
        const errorText = await response.text().catch(() => "");
        if (errorText) {
          errorMessage = `${errorMessage}: ${errorText.slice(0, 180)}`;
        }
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

    showIctPassFailNotification(successMessage, "success");
  } catch (error) {
    console.error(error);
    showIctPassFailNotification("Error al descargar el archivo", "error");
  }
}

async function loadHistorialIctPassFailData() {
  showIctPassFailLoading();

  try {
    const { fechaDesde, fechaHasta, numeroParte, turno, barcode } =
      resolveIctPassFailFilters();

    const url =
      `/api/ict/pass-fail?fecha_desde=${encodeURIComponent(fechaDesde)}` +
      `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
      `&numero_parte=${encodeURIComponent(numeroParte)}` +
      `&turno=${encodeURIComponent(turno)}` +
      `&barcode=${encodeURIComponent(barcode)}`;

    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error || "Error al consultar historial ICT % pass/fail");
    }

    ictPassFailModuleData = Array.isArray(data) ? data : [];

    const recordCount = document.getElementById("ict-pass-fail-record-count");
    if (recordCount) {
      recordCount.textContent = `${ictPassFailModuleData.length} registro${ictPassFailModuleData.length !== 1 ? "s" : ""}`;
    }

    renderHistorialIctPassFailTable(ictPassFailModuleData);
  } catch (error) {
    console.error(error);
    renderHistorialIctPassFailTable([]);
    showIctPassFailNotification("Error al cargar datos", "error");
  } finally {
    hideIctPassFailLoading();
  }
}

function renderHistorialIctPassFailTable(data) {
  const tbody = document.getElementById("ict-pass-fail-body");
  if (!tbody) {
    return;
  }

  if (!Array.isArray(data) || data.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="11" class="ict-pass-fail-table-empty">No se encontraron registros.</td></tr>';
    return;
  }

  tbody.innerHTML = data
    .map((row, index) => {
      const passRate = Number(row.porcentaje_ok || 0);
      const failRate = Number(row.porcentaje_ng || 0);

      return `
        <tr class="ict-pass-fail-summary-row" data-ict-pass-fail-row-index="${index}" title="Doble click para ver detalle por barcode">
          <td>${escapeIctPassFailHtml(row.fecha ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.linea ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.ict ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.turno ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.numero_parte ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.total ?? 0)}</td>
          <td>${escapeIctPassFailHtml(row.ok_count ?? 0)}</td>
          <td>${escapeIctPassFailHtml(row.ng_count ?? 0)}</td>
          <td class="${passRate >= 90 ? "ict-pass-fail-rate-good" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(passRate))}</td>
          <td class="${failRate > 10 ? "ict-pass-fail-rate-bad" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(failRate))}</td>
          <td>${buildIctPassFailBar(passRate, failRate)}</td>
        </tr>
      `;
    })
    .join("");
}

function buildIctPassFailBar(passRate, failRate) {
  const okWidth = normalizeIctPassFailBarWidth(passRate);
  const ngWidth = normalizeIctPassFailBarWidth(failRate);
  const passLabel = formatIctPassFailPercent(passRate);
  const failLabel = formatIctPassFailPercent(failRate);

  return `
    <div class="ict-pass-fail-bar-row" aria-label="OK ${passLabel} NG ${failLabel}">
      <div class="ict-pass-fail-bar">
        <span class="ict-pass-fail-bar-ok" style="width: ${okWidth}%">
          <span class="ict-pass-fail-bar-label">${escapeIctPassFailHtml(passLabel)}</span>
        </span>
        <span class="ict-pass-fail-bar-ng" style="width: ${ngWidth}%"></span>
      </div>
      <span class="ict-pass-fail-bar-side-label">${escapeIctPassFailHtml(failLabel)}</span>
    </div>
  `;
}

function normalizeIctPassFailBarWidth(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(100, numeric));
}

function formatIctPassFailPercent(value) {
  const numeric = Number(value || 0);
  return `${numeric.toFixed(2)}%`;
}

function formatIctPassFailNumber(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) {
    return "0";
  }

  return numeric.toLocaleString("en-US");
}

function getIctPassFailDetailModal() {
  const modals = Array.from(
    document.querySelectorAll("#ict-pass-fail-detail-modal"),
  );
  if (modals.length <= 1) {
    return modals[0] || null;
  }

  const rootModal = document
    .getElementById("historial-ict-pass-fail-root")
    ?.querySelector("#ict-pass-fail-detail-modal");
  const keepModal = rootModal || modals[modals.length - 1];

  modals.forEach((modal) => {
    if (modal !== keepModal) {
      modal.remove();
    }
  });

  return keepModal;
}

function setIctPassFailDetailLoading(isLoading) {
  const loader = document.getElementById("ict-pass-fail-detail-loading");
  if (!loader) {
    return;
  }

  loader.classList.toggle("active", Boolean(isLoading));
}

function setIctPassFailDetailSummary(summary = {}) {
  const values = {
    "ict-pass-fail-detail-total-intentos": formatIctPassFailNumber(summary.total_intentos),
    "ict-pass-fail-detail-ok-total": formatIctPassFailNumber(summary.ok_total),
    "ict-pass-fail-detail-ng-total": formatIctPassFailNumber(summary.ng_total),
    "ict-pass-fail-detail-piezas-unicas": formatIctPassFailNumber(summary.piezas_unicas),
    "ict-pass-fail-detail-repetidas": formatIctPassFailNumber(summary.piezas_repetidas),
    "ict-pass-fail-detail-reparacion": formatIctPassFailNumber(summary.piezas_reparacion),
    "ict-pass-fail-detail-pass-real": formatIctPassFailNumber(summary.pass_real),
    "ict-pass-fail-detail-pass-rate": formatIctPassFailPercent(summary.porcentaje_pass_real),
  };

  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value;
    }
  });
}

function renderIctPassFailDetailRows(rows) {
  const tbody = document.getElementById("ict-pass-fail-detail-body");
  if (!tbody) {
    return;
  }

  if (!Array.isArray(rows) || rows.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="13" class="ict-pass-fail-table-empty">No se encontraron barcodes para este detalle.</td></tr>';
    return;
  }

  tbody.innerHTML = rows
    .map((row) => {
      const intentos = Number(row.intentos || 0);
      const fueReparacion = Boolean(row.fue_reparacion);
      const resultadoPrimer = String(row.resultado_primer || "").toUpperCase();
      const resultadoFinal = String(row.resultado_final || "").toUpperCase();
      const defectText = row.defectos || (fueReparacion ? "SIN DEFECTO CAPTURADO" : "NO");
      const rowClasses = [
        intentos > 1 ? "ict-pass-fail-detail-repeated-row" : "",
        fueReparacion ? "ict-pass-fail-detail-repair-row" : "",
      ]
        .filter(Boolean)
        .join(" ");

      return `
        <tr class="${rowClasses}">
          <td>${escapeIctPassFailHtml(row.barcode ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.numero_parte ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.linea ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.ict ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.turno ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.primer_test ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.ultimo_test ?? "")}</td>
          <td><span class="${intentos > 1 ? "ict-pass-fail-detail-badge-warn" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(intentos)}</span></td>
          <td>${escapeIctPassFailHtml(row.ok_count ?? 0)}</td>
          <td>${escapeIctPassFailHtml(row.ng_count ?? 0)}</td>
          <td><span class="${resultadoPrimer === "OK" ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge-ng"}">${escapeIctPassFailHtml(resultadoPrimer || "-")}</span></td>
          <td><span class="${resultadoFinal === "OK" ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge-ng"}">${escapeIctPassFailHtml(resultadoFinal || "-")}</span></td>
          <td class="ict-pass-fail-detail-defect-cell" title="${escapeIctPassFailHtml(defectText)}">${escapeIctPassFailHtml(defectText)}</td>
        </tr>
      `;
    })
    .join("");
}

function openIctPassFailDetailModal(row) {
  const modal = getIctPassFailDetailModal();
  if (!modal || !row) {
    return;
  }

  if (modal.parentNode !== document.body) {
    document.body.appendChild(modal);
  }

  ictPassFailDetailContext = {
    fecha: row.fecha || "",
    linea: row.linea || "",
    ict: row.ict || "",
    turno: row.turno || "",
    numeroParte: row.numero_parte || "",
  };

  const title = document.getElementById("ict-pass-fail-detail-title");
  const subtitle = document.getElementById("ict-pass-fail-detail-subtitle");
  const detailBarcodeFilter = document.getElementById("ict-pass-fail-detail-filter-barcode");
  const detailIntentosFilter = document.getElementById("ict-pass-fail-detail-filter-intentos");
  const mainBarcodeFilter = getIctPassFailFilterElements().barcode;

  if (title) {
    title.textContent = "Detalle ICT Pass/Fail";
  }

  if (subtitle) {
    subtitle.textContent =
      `${ictPassFailDetailContext.fecha} | ${ictPassFailDetailContext.linea} | ICT ${ictPassFailDetailContext.ict} | ${ictPassFailDetailContext.turno} | ${ictPassFailDetailContext.numeroParte}`;
  }

  if (detailBarcodeFilter) {
    detailBarcodeFilter.value = mainBarcodeFilter?.value || "";
  }

  if (detailIntentosFilter) {
    detailIntentosFilter.value = "1";
  }

  setIctPassFailDetailSummary({});
  renderIctPassFailDetailRows([]);
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("ict-pass-fail-detail-open");
  loadIctPassFailDetailData();
}

function closeIctPassFailDetailModal(options = {}) {
  const modal = getIctPassFailDetailModal();
  if (!modal) {
    return;
  }

  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("ict-pass-fail-detail-open");
  ictPassFailDetailContext = null;
  setIctPassFailDetailLoading(false);

  if (ictPassFailDetailSearchTimer) {
    window.clearTimeout(ictPassFailDetailSearchTimer);
    ictPassFailDetailSearchTimer = null;
  }

  if (options.restoreToContainer) {
    const ictPassFailRoot = document.getElementById("historial-ict-pass-fail-root");
    if (ictPassFailRoot && modal.parentNode === document.body) {
      ictPassFailRoot.appendChild(modal);
    }
  }
}

function scheduleIctPassFailDetailReload() {
  if (!ictPassFailDetailContext) {
    return;
  }

  if (ictPassFailDetailSearchTimer) {
    window.clearTimeout(ictPassFailDetailSearchTimer);
  }

  ictPassFailDetailSearchTimer = window.setTimeout(() => {
    loadIctPassFailDetailData();
  }, 350);
}

async function loadIctPassFailDetailData() {
  if (!ictPassFailDetailContext) {
    return;
  }

  setIctPassFailDetailLoading(true);

  try {
    const barcode = document.getElementById("ict-pass-fail-detail-filter-barcode")?.value || "";
    const minIntentos =
      document.getElementById("ict-pass-fail-detail-filter-intentos")?.value || "1";
    const params = new URLSearchParams({
      fecha: ictPassFailDetailContext.fecha,
      linea: ictPassFailDetailContext.linea,
      ict: String(ictPassFailDetailContext.ict),
      turno: ictPassFailDetailContext.turno,
      numero_parte: ictPassFailDetailContext.numeroParte,
      barcode,
      min_intentos: minIntentos,
    });

    const response = await fetch(`/api/ict/pass-fail/detail?${params.toString()}`, {
      credentials: "same-origin",
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error || "Error al consultar detalle ICT Pass/Fail");
    }

    setIctPassFailDetailSummary(data.summary || {});
    renderIctPassFailDetailRows(Array.isArray(data.rows) ? data.rows : []);
  } catch (error) {
    console.error(error);
    setIctPassFailDetailSummary({});
    renderIctPassFailDetailRows([]);
    showIctPassFailNotification("Error al cargar detalle", "error");
  } finally {
    setIctPassFailDetailLoading(false);
  }
}

async function exportHistorialIctPassFailToExcel() {
  const { fechaDesde, fechaHasta, numeroParte, turno, barcode } =
    resolveIctPassFailFilters();

  const url =
    `/api/ict/pass-fail/export?fecha_desde=${encodeURIComponent(fechaDesde)}` +
    `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
    `&numero_parte=${encodeURIComponent(numeroParte)}` +
    `&turno=${encodeURIComponent(turno)}` +
    `&barcode=${encodeURIComponent(barcode)}`;

  await downloadIctPassFailFile(
    url,
    `historial_ict_pass_fail_${Date.now()}.xlsx`,
    "Exportacion completada",
  );
}

function initializeHistorialIctPassFailEventListeners() {
  if (
    document.body.dataset.ictPassFailListenersAttached ===
    ICT_PASS_FAIL_LISTENER_VERSION
  ) {
    return;
  }

  const listenerOptions = {};
  if (typeof AbortController !== "undefined") {
    if (window.__ictPassFailListenersAbortController) {
      window.__ictPassFailListenersAbortController.abort();
    }
    window.__ictPassFailListenersAbortController = new AbortController();
    listenerOptions.signal = window.__ictPassFailListenersAbortController.signal;
  }

  document.body.addEventListener("click", function (e) {
    const target = e.target;

    if (
      target.id === "ict-pass-fail-btn-consultar" ||
      target.closest("#ict-pass-fail-btn-consultar")
    ) {
      e.preventDefault();
      loadHistorialIctPassFailData();
      return;
    }

    if (
      target.id === "ict-pass-fail-btn-export-excel" ||
      target.closest("#ict-pass-fail-btn-export-excel")
    ) {
      e.preventDefault();
      exportHistorialIctPassFailToExcel();
      return;
    }

    if (target.closest("[data-ict-pass-fail-detail-close]")) {
      e.preventDefault();
      closeIctPassFailDetailModal();
    }
  }, listenerOptions);

  document.body.addEventListener("dblclick", function (e) {
    const tableRow = e.target.closest(
      "#ict-pass-fail-body tr[data-ict-pass-fail-row-index]",
    );
    if (!tableRow) {
      return;
    }

    const rowIndex = Number(tableRow.dataset.ictPassFailRowIndex);
    const row = ictPassFailModuleData[rowIndex];
    if (row) {
      openIctPassFailDetailModal(row);
    }
  }, listenerOptions);

  document.body.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && getIctPassFailDetailModal()?.classList.contains("is-open")) {
      closeIctPassFailDetailModal();
      return;
    }

    if (e.key === "Enter" && e.target?.id === "ict-pass-fail-detail-filter-barcode") {
      e.preventDefault();
      loadIctPassFailDetailData();
      return;
    }

    const ictPassFailRoot = document.getElementById("historial-ict-pass-fail-root");
    if (!ictPassFailRoot || !e.target || !ictPassFailRoot.contains(e.target)) {
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      loadHistorialIctPassFailData();
    }
  }, listenerOptions);

  document.body.addEventListener("input", function (e) {
    if (e.target?.id === "ict-pass-fail-detail-filter-barcode") {
      scheduleIctPassFailDetailReload();
      return;
    }

    const ictPassFailRoot = document.getElementById("historial-ict-pass-fail-root");
    if (!ictPassFailRoot || !e.target || !ictPassFailRoot.contains(e.target)) {
      return;
    }

    if (
      e.target.id === "ict-pass-fail-filter-fecha-desde" ||
      e.target.id === "ict-pass-fail-filter-fecha-hasta" ||
      e.target.id === "ict-pass-fail-filter-numero-parte" ||
      e.target.id === "ict-pass-fail-filter-turno" ||
      e.target.id === "ict-pass-fail-filter-barcode"
    ) {
      saveIctPassFailFilters();
    }
  }, listenerOptions);

  document.body.addEventListener("change", function (e) {
    if (e.target.id === "ict-pass-fail-detail-filter-intentos") {
      loadIctPassFailDetailData();
    }
  }, listenerOptions);

  document.body.dataset.ictPassFailListenersAttached =
    ICT_PASS_FAIL_LISTENER_VERSION;
}

function showIctPassFailNotification(message, type = "info") {
  const existingNotification = document.querySelector(".ict-pass-fail-notification");
  if (existingNotification) {
    existingNotification.remove();
  }

  const notification = document.createElement("div");
  notification.className = "ict-pass-fail-notification";
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

function setIctPassFailDefaultDate() {
  resolveIctPassFailFilters();
}

function escapeIctPassFailHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

window.initializeHistorialIctPassFailEventListeners =
  initializeHistorialIctPassFailEventListeners;
window.loadHistorialIctPassFailData = loadHistorialIctPassFailData;
window.exportHistorialIctPassFailToExcel = exportHistorialIctPassFailToExcel;
window.initializeIctPassFailEventListeners =
  initializeHistorialIctPassFailEventListeners;
window.loadIctPassFailData = loadHistorialIctPassFailData;

document.addEventListener("DOMContentLoaded", function () {
  setIctPassFailDefaultDate();
  initializeHistorialIctPassFailEventListeners();
  loadHistorialIctPassFailData();
});

if (document.readyState === "interactive" || document.readyState === "complete") {
  setIctPassFailDefaultDate();
  initializeHistorialIctPassFailEventListeners();
  setTimeout(() => loadHistorialIctPassFailData(), 100);
}
