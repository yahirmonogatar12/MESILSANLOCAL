/* Control de material (Informacion Basica).
 * CRUD AJAX sobre la tabla MySQL `materiales` + costos por vendedor
 * (tabla material_costos, con moneda e historial).
 * WF_003/WF_004/WF_005: estilos asegurados desde JS, texto escapado,
 *   listeners idempotentes (el loader re-ejecuta este script en cada apertura).
 */
(function () {
  "use strict";

  const STYLESHEET_ID = "control-material-info-css";
  const STYLESHEET_HREF = "/static/css/control_material_info.css?v=20260612a";
  const API_BASE = "/api/informacion_basica/control_material";
  const API_MATERIALES = `${API_BASE}/materiales`;
  const MONEDAS = ["USD", "MXN", "KRW"]; // fallback; la fuente real es /catalogos
  const MAX_COSTO = 99999999.9999; // tope de DECIMAL(12,4) en material_costos

  let records = [];
  let catalogos = { clasificaciones: [], propiedades: [], unidades_empaque: [], unidades_medida: [], monedas: MONEDAS };
  let savingMaterial = false; // anti doble-submit del formulario
  let loadSeq = 0; // secuencia de carga: descarta respuestas viejas

  function ensureStylesheet() {
    const existing = document.getElementById(STYLESHEET_ID);
    if (existing) {
      if (existing.getAttribute("href") !== STYLESHEET_HREF) {
        existing.setAttribute("href", STYLESHEET_HREF);
      }
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

  function getElements(root) {
    return {
      root,
      filters: root.querySelector("#cmat-filters"),
      search: root.querySelector("#cmat-search"),
      clasificacionFilter: root.querySelector("#cmat-clasificacion-filter"),
      clear: root.querySelector("#cmat-clear"),
      exportBtn: root.querySelector("#cmat-export"),
      refresh: root.querySelector("#cmat-refresh"),
      create: root.querySelector("#cmat-new"),
      loading: root.querySelector("#cmat-loading"),
      tbody: root.querySelector("#cmat-tbody"),
      total: root.querySelector("#cmat-total"),
      // Formulario
      formPanel: root.querySelector("#cmat-form-panel"),
      form: root.querySelector("#cmat-form"),
      formTitle: root.querySelector("#cmat-form-title"),
      np: root.querySelector("#cmat-np"),
      propiedad: root.querySelector("#cmat-propiedad"),
      clasificacion: root.querySelector("#cmat-clasificacion"),
      especificacion: root.querySelector("#cmat-especificacion"),
      unidadEmpaque: root.querySelector("#cmat-unidad-empaque"),
      unidadMedida: root.querySelector("#cmat-unidad-medida"),
      vendedoresRows: root.querySelector("#cmat-vendedores-rows"),
      addVendor: root.querySelector("#cmat-add-vendor"),
      cancel: root.querySelector("#cmat-cancel"),
      cancelBottom: root.querySelector("#cmat-cancel-bottom"),
      // Datalists
      dlClasificaciones: root.querySelector("#cmat-clasificaciones-list"),
      dlPropiedades: root.querySelector("#cmat-propiedades-list"),
      dlUnidadesEmpaque: root.querySelector("#cmat-unidades-empaque-list"),
      dlUnidadesMedida: root.querySelector("#cmat-unidades-medida-list"),
      // Historial
      historialPanel: root.querySelector("#cmat-historial-panel"),
      historialTitle: root.querySelector("#cmat-historial-title"),
      historialVendedor: root.querySelector("#cmat-historial-vendedor"),
      historialTbody: root.querySelector("#cmat-historial-tbody"),
      historialClose: root.querySelector("#cmat-historial-close"),
    };
  }

  function notify(message, type) {
    const old = document.querySelector(".cmat-toast");
    if (old) old.remove();
    const toast = document.createElement("div");
    toast.className = `cmat-toast cmat-toast--${type || "info"}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 4200);
  }

  function setLoading(elements, loading) {
    if (elements.loading) elements.loading.hidden = !loading;
    elements.root.classList.toggle("is-loading", loading);
    elements.root.querySelectorAll("button, input, select").forEach((el) => {
      const inOpenModal =
        (elements.formPanel && !elements.formPanel.hidden && elements.formPanel.contains(el)) ||
        (elements.historialPanel && !elements.historialPanel.hidden && elements.historialPanel.contains(el));
      if (inOpenModal) return;
      el.disabled = loading;
    });
  }

  async function fetchJson(url, options) {
    const headers = {
      "Content-Type": "application/json",
      ...(options && options.headers ? options.headers : {}),
    };
    const response = await fetch(url, {
      credentials: "same-origin",
      ...(options || {}),
      headers,
    });
    const text = await response.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (error) {
        payload = {};
      }
    }
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || `Solicitud fallida (${response.status})`);
    }
    return payload;
  }

  function buildListUrl(elements, base) {
    const params = new URLSearchParams();
    const q = elements.search.value.trim();
    const clasificacion = elements.clasificacionFilter.value;
    if (q) params.set("q", q);
    if (clasificacion) params.set("clasificacion", clasificacion);
    const query = params.toString();
    return `${base || API_MATERIALES}${query ? `?${query}` : ""}`;
  }

  function formatCosto(costo) {
    return costo === null || costo === undefined || costo === "" ? "" : costo;
  }

  function costBadges(row) {
    const costos = row.costos || [];
    const conCosto = costos.filter((c) => c.costo !== null && c.costo !== undefined && c.costo !== "");
    if (!conCosto.length) return "—";
    return conCosto
      .map(
        (c) =>
          `<span class="cmat-cost-badge" title="${esc(c.vendedor)}">${esc(c.vendedor)} · $${esc(formatCosto(c.costo))} ${esc(c.moneda)}</span>`
      )
      .join(" ");
  }

  function vendorsText(row) {
    const vendedores = row.vendedores || [];
    return vendedores.length ? esc(vendedores.join(", ")) : "—";
  }

  function rowActions(row) {
    const np = esc(row.numero_parte);
    return `
      <div class="cmat-row-actions">
        <button class="cmat-icon-btn" type="button" title="Editar" aria-label="Editar ${np}" data-action="edit" data-np="${np}">
          <i class="bi bi-pencil" aria-hidden="true"></i>
        </button>
        <button class="cmat-icon-btn" type="button" title="Historial de costos" aria-label="Historial de ${np}" data-action="costos" data-np="${np}">
          <i class="bi bi-clock-history" aria-hidden="true"></i>
        </button>
        <button class="cmat-icon-btn cmat-danger" type="button" title="Eliminar" aria-label="Eliminar ${np}" data-action="delete" data-np="${np}">
          <i class="bi bi-trash" aria-hidden="true"></i>
        </button>
      </div>
    `;
  }

  function renderTable(elements) {
    elements.total.textContent = String(records.length);
    if (!records.length) {
      elements.tbody.innerHTML = '<tr><td colspan="11" class="cmat-empty">Sin materiales registrados</td></tr>';
      return;
    }
    elements.tbody.innerHTML = records
      .map(
        (row) => `
          <tr>
            <td><span class="cmat-code">${esc(row.numero_parte)}</span></td>
            <td>${esc(row.propiedad_material || "—")}</td>
            <td>${esc(row.clasificacion || "—")}</td>
            <td class="cmat-cell-left">${esc(row.especificacion_material || "—")}</td>
            <td>${esc(row.unidad_empaque || "—")}</td>
            <td>${esc(row.unidad_medida || "—")}</td>
            <td class="cmat-cell-left">${vendorsText(row)}</td>
            <td class="cmat-cell-left">${costBadges(row)}</td>
            <td>${esc(row.fecha_registro || "—")}</td>
            <td>${esc(row.usuario_registro || "—")}</td>
            <td>${rowActions(row)}</td>
          </tr>
        `
      )
      .join("");
  }

  function fillDatalist(node, values) {
    if (!node) return;
    node.innerHTML = (values || [])
      .map((v) => `<option value="${esc(v)}"></option>`)
      .join("");
  }

  function fillClasificacionFilter(elements) {
    const current = elements.clasificacionFilter.value;
    const opts = ['<option value="">Todas</option>'].concat(
      (catalogos.clasificaciones || []).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`)
    );
    elements.clasificacionFilter.innerHTML = opts.join("");
    elements.clasificacionFilter.value = current;
  }

  async function loadCatalogos(elements) {
    try {
      const payload = await fetchJson(`${API_BASE}/catalogos`);
      catalogos = {
        clasificaciones: payload.clasificaciones || [],
        propiedades: payload.propiedades || [],
        unidades_empaque: payload.unidades_empaque || [],
        unidades_medida: payload.unidades_medida || [],
        monedas: payload.monedas && payload.monedas.length ? payload.monedas : MONEDAS,
      };
      fillClasificacionFilter(elements);
      fillDatalist(elements.dlClasificaciones, catalogos.clasificaciones);
      fillDatalist(elements.dlPropiedades, catalogos.propiedades);
      fillDatalist(elements.dlUnidadesEmpaque, catalogos.unidades_empaque);
      fillDatalist(elements.dlUnidadesMedida, catalogos.unidades_medida);
    } catch (error) {
      // Los catalogos son auxiliares; no bloquean el modulo.
      console.warn("No se pudieron cargar los catalogos de material:", error);
    }
  }

  async function loadMateriales(elements) {
    // Secuencia: si llega una carga mas nueva mientras esta esta en vuelo,
    // descartamos la respuesta vieja para que no sobreescriba la lista actual.
    const seq = ++loadSeq;
    setLoading(elements, true);
    try {
      const payload = await fetchJson(buildListUrl(elements));
      if (seq !== loadSeq) return;
      records = payload.records || [];
      renderTable(elements);
    } catch (error) {
      if (seq !== loadSeq) return;
      records = [];
      renderTable(elements);
      notify(error.message || "No fue posible cargar los materiales.", "error");
    } finally {
      if (seq === loadSeq) setLoading(elements, false);
    }
  }

  // ===================== Editor de vendedores =====================

  function monedaOptions(selected) {
    return (catalogos.monedas || MONEDAS)
      .map((m) => `<option value="${esc(m)}" ${m === selected ? "selected" : ""}>${esc(m)}</option>`)
      .join("");
  }

  function addVendorRow(elements, data) {
    const d = data || {};
    const wrap = document.createElement("div");
    wrap.className = "cmat-vendor-row";
    wrap.innerHTML = `
      <input type="text" class="cmat-vendor-name" maxlength="100" autocomplete="off" placeholder="Vendedor" value="${esc(d.vendedor || "")}">
      <input type="number" class="cmat-vendor-cost" step="0.0001" min="0" autocomplete="off" placeholder="0.0000" value="${esc(d.costo !== null && d.costo !== undefined ? d.costo : "")}">
      <select class="cmat-vendor-moneda">${monedaOptions(d.moneda || "USD")}</select>
      <button type="button" class="cmat-icon-btn cmat-danger" data-action="remove-vendor" title="Quitar vendedor" aria-label="Quitar vendedor">
        <i class="bi bi-x-lg" aria-hidden="true"></i>
      </button>
    `;
    elements.vendedoresRows.appendChild(wrap);
  }

  function readVendorRows(elements) {
    const rows = Array.from(elements.vendedoresRows.querySelectorAll(".cmat-vendor-row"));
    const vendedores = [];
    const vistos = new Set();
    for (const r of rows) {
      const vendedor = r.querySelector(".cmat-vendor-name").value.trim();
      if (!vendedor) continue;
      if (vendedor.includes(",")) {
        throw new Error(`El vendedor "${vendedor}" no puede contener comas.`);
      }
      const clave = vendedor.toLowerCase();
      if (vistos.has(clave)) {
        throw new Error(`El vendedor "${vendedor}" está duplicado.`);
      }
      vistos.add(clave);
      const costoRaw = r.querySelector(".cmat-vendor-cost").value.trim();
      const costoNum = Number(costoRaw);
      if (costoRaw !== "" && (!Number.isFinite(costoNum) || costoNum < 0)) {
        throw new Error(`El costo de "${vendedor}" debe ser un número válido mayor o igual a 0.`);
      }
      if (costoNum > MAX_COSTO) {
        throw new Error(`El costo de "${vendedor}" excede el máximo permitido (99,999,999.9999).`);
      }
      const moneda = r.querySelector(".cmat-vendor-moneda").value || "USD";
      vendedores.push({ vendedor, costo: costoRaw === "" ? "0" : costoRaw, moneda });
    }
    return vendedores;
  }

  // ===================== Formulario alta/edicion =====================

  function resetForm(elements) {
    elements.np.value = "";
    elements.np.readOnly = false;
    elements.propiedad.value = "";
    elements.clasificacion.value = "";
    elements.especificacion.value = "";
    elements.unidadEmpaque.value = "";
    elements.unidadMedida.value = "";
    elements.vendedoresRows.innerHTML = "";
  }

  function openForm(elements, record) {
    resetForm(elements);
    if (record) {
      elements.formTitle.textContent = "Editar material";
      elements.np.value = record.numero_parte || "";
      elements.np.readOnly = true; // numero_parte es PK
      elements.propiedad.value = record.propiedad_material || "";
      elements.clasificacion.value = record.clasificacion || "";
      elements.especificacion.value = record.especificacion_material || "";
      elements.unidadEmpaque.value = record.unidad_empaque || "";
      elements.unidadMedida.value = record.unidad_medida || "";
      const costos = record.costos || [];
      if (costos.length) {
        costos.forEach((c) => addVendorRow(elements, c));
      } else {
        (record.vendedores || []).forEach((v) => addVendorRow(elements, { vendedor: v }));
      }
    } else {
      elements.formTitle.textContent = "Nuevo material";
      elements.unidadMedida.value = "EA";
      addVendorRow(elements, {});
    }
    elements.formPanel.hidden = false;
    elements.np.focus();
  }

  function closeForm(elements) {
    resetForm(elements);
    elements.formPanel.hidden = true;
  }

  function setFormSaving(elements, saving) {
    elements.form.querySelectorAll("button, input, select, textarea").forEach((el) => {
      el.disabled = saving;
    });
  }

  async function saveMaterial(elements) {
    if (savingMaterial) return; // evita doble POST/PUT por doble click
    const vendedores = readVendorRows(elements); // lanza si hay coma/duplicado
    const isEdit = elements.np.readOnly;
    const payload = {
      numero_parte: elements.np.value.trim(),
      propiedad_material: elements.propiedad.value.trim(),
      clasificacion: elements.clasificacion.value.trim(),
      especificacion_material: elements.especificacion.value.trim(),
      unidad_empaque: elements.unidadEmpaque.value.trim(),
      unidad_medida: elements.unidadMedida.value.trim() || "EA",
      vendedores,
    };

    // Validacion en cliente (espejo del backend) para feedback inmediato.
    if (!payload.numero_parte) {
      throw new Error("El número de parte es requerido.");
    }
    if (!payload.especificacion_material) {
      throw new Error("La especificación del material es requerida.");
    }

    savingMaterial = true;
    setFormSaving(elements, true); // feedback visual: bloquea el form mientras guarda
    try {
      await fetchJson(API_MATERIALES, {
        method: isEdit ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      notify(isEdit ? "Material actualizado." : "Material creado.", "success");
      closeForm(elements);
      await Promise.all([loadMateriales(elements), loadCatalogos(elements)]);
    } finally {
      savingMaterial = false;
      setFormSaving(elements, false);
    }
  }

  function findRecord(np) {
    return records.find((item) => item.numero_parte === np);
  }

  async function deleteMaterial(elements, record) {
    const ok = confirm(
      `Dar de baja el material ${record.numero_parte}?\n` +
      `Dejará de aparecer en el listado. El historial de costos se conserva ` +
      `y podrá reactivarse dándolo de alta con el mismo número de parte.`
    );
    if (!ok) return;
    await fetchJson(API_MATERIALES, {
      method: "DELETE",
      body: JSON.stringify({ numero_parte: record.numero_parte }),
    });
    notify("Material dado de baja.", "success");
    await loadMateriales(elements);
  }

  // ===================== Historial de costos =====================

  let historialData = [];

  function renderHistorial(elements) {
    const filtro = elements.historialVendedor.value;
    const rows = filtro ? historialData.filter((r) => r.vendedor === filtro) : historialData;
    if (!rows.length) {
      elements.historialTbody.innerHTML = '<tr><td colspan="5" class="cmat-empty">Sin historial</td></tr>';
      return;
    }
    elements.historialTbody.innerHTML = rows
      .map(
        (r) => `
          <tr>
            <td>${esc(r.vendedor)}</td>
            <td>$${esc(formatCosto(r.costo))}</td>
            <td>${esc(r.moneda)}</td>
            <td>${esc(r.usuario_registro || "—")}</td>
            <td>${esc(r.fecha_registro || "—")}</td>
          </tr>
        `
      )
      .join("");
  }

  async function openHistorial(elements, record) {
    elements.historialTitle.textContent = `Historial de costos · ${record.numero_parte}`;
    const params = new URLSearchParams({ numero_parte: record.numero_parte });
    elements.historialPanel.hidden = false;
    try {
      const payload = await fetchJson(`${API_BASE}/costos/historial?${params.toString()}`);
      historialData = payload.records || [];
    } catch (error) {
      historialData = [];
      notify(error.message || "No fue posible cargar el historial.", "error");
    }
    const vendedores = Array.from(new Set(historialData.map((r) => r.vendedor)));
    elements.historialVendedor.innerHTML = ['<option value="">Todos</option>']
      .concat(vendedores.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`))
      .join("");
    renderHistorial(elements);
  }

  function closeHistorial(elements) {
    elements.historialPanel.hidden = true;
    historialData = [];
  }

  // ===================== Wiring =====================

  function bindEvents(elements) {
    elements.filters.addEventListener("submit", (event) => {
      event.preventDefault();
      loadMateriales(elements);
    });
    elements.clasificacionFilter.addEventListener("change", () => loadMateriales(elements));
    elements.clear.addEventListener("click", () => {
      elements.search.value = "";
      elements.clasificacionFilter.value = "";
      loadMateriales(elements);
    });
    elements.refresh.addEventListener("click", () => loadMateriales(elements));
    elements.exportBtn.addEventListener("click", () => {
      window.open(buildListUrl(elements, `${API_BASE}/export`), "_blank");
    });
    elements.create.addEventListener("click", () => openForm(elements));

    // Formulario
    elements.cancel.addEventListener("click", () => closeForm(elements));
    elements.cancelBottom.addEventListener("click", () => closeForm(elements));
    elements.formPanel.addEventListener("click", (event) => {
      if (event.target === elements.formPanel) closeForm(elements);
    });
    elements.addVendor.addEventListener("click", () => addVendorRow(elements, {}));
    elements.vendedoresRows.addEventListener("click", (event) => {
      const btn = event.target.closest('[data-action="remove-vendor"]');
      if (btn) btn.closest(".cmat-vendor-row").remove();
    });
    elements.form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveMaterial(elements).catch((error) => notify(error.message, "error"));
    });

    // Historial
    elements.historialClose.addEventListener("click", () => closeHistorial(elements));
    elements.historialPanel.addEventListener("click", (event) => {
      if (event.target === elements.historialPanel) closeHistorial(elements);
    });
    elements.historialVendedor.addEventListener("change", () => renderHistorial(elements));

    // Tabla principal
    elements.tbody.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const record = findRecord(button.dataset.np);
      if (!record) {
        notify("El material ya no está en la lista. Actualiza el módulo.", "error");
        return;
      }
      const action = button.dataset.action;
      if (action === "edit") {
        openForm(elements, record);
      } else if (action === "costos") {
        openHistorial(elements, record).catch((error) => notify(error.message, "error"));
      } else if (action === "delete") {
        deleteMaterial(elements, record).catch((error) => notify(error.message, "error"));
      }
    });

    // Escape cierra el modal abierto (un solo binding global, idempotente)
    if (!document.body.dataset.cmatEscBound) {
      document.body.dataset.cmatEscBound = "true";
      document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const root = document.querySelector("#cmat-module");
        if (!root) return;
        const el = getElements(root);
        if (el.formPanel && !el.formPanel.hidden) closeForm(el);
        else if (el.historialPanel && !el.historialPanel.hidden) closeHistorial(el);
      });
    }
  }

  function validarElementos(elements) {
    const requeridos = [
      "filters", "search", "clasificacionFilter", "tbody", "total",
      "formPanel", "form", "np", "especificacion", "vendedoresRows",
      "addVendor", "historialPanel", "historialTbody",
    ];
    const faltantes = requeridos.filter((k) => !elements[k]);
    if (faltantes.length) {
      throw new Error(`Faltan elementos del módulo Control de material: ${faltantes.join(", ")}`);
    }
  }

  function inicializarControlMaterialInfo(root) {
    ensureStylesheet();
    const moduleRoot = typeof root === "string" ? document.querySelector(root) : root;
    if (!moduleRoot || moduleRoot.dataset.initialized === "true") return;
    const elements = getElements(moduleRoot);
    try {
      validarElementos(elements);
    } catch (error) {
      // No marcamos initialized: si el HTML se re-renderiza corregido, el
      // siguiente intento puede inicializar el modulo.
      console.error(error);
      notify(error.message, "error");
      return;
    }
    moduleRoot.dataset.initialized = "true";
    bindEvents(elements);
    loadCatalogos(elements);
    loadMateriales(elements);
  }

  window.inicializarControlMaterialInfo = inicializarControlMaterialInfo;
  window.initializeControlMaterialInfoEventListeners = function () {
    document.querySelectorAll("#cmat-module").forEach(inicializarControlMaterialInfo);
  };
  document.querySelectorAll("#cmat-module").forEach(inicializarControlMaterialInfo);
})();
