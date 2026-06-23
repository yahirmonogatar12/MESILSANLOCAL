// ====== Modulo Trazabilidad de PCB (prefijo trz-) ======
// Unifica trazabilidad_material_pcb (ASSY) + _imd + _smt. Solo lectura.
// WF_003 (API/JS) + WF_004 (CSS persistente).

const TRZ_CSS_ID = "trazabilidad-pcb-css";
const TRZ_CSS_VER = "20260623g";
const TRZ_CSS_HREF = "/static/css/trazabilidad_pcb.css?v=" + TRZ_CSS_VER;

function trzEnsureStyles() {
  const cur = document.getElementById(TRZ_CSS_ID);
  if (cur) {
    if (!cur.getAttribute("href")?.includes(TRZ_CSS_VER)) cur.setAttribute("href", TRZ_CSS_HREF);
    return;
  }
  const link = document.createElement("link");
  link.id = TRZ_CSS_ID;
  link.rel = "stylesheet";
  link.href = TRZ_CSS_HREF;
  document.head.appendChild(link);
}

function trzEsc(v) {
  return String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function trzNotify(msg, type = "info") {
  const old = document.querySelector(".trz-notification");
  if (old) old.remove();
  const el = document.createElement("div");
  el.className = "trz-notification";
  el.style.cssText =
    "position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:#fff;" +
    "font-weight:600;font-size:0.9rem;z-index:10000;box-shadow:0 4px 12px rgba(0,0,0,.3);";
  el.style.backgroundColor = type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { if (el.parentNode) el.remove(); }, 4000);
}

function trzShowLoading(p) {
  const l = document.getElementById(`trz-${p}-loading`);
  if (l) l.classList.add("active");
}
function trzHideLoading(p) {
  const l = document.getElementById(`trz-${p}-loading`);
  if (l) l.classList.remove("active");
}

// ── Filtros por panel → query string ──
function trzParams(panel) {
  const g = (id) => (document.getElementById(id)?.value || "").trim();
  const qs = new URLSearchParams();
  if (panel === "q") {
    if (g("trz-q-pcb")) qs.set("pcb", g("trz-q-pcb"));
    if (g("trz-q-proceso")) qs.set("proceso", g("trz-q-proceso"));
  } else if (panel === "m") {
    if (g("trz-m-proceso")) qs.set("proceso", g("trz-m-proceso"));
    if (g("trz-m-lote")) qs.set("lot_no", g("trz-m-lote"));
    if (g("trz-m-parte")) qs.set("part_no", g("trz-m-parte"));
    if (g("trz-m-material")) qs.set("material", g("trz-m-material"));
    if (g("trz-m-desde")) qs.set("fecha_inicio", g("trz-m-desde"));
    if (g("trz-m-hasta")) qs.set("fecha_fin", g("trz-m-hasta"));
  } else {
    if (g("trz-p-proceso")) qs.set("proceso", g("trz-p-proceso"));
    if (g("trz-p-material")) qs.set("material", g("trz-p-material"));
    if (g("trz-p-desde")) qs.set("fecha_inicio", g("trz-p-desde"));
    if (g("trz-p-hasta")) qs.set("fecha_fin", g("trz-p-hasta"));
  }
  return qs.toString();
}

// ── Vista PCB: materiales de un QR/barcode especifico ──
async function trzLoadPcb() {
  const pcb = (document.getElementById("trz-q-pcb")?.value || "").trim();
  const status = document.getElementById("trz-q-status");
  const tbody = document.getElementById("trz-q-body");
  if (!pcb) {
    if (tbody) tbody.innerHTML = "";
    if (status) status.textContent = "Escanea un PCB";
    return;
  }
  trzShowLoading("q");
  try {
    const res = await fetch(`/api/trazabilidad_pcb/por_pcb?${trzParams("q")}`, { credentials: "same-origin" });
    const data = await res.json();
    if (data.status !== "success") { trzNotify("Error: " + (data.message || "?"), "error"); return; }
    tbody.innerHTML = "";
    data.items.forEach((r) => {
      const tr = document.createElement("tr");
      const refill = r.refill_number != null ? `#${r.refill_number}` : "";
      const ini = r.cantidad_inicial != null ? Math.round(r.cantidad_inicial) : "";
      const rest = r.cantidad_restante != null ? Math.round(r.cantidad_restante) : "";
      const qpp = r.qty_per_pcb != null ? r.qty_per_pcb : "";
      tr.innerHTML =
        `<td><span class="trz-badge ${trzEsc(r.proceso.toLowerCase())}">${trzEsc(r.proceso)}</span></td>` +
        `<td>${trzEsc(r.pcb_serial)}</td><td>${trzEsc(r.ts)}</td><td>${trzEsc(r.lot_no)}</td>` +
        `<td>${trzEsc(r.linea)}</td><td>${trzEsc(r.part_no)}</td><td>${trzEsc(r.material_code)}</td>` +
        `<td>${trzEsc(r.spec)}</td><td>${trzEsc(r.numero_lote_material)}</td><td>${trzEsc(r.posicion)}</td>` +
        `<td>${trzEsc(refill)}</td><td>${ini}</td><td>${rest}</td><td>${trzEsc(qpp)}</td>` +
        `<td>${trzEsc(r.container_id)}</td>`;
      tbody.appendChild(tr);
    });
    if (status) {
      status.textContent = data.items.length
        ? `${data.items.length} material${data.items.length !== 1 ? "es" : ""}`
        : "Sin trazabilidad para ese PCB";
    }
    // Cargar historial de verificaciones del primer PCB (todas las filas comparten input_main_id)
    const first = data.items.find((x) => x.input_main_id);
    if (first) trzLoadHistorial(first.input_main_id, first.proceso);
    else trzClearHistorial();
  } catch (e) {
    console.error(e); trzNotify("Error al buscar el PCB", "error");
  } finally {
    trzHideLoading("q");
  }
}

function trzClearHistorial() {
  const wrap = document.getElementById("trz-q-hist-wrap");
  if (wrap) wrap.style.display = "none";
}

async function trzLoadHistorial(inputMainId, proceso) {
  try {
    const res = await fetch(
      `/api/trazabilidad_pcb/historial_pcb?input_main_id=${encodeURIComponent(inputMainId)}&proceso=${encodeURIComponent(proceso)}`,
      { credentials: "same-origin" });
    const data = await res.json();
    const wrap = document.getElementById("trz-q-hist-wrap");
    const tbody = document.getElementById("trz-q-hist-body");
    const count = document.getElementById("trz-q-hist-count");
    if (data.status !== "success" || !data.items.length) { if (wrap) wrap.style.display = "none"; return; }
    tbody.innerHTML = "";
    data.items.forEach((h) => {
      const tr = document.createElement("tr");
      const okCls = (h.result || "").toUpperCase() === "OK" ? "trz-res-ok" : "trz-res-ng";
      tr.innerHTML =
        `<td>${trzEsc(h.hora)}</td><td>${trzEsc(h.contenedor)}</td><td>${trzEsc(h.material)}</td>` +
        `<td>${trzEsc(h.posicion)}</td><td>${trzEsc(h.spec)}</td><td>${trzEsc(h.qty)}</td>` +
        `<td>${trzEsc(h.proveedor)}</td><td>${trzEsc(h.lote_proveedor)}</td>` +
        `<td class="${okCls}">${trzEsc(h.result)}</td>`;
      tbody.appendChild(tr);
    });
    if (count) count.textContent = data.items.length;
    if (wrap) wrap.style.display = "block";
  } catch (e) {
    console.error(e);
  }
}

// ── Vista 1: materiales por lote ──
// Flag: la primera carga preselecciona el filtro Desde en la fecha de hoy
// (fecha_hoy viene del backend con el helper de shared) y recarga filtrada.
let trzFechaInicializada = false;

async function trzLoadMateriales() {
  trzShowLoading("m");
  const status = document.getElementById("trz-m-status");
  try {
    const res = await fetch(`/api/trazabilidad_pcb/materiales?${trzParams("m")}`, { credentials: "same-origin" });
    const data = await res.json();
    if (data.status !== "success") { trzNotify("Error: " + (data.message || "?"), "error"); return; }

    // Primera carga: si el campo Desde esta vacio, preseleccionar hoy y recargar.
    if (!trzFechaInicializada) {
      trzFechaInicializada = true;
      const desde = document.getElementById("trz-m-desde");
      if (desde && !desde.value && data.fecha_hoy) {
        desde.value = data.fecha_hoy;
        trzHideLoading("m");
        return trzLoadMateriales();
      }
    }

    const tbody = document.getElementById("trz-m-body");
    tbody.innerHTML = "";
    data.items.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td><span class="trz-badge ${trzEsc(r.proceso.toLowerCase())}">${trzEsc(r.proceso)}</span></td>` +
        `<td>${trzEsc(r.lot_no)}</td><td>${trzEsc(r.linea)}</td><td>${trzEsc(r.part_no)}</td>` +
        `<td>${trzEsc(r.material_code)}</td><td>${trzEsc(r.numero_lote_material)}</td><td>${trzEsc(r.posicion)}</td>` +
        `<td>${r.cantidad_inicial}</td><td>${r.cantidad_consumida}</td><td>${r.cantidad_restante}</td><td>${r.pcb_count}</td>` +
        `<td><span class="trz-badge ${trzEsc(r.status)}">${trzEsc(r.status)}</span></td>` +
        `<td>${trzEsc(r.material_start_ts)}</td><td>${trzEsc(r.pcb_last_ts)}</td>`;
      tbody.appendChild(tr);
    });
    if (status) status.textContent = `${data.items.length} registro${data.items.length !== 1 ? "s" : ""}`;
  } catch (e) {
    console.error(e); trzNotify("Error al cargar trazabilidad", "error");
  } finally {
    trzHideLoading("m");
  }
}

// ── Vista 2: inversa por proveedor ──
async function trzLoadProveedor() {
  trzShowLoading("p");
  const status = document.getElementById("trz-p-status");
  try {
    const res = await fetch(`/api/trazabilidad_pcb/por_proveedor?${trzParams("p")}`, { credentials: "same-origin" });
    const data = await res.json();
    if (data.status !== "success") { trzNotify("Error: " + (data.message || "?"), "error"); return; }
    const tbody = document.getElementById("trz-p-body");
    tbody.innerHTML = "";
    data.items.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td><span class="trz-badge ${trzEsc(r.proceso.toLowerCase())}">${trzEsc(r.proceso)}</span></td>` +
        `<td>${trzEsc(r.pcb_serial)}</td><td>${trzEsc(r.ts)}</td><td>${trzEsc(r.lote_proveedor)}</td>` +
        `<td>${trzEsc(r.material_code)}</td><td>${trzEsc(r.lot_no)}</td><td>${trzEsc(r.linea)}</td>` +
        `<td>${trzEsc(r.part_no)}</td><td>${trzEsc(r.posicion)}</td>`;
      tbody.appendChild(tr);
    });
    if (status) {
      status.textContent = data.message
        ? data.message
        : `${data.items.length} PCB${data.items.length !== 1 ? "s" : ""}`;
    }
  } catch (e) {
    console.error(e); trzNotify("Error al cargar trazabilidad inversa", "error");
  } finally {
    trzHideLoading("p");
  }
}

// ── Export ──
async function trzExport(endpoint, panel) {
  try {
    const res = await fetch(`/api/trazabilidad_pcb/${endpoint}/export?${trzParams(panel)}`, { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const blob = await res.blob();
    let filename = `trazabilidad_${endpoint}.xlsx`;
    const disp = res.headers.get("content-disposition");
    if (disp) {
      const m = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disp);
      if (m && m[1]) filename = m[1].replace(/['"]/g, "");
    }
    const a = document.createElement("a");
    a.href = window.URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    trzNotify("Exportación completada", "success");
  } catch (e) {
    console.error(e); trzNotify("Error al exportar", "error");
  }
}

function trzClearQ() {
  ["trz-q-pcb", "trz-q-proceso"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  const tbody = document.getElementById("trz-q-body");
  if (tbody) tbody.innerHTML = "";
  const status = document.getElementById("trz-q-status");
  if (status) status.textContent = "Escanea un PCB";
  trzClearHistorial();
  document.getElementById("trz-q-pcb")?.focus();
}

function trzClearM() {
  ["trz-m-proceso", "trz-m-lote", "trz-m-parte", "trz-m-material", "trz-m-desde", "trz-m-hasta"]
    .forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  trzLoadMateriales();
}
function trzClearP() {
  ["trz-p-proceso", "trz-p-material", "trz-p-desde", "trz-p-hasta"]
    .forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  trzLoadProveedor();
}

function trzSwitchTab(panel) {
  document.querySelectorAll(".tab-trz").forEach((t) =>
    t.classList.toggle("active", t.dataset.panel === panel));
  document.getElementById("trz-panel-pcb")?.classList.toggle("active", panel === "pcb");
  document.getElementById("trz-panel-materiales")?.classList.toggle("active", panel === "materiales");
  document.getElementById("trz-panel-proveedor")?.classList.toggle("active", panel === "proveedor");
  if (panel === "pcb") document.getElementById("trz-q-pcb")?.focus();
  if (panel === "materiales") trzLoadMateriales();
  if (panel === "proveedor") trzLoadProveedor();
}

// ── Event delegation (idempotente) ──
function trzInitListeners() {
  if (document.body.dataset.trzListenersAttached) return;
  document.body.addEventListener("click", (e) => {
    const t = e.target;
    if (t.closest(".tab-trz")) { trzSwitchTab(t.closest(".tab-trz").dataset.panel); return; }
    if (t.id === "trz-q-buscar") { e.preventDefault(); trzLoadPcb(); return; }
    if (t.id === "trz-q-limpiar") { e.preventDefault(); trzClearQ(); return; }
    if (t.id === "trz-q-exportar") { e.preventDefault(); trzExport("por_pcb", "q"); return; }
    if (t.id === "trz-m-buscar") { e.preventDefault(); trzLoadMateriales(); return; }
    if (t.id === "trz-m-limpiar") { e.preventDefault(); trzClearM(); return; }
    if (t.id === "trz-m-exportar") { e.preventDefault(); trzExport("materiales", "m"); return; }
    if (t.id === "trz-p-buscar") { e.preventDefault(); trzLoadProveedor(); return; }
    if (t.id === "trz-p-limpiar") { e.preventDefault(); trzClearP(); return; }
    if (t.id === "trz-p-exportar") { e.preventDefault(); trzExport("por_proveedor", "p"); return; }
  });
  // Enter en el campo de PCB = buscar (la pistola termina el scan con Enter).
  document.body.addEventListener("keydown", (e) => {
    if (e.target.id === "trz-q-pcb" && e.key === "Enter") { e.preventDefault(); trzLoadPcb(); }
  });
  document.body.dataset.trzListenersAttached = "true";
}

function trzInit() {
  trzEnsureStyles();
  trzInitListeners();
  document.getElementById("trz-q-pcb")?.focus();
}

window.initializeTrazabilidadPcbEventListeners = trzInitListeners;
window.loadTrazabilidadPcbData = trzInit;
window.limpiarTrazabilidadPcb = function () {
  ["m", "p"].forEach(trzHideLoading);
};

document.addEventListener("DOMContentLoaded", trzInit);
if (document.readyState === "interactive" || document.readyState === "complete") {
  setTimeout(trzInit, 100);
}
