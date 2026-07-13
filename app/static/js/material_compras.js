(function () {
  // Reusa el CSS del modulo de invoices (clases mat-invoice-*).
  const STYLE_ID = "material-invoices-css";
  const STYLE_VERSION = "20260707a";
  const STYLE_HREF = `/static/css/material_invoices.css?v=${STYLE_VERSION}`;

  const state = {
    selectedTransaccion: null,
    selectedTipo: null,
    selectedTransactionData: null,
    activeTab: "lineas",
    pendingUpload: null,
    inicialHecha: {},
    data: { transacciones: [], lineas: [], links: [] },
  };

  const COMPRAS_LIST_COLUMNS = [
    { field: "numero_transaccion", label: "Transaccion" },
    { field: "tipo", label: "Tipo" },
    { field: "estado", label: "Estado" },
    { field: "proveedor", label: "Proveedor" },
    { field: "num_partes", label: "Partes", value: (row) => numberText(row.num_partes) },
    { field: "num_lineas", label: "Lineas", value: (row) => numberText(row.num_lineas) },
    { field: "total_monto", label: "Monto", value: (row) => numberText(row.total_monto) },
    { field: "fecha_compra", label: "Fecha" },
  ];

  const COMPRAS_LINEAS_COLUMNS = [
    { field: "numero_parte", label: "Parte" },
    { field: "numero_parte_sistema", label: "Parte sistema" },
    { field: "descripcion", label: "Descripcion" },
    { field: "spec", label: "Spec" },
    { field: "cantidad", label: "Comprado", value: (row) => numberText(row.cantidad) },
    { field: "aplicado", label: "Recibido", value: (row) => numberText(row.aplicado) },
    { field: "pendiente", label: "Pendiente", value: (row) => numberText(row.pendiente) },
    { field: "estado", label: "Estado" },
    { field: "moneda", label: "Curr." },
    { field: "costo_unitario", label: "P. Unit.", value: (row) => numberText(row.costo_unitario) },
    { field: "costo_total", label: "Total", value: (row) => numberText(row.costo_total) },
    { field: "proveedor", label: "Proveedor" },
    { field: "factura", label: "Factura" },
    { field: "modelo", label: "Modelo" },
    { field: "categoria", label: "Cat." },
    { field: "fecha_compra", label: "Fecha" },
  ];

  const COMPRAS_LINKS_COLUMNS = [
    { field: "codigo_material_recibido", label: "Lote" },
    { field: "numero_parte_sistema", label: "Parte sistema" },
    { field: "cantidad_aplicada", label: "Cantidad", value: (row) => numberText(row.cantidad_aplicada) },
    { field: "costo_unitario", label: "Costo unit.", value: (row) => numberText(row.costo_unitario) },
    { field: "moneda", label: "Moneda" },
    { field: "estado", label: "Estado" },
    { field: "usuario_aplicacion", label: "Usuario" },
    { field: "fecha_aplicacion", label: "Fecha vinculacion" },
  ];

  function ensureModuleStyles() {
    const current = document.getElementById(STYLE_ID);
    if (current) {
      if (!current.getAttribute("href")?.includes(STYLE_VERSION)) {
        current.setAttribute("href", STYLE_HREF);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = STYLE_ID;
    link.rel = "stylesheet";
    link.href = STYLE_HREF;
    document.head.appendChild(link);
  }

  function el(id) {
    return document.getElementById(id);
  }

  // Modales viven en document.body (mismo patron que invoices).
  function openModal(id) {
    const modal = el(id);
    if (!modal) return null;
    if (modal.parentElement !== document.body) document.body.appendChild(modal);
    modal.hidden = false;
    modal.style.cssText = `
      display: flex !important; position: fixed !important; top: 0 !important;
      left: 0 !important; width: 100% !important; height: 100% !important;
      background: rgba(0,0,0,0.6) !important; justify-content: center !important;
      align-items: center !important; padding: 12px !important;
      z-index: 2147483600 !important; opacity: 1 !important; visibility: visible !important;`;
    return modal;
  }

  function hideModal(id) {
    const modal = el(id);
    if (!modal) return;
    modal.style.cssText = "display: none !important;";
    modal.hidden = true;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function numberText(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
  }

  function statusBadge(value) {
    const text = String(value || "");
    return `<span class="mat-invoice-status ${escapeHtml(text)}">${escapeHtml(text)}</span>`;
  }

  function setMessage(targetId, message, type) {
    const box = el(targetId);
    if (!box) return;
    if (!message) {
      box.hidden = true;
      box.textContent = "";
      box.classList.remove("success");
      return;
    }
    box.hidden = false;
    box.textContent = message;
    box.classList.toggle("success", type === "success");
  }

  function setLoading(active) {
    const loader = el("mat-compras-loading");
    if (loader) loader.hidden = !active;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, { credentials: "same-origin", ...(options || {}) });
    const ct = res.headers.get("content-type") || "";
    const data = ct.includes("application/json") ? await res.json() : { error: await res.text() };
    if (!res.ok || data.error || data.success === false) {
      const err = new Error(data.message || data.error || `HTTP ${res.status}`);
      err.payload = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function queryParams() {
    const params = new URLSearchParams();
    const q = el("mat-compras-search")?.value.trim();
    const tipo = el("mat-compras-type-filter")?.value;
    const estado = el("mat-compras-estado-filter")?.value;
    const desde = el("mat-compras-date-from")?.value;
    const hasta = el("mat-compras-date-to")?.value;
    if (q) params.set("q", q);
    if (tipo) params.set("tipo", tipo);
    if (estado) params.set("estado", estado);
    if (desde) params.set("fecha_inicio", desde);
    if (hasta) params.set("fecha_fin", hasta);
    return params;
  }

  function columnFilters() {
    return window.MatColumnFilters || null;
  }

  function setupFilterHeaders() {
    const filters = columnFilters();
    if (!filters) return;
    filters.attachGlobalHandlers();
    filters.renderHead("compras:list", "mat-compras-list-head", COMPRAS_LIST_COLUMNS);
    filters.renderHead("compras:lineas", "mat-compras-lineas-head", COMPRAS_LINEAS_COLUMNS);
    filters.renderHead("compras:links", "mat-compras-links-head", COMPRAS_LINKS_COLUMNS);
  }

  function filterRows(tableKey, columns, rows) {
    return columnFilters()?.filterRows(tableKey, columns, rows) || rows || [];
  }

  function rerenderFilteredTable(tableKey) {
    if (tableKey === "compras:list") {
      renderTransacciones(state.data.transacciones || []);
    } else if (tableKey === "compras:lineas") {
      renderLineas(state.data.lineas || []);
    } else if (tableKey === "compras:links") {
      renderLinks(state.data.links || []);
    }
  }

  function clearColumnFilters() {
    columnFilters()?.clearByPrefix("compras:");
    setupFilterHeaders();
    renderLineas(state.data.lineas || []);
    renderLinks(state.data.links || []);
  }

  function clearFilters() {
    if (el("mat-compras-search")) el("mat-compras-search").value = "";
    if (el("mat-compras-type-filter")) el("mat-compras-type-filter").value = "";
    if (el("mat-compras-estado-filter")) el("mat-compras-estado-filter").value = "";
    if (el("mat-compras-date-from")) el("mat-compras-date-from").value = "";
    if (el("mat-compras-date-to")) el("mat-compras-date-to").value = "";
    clearColumnFilters();
    loadTransacciones();
  }

  // Consulta qué tipos ya tienen carga inicial para deshabilitar ese botón.
  async function refreshInicialState() {
    try {
      const data = await fetchJson("/api/material_admin/compras/estado-inicial");
      state.inicialHecha = data.inicial_hecha || {};
    } catch (_) {
      state.inicialHecha = {};
    }
    updateInicialButton();
  }

  function updateInicialButton() {
    const btn = el("mat-compras-btn-inicial");
    const tipo = el("mat-compras-upload-type")?.value;
    if (!btn) return;
    const hecha = !!state.inicialHecha[tipo];
    btn.disabled = hecha;
    btn.title = hecha
      ? `Ya existe carga inicial para ${tipo}. Usa Actualizar.`
      : "Carga histórica de una sola vez por tipo. Entra CERRADA: no aparece en almacén, solo para costear.";
  }

  async function loadTransacciones() {
    ensureModuleStyles();
    setLoading(true);
    setMessage("mat-compras-upload-message", "");
    try {
      const params = queryParams();
      const data = await fetchJson(`/api/material_admin/compras/transacciones?${params.toString()}`);
      state.data.transacciones = data.records || [];
      renderTransacciones(state.data.transacciones);
    } catch (err) {
      setMessage("mat-compras-upload-message", `No se pudieron cargar las transacciones: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderTransacciones(rows) {
    const body = el("mat-compras-list-body");
    state.data.transacciones = rows;
    if (!body) return;
    const visibleRows = filterRows("compras:list", COMPRAS_LIST_COLUMNS, rows);
    if (!visibleRows.length) {
      const message = rows.length ? "Sin resultados con filtros." : "Sin resultados.";
      body.innerHTML = `<tr><td colspan="8" class="mat-invoice-empty">${message}</td></tr>`;
      return;
    }
    body.innerHTML = visibleRows
      .map((r) => `
        <tr data-transaccion="${escapeHtml(r.numero_transaccion)}" data-tipo="${escapeHtml(r.tipo)}" class="mat-invoice-row">
          <td>${escapeHtml(r.numero_transaccion)}</td>
          <td>${escapeHtml(r.tipo || "")}</td>
          <td>${statusBadge(r.estado)}</td>
          <td>${escapeHtml(r.proveedor || "")}</td>
          <td>${numberText(r.num_partes)}</td>
          <td>${numberText(r.num_lineas)}</td>
          <td>${numberText(r.total_monto)}</td>
          <td>${escapeHtml(r.fecha_compra || "")}</td>
        </tr>`)
      .join("");
  }

  async function loadDetail(numeroTransaccion, tipo) {
    setLoading(true);
    setMessage("mat-compras-detail-message", "");
    try {
      const params = new URLSearchParams({ tipo: tipo || "" });
      const url = `/api/material_admin/compras/transacciones/${encodeURIComponent(numeroTransaccion)}?${params.toString()}`;
      const data = await fetchJson(url);
      state.selectedTransaccion = numeroTransaccion;
      state.selectedTipo = data.tipo || tipo;
      state.selectedTransactionData = data.transaccion || {};
      state.data.lineas = data.lineas || [];
      state.data.links = data.links || [];
      renderLineas(state.data.lineas);
      renderLinks(state.data.links);
      const detail = el("mat-compras-detail");
      if (detail) detail.hidden = false;
      const title = el("mat-compras-detail-title");
      if (title) title.textContent = `Transaccion ${numeroTransaccion}`;
      const sub = el("mat-compras-detail-subtitle");
      if (sub) sub.textContent = `${state.selectedTipo || ""} · ${state.selectedTransactionData.estado || ""} · ${state.data.lineas.length} renglones · ${state.data.links.length} lotes vinculados`;
      const closeTransactionBtn = el("mat-compras-transaction-close");
      if (closeTransactionBtn) {
        const cerrada = state.selectedTransactionData.cerrada === true;
        closeTransactionBtn.textContent = cerrada ? "Reabrir transaccion" : "Cerrar transaccion";
        closeTransactionBtn.dataset.cerrada = cerrada ? "1" : "0";
      }
      syncTabs();
      detail?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      setMessage("mat-compras-detail-message", `No se pudo abrir la transaccion: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderLineas(rows) {
    const body = el("mat-compras-lineas-body");
    state.data.lineas = rows;
    if (!body) return;
    const visibleRows = filterRows("compras:lineas", COMPRAS_LINEAS_COLUMNS, rows);
    if (!visibleRows.length) {
      const message = rows.length ? "Sin resultados con filtros." : "Sin renglones.";
      body.innerHTML = `<tr><td colspan="16" class="mat-invoice-empty">${message}</td></tr>`;
      return;
    }
    body.innerHTML = visibleRows
      .map((r) => `
        <tr>
          <td>${escapeHtml(r.numero_parte || "")}</td>
          <td>${escapeHtml(r.numero_parte_sistema || "")}</td>
          <td>${escapeHtml(r.descripcion || "")}</td>
          <td>${escapeHtml(r.spec || "")}</td>
          <td>${numberText(r.cantidad)}</td>
          <td>${numberText(r.aplicado)}</td>
          <td>${numberText(r.pendiente)}</td>
          <td>${statusBadge(r.estado)}</td>
          <td>${escapeHtml(r.moneda || "")}</td>
          <td>${numberText(r.costo_unitario)}</td>
          <td>${numberText(r.costo_total)}</td>
          <td>${escapeHtml(r.proveedor || "")}</td>
          <td>${escapeHtml(r.factura || "")}</td>
          <td>${escapeHtml(r.modelo || "")}</td>
          <td>${escapeHtml(r.categoria || "")}</td>
          <td>${escapeHtml(r.fecha_compra || "")}</td>
        </tr>`)
      .join("");
  }

  function renderLinks(rows) {
    const body = el("mat-compras-links-body");
    state.data.links = rows;
    if (!body) return;
    const visibleRows = filterRows("compras:links", COMPRAS_LINKS_COLUMNS, rows);
    if (!visibleRows.length) {
      const message = rows.length ? "Sin resultados con filtros." : "Sin lotes vinculados.";
      body.innerHTML = `<tr><td colspan="8" class="mat-invoice-empty">${message}</td></tr>`;
      return;
    }
    body.innerHTML = visibleRows.map((row) => `<tr>
      <td title="${escapeHtml(row.codigo_material_recibido)}">${escapeHtml(row.codigo_material_recibido)}</td>
      <td>${escapeHtml(row.numero_parte_sistema || "")}</td>
      <td>${numberText(row.cantidad_aplicada)}</td>
      <td>${numberText(row.costo_unitario)}</td>
      <td>${escapeHtml(row.moneda || "")}</td>
      <td>${statusBadge(row.estado)}</td>
      <td>${escapeHtml(row.usuario_aplicacion || "")}</td>
      <td>${escapeHtml(row.fecha_aplicacion || "")}</td>
    </tr>`).join("");
  }

  function syncTabs() {
    const page = el("mat-compras-page");
    if (!page) return;
    page.querySelectorAll("[data-compras-tab]").forEach((button) => {
      button.classList.toggle("active", button.dataset.comprasTab === state.activeTab);
    });
    ["lineas", "links"].forEach((tab) => {
      const panel = el(`mat-compras-tab-${tab}`);
      if (panel) panel.hidden = state.activeTab !== tab;
    });
  }

  async function toggleTransactionClosed(button) {
    if (!state.selectedTransaccion || !state.selectedTipo) return;
    const cerrar = button.dataset.cerrada !== "1";
    setLoading(true);
    setMessage("mat-compras-detail-message", "");
    try {
      const url = `/api/material_admin/compras/transacciones/${encodeURIComponent(state.selectedTransaccion)}/close`;
      await fetchJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo: state.selectedTipo, cerrado: cerrar }),
      });
      setMessage(
        "mat-compras-detail-message",
        cerrar ? "Transaccion cerrada." : "Transaccion reabierta.",
        "success"
      );
      await loadDetail(state.selectedTransaccion, state.selectedTipo);
      await loadTransacciones();
    } catch (err) {
      setMessage("mat-compras-detail-message", `No se pudo cambiar el estado: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // --- Carga (preview + confirmar) ---

  async function openPreview(modo) {
    const fileInput = el("mat-compras-upload-file");
    const tipo = el("mat-compras-upload-type")?.value || "";
    const file = fileInput?.files?.[0];
    if (!file) {
      setMessage("mat-compras-upload-message", "Selecciona un archivo Excel.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("tipo", tipo);
    form.append("modo", modo);
    setLoading(true);
    setMessage("mat-compras-upload-message", "");
    try {
      const data = await fetchJson("/api/material_admin/compras/preview", { method: "POST", body: form });
      state.pendingUpload = { file, tipo, modo };
      renderPreview(data, modo);
      openModal("mat-compras-preview");
    } catch (err) {
      setMessage("mat-compras-upload-message", `No se pudo previsualizar: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderPreview(data, modo) {
    const sub = el("mat-compras-preview-subtitle");
    if (sub) {
      const modoTxt = modo === "INICIAL" ? "Carga inicial (CERRADA)" : "Actualizar (ABIERTA)";
      const nuevasTxt = data.transacciones_nuevas != null
        ? ` · ${numberText(data.transacciones_nuevas)} nuevas / ${numberText(data.transacciones_existentes)} ya existen`
        : "";
      const lineasTxt = data.lineas_nuevas != null
        ? ` · ${numberText(data.lineas_nuevas)} renglones nuevos / ${numberText(data.lineas_existentes)} ya existen`
        : "";
      sub.textContent =
        `${data.tipo} · ${modoTxt} · ${numberText(data.total_lineas)} renglones · ` +
        `${numberText(data.total_transacciones)} transacciones${nuevasTxt}${lineasTxt}`;
    }
    // Aviso si en ACTUALIZACION no hay transacciones nuevas, o si el inicial ya existe.
    let aviso = (data.warnings || []).join(" ") || "";
    if (data.bloqueado_inicial) {
      aviso = `Ya existe carga inicial para ${data.tipo}. Usa Actualizar. ${aviso}`;
    } else if (modo === "ACTUALIZACION" && data.lineas_nuevas === 0) {
      aviso = `No hay renglones nuevos que agregar. ${aviso}`;
    }
    setMessage("mat-compras-preview-message", aviso.trim());
    const body = el("mat-compras-preview-body");
    if (!body) return;
    body.innerHTML = (data.sample || [])
      .map((r) => `
        <tr>
          <td>${escapeHtml(r.numero_transaccion || "")}</td>
          <td>${escapeHtml(r.numero_parte || "")}</td>
          <td>${escapeHtml(r.numero_parte_sistema || "")}</td>
          <td>${escapeHtml(r.descripcion || "")}</td>
          <td>${numberText(r.cantidad)}</td>
          <td>${numberText(r.costo_unitario)}</td>
          <td>${numberText(r.costo_total)}</td>
          <td>${escapeHtml(r.fecha_compra || "")}</td>
        </tr>`)
      .join("");
  }

  async function confirmUpload() {
    if (!state.pendingUpload) return;
    const { file, tipo, modo } = state.pendingUpload;
    const form = new FormData();
    form.append("file", file);
    form.append("tipo", tipo);
    form.append("modo", modo);
    setLoading(true);
    setMessage("mat-compras-preview-message", "");
    try {
      const data = await fetchJson("/api/material_admin/compras/upload", { method: "POST", body: form });
      hideModal("mat-compras-preview");
      state.pendingUpload = null;
      const fileInput = el("mat-compras-upload-file");
      if (fileInput) fileInput.value = "";
      const estadoTxt = data.estado_lineas === "CERRADA" ? " (cerradas, histórico)" : " (abiertas, almacén)";
      const msg = data.total_lineas === 0
        ? "Sin renglones nuevos que agregar."
        : `Cargado: ${data.total_lineas} renglones, ${data.total_transacciones} transacciones (${data.tipo})${estadoTxt}.`;
      setMessage("mat-compras-upload-message", msg, "success");
      refreshInicialState();
      loadTransacciones();
    } catch (err) {
      const p = err.payload || {};
      let msg = `No se pudo cargar: ${err.message}`;
      if (p.bloqueado_inicial) msg = p.message || "Ya existe una carga inicial para este tipo.";
      else if (p.duplicado) msg = "Este archivo ya fue cargado.";
      setMessage("mat-compras-preview-message", msg);
    } finally {
      setLoading(false);
    }
  }

  // --- Export (SheetJS) ---

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function ensureSheetJs() {
    if (typeof window.XLSX !== "undefined") return;
    try {
      await loadScript("/static/js/lib/xlsx.full.min.js");
    } catch (err) {
      await loadScript("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js");
    }
    if (typeof window.XLSX === "undefined") throw new Error("La libreria de Excel no se cargo.");
  }

  function numericCell(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    return Number.isFinite(n) ? n : value;
  }

  async function exportLineas() {
    const rows = state.data.lineas || [];
    if (!rows.length) {
      setMessage("mat-compras-detail-message", "No hay datos para exportar.");
      return;
    }
    const columns = [
      ["Transaccion", (r) => r.numero_transaccion],
      ["Parte", (r) => r.numero_parte],
      ["Parte sistema", (r) => r.numero_parte_sistema],
      ["Descripcion", (r) => r.descripcion],
      ["Spec", (r) => r.spec],
      ["Cantidad", (r) => numericCell(r.cantidad)],
      ["Moneda", (r) => r.moneda],
      ["P. Unit.", (r) => numericCell(r.costo_unitario)],
      ["Total", (r) => numericCell(r.costo_total)],
      ["Proveedor", (r) => r.proveedor],
      ["Factura", (r) => r.factura],
      ["Modelo", (r) => r.modelo],
      ["Categoria", (r) => r.categoria],
      ["Fecha", (r) => r.fecha_compra],
      ["Estado", (r) => r.estado_match],
    ];
    setLoading(true);
    try {
      await ensureSheetJs();
      const aoa = [columns.map(([title]) => title)];
      rows.forEach((row) => aoa.push(columns.map(([, acc]) => {
        const v = acc(row);
        return v === null || v === undefined ? "" : v;
      })));
      const wb = window.XLSX.utils.book_new();
      window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet(aoa), "Compras");
      const fecha = new Date().toISOString().slice(0, 10);
      const name = `compras_${state.selectedTransaccion || "detalle"}_${fecha}.xlsx`.replace(/[^A-Za-z0-9._-]+/g, "_");
      window.XLSX.writeFile(wb, name);
    } catch (err) {
      setMessage("mat-compras-detail-message", `No se pudo exportar: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // --- Listeners ---

  let listenersAttached = false;
  function attachListeners() {
    if (listenersAttached) return;
    listenersAttached = true;

    document.addEventListener("submit", (e) => {
      if (e.target && e.target.id === "mat-compras-upload-form") e.preventDefault();
    });

    document.addEventListener("click", (e) => {
      const t = e.target?.closest("button, tr[data-transaccion]") || e.target;
      if (!t) return;
      if (t.id === "mat-compras-btn-inicial") {
        openPreview("INICIAL");
      } else if (t.id === "mat-compras-btn-actualizar") {
        openPreview("ACTUALIZACION");
      } else if (t.id === "mat-compras-refresh" || t.id === "mat-compras-search-btn") {
        loadTransacciones();
      } else if (t.id === "mat-compras-clear-filters") {
        clearFilters();
      } else if (t.id === "mat-compras-preview-confirm") {
        confirmUpload();
      } else if (t.hasAttribute && t.hasAttribute("data-preview-close")) {
        hideModal("mat-compras-preview");
      } else if (t.id === "mat-compras-transaction-close") {
        toggleTransactionClosed(t);
      } else if (t.id === "mat-compras-detail-close") {
        const detail = el("mat-compras-detail");
        if (detail) detail.hidden = true;
        state.selectedTransaccion = null;
        state.selectedTipo = null;
        state.selectedTransactionData = null;
        state.data.links = [];
      } else if (t.dataset && t.dataset.comprasTab) {
        state.activeTab = t.dataset.comprasTab;
        syncTabs();
      } else if (t.dataset && t.dataset.export === "lineas") {
        exportLineas();
      } else if (t.dataset && t.dataset.transaccion) {
        loadDetail(t.dataset.transaccion, t.dataset.tipo);
      }
    });

    document.addEventListener("change", (e) => {
      if (e.target && e.target.id === "mat-compras-upload-type") updateInicialButton();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target && e.target.id === "mat-compras-search") {
        e.preventDefault();
        loadTransacciones();
      } else if (e.key === "Escape") {
        hideModal("mat-compras-preview");
      }
    });

    document.addEventListener("mat-column-filter-change", (event) => {
      const tableKey = event.detail?.tableKey || "";
      if (tableKey.startsWith("compras:")) rerenderFilteredTable(tableKey);
    });
  }

  function initMaterialCompras() {
    ensureModuleStyles();
    attachListeners();
    setupFilterHeaders();
    refreshInicialState();
    loadTransacciones();
  }

  window.initMaterialCompras = initMaterialCompras;
})();
