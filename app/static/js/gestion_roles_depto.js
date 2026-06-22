// ====== Gestión de roles por departamento (prefijo grd-) ======
// Listeners DELEGADOS en document (sobreviven a re-inyección del fragmento AJAX).
// WF_005: sin handlers inline para datos dinámicos; escapeHtml en texto visible.

let grdCtx = { es_superadmin: false, departamento: "" };
let grdRoles = [];
let grdDisponibles = {};      // {pagina: {seccion: [{id,boton,descripcion}]}}
let grdRolActual = null;      // {id, nombre, ...}

// Nombre legible del navbar para cada pagina (LISTA_*).
const GRD_NOMBRE_PAGINA = {
  "LISTA_INFORMACIONBASICA": "Información Básica",
  "LISTA_DE_MATERIALES": "Control de material",
  "LISTA_CONTROLDEPRODUCCION": "Control de producción",
  "LISTA_CONTROL_DE_PROCESO": "Control de proceso",
  "LISTA_CONTROL_DE_CALIDAD": "Control de calidad",
  "LISTA_DE_CONTROL_DE_RESULTADOS": "Control de resultados",
  "LISTA_DE_CONTROL_DE_REPORTE": "Control de reporte",
  "LISTA_DE_CONFIGPG": "Configuración de programa",
  "APP_REGISTRO_EMBARQUES": "App Registro de Embarques",
};

function grdNombrePagina(pagina) {
  return GRD_NOMBRE_PAGINA[pagina] || pagina;
}

// Orden de las páginas igual al navbar.
const GRD_ORDEN_PAGINA = [
  "LISTA_INFORMACIONBASICA",
  "LISTA_DE_MATERIALES",
  "LISTA_CONTROLDEPRODUCCION",
  "LISTA_CONTROL_DE_PROCESO",
  "LISTA_CONTROL_DE_CALIDAD",
  "LISTA_DE_CONTROL_DE_RESULTADOS",
  "LISTA_DE_CONTROL_DE_REPORTE",
  "LISTA_DE_CONFIGPG",
];

function grdOrdenarPaginas(paginas) {
  return paginas.slice().sort((a, b) => {
    let ia = GRD_ORDEN_PAGINA.indexOf(a);
    let ib = GRD_ORDEN_PAGINA.indexOf(b);
    if (ia === -1) ia = 999;  // páginas desconocidas al final
    if (ib === -1) ib = 999;
    if (ia !== ib) return ia - ib;
    return a.localeCompare(b);
  });
}

function grdEscapeHtml(v) {
  return String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function grdNotify(msg, type) {
  const old = document.querySelector(".grd-notification");
  if (old) old.remove();
  const el = document.createElement("div");
  el.className = "grd-notification";
  el.style.cssText =
    "position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:#fff;font-weight:600;font-size:.9rem;z-index:2147483647;box-shadow:0 4px 12px rgba(0,0,0,.3);";
  el.style.backgroundColor = type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function grdLoadContexto() {
  const res = await fetch("/api/gestion-roles-depto/contexto");
  grdCtx = await res.json();
  const hint = document.getElementById("grd-scope-hint");
  if (hint) hint.textContent = grdCtx.es_superadmin ? "Todos" : (grdCtx.departamento || "");
}

async function grdLoadRoles() {
  const res = await fetch("/api/gestion-roles-depto/roles");
  const data = await res.json();
  if (data.error) { grdNotify(data.error, "error"); return; }
  grdRoles = data;
  grdRenderRoles();
}

function grdRenderRoles() {
  const cont = document.getElementById("grd-roles-list");
  if (!cont) return;
  if (!grdRoles.length) {
    cont.innerHTML = '<span class="grd-muted">Sin roles en tu departamento. Crea uno nuevo.</span>';
    return;
  }
  cont.innerHTML = "";
  grdRoles.forEach((r) => {
    const div = document.createElement("div");
    div.className = "grd-role-item" + (grdRolActual && grdRolActual.id === r.id ? " active" : "");
    div.dataset.rolId = r.id;
    div.innerHTML =
      `<div class="grd-role-name">${grdEscapeHtml(r.nombre)}</div>` +
      `<div class="grd-role-meta">${grdEscapeHtml(r.departamento || "Transversal")} · ${r.total_usuarios} usuario(s)</div>`;
    cont.appendChild(div);
  });
}

async function grdLoadDisponibles() {
  const res = await fetch("/api/gestion-roles-depto/permisos-disponibles");
  grdDisponibles = await res.json();
  if (grdDisponibles.error) { grdNotify(grdDisponibles.error, "error"); grdDisponibles = {}; }
}

async function grdSeleccionarRol(rolId) {
  grdRolActual = grdRoles.find((r) => r.id == rolId);
  if (!grdRolActual) return;
  grdRenderRoles();

  document.getElementById("grd-perms-title").textContent = "Permisos de: " + grdRolActual.nombre;
  document.getElementById("grd-btn-editar-rol").style.display = "";
  document.getElementById("grd-btn-guardar-perms").style.display = "";

  // Permisos actualmente asignados al rol.
  const res = await fetch(`/api/gestion-roles-depto/permisos-rol/${rolId}`);
  const asignados = await res.json();
  grdPermFiltro = "";
  const setAsignados = new Set(Array.isArray(asignados) ? asignados : []);
  grdRenderPermisos(setAsignados);
}

let grdAsignados = new Set();   // ids de permisos marcados (estado vivo)

function grdRenderPermisos(setAsignados) {
  grdAsignados = setAsignados instanceof Set ? setAsignados : new Set(setAsignados || []);
  const body = document.getElementById("grd-perms-body");
  body.innerHTML = "";
  const paginas = grdOrdenarPaginas(Object.keys(grdDisponibles));
  if (!paginas.length) {
    body.innerHTML = '<div class="grd-empty">No hay permisos de tu área disponibles.</div>';
    return;
  }

  // Barra de herramientas: buscar + marcar/limpiar todo.
  const toolbar = document.createElement("div");
  toolbar.className = "grd-perms-toolbar";
  toolbar.innerHTML =
    `<input type="text" id="grd-perms-search" class="grd-perms-search" placeholder="Buscar permiso...">` +
    `<button type="button" class="grd-mini-btn" data-grd-all="1">Marcar todo</button>` +
    `<button type="button" class="grd-mini-btn" data-grd-all="0">Limpiar todo</button>`;
  body.appendChild(toolbar);

  const filtro = (grdPermFiltro || "").toLowerCase();

  paginas.forEach((pagina) => {
    const secciones = grdDisponibles[pagina];
    const nombrePag = grdNombrePagina(pagina);
    // Filtrar permisos por texto (incluye el nombre legible de la página).
    const seccionesVis = {};
    Object.keys(secciones).forEach((sec) => {
      const items = secciones[sec].filter(
        (p) => !filtro || (`${p.boton} ${p.descripcion || ""} ${sec} ${nombrePag}`).toLowerCase().includes(filtro)
      );
      if (items.length) seccionesVis[sec] = items;
    });
    if (!Object.keys(seccionesVis).length) return;

    const idsPagina = [];
    Object.values(seccionesVis).forEach((arr) => arr.forEach((p) => idsPagina.push(p.id)));
    const marcadosPag = idsPagina.filter((id) => grdAsignados.has(id)).length;

    const grupo = document.createElement("details");
    grupo.className = "grd-pagina-group";
    grupo.open = !!filtro;  // cerrados por defecto; solo expandir al buscar
    grupo.innerHTML =
      `<summary class="grd-pagina-summary">` +
        `<span class="grd-pagina-title">${grdEscapeHtml(grdNombrePagina(pagina))}</span>` +
        `<span class="grd-pagina-count">${marcadosPag}/${idsPagina.length}</span>` +
        `<span class="grd-mini-btn grd-toggle-grp" data-ids="${idsPagina.join(",")}">Alternar</span>` +
      `</summary>`;

    Object.keys(seccionesVis).forEach((seccion) => {
      const idsSec = seccionesVis[seccion].map((p) => p.id);
      const secWrap = document.createElement("div");
      secWrap.className = "grd-seccion";
      secWrap.innerHTML =
        `<div class="grd-seccion-title">` +
          `<span>${grdEscapeHtml(seccion)}</span>` +
          `<span class="grd-mini-btn grd-toggle-grp" data-ids="${idsSec.join(",")}">Alternar sección</span>` +
        `</div>`;
      seccionesVis[seccion].forEach((p) => {
        const checked = grdAsignados.has(p.id);
        const row = document.createElement("label");
        row.className = "grd-perm-item" + (checked ? " on" : "");
        row.dataset.permId = p.id;
        row.innerHTML =
          `<input type="checkbox" class="grd-perm-cb" value="${p.id}" ${checked ? "checked" : ""}>` +
          `<span class="grd-perm-text"><span class="grd-perm-boton">${grdEscapeHtml(p.boton)}</span>` +
          (p.descripcion ? `<span class="grd-perm-desc">${grdEscapeHtml(p.descripcion)}</span>` : "") +
          `</span>`;
        secWrap.appendChild(row);
      });
      grupo.appendChild(secWrap);
    });
    body.appendChild(grupo);
  });

  grdActualizarContador();
}

function grdActualizarContador() {
  let total = 0;
  Object.values(grdDisponibles).forEach((secs) =>
    Object.values(secs).forEach((arr) => (total += arr.length))
  );
  const count = document.getElementById("grd-perms-count");
  if (count) count.textContent = `${grdAsignados.size}/${total}`;
}

let grdPermFiltro = "";

function grdTodosLosIds() {
  const s = new Set();
  Object.values(grdDisponibles).forEach((secs) =>
    Object.values(secs).forEach((arr) => arr.forEach((p) => s.add(p.id)))
  );
  return s;
}

// ----- Modal rol -----
function grdAbrirModal() {
  const m = document.getElementById("grd-modal");
  if (m) { m.classList.add("is-open"); m.setAttribute("aria-hidden", "false"); }
}
function grdCerrarModal() {
  const m = document.getElementById("grd-modal");
  if (m) { m.classList.remove("is-open"); m.setAttribute("aria-hidden", "true"); }
}

function grdNuevoRol() {
  document.getElementById("grd-modal-title").textContent = "Nuevo rol";
  document.getElementById("grd-rol-nombre").value = "";
  document.getElementById("grd-rol-nombre").readOnly = false;
  document.getElementById("grd-rol-descripcion").value = "";
  document.getElementById("grd-btn-guardar-rol").dataset.rolId = "";
  grdConfigDeptoModal(null);
  grdAbrirModal();
}

function grdEditarRol() {
  if (!grdRolActual) return;
  document.getElementById("grd-modal-title").textContent = "Editar rol";
  document.getElementById("grd-rol-nombre").value = grdRolActual.nombre;
  document.getElementById("grd-rol-descripcion").value = grdRolActual.descripcion || "";
  document.getElementById("grd-btn-guardar-rol").dataset.rolId = grdRolActual.id;
  grdConfigDeptoModal(grdRolActual.departamento || "");
  grdAbrirModal();
}

function grdConfigDeptoModal(deptoActual) {
  const group = document.getElementById("grd-rol-depto-group");
  const fijo = document.getElementById("grd-rol-depto-fijo");
  if (grdCtx.es_superadmin) {
    // Superadmin: por simplicidad deja el departamento como está (no editable aquí).
    group.style.display = "none";
    fijo.textContent = deptoActual ? `Departamento: ${deptoActual}` : "Rol transversal";
  } else {
    group.style.display = "none";
    fijo.textContent = `Este rol pertenecerá al departamento: ${grdCtx.departamento}`;
  }
}

async function grdGuardarRol() {
  const rolId = document.getElementById("grd-btn-guardar-rol").dataset.rolId;
  const payload = {
    rol_id: rolId ? parseInt(rolId) : null,
    nombre: document.getElementById("grd-rol-nombre").value.trim(),
    descripcion: document.getElementById("grd-rol-descripcion").value.trim(),
  };
  if (!payload.nombre) { grdNotify("El nombre es requerido", "error"); return; }
  try {
    const res = await fetch("/api/gestion-roles-depto/guardar-rol", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || data.error) { grdNotify(data.error || "Error", "error"); return; }
    grdNotify(data.mensaje || "Guardado", "success");
    grdCerrarModal();
    await grdLoadRoles();
    if (data.rol_id) await grdSeleccionarRol(data.rol_id);
  } catch (e) { grdNotify("Error al guardar", "error"); }
}

async function grdGuardarPermisos() {
  if (!grdRolActual) return;
  // Usa el estado vivo (grdAsignados), no solo los checkboxes visibles:
  // con el buscador activo, algunos podrían estar fuera del DOM.
  const ids = Array.from(grdAsignados);
  try {
    const res = await fetch("/api/gestion-roles-depto/guardar-permisos", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rol_id: grdRolActual.id, permisos_ids: ids }),
    });
    const data = await res.json();
    if (!res.ok || data.error) { grdNotify(data.error || "Error", "error"); return; }
    grdNotify(data.mensaje || "Permisos guardados", "success");
    await grdSeleccionarRol(grdRolActual.id);
  } catch (e) { grdNotify("Error al guardar permisos", "error"); }
}

function grdInitListeners() {
  if (document.body.dataset.grdListenersAttached) return;
  document.body.dataset.grdListenersAttached = "true";

  document.addEventListener("click", function (e) {
    if (e.target.closest("#grd-btn-nuevo-rol")) { grdNuevoRol(); return; }
    if (e.target.closest("#grd-btn-editar-rol")) { grdEditarRol(); return; }
    if (e.target.closest("#grd-btn-guardar-rol")) { grdGuardarRol(); return; }
    if (e.target.closest("#grd-btn-guardar-perms")) { grdGuardarPermisos(); return; }

    // Marcar/limpiar todo (sobre lo disponible completo).
    const allBtn = e.target.closest("[data-grd-all]");
    if (allBtn) {
      const marcar = allBtn.dataset.grdAll === "1";
      grdAsignados = marcar ? grdTodosLosIds() : new Set();
      grdRenderPermisos(grdAsignados);
      return;
    }

    // Alternar un grupo (página o sección).
    const grp = e.target.closest(".grd-toggle-grp");
    if (grp) {
      e.preventDefault();
      const ids = grp.dataset.ids.split(",").filter(Boolean).map(Number);
      const todosMarcados = ids.every((id) => grdAsignados.has(id));
      ids.forEach((id) => { todosMarcados ? grdAsignados.delete(id) : grdAsignados.add(id); });
      grdRenderPermisos(grdAsignados);
      return;
    }

    const role = e.target.closest(".grd-role-item");
    if (role) { grdSeleccionarRol(role.dataset.rolId); return; }
    if (e.target.closest("#grd-modal") && e.target.closest("[data-grd-close]")) { grdCerrarModal(); }
  });

  // Checkbox individual -> actualizar estado vivo.
  document.addEventListener("change", function (e) {
    if (e.target.classList && e.target.classList.contains("grd-perm-cb")) {
      const id = parseInt(e.target.value);
      if (e.target.checked) grdAsignados.add(id); else grdAsignados.delete(id);
      const row = e.target.closest(".grd-perm-item");
      if (row) row.classList.toggle("on", e.target.checked);
      grdActualizarContador();
    }
  });

  // Buscador (no re-renderiza desde cero el estado, solo filtra la vista).
  document.addEventListener("input", function (e) {
    if (e.target.id === "grd-perms-search") {
      grdPermFiltro = e.target.value;
      grdRenderPermisos(grdAsignados);
      const inp = document.getElementById("grd-perms-search");
      if (inp) { inp.focus(); inp.value = grdPermFiltro; inp.setSelectionRange(grdPermFiltro.length, grdPermFiltro.length); }
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") grdCerrarModal();
  });
}

async function grdInit() {
  grdInitListeners();
  await grdLoadContexto();
  await grdLoadDisponibles();
  await grdLoadRoles();
}

window.grdInit = grdInit;
window.limpiarGestionRolesDepto = function () {
  const n = document.querySelector(".grd-notification");
  if (n) n.remove();
};

document.addEventListener("DOMContentLoaded", grdInit);
if (document.readyState === "interactive" || document.readyState === "complete") {
  setTimeout(grdInit, 50);
}
