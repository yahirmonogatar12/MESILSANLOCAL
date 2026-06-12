(function () {
  const STYLE_ID = "material-invoices-css";
  const STYLE_VERSION = "20260612e";
  const STYLE_HREF = `/static/css/material_invoices.css?v=${STYLE_VERSION}`;

  const state = {
    selectedInvoiceId: null,
    selectedInvoice: null,
    activeTab: "lines",
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

  function aliasQueryParams() {
    const params = new URLSearchParams();
    const q = el("mat-invoice-alias-search")?.value.trim();
    if (q) params.set("q", q);
    if (el("mat-invoice-alias-include-inactive")?.checked) params.set("include_inactive", "1");
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
      body.innerHTML = `<tr><td colspan="7">No hay invoices cargadas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const selected = Number(row.id) === Number(state.selectedInvoiceId) ? " selected" : "";
      return `<tr class="${selected}" data-invoice-id="${escapeHtml(row.id)}">
        <td class="mat-invoice-clickable">${escapeHtml(row.numero_invoice)}</td>
        <td>${statusBadge(row.estado)}</td>
        <td title="${escapeHtml(row.tipo)}">${escapeHtml(row.tipo)}</td>
        <td>${numberText(row.total_lineas)}</td>
        <td>${numberText(row.total_packing)}</td>
        <td>${numberText(row.links_activos)}</td>
        <td>${escapeHtml(row.fecha_carga)}</td>
      </tr>`;
    }).join("");
  }

  async function loadAliases() {
    ensureModuleStyles();
    try {
      const data = await fetchJson(`/api/material_admin/invoices/aliases?${aliasQueryParams().toString()}`);
      renderAliases(data.records || []);
    } catch (err) {
      setMessage("mat-invoice-alias-message", `Error al cargar equivalentes: ${err.message}`);
    }
  }

  function renderAliases(rows) {
    const body = el("mat-invoice-alias-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="7">No hay equivalentes registrados.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const active = String(row.activo) === "1";
      return `<tr>
        <td title="${escapeHtml(row.numero_parte_original)}">${escapeHtml(row.numero_parte_original)}</td>
        <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
        <td title="${escapeHtml(row.tipo)}">${escapeHtml(row.tipo)}</td>
        <td>${String(row.sistema_existe) === "1" ? "Si" : "No"}</td>
        <td>${active ? "Si" : "No"}</td>
        <td>${escapeHtml(row.fecha_registro)}</td>
        <td>
          <button class="mat-invoice-btn small danger" type="button" data-alias-delete-id="${escapeHtml(row.id)}" ${active ? "" : "disabled"}>Desactivar</button>
        </td>
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

  async function uploadInvoice(event) {
    event.preventDefault();
    const form = el("mat-invoice-upload-form");
    const file = el("mat-invoice-upload-file")?.files?.[0];
    if (!form || !file) {
      setMessage("mat-invoice-upload-message", "Selecciona un archivo Excel.");
      return;
    }
    const payload = new FormData(form);
    setLoading(true);
    try {
      const data = await fetchJson("/api/material_admin/invoices/upload", {
        method: "POST",
        body: payload,
      });
      setMessage("mat-invoice-upload-message", `Invoice cargada: ${data.lineas} lineas, ${data.packing} packing.`, "success");
      form.reset();
      await loadInvoices();
      await loadDetail(data.invoice_id);
    } catch (err) {
      if (err.status === 409 && err.payload?.duplicado) {
        setMessage("mat-invoice-upload-message", `${err.payload.message || "Duplicado"} (${err.payload.motivo || ""})`);
      } else {
        setMessage("mat-invoice-upload-message", `Error al cargar: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }

  async function saveAlias(event) {
    event.preventDefault();
    const aliasPart = el("mat-invoice-alias-part")?.value.trim();
    const systemPart = el("mat-invoice-alias-system")?.value.trim();
    const type = el("mat-invoice-alias-type")?.value.trim();
    if (!aliasPart || !systemPart) {
      setMessage("mat-invoice-alias-message", "Número de parte original y parte sistema son requeridos.");
      return;
    }
    setLoading(true);
    try {
      await fetchJson("/api/material_admin/invoices/aliases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          numero_parte_original: aliasPart,
          numero_parte_sistema: systemPart,
          tipo: type,
        }),
      });
      setMessage("mat-invoice-alias-message", "Equivalente guardado.", "success");
      el("mat-invoice-alias-form")?.reset();
      await loadAliases();
    } catch (err) {
      setMessage("mat-invoice-alias-message", `Error al guardar equivalente: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function importAliases() {
    const file = el("mat-invoice-alias-import-file")?.files?.[0];
    const type = el("mat-invoice-alias-type")?.value.trim();
    if (!file) {
      setMessage("mat-invoice-alias-message", "Selecciona un Excel de equivalentes.");
      return;
    }
    const payload = new FormData();
    payload.append("file", file);
    if (type) payload.append("tipo", type);
    setLoading(true);
    try {
      const data = await fetchJson("/api/material_admin/invoices/aliases/import", {
        method: "POST",
        body: payload,
      });
      setMessage(
        "mat-invoice-alias-message",
        `Equivalentes importados: ${numberText(data.importados)}. Omitidos: ${numberText(data.omitidos)}. Sin parte sistema: ${numberText(data.omitidos_sistema || 0)}. Conflictos: ${numberText(data.omitidos_conflicto || 0)}.`,
        "success"
      );
      if (el("mat-invoice-alias-import-file")) el("mat-invoice-alias-import-file").value = "";
      await loadAliases();
    } catch (err) {
      setMessage("mat-invoice-alias-message", `Error al importar equivalentes: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function deactivateAlias(aliasId) {
    if (!aliasId) return;
    setLoading(true);
    try {
      await fetchJson(`/api/material_admin/invoices/aliases/${encodeURIComponent(aliasId)}`, {
        method: "DELETE",
      });
      setMessage("mat-invoice-alias-message", "Equivalente desactivado.", "success");
      await loadAliases();
    } catch (err) {
      setMessage("mat-invoice-alias-message", `Error al desactivar equivalente: ${err.message}`);
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

  function attachListeners() {
    if (document.body.dataset.materialInvoicesListenersAttached) return;

    document.body.addEventListener("submit", (event) => {
      if (event.target?.id === "mat-invoice-upload-form") {
        uploadInvoice(event);
        return;
      }
      if (event.target?.id === "mat-invoice-alias-form") {
        saveAlias(event);
      }
    });

    document.body.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

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
      if (target.closest("#mat-invoice-alias-refresh") || target.closest("#mat-invoice-alias-search-btn")) {
        event.preventDefault();
        loadAliases();
        return;
      }
      if (target.closest("#mat-invoice-alias-import-btn")) {
        event.preventDefault();
        importAliases();
        return;
      }
      const aliasDelete = target.closest("[data-alias-delete-id]");
      if (aliasDelete) {
        event.preventDefault();
        deactivateAlias(aliasDelete.getAttribute("data-alias-delete-id"));
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
      if (target.id === "mat-invoice-alias-include-inactive") {
        loadAliases();
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-invoice-search" && event.key === "Enter") {
        event.preventDefault();
        loadInvoices();
      }
      if (target.id === "mat-invoice-alias-search" && event.key === "Enter") {
        event.preventDefault();
        loadAliases();
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
    if (el("mat-invoice-detail")) el("mat-invoice-detail").hidden = true;
    if (el("mat-invoice-export")) el("mat-invoice-export").disabled = true;
    loadInvoices();
    loadAliases();
  };
})();
