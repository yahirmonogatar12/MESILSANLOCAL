let visionModuleData = [];
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

async function loadHistorialVisionData() {
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

    const url =
      `/api/vision/data?fecha_desde=${encodeURIComponent(fechaDesde)}` +
      `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
      `&linea=${encodeURIComponent(linea)}` +
      `&resultado=${encodeURIComponent(resultado)}` +
      `&numero_parte=${encodeURIComponent(numeroParte)}` +
      `&qr=${encodeURIComponent(qr)}` +
      `&barcode=${encodeURIComponent(barcode)}`;

    const response = await fetch(url, { credentials: "same-origin" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error || "Error al consultar historial vision");
    }

    visionModuleData = Array.isArray(data) ? data : [];

    const recordCount = document.getElementById("vision-record-count");
    if (recordCount) {
      recordCount.textContent = `${visionModuleData.length} registro${visionModuleData.length !== 1 ? "s" : ""}`;
    }

    renderHistorialVisionTable(visionModuleData);
  } catch (error) {
    console.error(error);
    renderHistorialVisionTable([]);
    showVisionNotification("Error al cargar datos", "error");
  } finally {
    hideVisionLoading();
  }
}

function renderHistorialVisionTable(data) {
  const tbody = document.getElementById("vision-body");
  if (!tbody) {
    return;
  }

  if (!Array.isArray(data) || data.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="vision-table-empty">No se encontraron registros.</td></tr>';
    return;
  }

  tbody.innerHTML = data
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

  const url =
    `/api/vision/export?fecha_desde=${encodeURIComponent(fechaDesde)}` +
    `&fecha_hasta=${encodeURIComponent(fechaHasta)}` +
    `&linea=${encodeURIComponent(linea)}` +
    `&resultado=${encodeURIComponent(resultado)}` +
    `&numero_parte=${encodeURIComponent(numeroParte)}` +
    `&qr=${encodeURIComponent(qr)}` +
    `&barcode=${encodeURIComponent(barcode)}`;

  await downloadVisionFile(
    url,
    `historial_vision_${Date.now()}.xlsx`,
    "Exportacion completada",
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
  if (document.body.dataset.visionListenersAttached) {
    return;
  }

  document.body.addEventListener("click", function (e) {
    const target = e.target;

    if (
      target.id === "vision-btn-consultar" ||
      target.closest("#vision-btn-consultar")
    ) {
      e.preventDefault();
      loadHistorialVisionData();
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

    if (e.key === "Enter") {
      e.preventDefault();
      loadHistorialVisionData();
    }
  });

  document.body.addEventListener("input", function (e) {
    const visionRoot = document.getElementById("historial-vision-root");
    if (!visionRoot || !e.target || !visionRoot.contains(e.target)) {
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
