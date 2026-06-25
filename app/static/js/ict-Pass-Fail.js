// ====== WF_004: Garantizar CSS del modulo en <head> ======
(function ensureModuleStyles() {
  const sheets = [
    { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
    { id: "ict-css", href: "/static/css/ict.css?v=20260522a" },
    { id: "ict-pass-fail-css", href: "/static/css/ict-Pass-Fail.css?v=20260528e" },
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

let ictPassFailModuleData = [];
let ictPassFailDetailContext = null;
let ictPassFailDetailSearchTimer = null;
let ictPassFailDetailRows = [];
let ictPassFailDetailSummaryData = {};
const ICT_PASS_FAIL_FILTERS_STORAGE_KEY = "historialIctPassFailFilters";
const ICT_PASS_FAIL_MODE_STORAGE_KEY = "historialIctPassFailMode";
const ICT_PASS_FAIL_LISTENER_VERSION = "20260528f";

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

function normalizeIctPassFailMode(value) {
  return String(value || "").toLowerCase() === "detallado" ? "detallado" : "normal";
}

function getIctPassFailMode() {
  try {
    if (!window.__ictPassFailUrlModeApplied) {
      const queryMode = new URLSearchParams(window.location.search).get("modo");
      if (queryMode) {
        window.sessionStorage.setItem(
          ICT_PASS_FAIL_MODE_STORAGE_KEY,
          normalizeIctPassFailMode(queryMode),
        );
      }
      window.__ictPassFailUrlModeApplied = true;
    }

    return normalizeIctPassFailMode(
      window.sessionStorage.getItem(ICT_PASS_FAIL_MODE_STORAGE_KEY),
    );
  } catch (error) {
    return "normal";
  }
}

function setIctPassFailMode(mode) {
  const nextMode = normalizeIctPassFailMode(mode);

  try {
    window.sessionStorage.setItem(ICT_PASS_FAIL_MODE_STORAGE_KEY, nextMode);
  } catch (error) {
    console.warn("No se pudo guardar el modo de ICT Pass/Fail", error);
  }

  updateIctPassFailModeToggle();
  renderHistorialIctPassFailTable(ictPassFailModuleData);

  const modal = getIctPassFailDetailModal();
  if (modal?.classList.contains("is-open")) {
    setIctPassFailDetailSummary(ictPassFailDetailSummaryData);
    renderIctPassFailDetailRows(ictPassFailDetailRows);
  }
}

function updateIctPassFailModeToggle() {
  const mode = getIctPassFailMode();
  document
    .querySelectorAll("[data-ict-pass-fail-mode]")
    .forEach((button) => {
      const isActive = normalizeIctPassFailMode(button.dataset.ictPassFailMode) === mode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
}

function renderIctPassFailHeader(tableId, headers) {
  const headerRow = document.querySelector(`#${tableId} thead tr`);
  if (!headerRow) {
    return;
  }

  headerRow.innerHTML = headers
    .map((header) => `<th>${escapeIctPassFailHtml(header)}</th>`)
    .join("");
}

function renderHistorialIctPassFailHeader(mode) {
  const headers =
    mode === "detallado"
      ? [
          "Fecha",
          "Linea",
          "ICT",
          "Turno",
          "No. parte",
          "Operador(es)",
          "Tiempo ajuste",
          "Total real",
          "OK real",
          "Detect.",
          "F. neg.",
          "F. fail",
          "% Correct.",
          "% Det.",
          "% F. neg.",
          "% F. fail",
        ]
      : [
          "Fecha",
          "Linea",
          "ICT",
          "Turno",
          "No. parte",
          "Operador(es)",
          "Tiempo ajuste",
          "Total",
          "OK",
          "NG",
          "% Pass",
          "% Fail",
          "Porcentaje",
        ];

  const table = document.getElementById("ict-pass-fail-table");
  if (table) {
    table.dataset.mode = mode;
  }
  renderIctPassFailHeader("ict-pass-fail-table", headers);
}

function renderIctPassFailDetailHeader(mode) {
  const headers =
    mode === "detallado"
      ? [
          "Barcode",
          "Primer test",
          "Ultimo test",
          "Intentos",
          "OK",
          "NG",
          "OK real",
          "Detect.",
          "F. neg.",
          "F. fail",
          "Clase",
          "Primero",
          "Final",
          "Defecto / Ubic.",
        ]
      : [
          "Barcode",
          "Primer test",
          "Ultimo test",
          "Intentos",
          "OK",
          "NG",
          "Primero",
          "Final",
          "Defecto / Ubic.",
        ];

  const table = document.getElementById("ict-pass-fail-detail-table");
  if (table) {
    table.dataset.mode = mode;
  }
  renderIctPassFailHeader("ict-pass-fail-detail-table", headers);
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

  const mode = getIctPassFailMode();
  const emptyColspan = mode === "detallado" ? 16 : 13;
  renderHistorialIctPassFailHeader(mode);

  if (!Array.isArray(data) || data.length === 0) {
    tbody.innerHTML =
      `<tr><td colspan="${emptyColspan}" class="ict-pass-fail-table-empty">No se encontraron registros.</td></tr>`;
    return;
  }

  tbody.innerHTML = data
    .map((row, index) => {
      const ajusteDetalle = row.ajuste_detalle ?? "";
      const commonCells = `
          <td>${escapeIctPassFailHtml(row.fecha ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.linea ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.ict ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.turno ?? "")}</td>
          <td>${escapeIctPassFailHtml(row.numero_parte ?? "")}</td>
          <td title="${escapeIctPassFailHtml(row.operadores ?? "")}">${escapeIctPassFailHtml(row.operadores ?? "")}</td>
          <td title="${escapeIctPassFailHtml(ajusteDetalle)}">${escapeIctPassFailHtml(row.ajuste_total ?? "")}${ajusteDetalle ? ` <span class="ict-pass-fail-rate-neutral">(${escapeIctPassFailHtml(ajusteDetalle)})</span>` : ""}</td>`;

      if (mode === "detallado") {
        const correctRate = Number(row.porcentaje_ok || 0);
        const detectionRate = Number(row.porcentaje_deteccion || 0);
        const falseNegativeRate = Number(row.porcentaje_falso_negativo || 0);
        const falseFailRate = Number(row.porcentaje_falso_fail || 0);

        return `
          <tr class="ict-pass-fail-summary-row" data-ict-pass-fail-row-index="${index}" title="Doble click para ver detalle por barcode">
            ${commonCells}
            <td>${escapeIctPassFailHtml(row.total ?? 0)}</td>
            <td>${escapeIctPassFailHtml(row.ok_real ?? 0)}</td>
            <td>${escapeIctPassFailHtml(row.defectos_detectados ?? 0)}</td>
            <td>${escapeIctPassFailHtml(row.falsos_negativos ?? 0)}</td>
            <td>${escapeIctPassFailHtml(row.falsos_fail ?? 0)}</td>
            <td class="${correctRate >= 90 ? "ict-pass-fail-rate-good" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(correctRate))}</td>
            <td class="${detectionRate >= 90 ? "ict-pass-fail-rate-good" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(detectionRate))}</td>
            <td class="${falseNegativeRate > 0 ? "ict-pass-fail-rate-bad" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(falseNegativeRate))}</td>
            <td class="${falseFailRate > 10 ? "ict-pass-fail-rate-bad" : "ict-pass-fail-rate-neutral"}">${escapeIctPassFailHtml(formatIctPassFailPercent(falseFailRate))}</td>
          </tr>
        `;
      }

      const totalIntentos = Number(row.total_intentos ?? row.total ?? 0);
      const okCount = Number(row.ok_count_raw ?? row.ok_count ?? 0);
      const ngCount = Number(row.ng_count_raw ?? row.ng_count ?? 0);
      const passRate = totalIntentos > 0 ? (okCount / totalIntentos) * 100 : 0;
      const failRate = totalIntentos > 0 ? (ngCount / totalIntentos) * 100 : 0;

      return `
        <tr class="ict-pass-fail-summary-row" data-ict-pass-fail-row-index="${index}" title="Doble click para ver detalle por barcode">
          ${commonCells}
          <td>${escapeIctPassFailHtml(totalIntentos)}</td>
          <td>${escapeIctPassFailHtml(okCount)}</td>
          <td>${escapeIctPassFailHtml(ngCount)}</td>
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
  const container = document.querySelector(".ict-pass-fail-detail-summary");
  if (!container) {
    return;
  }

  const mode = getIctPassFailMode();
  const totalIntentos = Number(summary.total_intentos || 0);
  const okTotal = Number(summary.ok_total || 0);
  const ngTotal = Number(summary.ng_total || 0);
  const passRate = totalIntentos > 0 ? (okTotal / totalIntentos) * 100 : 0;
  const failRate = totalIntentos > 0 ? (ngTotal / totalIntentos) * 100 : 0;
  const correctoReal = Number(summary.correcto_real ?? summary.pass_real ?? 0);
  const totalReal = Number(summary.total_real || 0);
  const realRate = summary.porcentaje_pass_real ?? (
    totalReal > 0 ? (correctoReal / totalReal) * 100 : 0
  );

  const cards =
    mode === "detallado"
      ? [
          ["Total real", formatIctPassFailNumber(totalReal)],
          ["Correctos", formatIctPassFailNumber(correctoReal), "good"],
          ["OK real", formatIctPassFailNumber(summary.ok_real), "good"],
          ["Detectados", formatIctPassFailNumber(summary.defectos_detectados), "good"],
          ["F. negativos", formatIctPassFailNumber(summary.falsos_negativos), "bad"],
          ["F. fail", formatIctPassFailNumber(summary.falsos_fail), "bad"],
          ["% Correcto", formatIctPassFailPercent(realRate), realRate >= 90 ? "good" : ""],
          [
            "% Deteccion",
            formatIctPassFailPercent(summary.porcentaje_deteccion),
            Number(summary.porcentaje_deteccion || 0) >= 90 ? "good" : "",
          ],
          [
            "% F. negativo",
            formatIctPassFailPercent(summary.porcentaje_falso_negativo),
            Number(summary.porcentaje_falso_negativo || 0) > 0 ? "bad" : "",
          ],
          [
            "% F. fail",
            formatIctPassFailPercent(summary.porcentaje_falso_fail),
            Number(summary.porcentaje_falso_fail || 0) > 10 ? "bad" : "",
          ],
        ]
      : [
          ["Intentos", formatIctPassFailNumber(totalIntentos)],
          ["OK total", formatIctPassFailNumber(okTotal), "good"],
          ["NG total", formatIctPassFailNumber(ngTotal), "bad"],
          ["Piezas unicas", formatIctPassFailNumber(summary.piezas_unicas)],
          ["Repetidas", formatIctPassFailNumber(summary.piezas_repetidas)],
          ["Reparacion", formatIctPassFailNumber(summary.piezas_reparacion)],
          ["% Pass", formatIctPassFailPercent(passRate), passRate >= 90 ? "good" : ""],
          ["% Fail", formatIctPassFailPercent(failRate), failRate > 10 ? "bad" : ""],
        ];

  container.innerHTML = cards
    .map(([label, value, status]) => {
      const statusClass =
        status === "good"
          ? " ict-pass-fail-detail-stat-good"
          : status === "bad"
            ? " ict-pass-fail-detail-stat-bad"
            : "";
      return `
        <div class="ict-pass-fail-detail-stat${statusClass}">
          <span>${escapeIctPassFailHtml(label)}</span>
          <strong>${escapeIctPassFailHtml(value)}</strong>
        </div>
      `;
    })
    .join("");
}

function getIctPassFailCriterion(value) {
  const criterion = String(value || "").toUpperCase();
  const labels = {
    DEFECTO_DETECTADO: {
      label: "Detectado",
      className: "ict-pass-fail-detail-badge-ok",
    },
    FALSO_NEGATIVO: {
      label: "F. negativo",
      className: "ict-pass-fail-detail-badge-ng",
    },
    FALSO_FAIL: {
      label: "F. fail",
      className: "ict-pass-fail-detail-badge-warn",
    },
    OK_REAL: {
      label: "OK real",
      className: "ict-pass-fail-detail-badge-ok",
    },
  };

  return labels[criterion] || {
    label: criterion || "-",
    className: "ict-pass-fail-detail-badge",
  };
}

function renderIctPassFailDetailRows(rows) {
  const tbody = document.getElementById("ict-pass-fail-detail-body");
  if (!tbody) {
    return;
  }

  const mode = getIctPassFailMode();
  const emptyColspan = mode === "detallado" ? 14 : 9;
  renderIctPassFailDetailHeader(mode);

  if (!Array.isArray(rows) || rows.length === 0) {
    tbody.innerHTML =
      `<tr><td colspan="${emptyColspan}" class="ict-pass-fail-table-empty">No se encontraron barcodes para este detalle.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows
    .map((row) => {
      const intentos = Number(row.intentos || 0);
      const fueReparacion = Boolean(row.fue_reparacion);
      const resultadoPrimer = String(row.resultado_primer || "").toUpperCase();
      const resultadoFinal = String(row.resultado_final || "").toUpperCase();
      const okReal = Number(row.ok_real || 0);
      const detectado = Number(row.defectos_detectados || 0);
      const falsoNegativo = Number(row.falsos_negativos || 0);
      const falsoFail = Number(row.falsos_fail || 0);
      const criterio = getIctPassFailCriterion(row.criterio_real);
      const defectText = row.defectos || (fueReparacion ? "SIN DEFECTO CAPTURADO" : "NO");
      const rowClasses = [
        intentos > 1 ? "ict-pass-fail-detail-repeated-row" : "",
        fueReparacion ? "ict-pass-fail-detail-repair-row" : "",
      ]
        .filter(Boolean)
        .join(" ");

      if (mode === "detallado") {
        return `
          <tr class="${rowClasses}">
            <td class="ict-pass-fail-detail-barcode-cell" title="${escapeIctPassFailHtml(row.barcode ?? "")}">${escapeIctPassFailHtml(row.barcode ?? "")}</td>
            <td>${escapeIctPassFailHtml(row.primer_test ?? "")}</td>
            <td>${escapeIctPassFailHtml(row.ultimo_test ?? "")}</td>
            <td><span class="${intentos > 1 ? "ict-pass-fail-detail-badge-warn" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(intentos)}</span></td>
            <td>${escapeIctPassFailHtml(row.ok_count ?? 0)}</td>
            <td>${escapeIctPassFailHtml(row.ng_count ?? 0)}</td>
            <td><span class="${okReal > 0 ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(okReal)}</span></td>
            <td><span class="${detectado > 0 ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(detectado)}</span></td>
            <td><span class="${falsoNegativo > 0 ? "ict-pass-fail-detail-badge-ng" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(falsoNegativo)}</span></td>
            <td><span class="${falsoFail > 0 ? "ict-pass-fail-detail-badge-warn" : "ict-pass-fail-detail-badge"}">${escapeIctPassFailHtml(falsoFail)}</span></td>
            <td><span class="${criterio.className}">${escapeIctPassFailHtml(criterio.label)}</span></td>
            <td><span class="${resultadoPrimer === "OK" ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge-ng"}">${escapeIctPassFailHtml(resultadoPrimer || "-")}</span></td>
            <td><span class="${resultadoFinal === "OK" ? "ict-pass-fail-detail-badge-ok" : "ict-pass-fail-detail-badge-ng"}">${escapeIctPassFailHtml(resultadoFinal || "-")}</span></td>
            <td class="ict-pass-fail-detail-defect-cell" title="${escapeIctPassFailHtml(defectText)}">${escapeIctPassFailHtml(defectText)}</td>
          </tr>
        `;
      }

      return `
        <tr class="${rowClasses}">
          <td class="ict-pass-fail-detail-barcode-cell" title="${escapeIctPassFailHtml(row.barcode ?? "")}">${escapeIctPassFailHtml(row.barcode ?? "")}</td>
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

  ictPassFailDetailSummaryData = {};
  ictPassFailDetailRows = [];
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
  ictPassFailDetailSummaryData = {};
  ictPassFailDetailRows = [];
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

    ictPassFailDetailSummaryData = data.summary || {};
    ictPassFailDetailRows = Array.isArray(data.rows) ? data.rows : [];
    setIctPassFailDetailSummary(ictPassFailDetailSummaryData);
    renderIctPassFailDetailRows(ictPassFailDetailRows);
  } catch (error) {
    console.error(error);
    ictPassFailDetailSummaryData = {};
    ictPassFailDetailRows = [];
    setIctPassFailDetailSummary(ictPassFailDetailSummaryData);
    renderIctPassFailDetailRows(ictPassFailDetailRows);
    showIctPassFailNotification("Error al cargar detalle", "error");
  } finally {
    setIctPassFailDetailLoading(false);
  }
}

async function exportHistorialIctPassFailToExcel() {
  const { fechaDesde, fechaHasta, numeroParte, turno, barcode } =
    resolveIctPassFailFilters();
  const mode = getIctPassFailMode();

  const url =
    `/api/ict/pass-fail/export?fecha_desde=${encodeURIComponent(fechaDesde)}` +
    `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
    `&numero_parte=${encodeURIComponent(numeroParte)}` +
    `&turno=${encodeURIComponent(turno)}` +
    `&barcode=${encodeURIComponent(barcode)}` +
    `&modo=${encodeURIComponent(mode)}`;

  await downloadIctPassFailFile(
    url,
    `historial_ict_pass_fail_${mode}_${Date.now()}.xlsx`,
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
    const modeButton = target.closest("[data-ict-pass-fail-mode]");

    if (modeButton) {
      e.preventDefault();
      setIctPassFailMode(modeButton.dataset.ictPassFailMode);
      return;
    }

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
  updateIctPassFailModeToggle();
  renderHistorialIctPassFailHeader(getIctPassFailMode());
  renderIctPassFailDetailHeader(getIctPassFailMode());
  loadHistorialIctPassFailData();
});

if (document.readyState === "interactive" || document.readyState === "complete") {
  setIctPassFailDefaultDate();
  initializeHistorialIctPassFailEventListeners();
  updateIctPassFailModeToggle();
  renderHistorialIctPassFailHeader(getIctPassFailMode());
  renderIctPassFailDetailHeader(getIctPassFailMode());
  setTimeout(() => loadHistorialIctPassFailData(), 100);
}
