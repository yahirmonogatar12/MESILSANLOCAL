(function () {
  const STYLE_ID = "material-invoices-css";
  const STYLE_VERSION = "20260615g";
  const STYLE_HREF = `/static/css/material_invoices.css?v=${STYLE_VERSION}`;

  const state = {
    selectedInvoiceId: null,
    selectedInvoice: null,
    activeTab: "lines",
    viewerInvoiceId: null,
    viewerWorkbook: null,
    viewerSheet: null,
    pendingUpload: null,
  };

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

  // Patron de modales del MES (ver Documentacion/SOLUCION_MODALES.md):
  // los modales deben vivir en document.body, no dentro del contenedor AJAX
  // (#mat-invoice-page), porque el header/tabs global crea contexto de apilado
  // y recorte. Al abrir se fuerzan estilos inline con !important para ganarle
  // a cualquier CSS conflictivo.
  function openModal(id) {
    const modal = el(id);
    if (!modal) return null;
    if (modal.parentElement !== document.body) {
      document.body.appendChild(modal);
    }
    modal.hidden = false;
    modal.style.cssText = `
      display: flex !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      width: 100% !important;
      height: 100% !important;
      background: rgba(0,0,0,0.6) !important;
      justify-content: center !important;
      align-items: center !important;
      padding: 12px !important;
      z-index: 2147483600 !important;
      opacity: 1 !important;
      visibility: visible !important;
    `;
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
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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
    const loader = el("mat-invoice-loading");
    if (loader) loader.hidden = !active;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, { credentials: "same-origin", ...(options || {}) });
    const contentType = res.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await res.json() : { error: await res.text() };
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
    const q = el("mat-invoice-search")?.value.trim();
    const estado = el("mat-invoice-state")?.value;
    if (q) params.set("q", q);
    if (estado) params.set("estado", estado);
    return params;
  }

  async function loadInvoices() {
    ensureModuleStyles();
    setLoading(true);
    setMessage("mat-invoice-upload-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices?${queryParams().toString()}`);
      renderInvoiceList(data.records || []);
    } catch (err) {
      setMessage("mat-invoice-upload-message", `Error al cargar invoices: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderInvoiceList(rows) {
    const body = el("mat-invoice-list-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9">No hay invoices cargadas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const selected = Number(row.id) === Number(state.selectedInvoiceId) ? " selected" : "";
      const tieneArchivo = Boolean(row.archivo_ruta);
      const verBtn = tieneArchivo
        ? `<button class="mat-invoice-btn mat-invoice-view-excel" type="button" data-view-excel-id="${escapeHtml(row.id)}" data-view-excel-name="${escapeHtml(row.numero_invoice)}">Ver</button>`
        : `<span class="mat-invoice-muted">—</span>`;
      const tieneLinks = Number(row.links_activos) > 0;
      const delBtn = `<button class="mat-invoice-btn danger mat-invoice-delete" type="button" data-delete-invoice-id="${escapeHtml(row.id)}" data-delete-invoice-name="${escapeHtml(row.numero_invoice)}" ${tieneLinks ? "disabled title=\"Tiene links activos; no se puede eliminar\"" : ""}>Eliminar</button>`;
      return `<tr class="${selected}" data-invoice-id="${escapeHtml(row.id)}">
        <td class="mat-invoice-clickable">${escapeHtml(row.numero_invoice)}</td>
        <td>${statusBadge(row.estado)}</td>
        <td title="${escapeHtml(row.tipo)}">${escapeHtml(row.tipo)}</td>
        <td>${numberText(row.total_lineas)}</td>
        <td>${numberText(row.total_packing)}</td>
        <td>${numberText(row.links_activos)}</td>
        <td>${escapeHtml(row.fecha_carga)}</td>
        <td>${verBtn}</td>
        <td>${delBtn}</td>
      </tr>`;
    }).join("");
  }

  async function loadDetail(invoiceId) {
    if (!invoiceId) return;
    state.selectedInvoiceId = invoiceId;
    setLoading(true);
    setMessage("mat-invoice-detail-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}`);
      state.selectedInvoice = data.invoice;
      renderDetail(data);
      el("mat-invoice-detail").hidden = false;
      el("mat-invoice-export").disabled = false;
      await loadInvoices();
    } catch (err) {
      setMessage("mat-invoice-upload-message", `Error al cargar detalle: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderDetail(data) {
    const invoice = data.invoice || {};
    const title = el("mat-invoice-detail-title");
    const subtitle = el("mat-invoice-detail-subtitle");
    if (title) title.textContent = `Invoice ${invoice.numero_invoice || ""}`;
    if (subtitle) {
      subtitle.textContent = `${invoice.estado || ""} | ${invoice.tipo || ""} | ${invoice.archivo_nombre || ""}`;
    }
    renderLines(data.lines || []);
    renderPacking(data.packing || []);
    renderLinks(data.links || []);
    syncTabs();
  }

  function renderLines(rows) {
    const body = el("mat-invoice-lines-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9">Sin lineas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => `<tr>
      <td>${numberText(row.line_no)}</td>
      <td title="${escapeHtml(row.raw_part_num)}">${escapeHtml(row.raw_part_num)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td title="${escapeHtml(row.descripcion)}">${escapeHtml(row.descripcion)}</td>
      <td>${numberText(row.cantidad)}</td>
      <td>${escapeHtml(row.uom)}</td>
      <td>${numberText(row.costo_unitario)}</td>
      <td>${numberText(row.costo_total)}</td>
      <td>${statusBadge(row.estado_match)}</td>
    </tr>`).join("");
  }

  function renderPacking(rows) {
    const body = el("mat-invoice-packing-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="13">Sin packing.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => `<tr>
      <td>${numberText(row.line_no)}</td>
      <td>${escapeHtml(row.pallet_no_original)}</td>
      <td>${escapeHtml(row.pallet_no)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td>${numberText(row.cantidad_packing)}</td>
      <td>${numberText(row.entradas_recibidas)}</td>
      <td>${numberText(row.cantidad_recibida)}</td>
      <td>${numberText(row.cantidad_pendiente_entrada)}</td>
      <td>${numberText(row.cantidad_aplicada_activa)}</td>
      <td>${numberText(row.kg)}</td>
      <td>${numberText(row.cbm)}</td>
      <td>${statusBadge(row.estado_match)}</td>
      <td title="${escapeHtml(row.mensaje_match)}">${escapeHtml(row.mensaje_match)}</td>
    </tr>`).join("");
  }

  function renderLinks(rows) {
    const body = el("mat-invoice-links-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9">Sin links.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => `<tr>
      <td>${escapeHtml(row.id)}</td>
      <td title="${escapeHtml(row.codigo_material_recibido)}">${escapeHtml(row.codigo_material_recibido)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td>${numberText(row.cantidad_aplicada)}</td>
      <td>${numberText(row.costo_unitario)} ${escapeHtml(row.moneda)}</td>
      <td>${statusBadge(row.estado)}</td>
      <td>${escapeHtml(row.usuario_aplicacion)}</td>
      <td>${escapeHtml(row.fecha_aplicacion)}</td>
      <td>${escapeHtml(row.usuario_desaplicado)}</td>
    </tr>`).join("");
  }

  function closePreview() {
    hideModal("mat-invoice-preview");
    state.pendingUpload = null;
  }

  // Paso 1: parsea el Excel y muestra en un modal lo que se cargaria.
  async function openPreview(event) {
    event.preventDefault();
    const form = el("mat-invoice-upload-form");
    const file = el("mat-invoice-upload-file")?.files?.[0];
    if (!form || !file) {
      setMessage("mat-invoice-upload-message", "Selecciona un archivo Excel.");
      return;
    }
    // Guarda una copia del FormData para la confirmacion (el input no cambia).
    state.pendingUpload = new FormData(form);
    setLoading(true);
    try {
      const data = await fetchJson("/api/material_admin/invoices/preview", {
        method: "POST",
        body: state.pendingUpload,
      });
      renderPreview(data);
      openModal("mat-invoice-preview");
      setMessage("mat-invoice-upload-message", "");
    } catch (err) {
      state.pendingUpload = null;
      setMessage("mat-invoice-upload-message", `No se pudo previsualizar: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderPreview(data) {
    const subtitle = el("mat-invoice-preview-subtitle");
    if (subtitle) {
      const dup = data.duplicado
        ? ` — YA EXISTE (${data.duplicado.motivo})`
        : "";
      subtitle.textContent =
        `Invoice ${data.numero_invoice || ""} · ${numberText(data.total_lineas)} lineas · ` +
        `Total ${data.total_monto} · Sin parte en sistema: ${numberText(data.partes_sin_sistema)}${dup}`;
    }
    const msg = el("mat-invoice-preview-message");
    const confirmBtn = el("mat-invoice-preview-confirm");
    const avisos = [];
    if (data.duplicado) avisos.push("Esta invoice ya fue cargada; no se podra confirmar.");
    if (data.partes_sin_sistema) avisos.push(`${data.partes_sin_sistema} parte(s) no existen en materiales (quedaran como diferencia).`);
    (data.warnings || []).forEach((w) => avisos.push(w));
    if (avisos.length) {
      setMessage("mat-invoice-preview-message", avisos.join(" "), data.duplicado ? "" : "success");
    } else if (msg) {
      msg.hidden = true;
    }
    if (confirmBtn) confirmBtn.disabled = Boolean(data.duplicado);

    const body = el("mat-invoice-preview-body");
    if (!body) return;
    const rows = data.lines || [];
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="10">Sin lineas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const diff = row.estado_match === "SIN_ALIAS";
      return `<tr class="${diff ? "mat-invoice-row-diff" : ""}">
        <td>${escapeHtml(row.line_no)}</td>
        <td>${escapeHtml(row.pallet_no)}</td>
        <td>${escapeHtml(row.raw_part_num)}</td>
        <td>${escapeHtml(row.numero_parte_sistema)}</td>
        <td title="${escapeHtml(row.descripcion)}">${escapeHtml(row.descripcion)}</td>
        <td>${numberText(row.cantidad)}</td>
        <td>${escapeHtml(row.uom)}</td>
        <td>${escapeHtml(row.costo_unitario)}</td>
        <td>${escapeHtml(row.costo_total)}</td>
        <td>${escapeHtml(diff ? "SIN PARTE" : "OK")}</td>
      </tr>`;
    }).join("");
  }

  // Paso 2: confirma y carga de verdad usando el FormData previsualizado.
  async function confirmUpload() {
    if (!state.pendingUpload) return;
    setLoading(true);
    try {
      const data = await fetchJson("/api/material_admin/invoices/upload", {
        method: "POST",
        body: state.pendingUpload,
      });
      closePreview();
      setMessage("mat-invoice-upload-message", `Invoice cargada: ${data.lineas} lineas, ${data.packing} packing.`, "success");
      el("mat-invoice-upload-form")?.reset();
      await loadInvoices();
      await loadDetail(data.invoice_id);
    } catch (err) {
      if (err.status === 409 && err.payload?.duplicado) {
        setMessage("mat-invoice-preview-message", `${err.payload.message || "Duplicado"} (${err.payload.motivo || ""})`);
      } else {
        setMessage("mat-invoice-preview-message", `Error al cargar: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }

  async function deleteInvoice(invoiceId, numeroInvoice) {
    if (!invoiceId) return;
    if (!window.confirm(`¿Eliminar la invoice ${numeroInvoice || invoiceId}? Esta accion no se puede deshacer.`)) {
      return;
    }
    setLoading(true);
    try {
      await fetchJson(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}`, {
        method: "DELETE",
      });
      setMessage("mat-invoice-upload-message", `Invoice ${numeroInvoice || invoiceId} eliminada.`, "success");
      if (Number(state.selectedInvoiceId) === Number(invoiceId)) {
        state.selectedInvoiceId = null;
        if (el("mat-invoice-detail")) el("mat-invoice-detail").hidden = true;
      }
      await loadInvoices();
    } catch (err) {
      const msg = err.status === 409 ? (err.payload?.error || err.message) : err.message;
      setMessage("mat-invoice-upload-message", `No se pudo eliminar: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  async function postAction(action, body) {
    if (!state.selectedInvoiceId) return;
    setLoading(true);
    setMessage("mat-invoice-detail-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices/${state.selectedInvoiceId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const omitted = Number(data.omitidos || 0);
      const applied = Number(data.aplicados || 0);
      const unapplied = Number(data.links_desaplicados || data.unapply?.links_desaplicados || 0);
      setMessage(
        "mat-invoice-detail-message",
        `Estado: ${data.estado || ""}. Aplicados: ${applied}. Omitidos: ${omitted}. Desaplicados: ${unapplied}.`,
        "success"
      );
      await loadDetail(state.selectedInvoiceId);
    } catch (err) {
      setMessage("mat-invoice-detail-message", `Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function syncTabs() {
    document.querySelectorAll("#mat-invoice-page .mat-invoice-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === state.activeTab);
    });
    ["lines", "packing", "links"].forEach((tab) => {
      const panel = el(`mat-invoice-tab-${tab}`);
      if (panel) panel.hidden = tab !== state.activeTab;
    });
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[data-src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.dataset.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
      document.head.appendChild(script);
    });
  }

  // SheetJS vendored en static/js/lib con respaldo CDN (planta puede ir sin internet).
  async function ensureSheetJs() {
    if (typeof window.XLSX !== "undefined") return;
    try {
      await loadScript("/static/js/lib/xlsx.full.min.js");
    } catch (err) {
      await loadScript("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js");
    }
    if (typeof window.XLSX === "undefined") {
      throw new Error("La libreria de Excel no se cargo.");
    }
  }

  function closeViewer() {
    hideModal("mat-invoice-viewer");
    state.viewerWorkbook = null;
    state.viewerSheet = null;
  }

  function renderViewerSheet(sheetName) {
    const body = el("mat-invoice-viewer-body");
    const wb = state.viewerWorkbook;
    if (!body || !wb) return;
    const sheet = wb.Sheets[sheetName];
    if (!sheet) {
      body.innerHTML = "";
      return;
    }
    // SheetJS genera la tabla HTML respetando merges y valores.
    body.innerHTML = window.XLSX.utils.sheet_to_html(sheet, { id: "mat-invoice-xlsx-table" });
  }

  // Punto unico para cambiar de hoja: sincroniza pestanas, select y cuerpo.
  function selectViewerSheet(sheetName) {
    if (!sheetName) return;
    state.viewerSheet = sheetName;
    const sheetsSelect = el("mat-invoice-viewer-sheets");
    if (sheetsSelect && sheetsSelect.value !== sheetName) {
      sheetsSelect.value = sheetName;
    }
    const tabs = el("mat-invoice-viewer-tabs");
    if (tabs) {
      tabs.querySelectorAll("[data-sheet-name]").forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-sheet-name") === sheetName);
      });
    }
    const body = el("mat-invoice-viewer-body");
    if (body) body.scrollTop = 0;
    renderViewerSheet(sheetName);
  }

  function renderViewerTabs(names) {
    const tabs = el("mat-invoice-viewer-tabs");
    if (!tabs) return;
    tabs.innerHTML = names
      .map(
        (name) =>
          `<button type="button" class="mat-invoice-viewer-tab" data-sheet-name="${escapeHtml(name)}" title="${escapeHtml(name)}">${escapeHtml(name)}</button>`
      )
      .join("");
  }

  async function openExcelViewer(invoiceId, numeroInvoice) {
    const viewer = openModal("mat-invoice-viewer");
    if (!viewer) return;
    setMessage("mat-invoice-viewer-message", "", "");
    el("mat-invoice-viewer-message").hidden = true;
    const title = el("mat-invoice-viewer-title");
    const subtitle = el("mat-invoice-viewer-subtitle");
    const sheetsSelect = el("mat-invoice-viewer-sheets");
    const tabsEl = el("mat-invoice-viewer-tabs");
    const bodyEl = el("mat-invoice-viewer-body");
    if (title) title.textContent = `Excel: ${numeroInvoice || invoiceId}`;
    if (subtitle) subtitle.textContent = "Cargando...";
    if (bodyEl) bodyEl.innerHTML = "";
    if (sheetsSelect) sheetsSelect.innerHTML = "";
    if (tabsEl) tabsEl.innerHTML = "";
    state.viewerInvoiceId = invoiceId;

    try {
      await ensureSheetJs();
      const res = await fetch(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}/file`, {
        credentials: "same-origin",
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const data = await res.json();
          msg = data.error || msg;
        } catch (_) {}
        throw new Error(msg);
      }
      const buffer = await res.arrayBuffer();
      const wb = window.XLSX.read(buffer, { type: "array" });
      state.viewerWorkbook = wb;
      const names = wb.SheetNames || [];
      if (sheetsSelect) {
        sheetsSelect.innerHTML = names
          .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
          .join("");
      }
      renderViewerTabs(names);
      if (subtitle) subtitle.textContent = `${names.length} hoja(s)`;
      // Abre por defecto en INVOICE(CONVERTED) si existe.
      const preferida = names.find((n) => n.toUpperCase().replace(/\s+/g, "") === "INVOICE(CONVERTED)");
      const inicial = preferida || names[0];
      if (inicial) {
        selectViewerSheet(inicial);
      }
    } catch (err) {
      if (subtitle) subtitle.textContent = "";
      setMessage("mat-invoice-viewer-message", `No se pudo abrir el Excel: ${err.message}`);
    }
  }

  function attachListeners() {
    if (document.body.dataset.materialInvoicesListenersAttached) return;

    document.body.addEventListener("submit", (event) => {
      if (event.target?.id === "mat-invoice-upload-form") {
        openPreview(event);
      }
    });

    document.body.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

      if (target.closest("#mat-invoice-preview-confirm")) {
        event.preventDefault();
        confirmUpload();
        return;
      }
      if (target.closest("[data-preview-close]")) {
        event.preventDefault();
        closePreview();
        return;
      }
      const deleteBtn = target.closest("[data-delete-invoice-id]");
      if (deleteBtn) {
        event.preventDefault();
        event.stopPropagation();
        deleteInvoice(
          deleteBtn.getAttribute("data-delete-invoice-id"),
          deleteBtn.getAttribute("data-delete-invoice-name")
        );
        return;
      }

      const viewExcel = target.closest("[data-view-excel-id]");
      if (viewExcel) {
        event.preventDefault();
        openExcelViewer(
          viewExcel.getAttribute("data-view-excel-id"),
          viewExcel.getAttribute("data-view-excel-name")
        );
        return;
      }
      if (target.closest("[data-viewer-close]")) {
        event.preventDefault();
        closeViewer();
        return;
      }
      const sheetTab = target.closest("[data-sheet-name]");
      if (sheetTab) {
        event.preventDefault();
        selectViewerSheet(sheetTab.getAttribute("data-sheet-name"));
        return;
      }
      if (target.closest("#mat-invoice-viewer-download")) {
        event.preventDefault();
        if (state.viewerInvoiceId) {
          window.location.href = `/api/material_admin/invoices/${encodeURIComponent(state.viewerInvoiceId)}/file?download=1`;
        }
        return;
      }

      const row = target.closest("#mat-invoice-list-body tr[data-invoice-id]");
      if (row) {
        event.preventDefault();
        loadDetail(row.dataset.invoiceId);
        return;
      }
      if (target.closest("#mat-invoice-refresh") || target.closest("#mat-invoice-search-btn")) {
        event.preventDefault();
        loadInvoices();
        return;
      }
      if (target.closest("#mat-invoice-export")) {
        event.preventDefault();
        if (state.selectedInvoiceId) {
          window.location.href = `/api/material_admin/invoices/${state.selectedInvoiceId}/export`;
        }
        return;
      }
      if (target.closest("#mat-invoice-apply-auto")) {
        event.preventDefault();
        postAction("apply", {});
        return;
      }
      if (target.closest("#mat-invoice-reapply")) {
        event.preventDefault();
        postAction("reapply", { motivo: "Reaplicacion desde modulo web" });
        return;
      }
      if (target.closest("#mat-invoice-unapply")) {
        event.preventDefault();
        const motivo = window.prompt("Motivo de desaplicacion") || "";
        postAction("unapply", { motivo_desaplicado: motivo });
        return;
      }
      const tabButton = target.closest("#mat-invoice-page .mat-invoice-tab");
      if (tabButton?.dataset.tab) {
        event.preventDefault();
        state.activeTab = tabButton.dataset.tab;
        syncTabs();
      }
    });

    document.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-invoice-state") {
        loadInvoices();
      }
      if (target.id === "mat-invoice-viewer-sheets") {
        selectViewerSheet(target.value);
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-invoice-search" && event.key === "Enter") {
        event.preventDefault();
        loadInvoices();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!el("mat-invoice-preview")?.hidden) {
        closePreview();
      } else if (!el("mat-invoice-viewer")?.hidden) {
        closeViewer();
      }
    });

    document.body.dataset.materialInvoicesListenersAttached = "1";
  }

  window.initMaterialInvoices = function () {
    ensureModuleStyles();
    attachListeners();
    state.selectedInvoiceId = null;
    state.selectedInvoice = null;
    state.activeTab = "lines";
    state.viewerInvoiceId = null;
    state.viewerWorkbook = null;
    state.pendingUpload = null;
    hideModal("mat-invoice-viewer");
    hideModal("mat-invoice-preview");
    if (el("mat-invoice-detail")) el("mat-invoice-detail").hidden = true;
    if (el("mat-invoice-export")) el("mat-invoice-export").disabled = true;
    loadInvoices();
  };
})();
