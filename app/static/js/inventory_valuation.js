(function () {
  const STYLE_ID = "inventory-valuation-css";
  const STYLE_VERSION = "20260612d";
  const STYLE_HREF = `/static/css/inventory_valuation.css?v=${STYLE_VERSION}`;

  const state = {
    limit: 500,
    offset: 0,
    total: 0,
    lastPreview: null,
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

  function numberText(value, digits) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return n.toLocaleString("en-US", { maximumFractionDigits: digits ?? 4 });
  }

  function setMessage(message, type) {
    const box = el("inv-valuation-message");
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
    const loader = el("inv-valuation-loading");
    if (loader) loader.hidden = !active;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, { credentials: "same-origin", ...(options || {}) });
    const contentType = res.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await res.json() : { error: await res.text() };
    if (!res.ok || data.error || data.success === false) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  function params(includePaging) {
    const out = new URLSearchParams();
    const part = el("inv-valuation-part")?.value.trim();
    const code = el("inv-valuation-code")?.value.trim();
    const pallet = el("inv-valuation-pallet")?.value.trim();
    const source = el("inv-valuation-source")?.value;
    if (part) out.set("numero_parte", part);
    if (code) out.set("codigo_material_recibido", code);
    if (pallet) out.set("pallet_no", pallet);
    if (source) out.set("fuente_costo", source);
    if (el("inv-valuation-include-zero")?.checked) out.set("include_zero_stock", "1");
    if (includePaging) {
      state.limit = Number(el("inv-valuation-page-size")?.value || state.limit || 500);
      out.set("limit", String(state.limit));
      out.set("offset", String(state.offset));
    }
    return out;
  }

  async function loadSummary() {
    const data = await fetchJson(`/api/material_admin/inventory/valuation/summary?${params(false).toString()}`);
    renderSummary(data.records || []);
  }

  function renderSummary(rows) {
    const root = el("inv-valuation-summary");
    if (!root) return;
    if (!rows.length) {
      root.innerHTML = `<div class="inv-valuation-card"><strong>Sin registros</strong><span>0</span></div>`;
      return;
    }
    root.innerHTML = rows.map((row) => `<div class="inv-valuation-card">
      <strong>${escapeHtml(row.fuente_costo)} ${escapeHtml(row.moneda)}</strong>
      <span>${numberText(row.valor_total, 2)}</span>
      <small>${numberText(row.lotes, 0)} lotes | Stock ${numberText(row.stock_total, 2)}</small>
    </div>`).join("");
  }

  async function loadValuation(resetPage) {
    ensureModuleStyles();
    if (resetPage) state.offset = 0;
    setLoading(true);
    setMessage("");
    try {
      const [listData] = await Promise.all([
        fetchJson(`/api/material_admin/inventory/valuation?${params(true).toString()}`),
        loadSummary(),
      ]);
      state.total = Number(listData.total || 0);
      state.limit = Number(listData.limit || state.limit);
      state.offset = Number(listData.offset || state.offset);
      renderRows(listData.records || []);
      syncFooter(listData.records || []);
    } catch (err) {
      setMessage(`Error al cargar valorizacion: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function sourceBadge(value) {
    const text = String(value || "SIN_COSTO");
    return `<span class="inv-valuation-source ${escapeHtml(text)}">${escapeHtml(text)}</span>`;
  }

  function renderRows(rows) {
    const body = el("inv-valuation-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="13">No hay registros disponibles.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => `<tr>
      <td title="${escapeHtml(row.codigo_material_recibido)}">${escapeHtml(row.codigo_material_recibido)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td title="${escapeHtml(row.numero_lote)}">${escapeHtml(row.numero_lote)}</td>
      <td title="${escapeHtml(row.pallet_no_original)}">${escapeHtml(row.pallet_no)}</td>
      <td title="${escapeHtml(row.vendedor)}">${escapeHtml(row.vendedor)}</td>
      <td>${numberText(row.stock_actual, 4)}</td>
      <td>${escapeHtml(row.unidad_medida)}</td>
      <td>${numberText(row.costo_unitario, 4)}</td>
      <td>${escapeHtml(row.moneda)}</td>
      <td>${numberText(row.valor_total, 2)}</td>
      <td>${sourceBadge(row.fuente_costo)}</td>
      <td>${String(row.es_estimado) === "0" ? "No" : "Si"}</td>
      <td>${escapeHtml(row.numero_invoice || row.invoice_id || "")}</td>
      <td title="${escapeHtml(row.numero_transaccion)}">${escapeHtml(row.numero_transaccion || "")}</td>
    </tr>`).join("");
  }

  function syncFooter(rows) {
    const count = el("inv-valuation-count");
    if (count) {
      const start = state.total === 0 ? 0 : state.offset + 1;
      const end = Math.min(state.offset + rows.length, state.total);
      count.textContent = `Total Rows: ${state.total} (${start}-${end})`;
    }
    const page = el("inv-valuation-page-label");
    if (page) page.textContent = `Pagina ${Math.floor(state.offset / state.limit) + 1}`;
  }

  function closePreviewModal() {
    const modal = el("inv-valuation-preview-modal");
    if (modal) modal.hidden = true;
  }

  function openPreviewModal() {
    const modal = el("inv-valuation-preview-modal");
    if (modal) modal.hidden = false;
  }

  function renderPreviewStats(data) {
    const stats = el("inv-valuation-preview-stats");
    if (!stats) return;
    stats.innerHTML = [
      ["Inventario con stock", data.total_lotes],
      ["Se aplicarían", data.preview_total || data.asignables_control_material || 0],
      ["Ya tenían costo", data.ya_tenian_costo],
      ["Sin costo histórico", data.quedaron_sin_costo],
      ["Invoice no tocados", data.no_sobrescritos_invoice],
    ].map(([label, value]) => `
      <div class="inv-valuation-preview-stat">
        <strong>${escapeHtml(label)}</strong>
        <span>${numberText(value || 0, 0)}</span>
      </div>
    `).join("");
  }

  function renderPreviewRows(rows) {
    const body = el("inv-valuation-preview-body");
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9">No hay costos por aplicar.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => `<tr>
      <td title="${escapeHtml(row.codigo_material_recibido)}">${escapeHtml(row.codigo_material_recibido)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td title="${escapeHtml(row.numero_lote)}">${escapeHtml(row.numero_lote)}</td>
      <td title="${escapeHtml(row.pallet_no)}">${escapeHtml(row.pallet_no)}</td>
      <td title="${escapeHtml(row.vendedor)}">${escapeHtml(row.vendedor)}</td>
      <td>${numberText(row.stock_actual, 4)} ${escapeHtml(row.unidad_medida || "")}</td>
      <td>${numberText(row.costo_unitario, 4)}</td>
      <td>${escapeHtml(row.moneda)}</td>
      <td>${numberText(row.valor_total, 2)}</td>
    </tr>`).join("");
  }

  function renderPreviewModal(data) {
    state.lastPreview = data;
    renderPreviewStats(data);
    renderPreviewRows(data.preview_records || []);

    const note = el("inv-valuation-preview-note");
    if (note) {
      const shown = (data.preview_records || []).length;
      const total = Number(data.preview_total || data.asignables_control_material || 0);
      note.hidden = false;
      note.textContent = data.preview_truncated
        ? `Mostrando ${numberText(shown, 0)} de ${numberText(total, 0)} cambios. Aplica por bloques para no cargar la base de datos.`
        : `Mostrando todos los ${numberText(total, 0)} cambios que se harán.`;
    }

    const applyButton = el("inv-valuation-preview-apply");
    if (applyButton) applyButton.disabled = Number(data.preview_total || 0) <= 0;
    openPreviewModal();
  }

  async function runBackfill(dryRun) {
    setLoading(true);
    setMessage("");
    try {
      const batchSize = 500;
      const previewLimit = 5000;
      const data = await fetchJson(`/api/material_admin/inventory/valuation/backfill?dry_run=${dryRun ? "1" : "0"}&batch_size=${batchSize}&preview_limit=${previewLimit}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const pendingText = Number(data.pendientes_aplicables || 0) > 0
        ? ` Pendientes aplicables: ${numberText(data.pendientes_aplicables, 0)}.`
        : "";
      setMessage(
        `${dryRun ? "Simulación de costos" : "Aplicación de costos"}: inventario con stock ${data.total_lotes}, procesados ${numberText(data.procesados_lotes || 0, 0)}, asignados ${data.asignados_control_material}, sin costo ${data.quedaron_sin_costo}, invoice no tocados ${data.no_sobrescritos_invoice}.${pendingText}`,
        "success"
      );
      if (dryRun) {
        renderPreviewModal(data);
      } else {
        closePreviewModal();
        await loadValuation(true);
      }
    } catch (err) {
      setMessage(`Error en costos: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function exportValuation() {
    window.location.href = `/api/material_admin/inventory/valuation/export?${params(false).toString()}`;
  }

  function attachListeners() {
    if (document.body.dataset.inventoryValuationListenersAttached) return;

    document.body.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      if (target.closest("#inv-valuation-refresh") || target.closest("#inv-valuation-search")) {
        event.preventDefault();
        loadValuation(true);
        return;
      }
      if (target.closest("#inv-valuation-export")) {
        event.preventDefault();
        exportValuation();
        return;
      }
      if (target.closest("#inv-valuation-backfill-dry")) {
        event.preventDefault();
        runBackfill(true);
        return;
      }
      if (target.closest("#inv-valuation-backfill-apply")) {
        event.preventDefault();
        runBackfill(false);
        return;
      }
      if (target.closest("#inv-valuation-preview-close") || target.closest("#inv-valuation-preview-cancel")) {
        event.preventDefault();
        closePreviewModal();
        return;
      }
      if (target.closest("#inv-valuation-preview-apply")) {
        event.preventDefault();
        runBackfill(false);
        return;
      }
      if (target.id === "inv-valuation-preview-modal") {
        event.preventDefault();
        closePreviewModal();
        return;
      }
      if (target.closest("#inv-valuation-prev")) {
        event.preventDefault();
        state.offset = Math.max(0, state.offset - state.limit);
        loadValuation(false);
        return;
      }
      if (target.closest("#inv-valuation-next")) {
        event.preventDefault();
        const next = state.offset + state.limit;
        if (next < state.total) {
          state.offset = next;
          loadValuation(false);
        }
      }
    });

    document.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "inv-valuation-source" || target.id === "inv-valuation-include-zero" || target.id === "inv-valuation-page-size") {
        loadValuation(true);
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest("#inv-valuation-page") && !target.closest("#inv-valuation-preview-modal") && event.key === "Enter") {
        event.preventDefault();
        loadValuation(true);
        return;
      }
      if (event.key === "Escape") {
        closePreviewModal();
      }
    });

    document.body.dataset.inventoryValuationListenersAttached = "1";
  }

  window.initInventoryValuation = function () {
    ensureModuleStyles();
    attachListeners();
    state.limit = Number(el("inv-valuation-page-size")?.value || 500);
    state.offset = 0;
    state.total = 0;
    loadValuation(true);
  };
})();
