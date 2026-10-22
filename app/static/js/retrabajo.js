/* Solicitud de retrabajo (MES) y modal "Salida Retrabajo" de Salidas almacen embarques.
 * WF_003: loading, notify, load/render, export Excel, cleanup e init idempotente.
 * WF_004: asegura retrabajo.css en <head> (tambien persistente en MainTemplate).
 * WF_007: delegacion de eventos con data-action, sin handlers inline.
 * WF_008: modales con ID unico creados una sola vez en document.body.
 */
(function () {
  "use strict";

  const API = "/api/retrabajo";
  const STYLESHEET_ID = "retrabajo-css";
  const STYLESHEET_HREF = "/static/css/retrabajo.css?v=20261022a";
  const ORIGENES = [
    ["EMBARQUES", "Embarques"],
    ["SMD", "SMD"],
    ["PRODUCCION", "Producción"],
  ];
  const ESTADOS = {
    PENDIENTE: "Pendiente",
    EN_PROCESO: "En proceso",
    COMPLETADA: "Completada",
    CANCELADA: "Cancelada",
  };
  const ETAPAS = {
    CP_RETRABAJO: "Etiquetas / Reprogramación",
    CP_REPARACION: "Reparación ASSY",
    SMD_REPARACION: "Reparación SMD/IMD",
  };
  const ICONS = {
    nueva: '<path d="M12 4v16m8-8H4"></path>',
    detalle:
      '<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>',
    salida:
      '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>',
    ver: '<path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>',
    seccion: '<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"></path>',
  };

  function ensureStylesheet() {
    const existing = document.getElementById(STYLESHEET_ID);
    if (existing) {
      if (existing.getAttribute("href") !== STYLESHEET_HREF) existing.setAttribute("href", STYLESHEET_HREF);
      return;
    }
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function svg(name, cls) {
    return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${ICONS[name]}</svg>`;
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function isoDate(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function notify(message, type) {
    document.querySelectorAll(".rtb-toast").forEach((el) => el.remove());
    const toast = document.createElement("div");
    toast.className = `rtb-toast rtb-toast--${type || "info"}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
  }

  const HTTP_ERRORS = {
    401: "Tu sesión expiró. Inicia sesión de nuevo.",
    403: "No tienes permiso para esta acción.",
    404: "Recurso no encontrado.",
    500: "Error interno del servidor.",
  };

  async function request(url, options) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...(options || {}),
      headers: { "Content-Type": "application/json", ...((options && options.headers) || {}) },
    });
    if (response.redirected && /\/login/.test(response.url)) throw new Error(HTTP_ERRORS[401]);
    return response;
  }

  async function fetchJson(url, options) {
    const response = await request(url, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
    if (!response.ok || !payload || payload.success === false) {
      throw new Error((payload && payload.error) || HTTP_ERRORS[response.status] || `Respuesta inválida (${response.status})`);
    }
    return payload;
  }

  function chip(estado, texto) {
    return `<span class="rtb-chip rtb-chip--${esc(estado)}">${esc(texto || ESTADOS[estado] || estado)}</span>`;
  }

  function areasHtml(areas, align) {
    return `<div class="rtb-chips ${align || ""}">${(areas || [])
      .map((a) => chip(a.estado, `${a.nombre} ${a.hecho}/${a.total}`))
      .join("")}</div>`;
  }

  function slug(texto) {
    return String(texto)
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_");
  }

  // `clave` identifica la tabla para recordar sus filtros por columna.
  function tabla(headers, rows, emptyText, clave) {
    const body = rows.length
      ? rows.map((cells) => `<tr>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")
      : `<tr><td colspan="${headers.length}" class="rtb-empty">${esc(emptyText)}</td></tr>`;
    return `<div class="rtb-table-wrap rtb-table-wrap--compact"><table class="rtb-table rtb-table--compact" data-rtb-table="${esc(clave)}"><thead><tr>${headers
      .map((h) => `<th data-rtb-field="${esc(slug(h))}">${esc(h)}</th>`)
      .join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  // ===================== Filtro por columna (estilo ICT) =====================
  // Toda <table data-rtb-table="clave"> con <th data-rtb-field> recibe el embudo:
  // filtra en cliente por el texto de la celda y se recuerda por tabla, como ICT.
  const FILTROS_KEY = "retrabajo_columnFilters";

  function leerFiltros() {
    try {
      return JSON.parse(window.localStorage.getItem(FILTROS_KEY) || "{}") || {};
    } catch (error) {
      return {};
    }
  }

  function guardarFiltro(clave, campo, valor) {
    const state = leerFiltros();
    const filtros = state[clave] || {};
    if (valor) filtros[campo] = valor;
    else delete filtros[campo];
    state[clave] = filtros;
    try {
      window.localStorage.setItem(FILTROS_KEY, JSON.stringify(state));
    } catch (error) {
      // Sin localStorage (modo privado): el filtro funciona pero no se recuerda.
    }
  }

  function prepararFiltros(table) {
    const guardados = leerFiltros()[table.dataset.rtbTable] || {};
    table.querySelectorAll("th[data-rtb-field]").forEach((th) => {
      if (th.dataset.rtbFilterReady === "1") return;
      th.dataset.rtbFilterReady = "1";
      const label = th.textContent.trim();
      const campo = th.dataset.rtbField;
      th.classList.add("rtb-filterable");
      th.innerHTML = `
        <div class="rtb-column-header">
          <span>${esc(label)}</span>
          <button type="button" class="rtb-column-filter-btn" data-rtb-col-toggle title="Filtrar ${esc(label)}" aria-label="Filtrar ${esc(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
          </button>
        </div>
        <div class="rtb-column-filter-popover">
          <input class="rtb-column-filter-input" data-rtb-field="${esc(campo)}" value="${esc(guardados[campo] || "")}"
                 placeholder="Buscar..." aria-label="Buscar en ${esc(label)}" autocomplete="off">
          <div class="rtb-column-filter-actions">
            <button type="button" data-rtb-col-clear>Limpiar</button>
            <button type="button" data-rtb-col-clear-all>Todos</button>
          </div>
        </div>`;
    });
  }

  function aplicarFiltros(table) {
    const filtros = [];
    [...table.tHead.rows[0].cells].forEach((th, index) => {
      const input = th.querySelector(".rtb-column-filter-input");
      if (!input) return;
      const valor = input.value.trim().toLowerCase();
      th.querySelector(".rtb-column-filter-btn").classList.toggle("active", Boolean(valor));
      if (valor) filtros.push([index, valor]);
    });
    const tbody = table.tBodies[0];
    tbody.querySelectorAll("tr.rtb-no-match").forEach((tr) => tr.remove());
    const filas = [...tbody.rows].filter((tr) => !tr.querySelector(".rtb-empty"));
    filas.forEach((tr) => {
      tr.hidden = !filtros.every(([i, v]) => (tr.cells[i]?.textContent || "").toLowerCase().includes(v));
    });
    const visibles = filas.filter((tr) => !tr.hidden);
    if (filas.length && !visibles.length) {
      tbody.insertAdjacentHTML(
        "beforeend",
        `<tr class="rtb-no-match"><td colspan="${table.tHead.rows[0].cells.length}" class="rtb-empty">Sin coincidencias con el filtro</td></tr>`,
      );
    }
    if (typeof table.__rtbAfterFilter === "function") table.__rtbAfterFilter(visibles);
  }

  function activarFiltros(scope) {
    scope.querySelectorAll("table[data-rtb-table]").forEach((table) => {
      prepararFiltros(table);
      aplicarFiltros(table);
    });
  }

  function closeColumnFilters(except) {
    document.querySelectorAll(".rtb-column-filter-popover.open").forEach((popover) => {
      if (popover === except) return;
      popover.classList.remove("open");
      popover.closest("th").classList.remove("rtb-filter-open");
    });
  }

  // Un solo juego de listeners para todas las tablas (pagina y modales en body).
  if (!window.__rtbColumnFiltersBound) {
    window.__rtbColumnFiltersBound = true;
    document.addEventListener("click", (event) => {
      const toggle = event.target.closest("[data-rtb-col-toggle]");
      if (toggle) {
        const th = toggle.closest("th");
        const popover = th.querySelector(".rtb-column-filter-popover");
        closeColumnFilters(popover);
        th.classList.toggle("rtb-filter-open", popover.classList.toggle("open"));
        if (popover.classList.contains("open")) popover.querySelector("input").focus();
        return;
      }
      const limpiarUno = event.target.closest("[data-rtb-col-clear]");
      const limpiarTodos = event.target.closest("[data-rtb-col-clear-all]");
      if (limpiarUno || limpiarTodos) {
        const table = event.target.closest("table");
        const inputs = limpiarTodos
          ? [...table.querySelectorAll(".rtb-column-filter-input")]
          : [event.target.closest("th").querySelector(".rtb-column-filter-input")];
        inputs.forEach((input) => {
          input.value = "";
          guardarFiltro(table.dataset.rtbTable, input.dataset.rtbField, "");
        });
        if (limpiarTodos) closeColumnFilters();
        aplicarFiltros(table);
        return;
      }
      if (!event.target.closest(".rtb-column-filter-popover")) closeColumnFilters();
    });
    document.addEventListener("input", (event) => {
      const input = event.target.closest(".rtb-column-filter-input");
      if (!input) return;
      const table = input.closest("table");
      guardarFiltro(table.dataset.rtbTable, input.dataset.rtbField, input.value.trim());
      aplicarFiltros(table);
    });
  }

  function seccion(titulo) {
    return `<div class="rtb-section-title">${svg("seccion", "rtb-input-icon")}${esc(titulo)}</div>`;
  }

  // ===================== Modales (WF_008) =====================

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.style.display = "none";
    modal.style.opacity = "0";
    modal.style.visibility = "hidden";
    modal.querySelector(".rtb-modal-body").innerHTML = "";
  }

  // Idempotente: crea el modal una sola vez en document.body, con sus listeners.
  function ensureModal(id, overlayClose) {
    let modal = document.getElementById(id);
    if (modal) return modal;
    modal = document.createElement("div");
    modal.id = id;
    modal.className = "rtb-modal";
    modal.innerHTML = `
      <div class="rtb-modal-content" role="dialog" aria-modal="true" aria-labelledby="${id}-title">
        <div class="rtb-modal-header">
          <div class="rtb-modal-title-group">
            <span data-rtb-icon></span>
            <div>
              <h3 id="${id}-title"></h3>
              <span class="rtb-modal-subtitle" data-rtb-subtitle></span>
            </div>
          </div>
          <button type="button" class="rtb-close-btn" data-rtb-close aria-label="Cerrar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"></path></svg>
          </button>
        </div>
        <div class="rtb-modal-body"></div>
      </div>`;
    modal.addEventListener("click", (event) => {
      if (event.target.closest("[data-rtb-close]") || (overlayClose && event.target === modal)) closeModal(id);
    });
    document.body.appendChild(modal);
    return modal;
  }

  function openModal(id, { title, subtitle, icon, overlayClose = true }) {
    const modal = ensureModal(id, overlayClose);
    modal.querySelector(`#${id}-title`).textContent = title;
    modal.querySelector("[data-rtb-subtitle]").innerHTML = subtitle || "";
    modal.querySelector("[data-rtb-icon]").innerHTML = svg(icon, "rtb-modal-icon");
    modal.style.display = "flex";
    modal.style.opacity = "1";
    modal.style.visibility = "visible";
    return modal.querySelector(".rtb-modal-body");
  }

  if (!window.__rtbEscBound) {
    window.__rtbEscBound = true;
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      const abiertos = [...document.querySelectorAll("body > .rtb-modal")].filter((m) => m.style.display === "flex");
      if (abiertos.length) closeModal(abiertos[abiertos.length - 1].id);
    });
  }

  // ===================== Lista =====================

  function filaHtml(r) {
    return `<tr data-id="${r.id}" data-estado="${esc(r.estado)}">
      <td class="rtb-code rtb-nowrap">${esc(r.folio)}</td>
      <td class="rtb-nowrap">${esc(r.np_origen)}</td>
      <td class="rtb-nowrap">${esc(r.np_destino)}</td>
      <td>${r.cantidad}</td>
      <td>${r.tipo_material === "ASSY" ? "ASSY" : "IMD-SMD"}</td>
      <td class="rtb-nowrap">${esc(r.origenes_txt)}</td>
      <td>${areasHtml(r.areas)}</td>
      <td>${chip(r.estado)}</td>
      <td class="rtb-nowrap">${esc(r.solicitado_por)}</td>
      <td class="rtb-nowrap">${esc(r.created_at)}</td>
      <td><button type="button" class="rtb-icon-btn" data-action="ver" data-id="${r.id}" title="Ver detalle">${svg("ver", "")}Ver</button></td>
    </tr>`;
  }

  function renderFilas(root, records) {
    root.querySelector("#rtb-tbody").innerHTML = records.length
      ? records.map(filaHtml).join("")
      : '<tr><td colspan="11" class="rtb-empty">Sin solicitudes para los filtros seleccionados</td></tr>';
    aplicarFiltros(root.querySelector("#rtb-table"));
  }

  // Los contadores reflejan lo visible tras el filtro por columna, como ICT.
  function contarVisibles(root, visibles) {
    const estados = visibles.map((tr) => tr.dataset.estado);
    root.querySelector("#rtb-total").textContent = estados.length;
    root.querySelector("#rtb-abiertas").textContent = estados.filter((e) => e === "PENDIENTE" || e === "EN_PROCESO").length;
    root.querySelector("#rtb-completadas").textContent = estados.filter((e) => e === "COMPLETADA").length;
  }

  function filtrosParams(root) {
    const form = root.querySelector("#rtb-filters");
    const params = new URLSearchParams();
    ["desde", "hasta", "codigo", "estado"].forEach((name) => {
      const value = form.elements[name].value.trim();
      if (value) params.set(name, value);
    });
    return params;
  }

  function setLoading(root, loading) {
    root.querySelector("#rtb-loading").hidden = !loading;
  }

  async function cargarLista(root) {
    const tbody = root.querySelector("#rtb-tbody");
    setLoading(root, true);
    try {
      const { records } = await fetchJson(`${API}?${filtrosParams(root)}`);
      renderFilas(root, records);
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="11" class="rtb-empty">${esc(error.message)}</td></tr>`;
      notify(error.message, "error");
    } finally {
      setLoading(root, false);
    }
  }

  function fechasPorDefecto(root) {
    const form = root.querySelector("#rtb-filters");
    const hoy = new Date();
    const desde = new Date(hoy);
    desde.setDate(hoy.getDate() - 30);
    form.elements.desde.value = isoDate(desde);
    form.elements.hasta.value = isoDate(hoy);
  }

  async function exportarExcel(root, boton) {
    boton.disabled = true;
    try {
      const response = await request(`${API}/export?${filtrosParams(root)}`);
      if (!response.ok) {
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }
        throw new Error((payload && payload.error) || HTTP_ERRORS[response.status] || "No se pudo exportar.");
      }
      const blob = await response.blob();
      const match = /filename="?([^";]+)"?/.exec(response.headers.get("Content-Disposition") || "");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = match ? match[1] : "retrabajo.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      boton.disabled = false;
    }
  }

  // ===================== Alta =====================

  function componenteRow() {
    return `<tr>
      <td><select name="tipo"><option value="ASSY">ASSY</option><option value="SMD">SMD</option><option value="IMD">IMD</option></select></td>
      <td><input name="ubicacion" maxlength="100" placeholder="Ej. IC1"></td>
      <td><input name="np_anterior" maxlength="64"></td>
      <td><input name="np_nuevo" maxlength="64"></td>
      <td><button type="button" class="rtb-icon-btn rtb-icon-btn--danger" data-action="quitar-componente" title="Quitar">✕</button></td>
    </tr>`;
  }

  function leerFormulario(form) {
    const origenes = ORIGENES.map(([key]) => ({
      origen: key,
      cantidad: parseInt(form.elements[`origen_${key}`].value, 10) || 0,
    })).filter((o) => o.cantidad > 0);
    const programaciones = form.elements.programacion.checked
      ? [...form.querySelectorAll('[data-role="programaciones"] input:checked')].map((el) => ({
          ic_location: el.dataset.ic,
          programming_label: el.dataset.label,
        }))
      : [];
    const componentes = [...form.querySelectorAll('[data-role="componentes"] tr')]
      .map((tr) => ({
        tipo: tr.querySelector('[name="tipo"]').value,
        ubicacion: tr.querySelector('[name="ubicacion"]').value.trim(),
        np_anterior: tr.querySelector('[name="np_anterior"]').value.trim(),
        np_nuevo: tr.querySelector('[name="np_nuevo"]').value.trim(),
      }))
      .filter((c) => c.ubicacion);
    return {
      np_origen: form.elements.np_origen.value.trim().toUpperCase(),
      np_destino: form.elements.np_destino.value.trim().toUpperCase(),
      tipo_material: form.elements.tipo_material.value,
      origenes,
      programaciones,
      componentes,
      comentarios: form.elements.comentarios.value.trim(),
    };
  }

  // Misma derivacion que calcular_areas() en retrabajo.py.
  function areasPrevistas(data) {
    const areas = [];
    if (data.origenes.some((o) => o.origen === "EMBARQUES")) areas.push("Embarques: surtir material");
    const cambioNp = data.np_origen && data.np_destino && data.np_origen !== data.np_destino;
    if (data.programaciones.length) areas.push("MICOM: etiquetas de programación");
    if (cambioNp) areas.push("Impresión: etiquetas SMD");
    if (data.programaciones.length) areas.push("Control Producción: reprogramación");
    else if (cambioNp) areas.push("Control Producción: cambio de etiquetas");
    if (data.componentes.some((c) => c.tipo === "ASSY")) areas.push("Control Producción: reparación ASSY");
    if (data.componentes.some((c) => c.tipo === "SMD" || c.tipo === "IMD")) areas.push("Inventario SMD: reparación SMD/IMD");
    return areas;
  }

  async function cargarProgramaciones(form) {
    const box = form.querySelector('[data-role="programaciones"]');
    const part = form.elements.np_destino.value.trim().toUpperCase();
    if (!form.elements.programacion.checked) {
      box.innerHTML = "";
      return;
    }
    if (!/^[A-Z]{3}\d{8}$/.test(part)) {
      box.innerHTML = '<p class="rtb-hint">Captura primero el NP destino.</p>';
      return;
    }
    box.innerHTML = '<p class="rtb-hint">Consultando BOM...</p>';
    try {
      const { records } = await fetchJson(`${API}/programacion?part_no=${encodeURIComponent(part)}`);
      box.innerHTML = records.length
        ? records
            .map(
              (o) => `<label class="rtb-check"><input type="checkbox" checked
                 data-ic="${esc(o.ic_location)}" data-label="${esc(o.programming_label)}">
                 ${esc(o.programming_label)} · ${esc(o.ic_location)}</label>`,
            )
            .join("")
        : `<p class="rtb-hint">El BOM vigente de ${esc(part)} no tiene MICOM.</p>`;
    } catch (error) {
      box.innerHTML = `<p class="rtb-hint">${esc(error.message)}</p>`;
    }
  }

  function formularioHtml() {
    const campo = (label, input) => `<div class="rtb-filter-group"><label>${label}</label>${input}</div>`;
    return `<form data-role="form" autocomplete="off">
      <datalist id="rtb-partes"></datalist>
      <div class="rtb-form-grid">
        ${campo("NP origen", '<input name="np_origen" list="rtb-partes" maxlength="11" required placeholder="EBR########">')}
        ${campo("NP destino", '<input name="np_destino" list="rtb-partes" maxlength="11" required placeholder="EBR########">')}
        ${campo(
          "Tipo de material",
          `<select name="tipo_material">
            <option value="ASSY">ASSY (etiqueta SMD + ASSY)</option>
            <option value="IMD_SMD">IMD-SMD (solo etiqueta SMD)</option>
          </select>`,
        )}
      </div>
      ${seccion("Origen del material")}
      <div class="rtb-form-grid">${ORIGENES.map(([key, nombre]) =>
        campo(nombre, `<input type="number" min="0" max="999" name="origen_${key}" placeholder="0">`),
      ).join("")}</div>
      <p class="rtb-hint">Cantidad total: <strong data-role="total">0</strong></p>
      ${seccion("Programación")}
      <label class="rtb-check"><input type="checkbox" name="programacion"> Lleva programación (etiquetas MICOM)</label>
      <div class="rtb-boxes" data-role="programaciones"></div>
      ${seccion("Cambio de componentes")}
      <div class="rtb-table-wrap rtb-table-wrap--compact">
        <table class="rtb-table rtb-table--compact">
          <thead><tr><th>Tipo</th><th>Ubicación</th><th>NP anterior</th><th>NP nuevo</th><th></th></tr></thead>
          <tbody data-role="componentes"></tbody>
        </table>
      </div>
      <div class="rtb-modal-actions">
        <button type="button" class="rtb-btn-header" data-action="agregar-componente">+ Agregar componente</button>
      </div>
      <div class="rtb-filter-group rtb-filter-group--full">
        <label>Comentarios</label>
        <textarea name="comentarios" maxlength="2000"></textarea>
      </div>
      ${seccion("Áreas que recibirán la solicitud")}
      <div class="rtb-chips rtb-chips--left" data-role="areas"></div>
      <div class="rtb-modal-actions">
        <button type="button" class="rtb-btn-ghost" data-rtb-close>Cancelar</button>
        <button type="submit" class="rtb-btn-primary">Crear solicitud</button>
      </div>
    </form>`;
  }

  function abrirFormulario(root) {
    let idempotencyKey = uuid();
    const body = openModal("rtb-form-modal", {
      title: "Nueva solicitud de retrabajo",
      subtitle: "El MES define el retrabajo y cada área recibe su parte",
      icon: "nueva",
      overlayClose: false, // no perder lo capturado por un clic fuera
    });
    body.innerHTML = formularioHtml();
    const form = body.querySelector("form");

    fetchJson("/api/raw/modelos")
      .then(({ data }) => {
        body.querySelector("#rtb-partes").innerHTML = (data || [])
          .map((part) => `<option value="${esc(part)}"></option>`)
          .join("");
      })
      .catch(() => {});

    const refrescar = () => {
      const data = leerFormulario(form);
      form.querySelector('[data-role="total"]').textContent = data.origenes.reduce((sum, o) => sum + o.cantidad, 0);
      const areas = areasPrevistas(data);
      form.querySelector('[data-role="areas"]').innerHTML = areas.length
        ? areas.map((a) => chip("EN_PROCESO", a)).join("")
        : '<p class="rtb-hint">Indica cambio de NP, programación o componentes.</p>';
    };

    form.addEventListener("input", () => {
      // Datos distintos => solicitud distinta (la llave tambien reutiliza la FPA de MICOM).
      idempotencyKey = uuid();
      refrescar();
    });
    form.addEventListener("change", (event) => {
      if (event.target.name === "programacion" || event.target.name === "np_destino") {
        cargarProgramaciones(form).then(refrescar);
      }
      refrescar();
    });
    form.addEventListener("click", (event) => {
      if (event.target.closest('[data-action="agregar-componente"]')) {
        form.querySelector('[data-role="componentes"]').insertAdjacentHTML("beforeend", componenteRow());
      }
      const quitar = event.target.closest('[data-action="quitar-componente"]');
      if (quitar) {
        quitar.closest("tr").remove();
        refrescar();
      }
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      try {
        const { record } = await fetchJson(API, {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
          body: JSON.stringify(leerFormulario(form)),
        });
        notify(`Solicitud ${record.folio} creada`, "success");
        closeModal("rtb-form-modal");
        cargarLista(root);
      } catch (error) {
        notify(error.message, "error");
      } finally {
        submit.disabled = false;
      }
    });
    refrescar();
    form.elements.np_origen.focus();
  }

  // ===================== Detalle =====================

  function info(items) {
    return `<div class="rtb-info">${items
      .map(([label, value]) => `<div><small>${esc(label)}</small><strong>${value}</strong></div>`)
      .join("")}</div>`;
  }

  function salidasHtml(salidas, clave) {
    return tabla(
      ["Folio", "NP", "Cantidad", "Cajas", "Registró", "Fecha"],
      salidas.map((s) => [
        `<span class="rtb-code">${esc(s.folio)}</span>`,
        esc(s.part_number),
        s.cantidad,
        s.cajas.map((c) => `<span class="rtb-code">${esc(c)}</span>`).join("<br>"),
        esc(s.registrado_por),
        esc(s.created_at),
      ]),
      "Sin salidas",
      clave,
    );
  }

  function detalleHtml(r) {
    const code = (v) => (v ? `<span class="rtb-code">${esc(v)}</span>` : "—");
    return `
      ${info([
        ["NP origen", esc(r.np_origen)],
        ["NP destino", esc(r.np_destino)],
        ["Cantidad", r.cantidad],
        ["Material", r.tipo_material === "ASSY" ? "ASSY" : "IMD-SMD"],
        ["Estado", chip(r.estado)],
        ["Lote impresión", esc(r.lote_impresion || "—")],
        ["Solicitó", esc(r.solicitado_por)],
        ["Fecha", esc(r.created_at)],
      ])}
      ${r.cancelado_por ? `<p class="rtb-hint">Cancelada por <strong>${esc(r.cancelado_por)}</strong> el ${esc(r.cancelado_at)}</p>` : ""}
      ${r.comentarios ? `<p class="rtb-hint">${esc(r.comentarios)}</p>` : ""}
      ${seccion("Áreas")}${areasHtml(r.areas, "rtb-chips--left")}
      ${seccion("Origen del material")}
      <div class="rtb-chips rtb-chips--left">${r.origenes
        .map((o) => chip("", `${(ORIGENES.find(([k]) => k === o.origen) || [0, o.origen])[1]}: ${o.cantidad}`))
        .join("")}</div>
      ${seccion("Programación (MICOM)")}
      ${tabla(
        ["Ubicación", "MICOM", "Etiqueta", "FPA", "Estado FPA"],
        r.programaciones.map((p) => [
          esc(p.ic_location),
          esc(p.micom_part_no),
          `<span class="rtb-code">${esc(p.programming_label)}</span>`,
          esc(p.fpa_folio || p.fpa_request_id || "—"),
          esc(p.fpa_status || "—"),
        ]),
        "Sin programación",
        "detalle_programacion",
      )}
      ${seccion("Componentes")}
      ${tabla(
        ["Tipo", "Ubicación", "NP anterior", "NP nuevo"],
        r.componentes.map((c) => [esc(c.tipo), esc(c.ubicacion), esc(c.np_anterior || "—"), esc(c.np_nuevo || "—")]),
        "Sin cambio de componentes",
        "detalle_componentes",
      )}
      ${seccion("Salidas de Embarques")}
      ${salidasHtml(r.salidas_embarques, "detalle_salidas")}
      ${seccion("Escaneos (trazabilidad)")}
      ${tabla(
        ["Etapa", "QR SMD anterior", "QR SMD nuevo", "QR ASSY anterior", "QR ASSY nuevo", "Usuario", "Fecha"],
        r.escaneos.map((e) => [
          esc(ETAPAS[e.etapa] || e.etapa),
          code(e.qr_smd_anterior),
          code(e.qr_smd_nuevo),
          code(e.qr_assy_anterior),
          code(e.qr_assy_nuevo),
          esc(e.usuario),
          esc(e.created_at),
        ]),
        "Sin escaneos",
        "detalle_escaneos",
      )}
      ${
        r.status === "ACTIVA"
          ? `<div class="rtb-modal-actions"><button type="button" class="rtb-btn-danger" data-action="cancelar">Cancelar solicitud</button></div>`
          : ""
      }`;
  }

  async function abrirDetalle(root, id) {
    let record;
    try {
      ({ record } = await fetchJson(`${API}/${id}`));
    } catch (error) {
      notify(error.message, "error");
      return;
    }
    const body = openModal("rtb-detail-modal", {
      title: `Retrabajo ${record.folio}`,
      subtitle: `<strong>${esc(record.np_origen)}</strong> → <strong>${esc(record.np_destino)}</strong> · ${record.cantidad} pzs`,
      icon: "detalle",
    });
    body.innerHTML = `<div data-role="detalle">${detalleHtml(record)}</div>`;
    activarFiltros(body);
    body.firstElementChild.addEventListener("click", async (event) => {
      const boton = event.target.closest('[data-action="cancelar"]');
      if (!boton || !window.confirm(`¿Cancelar la solicitud ${record.folio}?`)) return;
      boton.disabled = true;
      try {
        const result = await fetchJson(`${API}/${id}/cancelar`, { method: "POST" });
        const avisos = result.avisos || [];
        notify(avisos.length ? `Cancelada. Revisa MICOM: ${avisos.join("; ")}` : "Solicitud cancelada", avisos.length ? "error" : "success");
        closeModal("rtb-detail-modal");
        cargarLista(root);
      } catch (error) {
        boton.disabled = false;
        notify(error.message, "error");
      }
    });
  }

  window.inicializarRetrabajo = function (selector) {
    ensureStylesheet();
    const root = typeof selector === "string" ? document.querySelector(selector || "#rtb-module") : selector;
    if (!root || root.dataset.initialized === "1") return;
    root.dataset.initialized = "1";
    fechasPorDefecto(root);
    const lista = root.querySelector("#rtb-table");
    prepararFiltros(lista);
    lista.__rtbAfterFilter = (visibles) => contarVisibles(root, visibles);
    root.querySelector("#rtb-filters").addEventListener("submit", (event) => {
      event.preventDefault();
      cargarLista(root);
    });
    root.addEventListener("click", (event) => {
      const accion = event.target.closest("[data-action]");
      if (!accion) return;
      const nombre = accion.dataset.action;
      if (nombre === "nueva") abrirFormulario(root);
      if (nombre === "actualizar") cargarLista(root);
      if (nombre === "exportar") exportarExcel(root, accion);
      if (nombre === "ver") abrirDetalle(root, accion.dataset.id);
      if (nombre === "limpiar") {
        root.querySelector("#rtb-filters").reset();
        fechasPorDefecto(root);
        cargarLista(root);
      }
    });
    root.addEventListener("dblclick", (event) => {
      const fila = event.target.closest("tr[data-id]");
      if (fila) abrirDetalle(root, fila.dataset.id);
    });
    cargarLista(root);
  };

  // WF_003: limpieza al navegar fuera del modulo.
  window.limpiarRetrabajo = function () {
    ["rtb-form-modal", "rtb-detail-modal", "rtb-emb-modal"].forEach(closeModal);
  };

  // ===================== Embarques: "Salida Retrabajo" =====================

  function ordenEmbarquesHtml(o) {
    const pendiente = o.emb_solicitado - o.emb_surtido;
    const campo = (label, input) => `<div class="rtb-filter-group"><label>${label}</label>${input}</div>`;
    return `
      ${info([
        ["NP origen", esc(o.np_origen)],
        ["Solicitado a Embarques", o.emb_solicitado],
        ["Surtido", o.emb_surtido],
        ["Pendiente", pendiente],
      ])}
      <form data-role="salida" autocomplete="off">
        ${seccion("Salida")}
        <div class="rtb-form-grid">
          ${campo("Número de parte", '<input name="partNumber" maxlength="64" required>')}
          ${campo("Cantidad", `<input name="cantidad" type="number" min="1" max="${pendiente}" required>`)}
          ${campo("Escanear caja (Enter)", '<input name="caja" class="rtb-input-scan" maxlength="100">')}
        </div>
        <div class="rtb-boxes" data-role="cajas"></div>
        <div class="rtb-modal-actions">
          <button type="submit" class="rtb-btn-primary">Dar salida</button>
        </div>
      </form>
      ${seccion("Salidas de esta orden")}
      <div data-role="historial"></div>`;
  }

  function abrirSalidaEmbarques() {
    ensureStylesheet();
    const body = openModal("rtb-emb-modal", {
      title: "Salida retrabajo",
      subtitle: "Cajas que salen de Embarques hacia retrabajo",
      icon: "salida",
      overlayClose: false,
    });
    body.innerHTML = `<div data-role="embarques">
        <div class="rtb-filter-group rtb-filter-group--wide"><label>Orden de retrabajo</label>
          <select data-role="orden"><option value="">Cargando...</option></select></div>
        <div data-role="orden-info"></div>
      </div>`;
    const wrapper = body.firstElementChild;
    const select = wrapper.querySelector('[data-role="orden"]');
    const contenedor = wrapper.querySelector('[data-role="orden-info"]');
    let ordenes = [];

    async function cargarOrdenes(seleccion) {
      try {
        ({ records: ordenes } = await fetchJson(`${API}/embarques/pendientes`));
      } catch (error) {
        select.innerHTML = '<option value="">Error al cargar</option>';
        notify(error.message, "error");
        return;
      }
      select.innerHTML = ordenes.length
        ? '<option value="">Selecciona una orden</option>' +
          ordenes
            .map((o) => `<option value="${o.id}">${esc(o.folio)} · ${esc(o.np_origen)} · ${o.emb_surtido}/${o.emb_solicitado}</option>`)
            .join("")
        : '<option value="">Sin órdenes pendientes</option>';
      select.value = ordenes.some((o) => String(o.id) === String(seleccion)) ? seleccion : "";
      mostrarOrden();
    }

    async function cargarHistorial(id) {
      const box = contenedor.querySelector('[data-role="historial"]');
      if (!box) return;
      try {
        const { records } = await fetchJson(`${API}/embarques/salidas?solicitud_id=${id}`);
        box.innerHTML = salidasHtml(records, "embarques_salidas");
        activarFiltros(box);
      } catch (error) {
        box.innerHTML = `<p class="rtb-hint">${esc(error.message)}</p>`;
      }
    }

    function mostrarOrden() {
      const orden = ordenes.find((o) => String(o.id) === select.value);
      contenedor.innerHTML = orden ? ordenEmbarquesHtml(orden) : "";
      if (!orden) return;
      const form = contenedor.querySelector("form");
      const cajas = [];
      const pintarCajas = () => {
        form.querySelector('[data-role="cajas"]').innerHTML = cajas
          .map(
            (c, i) =>
              `<span class="rtb-chip rtb-chip--EN_PROCESO">${esc(c)} <button type="button" class="rtb-icon-btn rtb-icon-btn--danger" data-quitar="${i}" title="Quitar">✕</button></span>`,
          )
          .join("");
      };
      form.elements.caja.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const caja = form.elements.caja.value.trim();
        form.elements.caja.value = "";
        if (!caja) return;
        if (cajas.some((c) => c.toUpperCase() === caja.toUpperCase())) {
          notify(`Caja repetida: ${caja}`, "error");
          return;
        }
        cajas.push(caja);
        pintarCajas();
      });
      form.addEventListener("click", (event) => {
        const quitar = event.target.closest("[data-quitar]");
        if (!quitar) return;
        cajas.splice(Number(quitar.dataset.quitar), 1);
        pintarCajas();
      });
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
          const result = await fetchJson(`${API}/${orden.id}/salida-embarques`, {
            method: "POST",
            body: JSON.stringify({
              partNumber: form.elements.partNumber.value.trim(),
              cantidad: form.elements.cantidad.value,
              boxCodes: cajas,
            }),
          });
          notify(`Salida ${result.folio} registrada`, "success");
          cargarOrdenes(orden.id);
        } catch (error) {
          notify(error.message, "error");
          submit.disabled = false;
        }
      });
      cargarHistorial(orden.id);
      form.elements.partNumber.focus();
    }

    select.addEventListener("change", mostrarOrden);
    cargarOrdenes("");
  }

  window.abrirSalidaRetrabajoEmbarques = abrirSalidaEmbarques;

  if (!window.__rtbEmbarquesBound) {
    window.__rtbEmbarquesBound = true;
    document.addEventListener("click", (event) => {
      if (event.target.closest("#almacen-embarques-exits-retrabajo-open-btn")) abrirSalidaEmbarques();
    });
  }
})();
