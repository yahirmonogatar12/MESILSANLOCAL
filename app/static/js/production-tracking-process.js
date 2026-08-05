// ====== Modulo Production Tracking By Process (prefijo ptp-) ======
// Historial de etapas de una pieza leido de la tabla Tracking (solo lectura,
// la llenan triggers). WF_003 (API/JS) + WF_004 (CSS persistente).

const PTP_CSS_ID = "production-tracking-process-css";
const PTP_CSS_VER = "20260805d";
const PTP_CSS_HREF = "/static/css/production_tracking_process.css?v=" + PTP_CSS_VER;

function ptpEnsureStyles() {
  const cur = document.getElementById(PTP_CSS_ID);
  if (cur) {
    if (!cur.getAttribute("href")?.includes(PTP_CSS_VER)) cur.setAttribute("href", PTP_CSS_HREF);
    return;
  }
  const link = document.createElement("link");
  link.id = PTP_CSS_ID;
  link.rel = "stylesheet";
  link.href = PTP_CSS_HREF;
  document.head.appendChild(link);
}

function ptpEsc(v) {
  return String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function ptpNotify(msg, type = "info") {
  const old = document.querySelector(".ptp-notification");
  if (old) old.remove();
  const el = document.createElement("div");
  el.className = "ptp-notification";
  el.style.cssText =
    "position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:#fff;" +
    "font-weight:600;font-size:0.9rem;z-index:10000;box-shadow:0 4px 12px rgba(0,0,0,.3);";
  el.style.backgroundColor = type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { if (el.parentNode) el.remove(); }, 4000);
}

function ptpShowLoading(id = "ptp-loading") {
  document.getElementById(id)?.classList.add("active");
}
function ptpHideLoading(id = "ptp-loading") {
  document.getElementById(id)?.classList.remove("active");
}

// Descarga un blob de respuesta respetando el filename del Content-Disposition.
async function ptpDescargar(res, porDefecto) {
  if (!res.ok) throw new Error(`Status ${res.status}`);
  const blob = await res.blob();
  let filename = porDefecto;
  const disp = res.headers.get("content-disposition");
  if (disp) {
    const m = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disp);
    if (m && m[1]) filename = m[1].replace(/['"]/g, "");
  }
  const a = document.createElement("a");
  a.href = window.URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  ptpNotify("Exportación completada", "success");
}

function ptpCodigo() {
  return (document.getElementById("ptp-codigo")?.value || "").trim();
}

// ── Render de una pieza ──
function ptpCard(item) {
  const filas = item.etapas.map((e, i) => {
    // Solo se atenua lo que si debio pasar y no paso; "N/A" (reparaciones,
    // scrap) es un resultado normal, no una etapa faltante.
    const rowCls = e.clase === "pendiente" ? ' class="ptp-row-pendiente"' : "";
    return `<tr${rowCls}>` +
      `<td>${i + 1}</td>` +
      `<td>${ptpEsc(e.etapa)}</td>` +
      `<td><span class="ptp-badge ${ptpEsc(e.clase)}">${ptpEsc(e.estado)}</span></td>` +
      `<td>${ptpEsc(e.fecha) || "—"}</td>` +
      `</tr>`;
  }).join("");

  const ultima = item.ultima_etapa
    ? `${ptpEsc(item.ultima_etapa)} — ${ptpEsc(item.ultima_fecha)}`
    : "—";

  // Las dos mitades del mismo hueco: sin barcode no se pueden saber las etapas
  // que cruzan por barcode, y sin QR las que cruzan por QR. Se avisa arriba
  // para que la tabla no se lea como "la pieza se quedó a medio camino".
  let aviso = "";
  if (item.sin_barcode) {
    aviso = `<div class="ptp-aviso">A esta pieza <b>no se le vinculó un barcode</b>: en ASSY
       solo se registró el QR. Lo más probable es que el barcode exista y tenga su
       propio historial de ICT, FCT, Packing QA, Releases OQC y Embarques — lo que
       falta es la unión entre ambos códigos, así que aquí <b>no se pueden
       determinar</b>.</div>`;
  } else if (item.reconstruido) {
    aviso = `<div class="ptp-aviso">A esta pieza <b>no se le vinculó un QR</b>, así que no tiene
       registro propio en Tracking. Lo que se muestra se reconstruyó leyendo
       directamente ICT, FCT, Packing, OQC y Embarques. Su QR probablemente exista
       con el historial de SMT, IMD y Assy, pero sin la unión entre ambos códigos
       <b>no se puede saber cuál es</b>.</div>`;
  }

  const campo = (valor, sinDato) => sinDato
    ? `<span class="ptp-badge nd">${valor}</span>`
    : `<span class="ptp-v">${ptpEsc(valor)}</span>`;

  return `
    <div class="ptp-card">
      <div class="ptp-card-head">
        <div class="ptp-field"><span class="ptp-k">QR</span>${campo(item.sin_qr ? "NO VINCULADO" : item.qr, item.sin_qr)}</div>
        <div class="ptp-field"><span class="ptp-k">Barcode</span>${campo(item.sin_barcode ? "NO VINCULADO" : item.barcode, item.sin_barcode)}</div>
        <div class="ptp-field"><span class="ptp-k">Etapas registradas</span><span class="ptp-v">${item.registradas} / ${item.total}</span></div>
        <div class="ptp-field"><span class="ptp-k">Última etapa</span><span class="ptp-v">${ultima}</span></div>
        <div class="ptp-field"><span class="ptp-k">Estado</span>
          <span class="ptp-badge ${ptpEsc(item.clase_global)}">${ptpEsc(item.estado_global)}</span></div>
      </div>
      ${aviso}
      <div class="ptp-table-wrap">
        <table class="ptp-table">
          <thead><tr><th>#</th><th>Etapa</th><th>Estado</th><th>Fecha / Hora</th></tr></thead>
          <tbody>${filas}</tbody>
        </table>
      </div>
    </div>`;
}

// ── Busqueda ──
async function ptpBuscar() {
  const codigo = ptpCodigo();
  const status = document.getElementById("ptp-status");
  const results = document.getElementById("ptp-results");
  if (!codigo) {
    if (results) results.innerHTML = "";
    if (status) status.textContent = "Escanea una pieza";
    return;
  }

  ptpShowLoading();
  try {
    const res = await fetch(`/api/production_tracking/buscar?codigo=${encodeURIComponent(codigo)}`,
      { credentials: "same-origin" });
    const data = await res.json();
    if (data.status !== "success") {
      ptpNotify("Error: " + (data.message || "?"), "error");
      return;
    }

    if (!data.items.length) {
      if (results) {
        results.innerHTML =
          `<div class="ptp-empty">Sin historial para <b>${ptpEsc(codigo)}</b>.<br>` +
          `No hay registro ni en Tracking ni en ICT, FCT, Packing, OQC o Embarques.</div>`;
      }
      if (status) status.textContent = data.message || "Sin resultados";
      return;
    }

    if (results) results.innerHTML = data.items.map(ptpCard).join("");
    if (status) {
      status.textContent = data.items.length === 1
        ? "1 pieza"
        : `${data.items.length} piezas`;
    }
  } catch (e) {
    console.error(e);
    ptpNotify("Error al buscar el historial", "error");
  } finally {
    ptpHideLoading();
  }
}

// ── Export ──
async function ptpExport() {
  const codigo = ptpCodigo();
  if (!codigo) { ptpNotify("Escanea una pieza primero", "error"); return; }
  try {
    const res = await fetch(`/api/production_tracking/buscar/export?codigo=${encodeURIComponent(codigo)}`,
      { credentials: "same-origin" });
    await ptpDescargar(res, "production_tracking_by_process.xlsx");
  } catch (e) {
    console.error(e);
    ptpNotify("Error al exportar", "error");
  }
}

// ====================================================================
// Lote: importar un Excel con muchos codigos.
// Una fila por codigo y una columna por etapa (la celda trae la fecha).
// ====================================================================

function ptpArchivo() {
  return document.getElementById("ptp-file")?.files?.[0] || null;
}

function ptpLoteFormData(formato) {
  const archivo = ptpArchivo();
  if (!archivo) { ptpNotify("Selecciona un archivo Excel primero", "error"); return null; }
  const fd = new FormData();
  fd.append("file", archivo);
  if (formato) fd.append("formato", formato);
  return fd;
}

function ptpLoteRender(data) {
  const head = document.getElementById("ptp-lote-head");
  const body = document.getElementById("ptp-lote-body");
  if (!head || !body) return;

  head.innerHTML = "<tr>" +
    ["#", "Código buscado", "Barcode", "Estado"].map((h) => `<th>${h}</th>`).join("") +
    data.etapas.map((e) => `<th>${ptpEsc(e)}</th>`).join("") +
    "</tr>";

  body.innerHTML = data.items.map((it, i) => {
    const celdas = it.etapas.map((e) =>
      `<td class="ptp-cell-${ptpEsc(e.clase)}">${ptpEsc(e.celda) || "—"}</td>`).join("");
    const rowCls = it.encontrado ? "" : ' class="ptp-row-pendiente"';
    // Reconstruida = sin fila propia en Tracking, leida de las tablas de origen.
    const bc = it.reconstruido
      ? `<span class="ptp-badge nd">QR NO VINCULADO</span>`
      : (ptpEsc(it.barcode) || "—");
    return `<tr${rowCls}>` +
      `<td>${i + 1}</td>` +
      `<td>${ptpEsc(it.codigo)}</td>` +
      `<td>${bc}</td>` +
      `<td><span class="ptp-badge ${ptpEsc(it.clase_global)}">${ptpEsc(it.estado_global)}</span></td>` +
      celdas +
      `</tr>`;
  }).join("");
}

async function ptpLoteBuscar() {
  const fd = ptpLoteFormData(null);
  if (!fd) return;
  const status = document.getElementById("ptp-lote-status");

  ptpShowLoading("ptp-lote-loading");
  try {
    const res = await fetch("/api/production_tracking/lote",
      { method: "POST", body: fd, credentials: "same-origin" });
    const data = await res.json();
    if (data.status !== "success") {
      ptpNotify("Error: " + (data.message || "?"), "error");
      if (status) status.textContent = data.message || "Error";
      return;
    }
    ptpLoteRender(data);
    if (status) {
      status.textContent =
        `${data.total} códigos · ${data.encontrados} con historial · ${data.no_encontrados} sin historial`;
    }
  } catch (e) {
    console.error(e);
    ptpNotify("Error al consultar el archivo", "error");
  } finally {
    ptpHideLoading("ptp-lote-loading");
  }
}

async function ptpLoteExport() {
  const fd = ptpLoteFormData("excel");
  if (!fd) return;
  try {
    const res = await fetch("/api/production_tracking/lote",
      { method: "POST", body: fd, credentials: "same-origin" });
    await ptpDescargar(res, "production_tracking_lote.xlsx");
  } catch (e) {
    console.error(e);
    ptpNotify("Error al exportar", "error");
  }
}

function ptpLoteLimpiar() {
  const input = document.getElementById("ptp-file");
  if (input) input.value = "";
  const head = document.getElementById("ptp-lote-head");
  const body = document.getElementById("ptp-lote-body");
  if (head) head.innerHTML = "";
  if (body) body.innerHTML = "";
  const status = document.getElementById("ptp-lote-status");
  if (status) status.textContent = "Selecciona un archivo";
}

function ptpSwitchTab(panel) {
  document.querySelectorAll(".ptp-tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.panel === panel));
  document.getElementById("ptp-panel-una")?.classList.toggle("active", panel === "una");
  document.getElementById("ptp-panel-lote")?.classList.toggle("active", panel === "lote");
  if (panel === "una") document.getElementById("ptp-codigo")?.focus();
}

function ptpLimpiar() {
  const input = document.getElementById("ptp-codigo");
  if (input) input.value = "";
  const results = document.getElementById("ptp-results");
  if (results) results.innerHTML = "";
  const status = document.getElementById("ptp-status");
  if (status) status.textContent = "Escanea una pieza";
  input?.focus();
}

// ── Event delegation (idempotente) ──
function ptpInitListeners() {
  if (document.body.dataset.ptpListenersAttached) return;
  document.body.addEventListener("click", (e) => {
    const t = e.target;
    if (t.closest(".ptp-tab")) { ptpSwitchTab(t.closest(".ptp-tab").dataset.panel); return; }
    if (t.id === "ptp-buscar") { e.preventDefault(); ptpBuscar(); return; }
    if (t.id === "ptp-limpiar") { e.preventDefault(); ptpLimpiar(); return; }
    if (t.id === "ptp-exportar") { e.preventDefault(); ptpExport(); return; }
    if (t.id === "ptp-lote-buscar") { e.preventDefault(); ptpLoteBuscar(); return; }
    if (t.id === "ptp-lote-limpiar") { e.preventDefault(); ptpLoteLimpiar(); return; }
    if (t.id === "ptp-lote-exportar") { e.preventDefault(); ptpLoteExport(); return; }
  });
  // La pistola termina el scan con Enter.
  document.body.addEventListener("keydown", (e) => {
    if (e.target.id === "ptp-codigo" && e.key === "Enter") { e.preventDefault(); ptpBuscar(); }
  });
  document.body.dataset.ptpListenersAttached = "true";
}

function ptpInit() {
  ptpEnsureStyles();
  ptpInitListeners();
  document.getElementById("ptp-codigo")?.focus();
}

window.initializeProductionTrackingEventListeners = ptpInitListeners;
window.loadProductionTrackingData = ptpInit;
window.limpiarProductionTracking = function () {
  ["ptp-loading", "ptp-lote-loading"].forEach((id) => ptpHideLoading(id));
};

document.addEventListener("DOMContentLoaded", ptpInit);
if (document.readyState === "interactive" || document.readyState === "complete") {
  setTimeout(ptpInit, 100);
}
