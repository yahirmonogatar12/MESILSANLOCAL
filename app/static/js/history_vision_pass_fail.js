let visionPassFailModuleData = [];
const VISION_PASS_FAIL_FILTERS_STORAGE_KEY =
  "historialVisionPassFailFilters";

function getVisionPassFailToday() {
  return new Date().toISOString().split("T")[0];
}

function getVisionPassFailFilterElements() {
  return {
    fechaDesde: document.getElementById("vision-pass-fail-filter-fecha-desde"),
    fechaHasta: document.getElementById("vision-pass-fail-filter-fecha-hasta"),
    numeroParte: document.getElementById(
      "vision-pass-fail-filter-numero-parte",
    ),
  };
}

function getStoredVisionPassFailFilters() {
  try {
    const rawValue = window.sessionStorage.getItem(
      VISION_PASS_FAIL_FILTERS_STORAGE_KEY,
    );
    if (!rawValue) {
      return null;
    }

    const parsedValue = JSON.parse(rawValue);
    return parsedValue && typeof parsedValue === "object" ? parsedValue : null;
  } catch (error) {
    console.warn("No se pudo leer el estado de filtros de Vision Pass/Fail", error);
    return null;
  }
}

function saveVisionPassFailFilters(filters = null) {
  const elements = getVisionPassFailFilterElements();
  const nextFilters = filters || {
    fechaDesde: elements.fechaDesde?.value || "",
    fechaHasta: elements.fechaHasta?.value || "",
    numeroParte: elements.numeroParte?.value || "",
  };

  try {
    window.sessionStorage.setItem(
      VISION_PASS_FAIL_FILTERS_STORAGE_KEY,
      JSON.stringify(nextFilters),
    );
  } catch (error) {
    console.warn("No se pudo guardar el estado de filtros de Vision Pass/Fail", error);
  }

  return nextFilters;
}

function resolveVisionPassFailFilters() {
  const elements = getVisionPassFailFilterElements();
  const storedFilters = getStoredVisionPassFailFilters() || {};
  const today = getVisionPassFailToday();

  const resolvedFilters = {
    fechaDesde:
      elements.fechaDesde?.value ||
      storedFilters.fechaDesde ||
      today,
    fechaHasta:
      elements.fechaHasta?.value ||
      storedFilters.fechaHasta ||
      today,
    numeroParte:
      elements.numeroParte?.value ||
      storedFilters.numeroParte ||
      "",
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

  saveVisionPassFailFilters(resolvedFilters);
  return resolvedFilters;
}

function showVisionPassFailLoading() {
  const loader = document.getElementById("vision-pass-fail-table-loading");
  if (loader) {
    loader.classList.add("active");
  }
}

function hideVisionPassFailLoading() {
  const loader = document.getElementById("vision-pass-fail-table-loading");
  if (loader) {
    loader.classList.remove("active");
  }
}

function cleanupVisionPassFailModule() {
  hideVisionPassFailLoading();
}

window.limpiarHistorialVisionPassFail = cleanupVisionPassFailModule;

async function downloadVisionPassFailFile(url, fallbackName, successMessage) {
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

    showVisionPassFailNotification(successMessage, "success");
  } catch (error) {
    console.error(error);
    showVisionPassFailNotification("Error al descargar el archivo", "error");
  }
}

async function loadHistorialVisionPassFailData() {
  showVisionPassFailLoading();

  try {
    const { fechaDesde, fechaHasta, numeroParte } =
      resolveVisionPassFailFilters();

    const url =
      `/api/vision/pass-fail-summary?fecha_desde=${encodeURIComponent(fechaDesde)}` +
      `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
      `&numero_parte=${encodeURIComponent(numeroParte)}`;

    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data?.error || "Error al consultar historial vision % pass/fail",
      );
    }

    visionPassFailModuleData = Array.isArray(data) ? data : [];

    const recordCount = document.getElementById("vision-pass-fail-record-count");
    if (recordCount) {
      recordCount.textContent = `${visionPassFailModuleData.length} part number${visionPassFailModuleData.length !== 1 ? "s" : ""}`;
    }

    renderHistorialVisionPassFailTable(visionPassFailModuleData);
  } catch (error) {
    console.error(error);
    renderHistorialVisionPassFailTable([]);
    showVisionPassFailNotification("Error al cargar datos", "error");
  } finally {
    hideVisionPassFailLoading();
  }
}

function renderHistorialVisionPassFailTable(data) {
  const tbody = document.getElementById("vision-pass-fail-body");
  if (!tbody) {
    return;
  }

  if (!Array.isArray(data) || data.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="vision-pass-fail-table-empty">No se encontraron registros.</td></tr>';
    return;
  }

  tbody.innerHTML = data
    .map((row) => {
      const passRate = Number(row.porcentaje_ok || 0);
      const failRate = Number(row.porcentaje_ng || 0);

      return `
        <tr>
          <td>${escapeVisionPassFailHtml(row.numero_parte ?? "")}</td>
          <td>${escapeVisionPassFailHtml(row.total ?? 0)}</td>
          <td>${escapeVisionPassFailHtml(row.ok_count ?? 0)}</td>
          <td>${escapeVisionPassFailHtml(row.ng_count ?? 0)}</td>
          <td class="${passRate >= 90 ? "vision-pass-fail-rate-good" : "vision-pass-fail-rate-neutral"}">${escapeVisionPassFailHtml(formatVisionPassFailPercent(passRate))}</td>
          <td class="${failRate > 10 ? "vision-pass-fail-rate-bad" : "vision-pass-fail-rate-neutral"}">${escapeVisionPassFailHtml(formatVisionPassFailPercent(failRate))}</td>
        </tr>
      `;
    })
    .join("");
}

function formatVisionPassFailPercent(value) {
  const numeric = Number(value || 0);
  return `${numeric.toFixed(2)}%`;
}

async function exportHistorialVisionPassFailToExcel() {
  const { fechaDesde, fechaHasta, numeroParte } =
    resolveVisionPassFailFilters();

  const url =
    `/api/vision/pass-fail-summary/export?fecha_desde=${encodeURIComponent(fechaDesde)}` +
    `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
    `&numero_parte=${encodeURIComponent(numeroParte)}`;

  await downloadVisionPassFailFile(
    url,
    `historial_vision_pass_fail_${Date.now()}.xlsx`,
    "Exportacion completada",
  );
}

function initializeHistorialVisionPassFailEventListeners() {
  if (document.body.dataset.visionPassFailListenersAttached) {
    return;
  }

  document.body.addEventListener("click", function (e) {
    const target = e.target;

    if (
      target.id === "vision-pass-fail-btn-consultar" ||
      target.closest("#vision-pass-fail-btn-consultar")
    ) {
      e.preventDefault();
      loadHistorialVisionPassFailData();
      return;
    }

    if (
      target.id === "vision-pass-fail-btn-export-excel" ||
      target.closest("#vision-pass-fail-btn-export-excel")
    ) {
      e.preventDefault();
      exportHistorialVisionPassFailToExcel();
    }
  });

  document.body.addEventListener("keydown", function (e) {
    const visionPassFailRoot = document.getElementById(
      "historial-vision-pass-fail-root",
    );
    if (
      !visionPassFailRoot ||
      !e.target ||
      !visionPassFailRoot.contains(e.target)
    ) {
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      loadHistorialVisionPassFailData();
    }
  });

  document.body.addEventListener("input", function (e) {
    const visionPassFailRoot = document.getElementById(
      "historial-vision-pass-fail-root",
    );
    if (!visionPassFailRoot || !e.target || !visionPassFailRoot.contains(e.target)) {
      return;
    }

    if (
      e.target.id === "vision-pass-fail-filter-fecha-desde" ||
      e.target.id === "vision-pass-fail-filter-fecha-hasta" ||
      e.target.id === "vision-pass-fail-filter-numero-parte"
    ) {
      saveVisionPassFailFilters();
    }
  });

  document.body.dataset.visionPassFailListenersAttached = "true";
}

function showVisionPassFailNotification(message, type = "info") {
  const existingNotification = document.querySelector(
    ".vision-pass-fail-notification",
  );
  if (existingNotification) {
    existingNotification.remove();
  }

  const notification = document.createElement("div");
  notification.className = "vision-pass-fail-notification";
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

function setVisionPassFailDefaultDate() {
  resolveVisionPassFailFilters();
}

function escapeVisionPassFailHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

window.initializeHistorialVisionPassFailEventListeners =
  initializeHistorialVisionPassFailEventListeners;
window.loadHistorialVisionPassFailData = loadHistorialVisionPassFailData;
window.exportHistorialVisionPassFailToExcel =
  exportHistorialVisionPassFailToExcel;

document.addEventListener("DOMContentLoaded", function () {
  setVisionPassFailDefaultDate();
  initializeHistorialVisionPassFailEventListeners();
  loadHistorialVisionPassFailData();
});

if (
  document.readyState === "interactive" ||
  document.readyState === "complete"
) {
  setVisionPassFailDefaultDate();
  initializeHistorialVisionPassFailEventListeners();
  setTimeout(() => loadHistorialVisionPassFailData(), 100);
}
