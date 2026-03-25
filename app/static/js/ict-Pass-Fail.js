// ====== ICT Pass/Fail Module ======
// Prefijo "pf-" en todos los IDs para evitar conflictos en el DOM

let pfModuleData = [];

// ====== Control de carga ======

function pfShowLoading() {
  const loader = document.getElementById("pf-ict-table-loading");
  const table  = document.getElementById("pf-ict-table");
  if (loader && table) {
    const wrap  = table.closest(".pf-table-wrap");
    const thead = table.querySelector("thead");
    if (wrap && thead) {
      wrap.style.setProperty("--thead-height", `${thead.offsetHeight}px`);
    }
    loader.classList.add("active");
  }
}

function pfHideLoading() {
  const loader = document.getElementById("pf-ict-table-loading");
  if (loader) loader.classList.remove("active");
}

// ====== Notificaciones ======

function pfNotify(message, type = "info") {
  const old = document.querySelector(".pf-notification");
  if (old) old.remove();

  const el = document.createElement("div");
  el.className = "pf-notification";
  el.style.cssText = `
    position:fixed; top:20px; right:20px; padding:12px 20px;
    border-radius:6px; color:#fff; font-weight:600; font-size:0.9rem;
    z-index:10000; box-shadow:0 4px 12px rgba(0,0,0,.3);
    animation:pf-fadeInUp .3s ease;
  `;
  el.style.backgroundColor =
    type === "success" ? "#27ae60" :
    type === "error"   ? "#e74c3c" : "#3498db";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => { if (el.parentNode) el.remove(); }, 4000);
}

// ====== Carga de datos ======

async function pfLoadData() {
  pfShowLoading();
  try {
    const fecha    = document.getElementById("pf-filter-fecha")?.value       || "";
    const linea    = document.getElementById("pf-filter-linea")?.value       || "";
    const no_parte = document.getElementById("pf-filter-part-number")?.value || "";

    const url = `/api/ict/pass-fail?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&no_parte=${encodeURIComponent(no_parte)}`;
    const res  = await fetch(url);
    const data = await res.json();

    if (data.error) {
      pfNotify("Error al consultar datos: " + data.error, "error");
      return;
    }

    pfModuleData = data;

    // Actualizar contador
    const counter = document.getElementById("pf-record-count");
    if (counter) {
      counter.textContent = `${data.length} registro${data.length !== 1 ? "s" : ""}`;
    }

    pfRenderTable(data);
  } catch (err) {
    console.error(err);
    pfNotify("Error al cargar datos", "error");
  } finally {
    pfHideLoading();
  }
}

// ====== Renderizado de tabla ======

function pfRenderTable(data) {
  const tbody = document.getElementById("pf-ict-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.fecha ?? ""}</td>
      <td>${row.linea ?? ""}</td>
      <td>${row.ict ?? ""}</td>
      <td>${row.no_parte ?? ""}</td>
      <td>${row.ok_count ?? 0}</td>
      <td>${row.ng_count ?? 0}</td>
      <td>${row.pct_ok ?? 0}%</td>
      <td>${row.pct_ng ?? 0}%</td>
      <td>${row.total ?? 0}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ====== Exportar a Excel ======

async function pfExportExcel() {
  const fecha    = document.getElementById("pf-filter-fecha")?.value       || "";
  const linea    = document.getElementById("pf-filter-linea")?.value       || "";
  const no_parte = document.getElementById("pf-filter-part-number")?.value || "";

  const url = `/api/ict/pass-fail/export?fecha=${encodeURIComponent(fecha)}&linea=${encodeURIComponent(linea)}&no_parte=${encodeURIComponent(no_parte)}`;

  try {
    const response = await fetch(url, { method: "GET", credentials: "same-origin" });
    if (!response.ok) throw new Error(`Status ${response.status}`);

    const blob = await response.blob();
    let filename = `ict_pass_fail_${Date.now()}.xlsx`;

    const disposition = response.headers.get("content-disposition");
    if (disposition) {
      const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (match && match[1]) filename = match[1].replace(/['"]/g, "");
    }

    const a = document.createElement("a");
    a.href = window.URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(a.href);

    pfNotify("Exportación completada", "success");
  } catch (err) {
    console.error(err);
    pfNotify("Error al exportar", "error");
  }
}

// ====== Fecha por defecto ======

function pfSetDefaultDate() {
  const input = document.getElementById("pf-filter-fecha");
  if (input && !input.value) {
    input.value = new Date().toISOString().split("T")[0];
  }
}

// ====== Cleanup ======

function pfCleanup() {
  const loader = document.getElementById("pf-ict-table-loading");
  if (loader) loader.classList.remove("active");
}
window.limpiarHistorialICTPassFail = pfCleanup;

// ====== Event Delegation ======

function pfInitListeners() {
  if (document.body.dataset.pfIctListenersAttached) return;

  document.body.addEventListener("click", function (e) {
    const target = e.target;

    // Botón consultar
    if (target.id === "pf-btn-consultar" || target.closest("#pf-btn-consultar")) {
      e.preventDefault();
      pfLoadData();
      return;
    }

    // Botón exportar
    if (target.id === "pf-btn-export-excel" || target.closest("#pf-btn-export-excel")) {
      e.preventDefault();
      pfExportExcel();
      return;
    }
  });

  document.body.dataset.pfIctListenersAttached = "true";
}

// ====== Exponer globalmente ======
window.pfLoadData     = pfLoadData;
window.pfExportExcel  = pfExportExcel;
window.pfInitListeners = pfInitListeners;

// ====== Auto-inicialización ======

document.addEventListener("DOMContentLoaded", function () {
  pfSetDefaultDate();
  pfInitListeners();
  pfLoadData();
});

if (document.readyState === "interactive" || document.readyState === "complete") {
  pfSetDefaultDate();
  pfInitListeners();
  setTimeout(() => pfLoadData(), 100);
}
