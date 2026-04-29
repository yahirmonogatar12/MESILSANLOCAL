let ictPassFailModuleData = [];
const ICT_PASS_FAIL_FILTERS_STORAGE_KEY = "historialIctPassFailFilters";

function getIctPassFailToday() {
  return new Date().toISOString().split("T")[0];
}

function getIctPassFailFilterElements() {
  return {
    fechaDesde: document.getElementById("ict-pass-fail-filter-fecha-desde"),
    fechaHasta: document.getElementById("ict-pass-fail-filter-fecha-hasta"),
    numeroParte: document.getElementById("ict-pass-fail-filter-numero-parte"),
    turno: document.getElementById("ict-pass-fail-filter-turno"),
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
    const { fechaDesde, fechaHasta, numeroParte, turno } =
      resolveIctPassFailFilters();

    const url =
      `/api/ict/pass-fail?fecha_desde=${encodeURIComponent(fechaDesde)}` +
      `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
      `&numero_parte=${encodeURIComponent(numeroParte)}` +
      `&turno=${encodeURIComponent(turno)}`;

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
    .map((row) => {
      const passRate = Number(row.porcentaje_ok || 0);
      const failRate = Number(row.porcentaje_ng || 0);

      return `
        <tr>
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

async function exportHistorialIctPassFailToExcel() {
  const { fechaDesde, fechaHasta, numeroParte, turno } =
    resolveIctPassFailFilters();

  const url =
    `/api/ict/pass-fail/export?fecha_desde=${encodeURIComponent(fechaDesde)}` +
    `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
    `&numero_parte=${encodeURIComponent(numeroParte)}` +
    `&turno=${encodeURIComponent(turno)}`;

  await downloadIctPassFailFile(
    url,
    `historial_ict_pass_fail_${Date.now()}.xlsx`,
    "Exportacion completada",
  );
}

function initializeHistorialIctPassFailEventListeners() {
  if (document.body.dataset.ictPassFailListenersAttached) {
    return;
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
    }
  });

  document.body.addEventListener("keydown", function (e) {
    const ictPassFailRoot = document.getElementById("historial-ict-pass-fail-root");
    if (!ictPassFailRoot || !e.target || !ictPassFailRoot.contains(e.target)) {
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      loadHistorialIctPassFailData();
    }
  });

  document.body.addEventListener("input", function (e) {
    const ictPassFailRoot = document.getElementById("historial-ict-pass-fail-root");
    if (!ictPassFailRoot || !e.target || !ictPassFailRoot.contains(e.target)) {
      return;
    }

    if (
      e.target.id === "ict-pass-fail-filter-fecha-desde" ||
      e.target.id === "ict-pass-fail-filter-fecha-hasta" ||
      e.target.id === "ict-pass-fail-filter-numero-parte" ||
      e.target.id === "ict-pass-fail-filter-turno"
    ) {
      saveIctPassFailFilters();
    }
  });

  document.body.dataset.ictPassFailListenersAttached = "true";
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
