// ====== Administración de usuario acotada por departamento (prefijo adu-) ======
// WF_003 frontend + WF_005 (sin handlers inline para datos dinámicos).

let aduUsuarios = [];
let aduContexto = { es_superadmin: false, departamento_propio: "", departamentos: [], roles: [], cargos: [] };

function aduEscapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function aduNotify(message, type) {
  const old = document.querySelector(".adu-notification");
  if (old) old.remove();
  const el = document.createElement("div");
  el.className = "adu-notification";
  el.style.cssText =
    "position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:#fff;font-weight:600;font-size:.9rem;z-index:10000;box-shadow:0 4px 12px rgba(0,0,0,.3);";
  el.style.backgroundColor = type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function aduFill(selectId, values, selected) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = "";
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    if (v === selected) opt.selected = true;
    sel.appendChild(opt);
  });
}

// Cargo = texto libre con sugerencias (datalist). Puebla las opciones del
// datalist y fija el valor actual del input.
function aduFillCargo(values, current) {
  const list = document.getElementById("adu-cargo-options");
  if (list) {
    list.innerHTML = "";
    values.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      list.appendChild(opt);
    });
  }
  const input = document.getElementById("adu-cargo");
  if (input) input.value = current || "";
}

function aduRenderRoles(selectedRoles) {
  const cont = document.getElementById("adu-roles-list");
  if (!cont) return;
  cont.innerHTML = "";
  if (!aduContexto.roles.length) {
    cont.innerHTML = '<span class="adu-muted">No hay roles asignables.</span>';
    return;
  }
  const sel = new Set(selectedRoles || []);
  aduContexto.roles.forEach((rol) => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = rol;
    cb.className = "adu-rol-cb";
    if (sel.has(rol)) cb.checked = true;
    const span = document.createElement("span");
    span.textContent = rol; // textContent => seguro ante caracteres especiales
    label.appendChild(cb);
    label.appendChild(span);
    cont.appendChild(label);
  });
}

async function aduLoadContexto() {
  const res = await fetch("/api/admin-usuarios-depto/contexto");
  aduContexto = await res.json();
  if (aduContexto.error) { aduNotify("Error: " + aduContexto.error, "error"); return; }

  const hint = document.getElementById("adu-scope-hint");
  if (hint) {
    hint.textContent = aduContexto.es_superadmin
      ? "Acceso total: puedes administrar todos los departamentos."
      : `Solo puedes administrar usuarios del departamento: ${aduContexto.departamento_propio || "(sin departamento)"}.`;
  }

  aduFill("adu-departamento", aduContexto.departamentos, aduContexto.departamento_propio);
  aduFillCargo(aduContexto.cargos, "");
  // Delegado: departamento fijo (no editable).
  const depSel = document.getElementById("adu-departamento");
  if (depSel) depSel.disabled = !aduContexto.es_superadmin;
  aduRenderRoles([]);
}

async function aduLoadUsuarios() {
  const res = await fetch("/api/admin-usuarios-depto/usuarios");
  const data = await res.json();
  if (data.error) { aduNotify("Error: " + data.error, "error"); return; }
  aduUsuarios = data;
  aduRenderTable();
}

function aduRenderTable() {
  const tbody = document.getElementById("adu-body");
  if (!tbody) return;
  const filtro = (document.getElementById("adu-buscar")?.value || "").toLowerCase();
  const rows = aduUsuarios.filter(
    (u) => !filtro ||
      (u.username || "").toLowerCase().includes(filtro) ||
      (u.nombre_completo || "").toLowerCase().includes(filtro)
  );

  const counter = document.getElementById("adu-count");
  if (counter) counter.textContent = `${rows.length} registro${rows.length !== 1 ? "s" : ""}`;

  tbody.innerHTML = "";
  rows.forEach((u) => {
    const tr = document.createElement("tr");
    const estado = u.activo
      ? '<span class="adu-badge on">Activo</span>'
      : '<span class="adu-badge off">Inactivo</span>';
    tr.innerHTML =
      `<td>${aduEscapeHtml(u.username)}</td>` +
      `<td>${aduEscapeHtml(u.nombre_completo)}</td>` +
      `<td>${aduEscapeHtml(u.departamento)}</td>` +
      `<td>${aduEscapeHtml((u.roles || []).join(", "))}</td>` +
      `<td>${estado}</td>` +
      `<td><span class="adu-link adu-edit" data-username="${aduEscapeHtml(u.username)}">Editar</span></td>`;
    tbody.appendChild(tr);
  });
}

function aduAbrirModal() {
  const modal = document.getElementById("adu-modal");
  if (modal) {
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
  }
}

function aduCerrarModal() {
  const modal = document.getElementById("adu-modal");
  if (modal) {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  }
}

function aduNuevo() {
  aduLimpiar();
  aduAbrirModal();
  setTimeout(() => document.getElementById("adu-username")?.focus(), 50);
}

function aduEditar(username) {
  const u = aduUsuarios.find((x) => x.username === username);
  if (!u) return;
  aduLimpiar();
  aduAbrirModal();
  document.getElementById("adu-form-title").textContent = "Editar usuario";
  document.getElementById("adu-username").value = u.username;
  document.getElementById("adu-username").readOnly = true;
  document.getElementById("adu-nombre").value = u.nombre_completo || "";
  document.getElementById("adu-email").value = u.email || "";
  document.getElementById("adu-password").value = "";
  document.getElementById("adu-pass-hint").textContent = "(dejar vacío para no cambiar)";
  if (aduContexto.es_superadmin) aduFill("adu-departamento", aduContexto.departamentos, u.departamento);
  aduFillCargo(aduContexto.cargos, u.cargo || "");
  document.getElementById("adu-activo").checked = !!u.activo;
  aduRenderRoles(u.roles || []);
}

function aduLimpiar() {
  ["adu-username", "adu-nombre", "adu-email", "adu-password", "adu-cargo"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  document.getElementById("adu-form-title").textContent = "Nuevo usuario";
  document.getElementById("adu-username").readOnly = false;
  document.getElementById("adu-pass-hint").textContent = "(requerida)";
  if (aduContexto.es_superadmin) {
    aduFill("adu-departamento", aduContexto.departamentos, "");
  } else {
    aduFill("adu-departamento", aduContexto.departamentos, aduContexto.departamento_propio);
  }
  document.getElementById("adu-departamento").disabled = !aduContexto.es_superadmin;
  document.getElementById("adu-activo").checked = true;
  aduRenderRoles([]);
}

async function aduGuardar() {
  const roles = Array.from(document.querySelectorAll(".adu-rol-cb:checked")).map((c) => c.value);
  const payload = {
    username: document.getElementById("adu-username").value.trim(),
    nombre_completo: document.getElementById("adu-nombre").value.trim(),
    email: document.getElementById("adu-email").value.trim(),
    password: document.getElementById("adu-password").value,
    departamento: document.getElementById("adu-departamento").value,
    cargo: document.getElementById("adu-cargo").value,
    activo: document.getElementById("adu-activo").checked ? 1 : 0,
    roles: roles,
  };
  if (!payload.username || !payload.nombre_completo) {
    aduNotify("Usuario y nombre son requeridos", "error");
    return;
  }
  try {
    const res = await fetch("/api/admin-usuarios-depto/guardar_usuario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      aduNotify("Error: " + (data.error || res.status), "error");
      return;
    }
    aduNotify(data.mensaje || "Guardado", "success");
    aduCerrarModal();
    aduLimpiar();
    aduLoadUsuarios();
  } catch (err) {
    console.error(err);
    aduNotify("Error al guardar", "error");
  }
}

function aduInitListeners() {
  // Listeners DELEGADOS en document, enganchados una sola vez globalmente.
  // Sobreviven a cada re-inyección del fragmento AJAX (el HTML del módulo se
  // re-crea con innerHTML, pero el handler vive en document, no en los nodos).
  if (document.body.dataset.aduListenersAttached) return;
  document.body.dataset.aduListenersAttached = "true";

  document.addEventListener("click", function (e) {
    if (e.target.closest("#adu-btn-nuevo")) { aduNuevo(); return; }
    if (e.target.closest("#adu-btn-guardar")) { aduGuardar(); return; }
    const edit = e.target.closest(".adu-edit");
    if (edit) { aduEditar(edit.dataset.username); return; }
    // Cerrar modal: backdrop, X o Cancelar (solo si el clic ocurre dentro del modal)
    if (e.target.closest("#adu-modal") && e.target.closest("[data-adu-close]")) {
      aduCerrarModal();
    }
  });

  document.addEventListener("input", function (e) {
    if (e.target.id === "adu-buscar") aduRenderTable();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") aduCerrarModal();
  });
}

async function aduInit() {
  aduInitListeners();
  await aduLoadContexto();
  await aduLoadUsuarios();
}

window.aduInit = aduInit;
window.limpiarAdminUsuariosDepto = function () {
  const n = document.querySelector(".adu-notification");
  if (n) n.remove();
};

document.addEventListener("DOMContentLoaded", aduInit);
if (document.readyState === "interactive" || document.readyState === "complete") {
  setTimeout(aduInit, 50);
}
